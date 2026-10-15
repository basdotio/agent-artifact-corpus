#!/usr/bin/env python3
"""Render an animated HTML page to a looping GIF, frame by frame. No screen recording.

The page animates with CSS animations or the Web Animations API. This script pauses every
animation, seeks them all to t = 0, 1/fps, 2/fps ... and screenshots each frame, then builds the
GIF. Same input, same GIF, every time.

Usage:
    python scripts/record_html.py page.html out.gif --w 1200 --h 600 --dur 8 [--fps 12] [--colors 128]
    python scripts/record_html.py page.html out.png --w 1200 --h 600 --still 6.5     # one frame, 2x

Page contract:
    - Fixed-size body: width and height equal --w and --h in CSS px.
    - Every animation has a finite duration and runs once. Choreograph with delays, so the whole
      piece runs once in --dur seconds and the GIF loops it.
    - Optional: window.__seek(ms) if the page drives something from JS. It is called every frame.

Needs: pip install playwright && python -m playwright install chromium.
ffmpeg on PATH gives the best GIF. Without it, Pillow builds the GIF instead (pip install pillow).
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

SEEK = """(ms) => {
  for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; }
  if (window.__seek) window.__seek(ms);
}"""


def capture(html, w, h, times_ms, scale, out_dir):
    """Screenshot the page at each time in times_ms. Returns the frame paths."""
    from playwright.sync_api import sync_playwright
    frames = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=scale)
        pg.goto(Path(html).resolve().as_uri())
        try:
            pg.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            pass  # offline: fonts fall back to system fonts, the frames still render
        pg.evaluate('document.fonts.ready')
        pg.wait_for_timeout(300)
        for i, t in enumerate(times_ms):
            pg.evaluate(SEEK, t)
            f = Path(out_dir) / f'f{i:05d}.png'
            pg.screenshot(path=str(f))
            frames.append(f)
        b.close()
    return frames


def build_gif(frames, out, fps, width, colors, hold=0.0):
    out = Path(out)
    if shutil.which('ffmpeg'):
        tail = f',tpad=stop_mode=clone:stop_duration={hold}' if hold else ''
        fc = (f'[0:v]fps={fps},scale={width}:-1:flags=lanczos{tail},split[x][y];'
              f'[x]palettegen=max_colors={colors}:stats_mode=full[pl];'
              '[y][pl]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps),
                        '-i', str(Path(frames[0]).parent / 'f%05d.png'), '-filter_complex', fc,
                        '-loop', '0', str(out)], check=True)
        return 'ffmpeg'
    from PIL import Image
    imgs = []
    for f in frames:
        im = Image.open(f).convert('RGB')
        if im.width != width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        imgs.append(im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    durations = [round(1000 / fps)] * len(imgs)
    if hold:
        durations[-1] += round(hold * 1000)
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=durations, loop=0, optimize=True, disposal=1)
    return 'pillow'


def record(html, out, w, h, dur, fps=12, scale=1.0, colors=128, hold=0.0):
    work = Path(tempfile.mkdtemp(prefix='rec-'))
    try:
        n = int(round(dur * fps))
        frames = capture(html, w, h, [i * 1000.0 / fps for i in range(n)], scale, work)
        how = build_gif(frames, out, fps, int(w * scale), colors, hold)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return how, n


def still(html, out, w, h, at, scale=2.0):
    work = Path(tempfile.mkdtemp(prefix='still-'))
    try:
        [f] = capture(html, w, h, [at * 1000.0], scale, work)
        shutil.copyfile(f, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('html')
    ap.add_argument('out')
    ap.add_argument('--w', type=int, default=1200)
    ap.add_argument('--h', type=int, default=600)
    ap.add_argument('--dur', type=float, default=8.0, help='seconds')
    ap.add_argument('--fps', type=int, default=12)
    ap.add_argument('--scale', type=float, default=1.0, help='device scale factor (2 = sharper, bigger file)')
    ap.add_argument('--colors', type=int, default=128)
    ap.add_argument('--hold', type=float, default=0.0, help='extra seconds to hold the last frame')
    ap.add_argument('--still', type=float, default=None, help='write one PNG at this second instead of a GIF')
    a = ap.parse_args()
    out = Path(a.out)
    if a.still is not None:
        still(a.html, out, a.w, a.h, a.still)
        print('wrote', out)
        return
    how, n = record(a.html, out, a.w, a.h, a.dur, a.fps, a.scale, a.colors, a.hold)
    print('wrote', out, round(out.stat().st_size / 1e6, 2), 'MB,', n, 'frames, via', how)


if __name__ == '__main__':
    main()
