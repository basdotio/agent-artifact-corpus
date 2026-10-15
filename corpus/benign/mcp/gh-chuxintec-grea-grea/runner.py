"""Owned process groups, bounded capture and immutable attempt receipts."""
import json,os,signal,subprocess,threading,time
from pathlib import Path
from .common import GreaError,hash_file,write_new,now,digest,implementation_identity
from .registry import tool,command

def terminate(proc):
    try:
        if os.name=='posix':os.killpg(proc.pid,signal.SIGTERM)
        elif proc.poll() is None:proc.terminate()
    except ProcessLookupError:pass
    try:proc.wait(timeout=1)
    except subprocess.TimeoutExpired:pass
    # Also settle inherited pipes held by descendants in our own POSIX group.
    try:
        if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
        elif proc.poll() is None:proc.kill()
    except ProcessLookupError:pass
    try:proc.wait(timeout=1)
    except subprocess.TimeoutExpired:pass

def execute(tool_id,arguments,run_dir,timeout_seconds=120,max_output_bytes=16777216,max_inline_bytes=32768,cancel=None,probe=False,working_directory=None):
    entry=tool(tool_id);argv=command(entry,probe=probe)+arguments;out=Path(run_dir).expanduser()
    if out.exists() or out.is_symlink():raise GreaError('OUTPUT_EXISTS','Use a new run directory for every attempt.')
    if not out.parent.is_dir():raise GreaError('INVALID_OUTPUT','Run directory parent must already exist.')
    cwd = Path(working_directory).expanduser() if working_directory is not None else None
    if cwd is not None and (not cwd.is_absolute() or not cwd.is_dir()):
        raise GreaError('INVALID_WORKING_DIRECTORY','working_directory must be an existing absolute directory.')
    bindings=[]
    for value in argv[:2]:
        path=Path(value)
        if path.is_file():
            path=path.resolve();size=path.stat().st_size
            bindings.append(hash_file(path) if size<=1048576 else {'path':str(path),'bytes':size,'sha256':None,'identity_level':'metadata_only'})
    shared=Path(argv[1]).parent/'_artifact_common.py' if len(argv)>1 else None
    if shared and shared.is_file():bindings.append(hash_file(shared))
    implementation=implementation_identity()
    limits={'timeout_seconds':timeout_seconds,'max_output_bytes':max_output_bytes,'max_inline_bytes':max_inline_bytes}
    out=out.parent.resolve()/out.name;out.mkdir();start=time.monotonic();began=now()
    count=0;lock=threading.Lock();overflow=threading.Event();threads=[];reason=None
    try:
        proc=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(cwd.resolve() if cwd else out),start_new_session=os.name=='posix')
    except OSError as e:
        write_new(out/'run.json',{'schema_version':1,'tool_id':tool_id,'status':'launch_failed','error':str(e),'started_at':began})
        raise GreaError('LAUNCH_FAILED',str(e),details={'run_dir':str(out)})
    def pump(pipe,path):
        nonlocal count
        with path.open('xb',buffering=0) as f:
            while True:
                chunk=pipe.read(65536)
                if not chunk:break
                with lock:
                    remaining=max(0,max_output_bytes-count);take=chunk[:remaining];count+=len(take)
                    if len(take)!=len(chunk):overflow.set()
                if take:f.write(take)
        pipe.close()
    for pipe,name in [(proc.stdout,'stdout.log'),(proc.stderr,'stderr.log')]:
        thread=threading.Thread(target=pump,args=(pipe,out/name),daemon=True);thread.start();threads.append(thread)
    try:
        while proc.poll() is None or any(t.is_alive() for t in threads):
            if cancel is not None and cancel.is_set():reason='CANCELLED';break
            if overflow.is_set():reason='OUTPUT_LIMIT';break
            if time.monotonic()-start>timeout_seconds:reason='TIMEOUT';break
            time.sleep(.02)
    except BaseException:
        reason='CANCELLED'
    finally:
        if reason:terminate(proc)
        for thread in threads:thread.join(timeout=2)
        if any(t.is_alive() for t in threads):reason=reason or 'CLEANUP_INCOMPLETE'
    if overflow.is_set():reason=reason or 'OUTPUT_LIMIT'
    code=proc.poll()
    logs=[];previews={};inline_truncated=False
    for name in ('stdout','stderr'):
        path=out/f'{name}.log';info=hash_file(path);logs.append(dict(info,kind='process_log',stream=name))
        with path.open('rb') as f:raw=f.read(max_inline_bytes+1)
        if len(raw)>max_inline_bytes:inline_truncated=True
        previews[name]=raw[:max_inline_bytes].decode('utf-8',errors='replace')
    accepted=(entry.get('execution') or {}).get('finding_exit_codes',[])
    status='error' if reason or code not in [0,*accepted] else ('partial' if code!=0 or inline_truncated else 'ok')
    parsed=None
    if not inline_truncated and previews['stdout'].strip():
        try:parsed=json.loads(previews['stdout'],parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-JSON constant '+value)))
        except ValueError:pass
    result={'tool_id':tool_id,'provider_contract_sha256':digest(entry),'implementation':implementation,'entrypoint_identities':bindings,'identity_observed_at':'before_launch','limits':limits,'cleanup_attempted':bool(reason),'command':argv,'working_directory':str(cwd.resolve() if cwd else out),'exit_code':code,'status':status,'reason':reason,'run_dir':str(out),'started_at':began,'finished_at':now(),'duration_seconds':round(time.monotonic()-start,3),'captured_bytes':count,'capture_complete':not reason,'inline_truncated':inline_truncated,'stdout':previews['stdout'],'stderr':previews['stderr'],'parsed_stdout':parsed,'process_group':proc.pid if os.name=='posix' else None,'cleanup_scope':'owned_process_group' if os.name=='posix' else 'owned_process_only'}
    write_new(out/'run.json',result)
    logs.append(dict(hash_file(out/'run.json'),kind='run_receipt'))
    error=None
    if status=='error':error=GreaError(reason or 'TOOL_FAILED','Registered tool did not complete successfully.',details={'tool_id':tool_id,'exit_code':code,'run_dir':str(out)},next_action='Inspect the preserved receipt/logs and current process state before retrying.')
    return result,logs,error
