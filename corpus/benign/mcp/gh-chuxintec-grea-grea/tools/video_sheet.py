"""Create a labelled contact sheet from a local recording; times are nominal samples."""
import argparse
import math
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--start', type=float, default=0)
    p.add_argument('--duration', type=float, default=2)
    p.add_argument('--fps', type=float, default=8)
    p.add_argument('--crop', nargs=4, type=int, metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'))
    p.add_argument('--columns', type=int, default=4)
    p.add_argument('--width', type=int, default=300)
    p.add_argument('--ffmpeg', default='ffmpeg')
    a = p.parse_args()
    if min(a.duration, a.fps, a.columns, a.width) <= 0 or a.start < 0:
        p.error('Dimensions, rate and duration must be positive; start must be nonnegative')
    if a.output.exists():
        p.error('Output already exists')
    with tempfile.TemporaryDirectory(prefix='game-frames-') as tmp:
        subprocess.run([a.ffmpeg, '-v', 'error', '-ss', str(a.start), '-i', str(a.source),
                        '-t', str(a.duration), '-vf', f'fps={a.fps}', str(Path(tmp)/'%06d.png')], check=True)
        frames = sorted(Path(tmp).glob('*.png'))
        if not frames:
            p.error('No frames decoded')
        tiles = []
        for f in frames:
            with Image.open(f) as source:
                im = source.convert('RGB')
            if a.crop:
                l, t, r, b = a.crop
                if not (0 <= l < r <= im.width and 0 <= t < b <= im.height):
                    p.error('Crop exceeds recording bounds')
                im = im.crop(a.crop)
            tiles.append(im.resize((a.width, round(im.height*a.width/im.width))))
        height = max(im.height for im in tiles)+24
        sheet = Image.new('RGB', (a.columns*a.width, math.ceil(len(tiles)/a.columns)*height), '#172033')
        draw = ImageDraw.Draw(sheet)
        for i, im in enumerate(tiles):
            x, y = i % a.columns*a.width, i//a.columns*height
            sheet.paste(im, (x, y))
            draw.text((x+8, y+height-20), f'~{a.start+i/a.fps:.3f}s', fill='white')
        a.output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(a.output)


if __name__ == '__main__':
    main()
