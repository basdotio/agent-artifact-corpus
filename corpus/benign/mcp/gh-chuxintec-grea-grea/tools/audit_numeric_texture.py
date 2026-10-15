#!/usr/bin/env python3
"""Audit raw little/big endian float texture data; never treat a PNG as numeric input."""
import argparse, hashlib, json, math, struct
from pathlib import Path

def audit(path,width,height,channels,dtype,endian,candidate=None):
    if min(width,height,channels)<=0 or channels>4: raise ValueError('Invalid dimensions/channels')
    fmt={'f16':'e','f32':'f'}[dtype];expected=width*height*channels*struct.calcsize(fmt)
    if path.stat().st_size!=expected: raise ValueError(f'Expected {expected} raw bytes; got {path.stat().st_size}')
    data=path.read_bytes();values=[x[0] for x in struct.iter_unpack(('<' if endian=='little' else '>')+fmt,data)]
    finite=[v for v in values if math.isfinite(v)]
    result={'schema_version':1,'source':str(path.resolve()),'sha256':hashlib.sha256(data).hexdigest(),'width':width,'height':height,'channels':channels,'dtype':dtype,'endian':endian,'bytes':len(data),'min':min(finite) if finite else None,'max':max(finite) if finite else None,'negative':sum(v<0 for v in finite),'above_one':sum(v>1 for v in finite),'nonfinite':len(values)-len(finite),'candidate_equal':None,'limitations':['Raw values only; use Unity probe for sampler settings and GPU results.']}
    if candidate is not None:result['candidate_equal']=candidate.read_bytes()==data
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
    for k in ['width','height','channels']:p.add_argument('--'+k,type=int,required=True)
    p.add_argument('--dtype',choices=['f16','f32'],required=True);p.add_argument('--endian',choices=['little','big'],default='little');p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:
        r=audit(a.source,a.width,a.height,a.channels,a.dtype,a.endian,a.candidate)
        if a.output:
            with a.output.open('x',encoding='utf-8') as f:json.dump(r,f,indent=2)
        print(json.dumps(r));return 1 if r['nonfinite'] or r['candidate_equal'] is False else 0
    except (OSError,ValueError) as e:p.error(str(e))
if __name__=='__main__':raise SystemExit(main())
