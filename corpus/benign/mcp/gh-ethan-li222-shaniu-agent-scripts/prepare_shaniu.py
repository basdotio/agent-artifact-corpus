"""Prepare the bundled Shaniu portrait for Wav2Lip; no upstream files are changed."""
import argparse
import json
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shaniu.avatar_catalog import avatar_root


def prepare(source, box=None, target=None):
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert('RGB')
        image.thumbnail((1080, 1440))
        rgb = np.array(image)
    height, width = rgb.shape[:2]
    if box is None:
        detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = detector.detectMultiScale(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), scaleFactor=1.05, minNeighbors=5, minSize=(100, 100))
        if len(faces) != 1:
            raise ValueError('Expected exactly one frontal face; provide --box X1 Y1 X2 Y2 after inspecting the image')
        x, y, w, h = map(int, faces[0])
        # Include the chin; coordinates describe the same crop used during inference.
        box = (max(0, x-int(w*.04)), max(0, y-int(h*.02)), min(width, x+w+int(w*.04)), min(height, y+h+int(h*.10)))
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError('Face crop must stay inside the prepared portrait')
    target = target or avatar_root('wav2lip_avatar_shaniu')
    # This fixed single-frame asset cannot leave stale numbered frames behind.
    for folder in ('full_imgs', 'face_imgs'):
        destination = target / folder
        destination.mkdir(parents=True, exist_ok=True)
        if any(p.name != '00000000.png' for p in destination.iterdir()):
            raise ValueError('Unexpected existing frames in Shaniu asset directory')
    image.save(target / 'full_imgs/00000000.png')
    crop = image.crop((x1, y1, x2, y2)).resize((256, 256), Image.Resampling.LANCZOS)
    crop.save(target / 'face_imgs/00000000.png')
    with (target / 'coords.pkl').open('wb') as file:
        pickle.dump([(y1, y2, x1, x2)], file)
    preview = image.copy()
    preview.thumbnail((480, 640))
    preview.save(target / 'preview.jpg', quality=90)
    metadata = dict(frames=1, source=str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else source.name, generated=False,
                    motion='TV still with feathered lower-face lip sync; no local face or body warps',
                    face_box=[x1, y1, x2, y2], image_size=[width, height])
    (target / 'prepared.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=False))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, help='Optional custom source; default prepares bundled original TV stills')
    parser.add_argument('--box', nargs=4, type=int, metavar=('X1', 'Y1', 'X2', 'Y2'))
    args = parser.parse_args()
    if args.image:
        prepare(args.image.resolve(), args.box)
    else:
        root = avatar_root('wav2lip_avatar_shaniu')
        silver = ROOT / 'assets/avatars/shaniu-stills/silver.jpg'
        red = ROOT / 'assets/avatars/shaniu-stills/red.jpg'
        if not silver.is_file() or not red.is_file():
            parser.error('TV stills are not distributed. Use --image with your own authorized portrait, or prepare_avatar.py for the default avatar.')
        # S3FD detections from upstream AIAvatar, with its default 10px chin pad.
        # Avoid the previous wide Haar/manual boxes that distorted model inputs.
        silver_box = (271, 151, 442, 443)
        red_box = (486, 127, 768, 542)
        prepare(silver, silver_box, root)
        for emotion in ('cool', 'happy', 'gentle', 'shy'):
            prepare(silver if emotion == 'cool' else red,
                    silver_box if emotion == 'cool' else red_box,
                    root / 'emotions' / emotion)
