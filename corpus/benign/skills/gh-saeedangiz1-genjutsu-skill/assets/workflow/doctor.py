"""Offline checks; never prints credential values or makes provider requests."""
import argparse
import importlib
import platform
import shutil
import subprocess
import sys
import sysconfig

from config import ROOT, setting
from platform_runtime import platform_guidance, venv_python


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-keys', action='store_true')
    parser.add_argument('--mesh', action='store_true', help='Require the separate Python 3.12 mesh worker and local model.')
    args = parser.parse_args(argv)
    if sysconfig.get_config_var('Py_GIL_DISABLED'):
        print('Free-threaded Python is unsupported by these compiled video wheels. Use regular CPython 3.12+ or the supported WSL2 runtime.')
        return 1
    failed = sys.version_info < (3, 12)
    print('Runtime platform:', platform.system(), platform.machine())
    print(platform_guidance())
    print('Python:', sys.version.split()[0], '(3.12+ required)')
    print('Dependency imports and configured-key checks are offline; no provider access or balance is tested.')
    for name in ['av', 'numpy', 'PIL', 'requests', 'fastapi', 'uvicorn', 'multipart', 'gradio_client', 'scipy', 'cv2']:
        try:
            importlib.import_module(name)
            print(name + ': OK')
        except Exception as exc:
            print(name + ': FAILED (' + type(exc).__name__ + ')')
            failed = True
    binary = shutil.which('rubberband')
    print('rubberband:', 'OK' if binary else 'MISSING — see references/setup.md')
    failed = failed or not binary
    if args.mesh:
        worker = venv_python(ROOT, '.venv-face')
        ready = False
        if worker.is_file():
            try:
                probe = subprocess.run([str(worker), '-c', 'import sys; assert sys.version_info[:2] == (3,12); import mediapipe,av,PIL,numpy'], capture_output=True, timeout=30, check=False)
                ready = probe.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                pass
        print('Face mesh worker (exact Python 3.12 + imports): ' + ('OK' if ready else 'MISSING/INCOMPATIBLE — run bash setup-face-mesh.sh'))
        model = ROOT / 'models' / 'face_landmarker.task'
        try:
            with model.open('rb') as handle:
                model_ready = len(handle.read(16)) == 16
        except OSError:
            model_ready = False
        print('Face mesh model: ' + ('readable (inference not tested)' if model_ready else 'MISSING/UNREADABLE — run bash setup-face-mesh.sh'))
        failed = failed or not ready or not model_ready
    missing = []
    for key in ['ENHANCOR_API_KEY', 'REPLICATE_API_TOKEN']:
        value = setting(key).strip()
        valid = bool(value) and not any(x in value.lower() for x in ['your_key', 'your_api', 'replace_me', 'placeholder'])
        print(key + ': ' + ('configured (not verified remotely)' if valid else 'MISSING'))
        if not valid:
            missing.append(key)
    if setting('MEDIA_HOST', 'tmpfiles') not in ['tmpfiles', 'catbox']:
        print('MEDIA_HOST must be tmpfiles or catbox')
        failed = True
    if not setting('ENHANCOR_WEBHOOK_URL'):
        print('WEBHOOK: not configured — launch the app with cloudflared or set your own HTTPS callback')
        missing.append('ENHANCOR_WEBHOOK_URL')
    if failed:
        print('DEPENDENCIES NOT READY')
        return 1
    if missing:
        print('LOCAL UI READY; GENERATION BLOCKED until required provider keys and callback are configured.')
        return 2 if args.require_keys else 0
    print('LOCAL SETUP READY; provider access/balance and video quality have not been verified.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
