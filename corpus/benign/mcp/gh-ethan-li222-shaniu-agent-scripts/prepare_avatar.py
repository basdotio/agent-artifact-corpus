"""Download selected AIAvatar avatars and a shared Wav2Lip checkpoint.

Files stay in Shaniu/data/avatar; the upstream checkout is unchanged.
"""
import hashlib
import argparse
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shaniu.avatar_catalog import AVATARS, DOWNLOADABLE_AVATARS, DEFAULT_AVATAR
DATA = ROOT / 'data/avatar'
BASE = 'https://huggingface.co/shibing624/ai-avatar-wav2lip/resolve/main'


def download(name, destination):
    for attempt in range(3):
        try:
            return download_once(name, destination)
        except (OSError, RuntimeError):
            if attempt == 2:
                raise
            print(f'Resuming {name}', flush=True)


def download_once(name, destination):
    if destination.is_file() and (destination.suffix != '.zip' or zipfile.is_zipfile(destination)):
        print(f'Existing: {name}', flush=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.part')
    if destination.is_file():
        destination.replace(partial)
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {'User-Agent': 'Shaniu-development/0.2'}
    if offset:
        headers['Range'] = f'bytes={offset}-'
    request = urllib.request.Request(f'{BASE}/{name}?download=true', headers=headers)
    print(f'Downloading {name}', flush=True)
    last = 0
    response = urllib.request.urlopen(request, timeout=60)
    resumed = response.status == 206 and offset > 0
    if resumed and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
        response.close()
        raise RuntimeError('Server returned an unexpected download range')
    expected = int(response.headers.get('Content-Length', 0))
    with response, partial.open('ab' if resumed else 'wb') as out:
        size = offset if resumed else 0
        initial = size
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
            size += len(chunk)
            if size - last >= 50 * 1024 * 1024:
                print(f'  {size // (1024 * 1024)} MiB', flush=True)
                last = size
    if expected and size - initial != expected:
        raise RuntimeError('Incomplete download; rerun to resume')
    if size < 1024:
        raise RuntimeError('Download is unexpectedly small')
    partial.replace(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='下载目录中的全部三套人物')
    parser.add_argument('--avatar', choices=[item['id'] for item in DOWNLOADABLE_AVATARS], default=DEFAULT_AVATAR)
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    model = DATA / 'wav2lip.pth'
    download('wav2lip.pth', model)
    for selected in [item['id'] for item in DOWNLOADABLE_AVATARS] if args.all else [args.avatar]:
        prepare(selected)
    with model.open('rb') as file:
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
    manifest = {'source': BASE, 'avatar': DEFAULT_AVATAR, 'model_sha256': digest,
                'avatars': [item for item in AVATARS if (DATA / item['id'] / 'coords.pkl').is_file()]}
    (DATA / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Avatars and checkpoint prepared in Shaniu/data/avatar', flush=True)


def prepare(selected):
    archive = DATA / (selected + '.zip')
    avatar = DATA / selected
    if not (avatar / 'prepared.json').is_file():
        download(selected + '.zip', archive)
        with zipfile.ZipFile(archive) as package:
            entries = package.infolist()
            if sum(e.file_size for e in entries) > 2 * 1024 ** 3:
                raise RuntimeError('Avatar archive exceeds size limit')
            for item in entries:
                if item.filename.startswith('__MACOSX/'):
                    continue
                target = (DATA / item.filename).resolve()
                if not target.is_relative_to(avatar.resolve()):
                    raise RuntimeError('Unsafe archive path')
                if item.is_dir():
                    continue
                # Extract only image assets and coordinates, never executable files.
                if target.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.pkl'}:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(item) as source, target.open('wb') as out:
                    while chunk := source.read(1024 * 1024):
                        out.write(chunk)
    if not all((avatar / name).exists() for name in ['full_imgs', 'face_imgs', 'coords.pkl']):
        raise RuntimeError('Avatar archive layout does not match expected structure')
    from render_avatar import CoordinateReader
    with (avatar / 'coords.pkl').open('rb') as file:
        coords = CoordinateReader(file).load()
    counts = [sum(p.suffix.lower() in {'.png', '.jpg', '.jpeg'} for p in (avatar / name).iterdir()) for name in ('full_imgs', 'face_imgs')]
    if not coords or counts != [len(coords), len(coords)]:
        raise RuntimeError('Avatar frame and coordinate counts do not match')
    from PIL import Image, ImageOps
    images = sorted(p for p in (avatar / 'full_imgs').iterdir() if p.suffix.lower() in {'.png', '.jpg', '.jpeg'})
    with Image.open(images[0]) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((480, 640))
        image.save(avatar / 'preview.jpg', quality=88)
    (avatar / 'prepared.json').write_text(json.dumps(dict(frames=len(coords), source=BASE)), encoding='utf-8')
    print(f'Prepared: {selected}', flush=True)


if __name__ == '__main__':
    main()
