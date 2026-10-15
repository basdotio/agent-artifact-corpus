from pathlib import Path
from fractions import Fraction
import av, mediapipe as mp, numpy as np, sys, json, urllib.request
from PIL import ImageDraw
root=Path(sys.argv[1]).resolve()
source=root/'original.mp4'
model=Path(__file__).resolve().parent/'models/face_landmarker.task'
if not model.exists():
 model.parent.mkdir(exist_ok=True)
 temporary=model.with_suffix('.download')
 urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task',str(temporary))
 temporary.replace(model)
opts=mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),running_mode=mp.tasks.vision.RunningMode.VIDEO,num_faces=1,min_face_detection_confidence=0.15,min_face_presence_confidence=0.15,min_tracking_confidence=0.15)
connections=mp.tasks.vision.FaceLandmarksConnections
counts=[];saved=[]
background=[]
if '--depth' in sys.argv:
 with av.open(str(root/'depth-composite-silent.mp4')) as bg:background=[f.to_image() for f in bg.decode(video=0)]
with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as detector, av.open(str(source)) as inp, av.open(str(root/'composite-silent.mp4'),'w') as out:
 stream=inp.streams.video[0]
 if background and (len(background)!=stream.frames or background[0].size!=(stream.width,stream.height)):raise ValueError('Depth and original frame count or dimensions differ; rebuild the depth composite before overlay.')
 vs=out.add_stream('libx264',rate=24);vs.width=stream.width;vs.height=stream.height;vs.pix_fmt='yuv420p';vs.options={'crf':'18'}
 for i,f in enumerate(inp.decode(video=0)):
  im=f.to_image();x0=int(im.width*.25);y0=0;cw=int(im.width*.5);ch=int(im.height*.65);crop=im.crop((x0,y0,x0+cw,ch));result=detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=np.array(crop)),round(i*1000/24));im=background[i].copy() if background else im;d=ImageDraw.Draw(im);counts.append(len(result.face_landmarks))
  saved.append({"frame":i,"time":i/24,"faces":[[{"x":(x0+l.x*cw)/im.width,"y":(y0+l.y*ch)/im.height} for l in face] for face in result.face_landmarks]})
  for face in result.face_landmarks:
   pts=[(round(x0+l.x*cw),round(y0+l.y*ch)) for l in face]
   for c in connections.FACE_LANDMARKS_TESSELATION:d.line([pts[c.start],pts[c.end]],fill=(50,170,205),width=1)
   for name,col in [('FACE_LANDMARKS_LIPS',(255,135,100)),('FACE_LANDMARKS_LEFT_EYE',(130,255,150)),('FACE_LANDMARKS_RIGHT_EYE',(130,255,150))]:
    for c in getattr(connections,name):d.line([pts[c.start],pts[c.end]],fill=col,width=2)
  vf=av.VideoFrame.from_image(im);vf.pts=i;vf.time_base=Fraction(1,24)
  for pkt in vs.encode(vf):out.mux(pkt)
  if i==30:im.save(root/'preview.jpg')
 for pkt in vs.encode():out.mux(pkt)
print({'frames':len(counts),'tracked':sum(x>0 for x in counts),'missing':[i for i,x in enumerate(counts) if not x]})

(root/'face-landmarks.json').write_text(json.dumps({'fps':24,'frames':saved}))
(root/'face-tracking.json').write_text(json.dumps({'frames':len(counts),'tracked':sum(bool(x) for x in counts),'missing_frames':[i for i,x in enumerate(counts) if not x]}))
if not counts or not all(counts):raise RuntimeError('Face tracking gaps: inspect face-tracking.json and repair before submitting.')
