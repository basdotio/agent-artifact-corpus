"""Mechanical inspection of SOAR's two-file exports; never extract or execute."""
import io
import json
from pathlib import PurePosixPath
import tarfile

from .client import reject_non_json_constant

MAX_BUNDLE_BYTES = 32 * 1024 * 1024


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key in Playbook bundle')
        value[key] = item
    return value


def read_bundle(raw):
    """Accept a single flat Python/JSON pair, preserving every member byte.

    Other layouts are explicitly unsupported, not silently projected. The size
    bound applies to both compressed input and total uncompressed member bytes.
    """
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError('Playbook bundle exceeds the declared 32 MiB limit')
    files = {}; total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                if (not member.isfile() or member.name != path.name or '\\' in member.name
                        or path.suffix not in ('.py', '.json') or member.name in files or len(files) >= 2):
                    raise ValueError('unsafe, duplicate or unsupported Playbook archive member')
                total += member.size
                if member.size < 0 or total > MAX_BUNDLE_BYTES:
                    raise ValueError('uncompressed Playbook bundle exceeds the declared 32 MiB limit')
                files[member.name] = archive.extractfile(member).read()
                if len(files[member.name]) != member.size:
                    raise ValueError('incomplete Playbook archive member')
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise ValueError('invalid gzip Playbook archive') from exc
    names = {PurePosixPath(name).stem for name in files}
    if len(files) != 2 or len(names) != 1:
        raise ValueError('expected one matching Python/JSON Playbook pair')
    name = names.pop()
    try:
        document = json.loads(files[name + '.json'].decode('utf-8'),
                              object_pairs_hook=unique_object, parse_constant=reject_non_json_constant)
        files[name + '.py'].decode('utf-8')
    except (KeyError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError('Playbook members must be UTF-8 Python and valid JSON') from exc
    if (not isinstance(document, dict) or not isinstance(document.get('coa'), dict)
            or not isinstance(document['coa'].get('data'), dict)
            or document['coa']['data'].get('name') != name):
        raise ValueError('Playbook metadata name must equal its archive member names')
    return name, files, document


def validate_import(raw, namespace):
    name, files, document = read_bundle(raw)
    from .operations import identifier
    prefix = namespace + '_'
    if not name.startswith(prefix):
        raise ValueError('Playbook name must be within the selected namespace')
    identifier(name[len(prefix):])
    for layer in (document, document['coa'], document['coa']['data']):
        if 'active' in layer and layer['active'] is not False:
            raise ValueError('import cannot request an active Playbook')
        if 'name' in layer and layer['name'] != name:
            raise ValueError('conflicting Playbook metadata names')
    return name
