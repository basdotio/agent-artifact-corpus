from pathlib import Path
import os,json,time,zipfile,io
import requests

def segment_raw(video,folder,prompt='person'):
    from preflight import inspect_reference,file_identity
    from job_state import load_submission,durable_submit,atomic_json
    from pipeline import poll_prediction,checked_prediction
    from config import credential
    inspect_reference(video)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    h={'Authorization':'Bearer '+credential('REPLICATE_API_TOKEN')}
    version='408f82fc20c300aac5d61d2e34ddb34cd0181e810e9f609d250aed14d5f81269'
    identity={'video':file_identity(video),'version':version,'prompt':prompt,'mask_only':True,'return_zip':True}
    j=load_submission(folder,'sam',identity)
    receipt=folder/'sam-artifacts.json'
    if j is not None and receipt.exists():
        data=json.loads(receipt.read_text())
        out=folder/'raw-masks'
        expected=data.get('masks',{})
        if data.get('identity')!=identity or not expected or set(expected)!={p.name for p in out.glob('mask_*.png')}:
            raise ValueError('Cached SAM artifact identity changed. Prepare a new job.')
        for name,fingerprint in expected.items():
            if Path(name).name!=name or file_identity(out/name)!=fingerprint:
                raise ValueError('Cached SAM mask changed. Prepare a new job.')
        return out
    if j is None:
        with open(video,'rb') as f:r=requests.post('https://api.replicate.com/v1/files',headers=h,files={'content':f},timeout=120)
        r.raise_for_status();url=r.json()['urls']['get']
        payload={'version':version,'input':{'video':url,'prompt':prompt,'mask_only':True,'return_zip':True}}
        def send():
            response=requests.post('https://api.replicate.com/v1/predictions',headers=h,json=payload,timeout=60)
            response.raise_for_status();return checked_prediction(response.json())
        j=durable_submit(folder,'sam',payload,send,identity)
    print('SAM raw-mask job:',j['id'],flush=True)
    j=poll_prediction(j,h,folder,'sam-raw-request.json')
    r=requests.get(j['output'],timeout=180);r.raise_for_status();(folder/'sam-masks.zip').write_bytes(r.content)
    out=folder/'raw-masks';out.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names=set()
        for name in z.namelist():
            base=Path(name).name
            if base.startswith('mask_') and base.endswith('.png'):
                if base in names:raise ValueError('SAM archive contains duplicate mask frame names.')
                names.add(base);(out/base).write_bytes(z.read(name))
        if not names:raise ValueError('SAM archive returned no masks.')
        # Previously interrupted artifacts must not leave extra shifted mask frames.
        for previous in out.glob('mask_*.png'):
            if previous.name not in names:previous.unlink()
    from PIL import Image
    for mask in out.glob('mask_*.png'):
        with Image.open(mask) as image:image.load()
    atomic_json(receipt,{'identity':identity,'prediction_id':j['id'],'masks':{p.name:file_identity(p) for p in out.glob('mask_*.png')}})
    return out

def clean_border_fragments(folder):
    """Remove tiny, narrow disconnected edge fragments; preserve large edge subjects."""
    import numpy as np
    from PIL import Image
    from scipy.ndimage import label
    folder=Path(folder);output=folder.parent/'clean-masks';output.mkdir(exist_ok=True)
    report=[]
    for p in sorted(folder.glob('mask_*.png')):
        a=np.asarray(Image.open(p).convert('L'))>127;labels,_=label(a);h,w=a.shape;removed=0
        for ident in (set(labels[:,0])|set(labels[:,-1]))-{0}:
            y,x=np.where(labels==ident)
            if len(x)<h*w*.03 and x.max()-x.min()+1<=max(6,int(w*.05)):
                a[labels==ident]=False;removed+=len(x)
        Image.fromarray(a.astype(np.uint8)*255).save(output/p.name)
        report.append({'frame':p.stem,'removed_border_pixels':removed,'mask_pixels':int(a.sum()),'left_right_edge_pixels':int(a[:,0].sum()+a[:,-1].sum())})
    valid={p.name for p in folder.glob('mask_*.png')}
    for previous in output.glob('mask_*.png'):
        if previous.name not in valid:previous.unlink()
    (folder.parent/'mask-cleanup-report.json').write_text(json.dumps(report,indent=2))
    return output
