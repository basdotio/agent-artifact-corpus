from pathlib import Path
import threading,uuid,shutil,json
from fastapi import FastAPI,UploadFile,File,Form,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from pipeline import run
ROOT=Path(__file__).resolve().parent
RUNS=ROOT/'runs';RUNS.mkdir(exist_ok=True)
app=FastAPI();jobs={}
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost'])

@app.middleware('http')
async def same_origin_mutations(request,call_next):
    if request.method not in ['GET','HEAD','OPTIONS']:
        origin=request.headers.get('origin')
        expected=f"{request.url.scheme}://{request.headers.get('host','')}"
        if (origin is not None and origin!=expected) or request.headers.get('sec-fetch-site')=='cross-site':
            return JSONResponse({'detail':'Cross-origin requests cannot start or change local jobs.'},status_code=403)
    return await call_next(request)

@app.get('/')
def index():return FileResponse(ROOT/'static/index.html')
@app.post('/jobs')
def create(video:UploadFile=File(...),prompt:str=Form('person'),provider:str=Form('replicate'),mode:str=Form('depth')):
    if mode not in ['depth','face_mesh','depth_mesh']:raise HTTPException(400,'Unknown workflow mode')
    if provider not in ['huggingface','replicate','replicate-chenxwh']:raise HTTPException(400,'Unknown provider')
    ident=uuid.uuid4().hex;folder=RUNS/ident;folder.mkdir();src=folder/'upload.mp4'
    with src.open('wb') as out:shutil.copyfileobj(video.file,out)
    jobs[ident]={'state':'running','status':'Starting','id':ident}
    def work():
        try:
            if mode=='face_mesh':
                from face_mesh import run as run_mesh
                run_mesh(src,folder,lambda s:jobs[ident].update(status=s))
            elif mode=='depth_mesh':
                from face_mesh import run_depth
                run_depth(src,folder,prompt,provider,lambda s:jobs[ident].update(status=s))
            else:run(src,folder,prompt,provider,lambda s:jobs[ident].update(status=s))
            jobs[ident].update(state='done',status='Preparation complete · input review required')
            (folder/'status.json').write_text(json.dumps(jobs[ident]))
        except Exception as e:
            jobs[ident].update(state='error',status=str(e))
            (folder/'status.json').write_text(json.dumps(jobs[ident]))
    threading.Thread(target=work,daemon=True).start();return jobs[ident]
@app.get('/jobs/{ident}')
def get(ident:str):
    if ident not in jobs:
        if len(ident)==32 and all(c in '0123456789abcdef' for c in ident) and (RUNS/ident/'status.json').exists():return json.loads((RUNS/ident/'status.json').read_text())
        raise HTTPException(404)
    return jobs[ident]
@app.post('/jobs/{ident}/seedance')
def seedance(ident:str,prompt:str=Form(...),sirio:UploadFile=File(...),tein:UploadFile|None=File(None)):
    if len(ident)!=32 or not all(c in '0123456789abcdef' for c in ident):raise HTTPException(404)
    folder=RUNS/ident
    if not (folder/'audio-manifest.json').exists():raise HTTPException(400,'Audio separation must complete first.')
    from mask_review import require_approved
    try:require_approved(folder)
    except ValueError as e:raise HTTPException(409,str(e))
    paths=[]
    references=folder/'references'/uuid.uuid4().hex
    references.mkdir(parents=True)
    from preflight import inspect_reference
    for name,upload in [('sirio-reference',sirio),('tein-reference',tein)]:
        if upload is None:
            paths.append(None)
            continue
        suffix=Path(upload.filename or '').suffix.lower()
        if suffix not in (['.png','.jpg','.jpeg','.webp','.mp4','.mov','.webm'] if name=='sirio-reference' else ['.png','.jpg','.jpeg','.webp']):raise HTTPException(400,'Use an image or a Sirio reference video.')
        path=references/(name+suffix)
        with path.open('wb') as f:shutil.copyfileobj(upload.file,f)
        try:inspect_reference(path,secondary=name=='tein-reference')
        except ValueError as e:raise HTTPException(400,str(e))
        paths.append(path)
    from seedance_bridge import submit
    try:request_id=submit(folder,prompt,*paths)
    except Exception as e:raise HTTPException(502,str(e))
    # Each submitted reference remains immutable; these copies only restore UI selection.
    for name,path in zip(['sirio-reference','tein-reference'],paths):
        if path is not None:shutil.copy2(path,folder/(name+path.suffix))
    jobs[ident]={'id':ident,'state':'running','status':'Seedance rendering: '+request_id}
    def collect():
        from seedance_bridge import wait_and_finish
        try:
            wait_and_finish(folder,request_id,lambda s:jobs[ident].update(status=s))
            jobs[ident].update(state='done',status='Final preview ready · entire original source audio',final_url='/runs/'+ident+'/final-preview.mp4')
        except Exception as e:jobs[ident].update(state='error',status=str(e))
        (folder/'status.json').write_text(json.dumps(jobs[ident]))
    threading.Thread(target=collect,daemon=True).start()
    return {'request_id':request_id,'id':ident,'state':'running','status':jobs[ident]['status']}

