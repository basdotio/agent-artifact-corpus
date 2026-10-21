"""Artifact identity and bounded inventories. Static bytes do not prove runtime behavior."""
import os,hashlib
from grea.host.paths import Path
from .common import GreaError,hash_file,digest

def format_of(path):
    with path.open('rb') as f: magic=f.read(8)
    if magic.startswith(b'\x7fELF'):return 'elf'
    if magic.startswith(b'MZ'):return 'pe'
    if magic.startswith(b'PK'):return 'archive'
    if magic[:4] in (b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe'):return 'mach-o'
    if magic.startswith(b'UnityFS'):return 'unity-bundle'
    return 'file'

def inspect_target(path,max_files=1000,max_bytes=268435456):
    path=Path(path).expanduser()
    if path.is_symlink() or not path.exists():raise GreaError('INVALID_TARGET','Target is missing or is a symlink.')
    path=path.resolve()
    if path.is_file():return {'target':dict(hash_file(path,max_bytes),format=format_of(path)), 'coverage':'complete','files_examined':1,'limitations':['Static artifact identity only; no application execution.']}
    if not path.is_dir():raise GreaError('INVALID_TARGET','Target must be a regular file or directory.')
    files=[];skipped=[];used=0;complete=True;stop=False
    for base,dirs,names in os.walk(path,followlinks=False):
        dirs.sort();names.sort()
        for name in list(dirs):
            p=Path(base)/name
            if p.is_symlink():dirs.remove(name);skipped.append(str(p.relative_to(path)));complete=False
        for name in names:
            p=Path(base)/name
            if p.is_symlink() or not p.is_file():skipped.append(str(p.relative_to(path)));complete=False;continue
            if len(files)>=max_files or used+p.stat().st_size>max_bytes:complete=False;stop=True;break
            info=hash_file(p,max_bytes-used);used+=info['bytes'];info['path']=str(p.relative_to(path));files.append(info)
        if stop:break
    return {'target':{'path':str(path),'format':'directory','sha256':digest(files) if complete else None},'observed_inventory_sha256':digest(files),'coverage':'complete' if complete else 'partial','files_examined':len(files),'bytes_examined':used,'files':files,'skipped':skipped,'limitations':['Directory digest is a sorted path/content manifest, not an archive digest.','Unknown/unexamined files are not absence.']}
