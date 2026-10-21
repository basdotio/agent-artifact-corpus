#!/usr/bin/env python3
"""Prepare, archive, verify and restore the self-contained 参考游戏 Unity reference source."""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
from grea.host.paths import Path
import re
import stat
import unicodedata
import zipfile

from grea.common import package_root
ROOT = package_root()
SOURCE = ROOT / 'tests/unity/reference-project'
FRAMEWORK = ROOT / 'tools/unity/framework/packages'
MANIFEST = 'distribution-manifest.json'
MAX_BYTES = 64 * 1024 * 1024


def sha(data): return hashlib.sha256(data).hexdigest()


def portable(name):
    parts = name.split('/')
    if not parts or any(not p or p in ('.','..') or re.search(r'[\\<>:"|?*\x00-\x1f]',p) or p[-1:] in (' ','.') or
                        p.split('.')[0].lower() in {'con','prn','aux','nul',*(f'com{i}' for i in range(1,10)),*(f'lpt{i}' for i in range(1,10))} for p in parts):
        raise ValueError('Nonportable archive path')
    return name


def new_output(path):
    path = Path(path).expanduser().absolute()
    if path.exists() or any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('Output must be a new path with no symlink components')
    return path


def source_files():
    files = {}
    lock=json.loads((SOURCE/'framework.lock.json').read_text(encoding='utf-8'))['packages']
    if set(lock) != {p.name for p in FRAMEWORK.iterdir() if p.is_dir()}:
        raise ValueError('Framework package inventory differs from reference lock')
    for name,identity in lock.items():
        package=FRAMEWORK/portable(name)
        if json.loads((package/'package.json').read_text(encoding='utf-8'))['version'] != identity['version']:
            raise ValueError('Framework version differs from reference lock: '+name)
        hashes={p.relative_to(package).as_posix():sha(p.read_bytes()) for p in sorted(package.rglob('*')) if p.is_file() and not p.is_symlink()}
        if sha(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode())!=identity['treeSha256']:
            raise ValueError('Framework differs from reference lock: '+name)
    for base, prefix in ((SOURCE,''),(FRAMEWORK,'Packages/')):
        for path in sorted(base.rglob('*')):
            if path.is_symlink(): raise ValueError('Symlinks cannot be distributed')
            if path.is_file():
                if set(path.relative_to(base).parts) & {'Library','Temp','Logs','Build','Obj','UserSettings','__pycache__','.private','.DS_Store'}:
                    raise ValueError('Generated or private file in source distribution')
                name=portable(prefix+path.relative_to(base).as_posix())
                if name in files: raise ValueError('Duplicate source path')
                files[name]=path.read_bytes()
    files['LICENSE.md']=(ROOT/'LICENSE').read_bytes()
    files['.gitignore']=b'/Library/\n/Temp/\n/Logs/\n/Obj/\n/UserSettings/\n/Build/\n*.csproj\n*.sln\n.DS_Store\n'
    if sum(map(len,files.values()))>MAX_BYTES: raise ValueError('Source budget exceeded')
    manifest={'schemaVersion':1,'product':'grea-signal-garden','version':'1.0.2-candidate','editor':'6000.6.2f1','target':'macOS-arm64-Mono',
              'files':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in sorted(files.items())}}
    files[MANIFEST]=(json.dumps(manifest,indent=2)+'\n').encode()
    return files


def write_project(output, files):
    output=new_output(output);output.mkdir(parents=True)
    for name,data in files.items():
        target=output/portable(name);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
    return {'output':str(output),'files':len(files),'unityExecuted':False}


def archive(output):
    output=new_output(output);files=source_files();output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,10,13,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    checksum=Path(str(output)+'.sha256')
    with checksum.open('x') as f:f.write(sha(output.read_bytes())+'  '+output.name+'\n')
    return {'archive':str(output),'sha256':sha(output.read_bytes()),'files':len(files)}


def read_archive(archive_path):
    files={};seen=set();total=0
    with zipfile.ZipFile(archive_path) as z:
        if len(z.infolist())>5000:raise ValueError('Too many archive entries')
        for info in z.infolist():
            name=portable(info.filename);key=unicodedata.normalize('NFC',name).casefold()
            if key in seen:raise ValueError('Duplicate or case/Unicode collision')
            seen.add(key)
            mode=info.external_attr>>16
            if info.is_dir() or (stat.S_IFMT(mode) not in (0,stat.S_IFREG)):raise ValueError('Only regular files accepted')
            total+=info.file_size
            if total>MAX_BYTES:raise ValueError('Archive byte budget exceeded')
            data=z.read(info)
            if len(data)!=info.file_size:raise ValueError('Truncated entry')
            files[name]=data
    manifest=json.loads(files[MANIFEST])
    if manifest.get('schemaVersion')!=1 or manifest.get('product')!='grea-signal-garden':raise ValueError('Unknown distribution')
    if set(files)-{MANIFEST}!=set(manifest['files']):raise ValueError('File inventory differs from manifest')
    for name,identity in manifest['files'].items():
        if len(files[name])!=identity['bytes'] or sha(files[name])!=identity['sha256']:raise ValueError('Content hash mismatch: '+name)
    return files


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('prepare','archive'):
        p=sub.add_parser(name);p.add_argument('--output',required=True)
    for name in ('verify','restore'):
        p=sub.add_parser(name);p.add_argument('--archive',required=True)
        if name=='restore':p.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='prepare':result=write_project(args.output,source_files())
    elif args.command=='archive':result=archive(args.output)
    else:
        files=read_archive(args.archive)
        result=write_project(args.output,files) if args.command=='restore' else {'verified':True,'files':len(files),'sha256':sha(Path(args.archive).read_bytes())}
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
