#!/usr/bin/env bash
# Install / repair the onetake-videogen environment. Safe to rerun.
#
#   ./install.sh [--no-tts] [--no-link]
#
#   ONETAKE_HOME   where OneTake lives (default ~/OneTake)
#   CLAUDE_CONFIG_DIR / ~/.claude   where the skill gets symlinked (skills/onetake-videogen)
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
ONETAKE="${ONETAKE_HOME:-$HOME/OneTake}"
ONETAKE_URL="https://github.com/leejersey/OneTake"
ONETAKE_COMMIT="3a49104e2dfb9f2c7833e0ca7e1adfc4a07826d8"
PYTHON="${PYTHON:-python3}"
WITH_TTS=1; LINK=1
for arg in "$@"; do
  case "$arg" in
    --no-tts) WITH_TTS=0 ;;
    --no-link) LINK=0 ;;
    *) echo "unknown option $arg" >&2; exit 1 ;;
  esac
done

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
need() { command -v "$1" >/dev/null || { echo "missing: $1 ($2)" >&2; exit 1; }; }

say "Checking prerequisites"
need git "git"
need ffmpeg "ffmpeg with libass + librubberband, NVENC recommended"
need ffprobe "ffmpeg"
need node "Node.js 20+"
need npm "Node.js 20+"
"$PYTHON" -c 'import sys; assert (3, 10) <= sys.version_info[:2] < (3, 13), sys.version' \
  || { echo "Python 3.10-3.12 required (VoxCPM2 does not support 3.13 yet); set PYTHON=..." >&2; exit 1; }
for f in subtitles rubberband sidechaincompress; do
  ffmpeg -hide_banner -filters 2>/dev/null | grep -q " $f " || echo "warning: ffmpeg lacks the '$f' filter"
done
ffmpeg -hide_banner -encoders 2>/dev/null | grep -q h264_nvenc || echo "warning: no h264_nvenc, renders fall back to libx264 (slower)"

say "OneTake at $ONETAKE"
if [[ ! -d "$ONETAKE/.git" ]]; then
  git clone "$ONETAKE_URL" "$ONETAKE"
fi
# Large pip/npm temp files go to disk, not a tmpfs /tmp.
mkdir -p "$ONETAKE/storage/tmp"
export TMPDIR="$ONETAKE/storage/tmp"
cd "$ONETAKE"
if git apply --reverse --check "$REPO/patches/onetake-gpu-longvideo.patch" 2>/dev/null; then
  echo "patch already applied"
else
  git checkout -q "$ONETAKE_COMMIT"
  git apply "$REPO/patches/onetake-gpu-longvideo.patch"
  echo "patch applied on $ONETAKE_COMMIT"
fi
if [[ ! -f .env ]]; then
  cat > .env <<'ENV'
WHISPER_MODEL=large-v3-turbo
WHISPER_DEVICE=auto
VIDEO_ENCODER=auto
FFMPEG_TIMEOUT=0
MAX_FILE_SIZE=21474836480
RETENTION_HOURS=0
HOST=127.0.0.1
ENV
fi

say "OneTake Python env (faster-whisper, CUDA libs, librosa)"
[[ -x .venv/bin/python ]] || "$PYTHON" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt librosa soundfile pillow

if [[ $WITH_TTS == 1 ]]; then
  say "VoxCPM2 voice-over env (PyTorch, a few GB)"
  mkdir -p videogen
  [[ -x videogen/tts-venv/bin/python ]] || "$PYTHON" -m venv videogen/tts-venv
  videogen/tts-venv/bin/pip install -q --upgrade pip
  videogen/tts-venv/bin/pip install -q voxcpm soundfile
fi

say "OneTake web UI dependencies"
(cd frontend && npm install --no-audit --no-fund --silent)

say "Remotion"
(cd "$REPO/remotion" && npm install --no-audit --no-fund --silent)

say "vtracer (illustrated mode: traces generated art to SVG)"
if ! command -v vtracer >/dev/null; then
  if command -v cargo >/dev/null; then
    cargo install vtracer
  else
    echo "note: install Rust, then run 'cargo install vtracer' to use scripts/split.py"
  fi
fi

if [[ $LINK == 1 ]]; then
  SKILLS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
  mkdir -p "$SKILLS"
  if [[ -e "$SKILLS/onetake-videogen" && ! -L "$SKILLS/onetake-videogen" ]]; then
    echo "warning: $SKILLS/onetake-videogen exists and is not a symlink; leaving it alone"
  else
    ln -sfn "$REPO" "$SKILLS/onetake-videogen"
    echo "skill linked: $SKILLS/onetake-videogen -> $REPO"
  fi
fi

say "Done"
echo "Try in Claude Code:  /onetake-videogen edit ~/Videos/raw.mp4"
