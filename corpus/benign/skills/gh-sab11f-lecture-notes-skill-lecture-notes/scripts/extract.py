"""Universal slide-PDF extractor: strips lines repeated on >40% of pages (footers,
author, course name) and collapses incremental overlays (a page whose text is a
prefix of the next page). usage: python3 extract.py slides.pdf slides.txt"""
import sys, re, subprocess
from collections import Counter
pdf, out = sys.argv[1], sys.argv[2]
txt = subprocess.run(["pdftotext","-layout",pdf,"-"],capture_output=True,text=True).stdout
raw = [p for p in txt.split("\f") if p.strip()]
# boilerplate = non-empty lines present on >40% of pages
cnt = Counter()
for p in raw:
    for l in set(l.strip() for l in p.split("\n") if l.strip()):
        cnt[l]+=1
boiler = {l for l,c in cnt.items() if c > 0.4*len(raw)}
def clean(p):
    return "\n".join(l.rstrip() for l in p.split("\n") if l.strip() and l.strip() not in boiler)
pages=[clean(p) for p in raw]
sq=lambda s: re.sub(r"\s+"," ",s).strip()
keep=[]
for i,p in enumerate(pages):
    if i+1<len(pages):
        a,b=sq(p),sq(pages[i+1])
        if b.startswith(a) and len(b)>len(a): continue
    keep.append(p)
open(out,"w").write("\n\n=====\n\n".join(keep))
print("boilerplate:",boiler); print(len(pages),"->",len(keep),"slides")
