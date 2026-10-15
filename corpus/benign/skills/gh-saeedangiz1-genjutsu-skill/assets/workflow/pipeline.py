from pathlib import Path
from fractions import Fraction
import os, shutil, json, time
import av, numpy as np, requests
from PIL import Image

from config import load_env
load_env()

DEPTH='depth-anything/Video-Depth-Anything'
SAM='linoyts/SAM3-Video'

def frames(path):
    with av.open(str(path)) as c:
        for f in c.decode(video=0): yield f.to_ndarray(format='rgb24')

def writer(path,w,h):
    c=av.open(str(path),'w');s=c.add_stream('libx264',rate=24);s.width=w;s.height=h;s.pix_fmt='yuv420p';s.options={'crf':'18','preset':'fast'}
    return c,s

def put(c,s,a,i):
    f=av.VideoFrame.from_ndarray(a,format='rgb24');f.pts=i;f.time_base=Fraction(1,24)
    for p in s.encode(f):c.mux(p)

def finish(c,s):
    for p in s.encode():c.mux(p)
    c.close()

def normalize(src,dst,inspection=None):
    with av.open(str(src)) as inp:
        vs=inp.streams.video[0];rate=float(vs.average_rate or 24)
        dur=(inspection or {}).get('duration')
        if dur is None:
            if vs.duration is not None:dur=float(vs.duration*vs.time_base)
            elif inp.duration is not None:dur=float(inp.duration/av.time_base)
            else:
                from preflight import _inspect_video
                dur=_inspect_video(src,require_audio=False,packet_probe=False)['duration']
        if dur>30:raise ValueError('Use a clip of 30 seconds or less for this hosted workflow.')
        it=iter(inp.decode(video=0));cur=next(it);start=float(cur.time or 0);nxt=next(it,None)
        scale=min(1,960/max(cur.width,cur.height));w=max(2,int(cur.width*scale)//2*2);h=max(2,int(cur.height*scale)//2*2)
        out,stream=writer(dst,w,h);count=max(1,round(dur*24))
        for i in range(count):
            t=i/24+start
            while nxt is not None and float(nxt.time)<=t:cur=nxt;nxt=next(it,None)
            a=np.asarray(cur.to_image().resize((w,h),Image.Resampling.LANCZOS));put(out,stream,a,i)
        finish(out,stream)
    return {'frames':count,'fps':24,'width':w,'height':h,'duration':count/24}

def file_path(x):
    if isinstance(x,str):return x
    if isinstance(x,dict):return file_path(x.get('video') or x.get('path'))
    raise ValueError('Provider did not return a downloadable video.')

def depth_hf(src,dst):
    from gradio_client import Client, handle_file
    from preflight import inspect_reference
    inspect_reference(src)
    c=Client(DEPTH,token=os.getenv('HF_TOKEN') or None,verbose=False)
    result=c.predict({'video':handle_file(str(src))},max_len=-1,target_fps=24,max_res=960,grayscale=False,api_name='/infer_video_depth')
    shutil.copy(file_path(result[1]),dst)

def poll_prediction(prediction, headers, folder, filename):
    """Resume an accepted prediction by GET; a timeout never starts another POST."""
    from job_state import atomic_json
    j=prediction
    atomic_json(Path(folder)/filename,j)
    for _ in range(180):
        if j['status'] in ['succeeded','failed','canceled']:break
        url=j.get('urls',{}).get('get')
        if not url:raise ValueError('Prediction has no poll URL; reconcile its saved provider ID before continuing.')
        time.sleep(5);r=requests.get(url,headers=headers,timeout=30);r.raise_for_status();j=r.json()
        atomic_json(Path(folder)/filename,j)
    if j['status'] not in ['succeeded','failed','canceled']:
        raise TimeoutError('Prediction is still pending. Its ID is saved; rerun preparation to resume without another billed submission.')
    if j['status']!='succeeded':raise RuntimeError(str(j.get('error') or j['status'])+'; create a new job for a deliberate retry.')
    return j


def checked_prediction(data):
    if not isinstance(data,dict) or not isinstance(data.get('id'),str) or not data['id']:
        raise ValueError('Provider response has no prediction ID.')
    if data.get('status') not in {'starting','processing','succeeded','failed','canceled'}:
        raise ValueError('Provider response has no recognized prediction status.')
    return data


def download(url,dst,timeout=120):
    r=requests.get(url,timeout=timeout);r.raise_for_status()
    if not r.content:raise ValueError('Provider returned an empty artifact.')
    dst=Path(dst);part=dst.with_name(dst.name+'.part');part.write_bytes(r.content);part.replace(dst)


def depth_replicate(src,dst,model_name="lucataco/depth-anything-video"):
    from preflight import inspect_reference, file_identity
    from job_state import durable_submit, load_submission,atomic_json
    inspect_reference(src)
    folder=Path(dst).parent
    identity={'source':file_identity(src),'model':model_name,'stage':'depth-v1'}
    saved=load_submission(folder,'depth',identity)
    artifact=folder/'depth-artifact.json'
    if saved is not None and artifact.exists():
        cache=json.loads(artifact.read_text())
        if cache.get('identity')!=identity or cache.get('artifact')!=file_identity(dst):
            raise ValueError('Cached depth artifact changed. Prepare a new job instead of reusing it.')
        inspect_reference(dst)
        return
    token=os.getenv('REPLICATE_API_TOKEN')
    if not token:raise ValueError('Replicate fallback requires REPLICATE_API_TOKEN in the server environment.')
    # Resolve live model schema instead of assuming an input field.
    headers={'Authorization':f'Bearer {token}'}
    if saved is None:
        r=requests.get('https://api.replicate.com/v1/models/'+model_name,headers=headers,timeout=30);r.raise_for_status();model=r.json();v=model['latest_version'];props=v['openapi_schema']['components']['schemas']['Input']['properties']
        key=next((k for k in props if 'video' in k and props[k].get('format')=='uri'),None)
        if not key:raise ValueError('Unable to identify Replicate video input in schema.')
        with open(src,'rb') as f:r=requests.post('https://api.replicate.com/v1/files',headers=headers,files={'content':f},timeout=120)
        r.raise_for_status();url=r.json()['urls']['get']
        payload={'version':v['id'],'input':{key:url}}
        def send():
            response=requests.post('https://api.replicate.com/v1/predictions',headers=headers,json=payload,timeout=60)
            response.raise_for_status();return checked_prediction(response.json())
        saved=durable_submit(folder,'depth',payload,send,identity)
    j=poll_prediction(saved,headers,folder,'depth-prediction.json')
    output=j['output'];url=output if isinstance(output,str) else output[0] if isinstance(output,list) else next(v for k,v in output.items() if 'depth' in k)
    download(url,dst)
    inspect_reference(dst)
    atomic_json(artifact,{'identity':identity,'artifact':file_identity(dst),'prediction_id':j['id']})

def grayscale(src,dst,inferno=False):
    out=s=None
    for i,a in enumerate(frames(src)):
        if inferno:
            import cv2
            lut=cv2.applyColorMap(np.arange(256,dtype=np.uint8)[:,None],cv2.COLORMAP_INFERNO)[:,0,::-1].astype(np.float32)
            pixels=a.reshape(-1,3).astype(np.float32);indices=[]
            for chunk in np.array_split(pixels,max(1,len(pixels)//4096)):
                dist=((chunk[:,None,:]-lut[None,:,:])**2).sum(axis=2)
                indices.append(dist.argmin(axis=1).astype(np.uint8))
            gray=np.concatenate(indices).reshape(a.shape[:2]);g=np.repeat(gray[:,:,None],3,axis=2)
        else:g=np.asarray(Image.fromarray(a).convert('L').convert('RGB'))
        if out is None:out,s=writer(dst,g.shape[1],g.shape[0])
        put(out,s,g,i)
    if out is None:raise ValueError('Empty depth video')
    finish(out,s)

def composite(original,depth,seg,directory,audio_source=None):
    raw=Path(seg).is_dir()
    mask_files=sorted(Path(seg).glob('mask_*.png')) if raw else []
    counts=[sum(1 for _ in frames(p)) for p in [original,depth]]+[len(mask_files) if raw else sum(1 for _ in frames(seg))]
    if len(set(counts))!=1:raise ValueError(f'Frame alignment failed (original/depth/SAM): {counts}. No misaligned export produced.')
    if raw and [int(p.stem.split('_')[-1]) for p in mask_files]!=list(range(counts[0])):raise ValueError('Missing or shifted frame indices in raw masks.')
    outs={};area=0
    for i,(rgb,d,sam) in enumerate(zip(frames(original),frames(depth),(np.asarray(Image.open(p).convert('RGB')) for p in mask_files) if raw else frames(seg))):
        h,w=rgb.shape[:2]
        if raw:
            mask=(sam[:,:,0]>127).astype(np.uint8)*255
        else:
            # Recover SAM's known 50% green overlay against the untouched depth frame.
            base=np.asarray(Image.fromarray(d).resize((sam.shape[1],sam.shape[0]),Image.Resampling.BILINEAR)).astype(np.float32)
            marked=base*0.5+np.array([0,127.5,0],dtype=np.float32)
            observed=sam.astype(np.float32)
            unchanged_error=((observed-base)**2).sum(axis=2)
            marked_error=((observed-marked)**2).sum(axis=2)
            mask=((marked_error+100<unchanged_error)&(observed[:,:,1]-base[:,:,1]>12)).astype(np.uint8)*255
        mask=np.asarray(Image.fromarray(mask).resize((w,h),Image.Resampling.NEAREST));area+=np.count_nonzero(mask)
        d=np.asarray(Image.fromarray(d).resize((w,h),Image.Resampling.BILINEAR));alpha=(mask>127)[:,:,None]
        result=np.where(alpha,d,rgb).astype(np.uint8)
        for name,a in [('mask',np.repeat(mask[:,:,None],3,axis=2)),('composite-silent',result)]:
            if name not in outs:outs[name]=writer(directory/(name+'.mp4'),w,h)
            put(*outs[name],a,i)
    for c,s in outs.values():finish(c,s)
    if area==0:raise ValueError('SAM 3 found no subject in the depth video. Try a simple prompt such as person, or provide a mask manually.')
    final=directory/'composite.mp4'
    with av.open(str(directory/'composite-silent.mp4')) as video, av.open(str(audio_source or original)) as aud, av.open(str(final),'w') as output:
        vs=output.add_stream_from_template(video.streams.video[0])
        astream=output.add_stream_from_template(aud.streams.audio[0]) if aud.streams.audio else None
        for packet in video.demux(video=0):
            if packet.dts is not None:packet.stream=vs;output.mux(packet)
        if aud.streams.audio:
            for packet in aud.demux(audio=0):
                if packet.dts is not None:packet.stream=astream;output.mux(packet)
    return counts[0]

def _run(src,directory,prompt='person',provider='replicate',status=print,mode='depth',preflight_report=None):
    from preflight import preflight_job,bind_preparation
    from job_state import atomic_json
    report=preflight_report or preflight_job(src,mode,provider)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    identity=bind_preparation(directory,report,prompt)
    src=directory/'upload.mp4'
    from audio_workflow import separate
    separate(src,directory,status)
    status('Preparing video · 24 fps');meta=normalize(src,directory/'original.mp4',report['source'])
    status('Video Depth Anything · generating depth')
    if provider=='huggingface':depth_hf(directory/'original.mp4',directory/'depth-raw.mp4')
    else:depth_replicate(directory/'original.mp4',directory/'depth-raw.mp4', 'chenxwh/depth-any-video' if provider=='replicate-chenxwh' else 'lucataco/depth-anything-video')
    shutil.copyfile(directory/'depth-raw.mp4',directory/'depth.mp4')
    status('SAM 3 · segmenting the depth subject')
    from raw_masks import segment_raw,clean_border_fragments
    raw_dir=clean_border_fragments(segment_raw(directory/'depth.mp4',directory,prompt))
    status('Compositing · depth subject over original background')
    composite(directory/'original.mp4',directory/'depth.mp4',raw_dir,directory,src)
    from audio_workflow import prepare_seedance_video
    status('Embedding isolated vocals · +3 semitones')
    prepare_seedance_video(directory)
    meta.update(prompt=prompt,depth_provider=provider,sam_space=SAM,mask_method='SAM 3 raw PNG masks')
    meta.update(source_identity=report['source']['sha256'],preparation_identity=identity)
    atomic_json(directory/'manifest.json',meta)
    atomic_json(directory/'workflow-mode.json',{'mode':mode,'provider':provider,'subject':prompt})
    atomic_json(directory/'preparation-state.json',{'identity':identity,'state':'depth_prepared' if mode=='depth_mesh' else 'prepared'})
    status('Complete')


def run(src,directory,prompt='person',provider='replicate',status=print):
    from preflight import preflight_job
    from job_state import job_lock
    # Reject invalid media and unavailable local workers before locking or spending.
    report=preflight_job(src,'depth',provider)
    with job_lock(directory):
        return _run(src,directory,prompt,provider,status,preflight_report=report)