@app.post('/jobs/{ident}/finish')
def finish(ident:str,video:UploadFile=File(...)):
    if len(ident)!=32 or not all(c in '0123456789abcdef' for c in ident):raise HTTPException(404)
    folder=RUNS/ident
    if not (folder/'upload.mp4').exists():raise HTTPException(400,'Original source is required.')
    from job_state import job_lock,atomic_json
    import tempfile,os,hashlib
    try:
        with job_lock(folder):
            if (folder/'final-preview.mp4').exists() or (folder/'seedance-result.mp4').exists():
                raise HTTPException(409,'A saved result already exists. Preserve it and resume its collection.')
            stage=Path(tempfile.mkdtemp(prefix='.manual-finish-',dir=folder))
            try:
                target=stage/'seedance-result.mp4'
                with target.open('wb') as f:shutil.copyfileobj(video.file,f)
                shutil.copy2(folder/'upload.mp4',stage/'upload.mp4')
                from audio_workflow import finish_preview
                finish_preview(target,stage)
                os.replace(stage/'final-preview.mp4',folder/'final-preview.mp4')
                os.replace(target,folder/'seedance-result.mp4')
                adjustment=stage/'duration-adjustment.json'
                if adjustment.exists():os.replace(adjustment,folder/'duration-adjustment.json')
                with (folder/'final-preview.mp4').open('rb') as f:output_hash=hashlib.file_digest(f,'sha256').hexdigest()
                atomic_json(folder/'manual-result.json',{'source':'user-imported result','output_sha256':output_hash})
            finally:
                if stage.resolve().parent!=folder.resolve():raise ValueError('Invalid temporary export directory')
                shutil.rmtree(stage)
    except HTTPException:raise
    except Exception as e:raise HTTPException(400,str(e))
    return {'url':'/runs/'+ident+'/final-preview.mp4'}

app.mount('/runs' ,StaticFiles(directory=RUNS),name='runs')

hd_jobs={}
hd_lock=threading.Lock()

def hd_folder(ident):
    if len(ident)!=32 or not all(c in '0123456789abcdef' for c in ident):raise HTTPException(404)
    folder=RUNS/ident
    if not folder.exists():raise HTTPException(404)
    return folder

@app.get('/jobs/{ident}/hd')
def get_hd(ident:str):
    folder=hd_folder(ident)
    if ident in hd_jobs:return hd_jobs[ident]
    saved=folder/'hd/status.json'
    if saved.exists():return json.loads(saved.read_text())
    return {'state':'idle','status':'Approve your draft to generate 1080p.'}

@app.post('/jobs/{ident}/hd')
def create_hd(ident:str):
    folder=hd_folder(ident)
    with hd_lock:
        previous=get_hd(ident)
        if previous['state'] in ['running','done']:return previous
        if not (folder/'final-preview.mp4').exists():raise HTTPException(400,'Complete and review a draft first.')
        hd=folder/'hd';hd.mkdir(exist_ok=True)
        hd_jobs[ident]={'state':'running','status':'Submitting approved draft for 1080p','id':ident}
        def save(): (hd/'status.json').write_text(json.dumps(hd_jobs[ident]))
        save()
    def work_hd():
        from seedance_bridge import submit_hd,wait_and_finish
        try:
            request_id=submit_hd(folder)
            hd_jobs[ident].update(request_id=request_id,status='Generating 1080p through Enhancor');save()
            wait_and_finish(hd,request_id,lambda s:hd_jobs[ident].update(status=s))
            hd_jobs[ident].update(state='done',status='1080p ready · original source audio restored')
        except Exception as e:hd_jobs[ident].update(state='error',status=str(e))
        save()
    threading.Thread(target=work_hd,daemon=True).start()
    return hd_jobs[ident]

@app.get('/jobs/{ident}/mask-review')
def get_mask_review(ident:str):
    from mask_review import state
    return state(hd_folder(ident))

@app.post('/jobs/{ident}/mask-review')
def save_mask_review(ident:str,approved:bool=Form(...),fingerprint:str=Form(...),note:str=Form('')):
    from mask_review import review
    try:return review(hd_folder(ident),approved,note,fingerprint)
    except ValueError as e:raise HTTPException(409,str(e))

app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

@app.on_event('startup')
def resume_saved_generations():
    """Resume collection only: never requeue a paid prediction on restart."""
    from seedance_bridge import wait_and_finish
    for root in RUNS.iterdir():
        if not root.is_dir() or len(root.name)!=32:continue
        for folder,response_file,registry in [(root,'seedance-response.json',jobs),(root/'hd','response.json',hd_jobs)]:
            response=folder/response_file
            if not response.exists() or (folder/'final-preview.mp4').exists():continue
            try:request_id=json.loads(response.read_text()).get('requestId')
            except (ValueError,OSError):continue
            if not request_id:continue
            registry[root.name]={'id':root.name,'state':'running','status':'Resuming saved request '+request_id}
            def collect_saved(folder=folder,ident=root.name,request_id=request_id,registry=registry):
                try:
                    wait_and_finish(folder,request_id,lambda message:registry[ident].update(status=message))
                    registry[ident].update(state='done',status='Final preview ready · original source audio')
                except Exception as e:registry[ident].update(state='error',status=str(e))
                (folder/'status.json').write_text(json.dumps(registry[ident]))
            threading.Thread(target=collect_saved,daemon=True).start()

@app.get('/health')
def health():
    return {'status':'ok','service':'Genjutsu Skill'}
