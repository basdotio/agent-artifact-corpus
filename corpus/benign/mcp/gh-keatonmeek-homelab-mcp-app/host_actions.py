"""Runs as the broker OS account; host namespaces only in explicit root mode. JSON stdin only; never logs command/file contents."""
import json
import os
import pwd
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import time
import uuid


def absolute(value):
    if not isinstance(value,str) or not os.path.isabs(value) or '\x00' in value:
        raise ValueError('absolute_path_required')
    path = Path(value)
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError('symlink_parent_refused')
    return path


def backup(path):
    target=path.with_name('.'+path.name+'.homelab-backup-'+str(int(time.time()))+'-'+uuid.uuid4().hex[:8])
    # Backups can contain secrets: force private permissions after copy.
    shutil.copy2(path,target,follow_symlinks=False)
    os.chown(target,path.stat().st_uid,path.stat().st_gid)
    os.chmod(target,0o600)
    return str(target)


def operate(request):
    method=request['method'];p=request['params']
    if method=='command':
        cwd=absolute(p['cwd']);os.chdir(cwd)
        env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':pwd.getpwuid(os.getuid()).pw_dir,'LANG':'C.UTF-8'}
        os.execve('/bin/bash',['bash','--noprofile','--norc','-c',p['command']],env)
    path=absolute(p['path'])
    if method=='file_read':
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise ValueError('regular_file_required')
            f.seek(p.get('offset',0));limit=p.get('limit',65536);raw=f.read(limit+1)
        return {'path':str(path),'offset':p.get('offset',0),'bytes_read':min(limit,len(raw)),
            'truncated':len(raw)>limit,'text':raw[:limit].decode('utf-8',errors='replace')}
    if method=='file_write':
        if path.is_symlink():raise ValueError('symlink_target_refused')
        if path.exists() and not path.is_file():raise ValueError('regular_file_required')
        if p.get('create_parents',False):path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        old=path.stat() if path.exists() else None
        saved=backup(path) if old else None
        fd,temp=tempfile.mkstemp(prefix='.homelab-write-',dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(p['text'].encode('utf-8'));f.flush();os.fsync(f.fileno())
                os.fchmod(f.fileno(),stat.S_IMODE(old.st_mode) if old else p.get('mode',0o600))
                if old:os.fchown(f.fileno(),old.st_uid,old.st_gid)
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        return {'path':str(path),'bytes_written':len(p['text'].encode()),'backup':saved,'atomic':True}
    if method=='file_move':
        destination=absolute(p['destination'])
        if path.is_symlink() or destination.is_symlink():raise ValueError('symlink_move_refused')
        if not path.exists():raise FileNotFoundError()
        saved=None
        if destination.exists():
            if not p.get('overwrite',False):raise FileExistsError()
            if not destination.is_file() or not path.is_file():raise ValueError('directory_overwrite_refused')
            saved=backup(destination)
        if not path.is_file() and not path.is_dir():raise ValueError('regular_file_or_directory_required')
        if path == destination:raise ValueError('same_path_refused')
        same_device=path.stat().st_dev==destination.parent.stat().st_dev
        if same_device:os.replace(path,destination)
        else:
            if destination.exists():raise ValueError('cross_device_overwrite_refused')
            shutil.move(str(path),str(destination))
        return {'source':str(path),'destination':str(destination),'backup':saved,'atomic':same_device}
    raise ValueError('unknown_operation')


if __name__=='__main__':
    try:
        request=json.loads(sys.stdin.buffer.readline(1048577))
        result=operate(request)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'error':type(e).__name__,'errno':getattr(e,'errno',None)}))
        sys.exit(1)
