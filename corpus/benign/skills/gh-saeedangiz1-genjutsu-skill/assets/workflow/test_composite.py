import tempfile
from pathlib import Path
import numpy as np
from pipeline import writer,put,finish,composite,frames
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)
 arrays={
 'original':np.full((64,64,3),(180,40,40),dtype=np.uint8),
 'depth':np.full((64,64,3),100,dtype=np.uint8),
 'seg':np.full((64,64,3),100,dtype=np.uint8)}
 arrays['seg'][16:48,16:48]=[50,177,50]
 for name,a in arrays.items():
  c,s=writer(p/(name+'.mp4'),64,64)
  for i in range(4):put(c,s,a,i)
  finish(c,s)
 assert composite(p/'original.mp4',p/'depth.mp4',p/'seg.mp4',p)==4
 a=next(frames(p/'composite.mp4'))
 assert np.max(np.abs(a[32,32].astype(int)-100))<10
 assert a[2,2,0]>160 and a[2,2,1]<60
 print('PASS: mask selects depth subject, background preserved, four aligned frames exported.')
