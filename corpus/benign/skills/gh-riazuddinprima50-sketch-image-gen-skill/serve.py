#!/usr/bin/env python3
"""Local image gallery server for generated images.

Serves a directory tree over HTTP with an auto-refreshing web gallery:
new images appear in the browser within a couple of seconds, no reload needed.

Endpoints:
  GET /                 -> gallery HTML
  GET /api/list         -> JSON {root, count, images:[{rel,name,mtime,size,dir}]}
  GET /img?p=<relpath>  -> full image
  GET /thumb?p=<relpath>-> thumbnail (needs Pillow; falls back to full image)

Usage:
  python3 serve.py [dir] [--port 8099] [--host 0.0.0.0] [--open]
  python3 serve.py --open            # serve the current directory and open browser
"""
import argparse
import io
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif"}
THUMB_MAX = 520

try:
    from PIL import Image  # type: ignore
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


PAGE = r"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>图片画廊 · Image Gallery</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #0d1117; color: #e6edf3;
         font: 14px/1.5 -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; }
  header { position: sticky; top: 0; z-index: 5; display: flex; gap: 14px; align-items: center;
           padding: 12px 18px; background: #161b22ee; backdrop-filter: blur(8px);
           border-bottom: 1px solid #30363d; flex-wrap: wrap; }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  .badge { background: #238636; color: #fff; border-radius: 999px; padding: 1px 10px; font-size: 12px; }
  .muted { color: #8b949e; font-size: 12px; }
  .spacer { flex: 1; }
  input#q { background: #0d1117; border: 1px solid #30363d; color: #e6edf3;
            border-radius: 6px; padding: 6px 10px; min-width: 180px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #3fb950; box-shadow: 0 0 8px #3fb950; }
  main { padding: 18px; }
  .grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; overflow: hidden;
          cursor: zoom-in; transition: transform .12s ease, border-color .12s ease; }
  .card:hover { transform: translateY(-2px); border-color: #58a6ff; }
  .thumb { width: 100%; aspect-ratio: 1/1; object-fit: contain; background: #0b0f14; display: block; }
  .meta { padding: 8px 10px; }
  .name { font-size: 12px; word-break: break-all; line-height 1.3; }
  .sub { font-size: 11px; color: #8b949e; margin-top: 2px; }
  .empty { color: #8b949e; text-align: center; padding: 60px 0; }
  #lightbox { position: fixed; inset: 0; z-index: 50; display: none; background: #000d;
              align-items: center; justify-content: center; flex-direction: column; }
  #lightbox.on { display: flex; }
  #lightbox img { max-width: 94vw; max-height: 82vh; border-radius: 8px; box-shadow: 0 10px 40px #000a; }
  #lightbox .bar { margin-top: 12px; display: flex; gap: 16px; align-items: center; color: #c9d1d9; }
  #lightbox a { color: #58a6ff; text-decoration: none; }
  .nav { position: absolute; top: 50%; font-size: 40px; color: #fff9; cursor: pointer; user-select: none;
         padding: 0 18px; transform: translateY(-50%); }
  .nav:hover { color: #fff; } #prev { left: 0; } #next { right: 0; }
</style>
</head>
<body>
<header>
  <span class="dot" id="dot" title="自动刷新中"></span>
  <h1>图片画廊</h1>
  <span class="badge" id="count">0</span>
  <input id="q" placeholder="搜索文件名…">
  <span class="spacer"></span>
  <span class="muted" id="root"></span>
</header>
<main><div class="grid" id="grid"></div><div class="empty" id="empty">暂无图片</div></main>
<div id="lightbox">
  <span class="nav" id="prev">‹</span><img id="lbimg" alt="">
  <span class="nav" id="next">›</span>
  <div class="bar"><span id="lbname"></span><a id="lbopen" target="_blank">原图 ↗</a><a id="lbdl" download>下载 ↓</a></div>
</div>
<script>
const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const q = document.getElementById('q');
document.getElementById('root').textContent = ROOT;
let items = [], filtered = [], cur = -1, sig = '';

function fmtSize(n){ if(n<1024)return n+' B'; if(n<1048576)return (n/1024).toFixed(1)+' KB'; return (n/1048576).toFixed(2)+' MB'; }
function enc(p){ return encodeURIComponent(p); }

function applyFilter(){
  const s = q.value.trim().toLowerCase();
  filtered = s ? items.filter(i => i.name.toLowerCase().includes(s)) : items;
  render();
}
function render(){
  document.getElementById('count').textContent = filtered.length;
  empty.style.display = filtered.length ? 'none' : 'block';
  grid.innerHTML = '';
  for(const it of filtered){
    const a = document.createElement('div');
    a.className = 'card';
    a.innerHTML = '<img class="thumb" loading="lazy" src="/thumb?p='+enc(it.rel)+'&t='+it.mtime+'">'
      + '<div class="meta"><div class="name">'+it.name+'</div>'
      + '<div class="sub">'+fmtSize(it.size)+' · '+(it.dir||'.')+'</div></div>';
    a.onclick = () => openLb(filtered.indexOf(it));
    grid.appendChild(a);
  }
}
function openLb(i){
  cur = i; const it = filtered[i]; if(!it) return;
  document.getElementById('lbimg').src = '/img?p='+enc(it.rel);
  document.getElementById('lbname').textContent = it.name+'  ('+fmtSize(it.size)+')';
  document.getElementById('lbopen').href = '/img?p='+enc(it.rel);
  document.getElementById('lbdl').href = '/img?p='+enc(it.rel);
  document.getElementById('lightbox').classList.add('on');
}
function closeLb(){ document.getElementById('lightbox').classList.remove('on'); }
document.getElementById('lightbox').onclick = e => { if(e.target.id==='lightbox') closeLb(); };
document.getElementById('prev').onclick = e => { e.stopPropagation(); if(filtered.length) openLb((cur-1+filtered.length)%filtered.length); };
document.getElementById('next').onclick = e => { e.stopPropagation(); if(filtered.length) openLb((cur+1)%filtered.length); };
document.addEventListener('keydown', e => {
  if(e.key==='Escape') closeLb();
  if(e.key==='ArrowLeft') document.getElementById('prev').click();
  if(e.key==='ArrowRight') document.getElementById('next').click();
});
q.addEventListener('input', applyFilter);

async function poll(){
  try{
    const r = await fetch('/api/list', {cache:'no-store'});
    const j = await r.json();
    const s = j.images.map(i => i.rel+':'+i.mtime).join('|');
    if(s !== sig){ sig = s; items = j.images; applyFilter();
      document.getElementById('dot').style.opacity = 1; }
  }catch(e){ document.getElementById('dot').style.opacity = 0.25; }
}
poll(); setInterval(poll, 2500);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    root: Path = Path(".").resolve()

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/plain; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _safe(self, rel):
        p = (self.root / rel).resolve()
        try:
            p.relative_to(self.root)
        except ValueError:
            return None
        return p if p.is_file() else None

    def _list(self):
        imgs = []
        for p in self.root.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMG_EXTS:
                try:
                    st = p.stat()
                except OSError:
                    continue
                rel = p.relative_to(self.root).as_posix()
                imgs.append({
                    "rel": rel,
                    "name": p.name,
                    "dir": str(Path(rel).parent) if Path(rel).parent != Path(".") else "",
                    "mtime": int(st.st_mtime),
                    "size": st.st_size,
                })
        imgs.sort(key=lambda i: i["mtime"], reverse=True)
        return imgs

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/":
            return self._send(200, PAGE.replace("ROOT", json.dumps(str(self.root))),
                              "text/html; charset=utf-8")
        if u.path == "/api/list":
            data = {"root": str(self.root), "count": 0, "images": self._list()}
            data["count"] = len(data["images"])
            return self._send(200, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")
        if u.path in ("/img", "/thumb"):
            qs = urllib.parse.parse_qs(u.query)
            rel = urllib.parse.unquote((qs.get("p") or [""])[0])
            p = self._safe(rel)
            if not p:
                return self._send(404, "not found")
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            if u.path == "/thumb" and HAVE_PIL and p.suffix.lower() not in (".gif",):
                try:
                    im = Image.open(p)
                    im.thumbnail((THUMB_MAX, THUMB_MAX))
                    buf = io.BytesIO()
                    im.convert("RGB").save(buf, format="JPEG", quality=82)
                    return self._send(200, buf.getvalue(), "image/jpeg")
                except Exception:
                    pass
            return self._send(200, p.read_bytes(), ctype)
        return self._send(404, "not found")


def open_browser(url):
    if os.environ.get("WSL_DISTRO_NAME") or Path("/mnt/c/Windows").exists():
        for cmd in (["explorer.exe", url], ["cmd.exe", "/c", "start", "", url]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                continue
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Local auto-refreshing image gallery.")
    ap.add_argument("dir", nargs="?", default=".", help="directory to serve (recursive)")
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--open", action="store_true", help="open the gallery in a browser")
    args = ap.parse_args()

    root = Path(args.dir).expanduser().resolve()
    if not root.is_dir():
        sys.exit("ERROR: not a directory: %s" % root)
    Handler.root = root

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = "http://localhost:%d/" % args.port
    print("image-gen gallery")
    print("  root : %s" % root)
    print("  url  : %s   (Ctrl+C to stop)" % url)
    if HAVE_PIL:
        print("  thumbs: Pillow on (%dpx)" % THUMB_MAX)
    else:
        print("  thumbs: Pillow off (serving full images; pip install Pillow for speed)")
    sys.stdout.flush()
    if args.open:
        time.sleep(0.4)
        open_browser(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
