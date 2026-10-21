"""Small shared identities and explicit errors; no process or client policy here."""
import hashlib,json,os,uuid,ctypes
from grea.host.paths import Path
from datetime import datetime,timezone
from . import __version__

class GreaError(Exception):
    def __init__(self, code, message, *, next_action='Correct the request and retry.', details=None, retryable=False):
        super().__init__(message); self.code=code; self.next_action=next_action; self.details=details or {}; self.retryable=retryable
    def as_dict(self): return {'code':self.code,'message':str(self),'next_action':self.next_action,'details':self.details,'retryable':self.retryable}

def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value): return hashlib.sha256(canonical(value)).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def package_root(): return Path(os.environ.get('GREA_HOME', Path(__file__).resolve().parents[2])).resolve()
def workspace_root(): return package_root().parent

def hash_file(path, max_bytes=None):
    path=Path(path).expanduser()
    if path.is_symlink() or not path.is_file(): raise GreaError('INVALID_TARGET','Expected a regular file, not a symlink.',details={'path':str(path)})
    path=path.resolve();before=path.stat()
    if max_bytes is not None and before.st_size>max_bytes:raise GreaError('RESOURCE_LIMIT','File exceeds requested byte budget.',details={'bytes':before.st_size,'max_bytes':max_bytes},next_action='Increase max_bytes explicitly or select a smaller artifact.')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise GreaError('STALE_INPUT','Input changed while hashing.',details={'path':str(path)})
    return {'path':str(path),'sha256':h.hexdigest(),'bytes':after.st_size}

def write_new(path,value):
    path=Path(path)
    if path.is_symlink():raise GreaError('OUTPUT_EXISTS','Output is a symlink.')
    try:
        with path.open('x',encoding='utf-8') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    except FileExistsError:raise GreaError('OUTPUT_EXISTS','Output already exists; evidence is never overwritten.',details={'path':str(path)})

def envelope(operation,result=None,*,status='ok',evidence=None,limitations=None,limits=None,error=None,run_id=None):
    return {'schema_version':1,'product':'grea','version':__version__,'operation':operation,'run_id':run_id or uuid.uuid4().hex,'status':status,'result':result,'evidence':evidence or [],'limitations':limitations or [],'limits':limits or {},'error':error.as_dict() if error else None}

def implementation_identity():
    root=Path(__file__).resolve().parent
    hashes={p.relative_to(root).as_posix():hash_file(p)['sha256'] for p in sorted(root.rglob('*.py'))}
    return {'version':__version__,'core_sha256':digest(hashes),'files':len(hashes)}


from .host.files import publish_directory
