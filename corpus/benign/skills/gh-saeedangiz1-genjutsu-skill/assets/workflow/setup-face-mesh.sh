#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
case "$(uname -s)" in
  Linux|Darwin) ;;
  *) echo "Use WSL2 Ubuntu on Windows; run this script inside WSL2."; exit 1 ;;
esac
FACE_PYTHON="${FACE_PYTHON:-python3.12}"
if ! command -v "$FACE_PYTHON" >/dev/null 2>&1; then
  echo "Install exact Python 3.12 and set FACE_PYTHON to its interpreter."; exit 1
fi
"$FACE_PYTHON" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else "Face mesh worker requires exact Python 3.12.")'
if [ ! -d .venv-face ]; then "$FACE_PYTHON" -m venv .venv-face; fi
if [ ! -x .venv-face/bin/python ]; then
  echo "Existing .venv-face is incompatible with this platform; move it aside and rerun."; exit 1
fi
.venv-face/bin/python -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else "Existing mesh worker needs exact Python 3.12; move it aside and rerun.")'
.venv-face/bin/python -m pip install mediapipe==1.1.0 av==19.0.1 pillow==12.3.0 numpy==2.5.3
.venv-face/bin/python - <<'PY'
from pathlib import Path
import os
import tempfile
import urllib.request

target = Path('models/face_landmarker.task')
if not target.is_file() or target.stat().st_size < 16:
    target.parent.mkdir(exist_ok=True)
    # Official versioned MediaPipe asset. This download never calls a billed provider.
    url = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'
    descriptor, temporary = tempfile.mkstemp(prefix='.face-landmarker-', suffix='.download', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output, urllib.request.urlopen(url, timeout=90) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if Path(temporary).stat().st_size < 1024 * 1024:
            raise RuntimeError('Downloaded face model is unexpectedly small; rerun setup-face-mesh.sh.')
        Path(temporary).replace(target)
    finally:
        Path(temporary).unlink(missing_ok=True)
print('Face model present:', target)
PY
.venv-face/bin/python -c 'import mediapipe,av,PIL,numpy; print("Face worker imports ready; inference has not been tested.")'
