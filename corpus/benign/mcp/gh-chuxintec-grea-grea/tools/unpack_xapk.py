"""Bounded APK/XAPK extraction with explicit scope and complete entry identities."""
import argparse
import hashlib
import json
from grea.host.paths import Path
import shutil
import stat
import sys
import tempfile
import zipfile

from grea.common import GreaError, hash_file, publish_directory
from grea.data_io import encode
from grea.safe_paths import disjoint, relative_name, unique_paths


def members(archive, max_files, max_bytes):
    entries = archive.infolist()
    files = []
    total = 0
    for item in entries:
        name = item.filename.rstrip('/')
        if not name:
            raise ValueError('Empty archive entry name')
        relative_name(name)
        kind = stat.S_IFMT(item.external_attr >> 16)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or item.flag_bits & 1:
            raise ValueError('Linked, special or encrypted archive entry')
        if not item.is_dir():
            files.append(item)
            total += item.file_size
    unique_paths([item.filename for item in files])
    if len(files) > max_files or total > max_bytes:
        raise ValueError('Archive entry or expanded-byte budget exceeded')
    return files


def stream_entry(archive, item, target=None):
    checksum = hashlib.sha256()
    size = 0
    output = None
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        output = target.open('xb')
    try:
        with archive.open(item) as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > item.file_size:
                    raise ValueError('Entry exceeds its declared size')
                checksum.update(chunk)
                if output:
                    output.write(chunk)
    finally:
        if output:
            output.close()
    if size != item.file_size:
        raise ValueError('Truncated archive entry')
    # ZipFile validates CRC when the stream reaches EOF.
    return dict(bytes=size, sha256=checksum.hexdigest(), crc32=f'{item.CRC:08x}')


def unpack(source, output, scope='assets', max_files=100000, max_bytes=16 * 1024**3):
    if scope not in ('assets', 'all-entries') or max_files < 1 or max_bytes < 1:
        raise ValueError('Explicit supported scope and positive budgets required')
    source = Path(source)
    source_identity = hash_file(source)
    output = disjoint(output, source)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output must be new or empty; earlier evidence is preserved')
    with zipfile.ZipFile(source) as outer:
        outer_files = members(outer, max_files, max_bytes)
        direct = any(item.filename == 'AndroidManifest.xml' for item in outer_files)
        apk_names = [item.filename for item in outer_files if item.filename.lower().endswith('.apk')]
        if not direct and not apk_names:
            raise ValueError('No APK entries or Android manifest; input is not a supported APK/XAPK')
        output.parent.mkdir(parents=True, exist_ok=True)
        from grea.host.files import private_directory
        stage = private_directory(output.parent,'.grea-unpack-')
        try:
            reference = stage / 'Reference'
            reference.mkdir()
            if direct:
                apk_name = 'source.apk'
                shutil.copyfile(source, reference / apk_name)
                apk_names = [apk_name]
                outer_bytes = source.stat().st_size
                outer_count = 1
            else:
                outer_bytes = sum(item.file_size for item in outer_files)
                outer_count = len(outer_files)
                for item in outer_files:
                    stream_entry(outer, item, reference / item.filename)
            entries = []
            analysis = stage / 'Analysis'
            analysis.mkdir()
            for apk_name in apk_names:
                apk = reference / apk_name
                stem = Path(apk_name).with_suffix('')
                with zipfile.ZipFile(apk) as archive:
                    items = members(archive, max_files - outer_count - len(entries), max_bytes - outer_bytes - sum(row['bytes'] for row in entries))
                    if not any(item.filename == 'AndroidManifest.xml' for item in items):
                        raise ValueError('Nested APK lacks AndroidManifest.xml: ' + apk_name)
                    for item in items:
                        selected = scope == 'all-entries' or item.filename.startswith('assets/') or item.filename.endswith('libil2cpp.so')
                        relative = Path('Analysis/unpacked') / stem / item.filename
                        detail = stream_entry(archive, item, stage / relative if selected else None)
                        entries.append(dict(apk=apk_name, entry=item.filename, status='selected' if selected else 'skipped',
                                            output=relative.as_posix() if selected else None, **detail))
                    listing = analysis / stem.parent / (stem.name + '-files.txt')
                    listing.parent.mkdir(parents=True, exist_ok=True)
                    with listing.open('x') as stream:
                        stream.write('\n'.join(item.filename for item in items))
            if hash_file(source)['sha256'] != source_identity['sha256']:
                raise ValueError('Original input changed during extraction')
            report = dict(schema_version=2, scope=scope, container_format='apk' if direct else 'xapk',
                          source=source_identity, apk_count=len(apk_names), entries=entries,
                          selected=sum(row['status'] == 'selected' for row in entries),
                          skipped=sum(row['status'] == 'skipped' for row in entries), failed=0,
                          game_recovery_proven=False,
                          limits=['All supplied APK entries are CRC/size/hash verified; skipped entries remain in preserved APKs.',
                                  'No application execution, code recovery, server completeness or game equivalence.'])
            (analysis / 'source.json').write_bytes(encode(source_identity))
            (analysis / 'apk-entry-manifest.json').write_bytes(encode(report))
            if output.exists():
                output.rmdir()  # Succeeds only if the explicitly allowed directory is still empty.
            publish_directory(stage, output)
            return report
        except BaseException as error:
            (stage / 'extraction-failure.json').write_bytes(encode(dict(status='incomplete', error=type(error).__name__, message=str(error), source=source_identity)))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scope', choices=('assets', 'all-entries'), default='assets')
    parser.add_argument('--max-files', type=int, default=100000)
    parser.add_argument('--max-bytes', type=int, default=16 * 1024**3)
    args = parser.parse_args()
    try:
        report = unpack(args.source, args.output, args.scope, args.max_files, args.max_bytes)
        print(json.dumps({key: report[key] for key in ('scope','apk_count','selected','skipped','failed')}))
        return 0
    except (OSError, ValueError, GreaError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
