#!/usr/bin/env bash
# macOS + OBS: record one app's front window edge-to-edge for N seconds (no black bars, no audio).
# One-time OBS setup: Tools > WebSocket Server Settings (enable, note password); add a scene with a
# "macOS Screen Capture" source, Method = Application Capture, Application = the app to record.
# usage: OBS_WS_PASSWORD=... scripts/record_window.sh <seconds> <out.mp4> [app-name=Claude] [scene] [source]
set -euo pipefail
secs="$1"; out="$2"; app="${3:-Claude}"
scene="${4:-Claude App Demo}"; source="${5:-Claude App Capture}"
here="$(cd "$(dirname "$0")" && pwd)"
obs() { node "$here/obs.js" "$@"; }
# field <key>: pull one value out of an obs.js JSON line
field() { python3 -c "import json,sys; print(json.loads(sys.stdin.readline())['data']['$1'])"; }
read X Y W H CW CH <<< "$(swift - "$app" <<'SWIFT'
import CoreGraphics
let app = CommandLine.arguments[1]
let main = CGDisplayBounds(CGMainDisplayID())
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as! [[String: Any]]
for w in list {
  guard let o = w[kCGWindowOwnerName as String] as? String, o == app,
        let l = w[kCGWindowLayer as String] as? Int, l == 0,
        let b = w[kCGWindowBounds as String] as? [String: Any],
        let wd = b["Width"] as? Int, wd > 400 else { continue }
  print(b["X"]!, b["Y"]!, wd, b["Height"]!, Int(main.width), Int(main.height)); break
}
SWIFT
)"
[ -n "${W:-}" ] || { echo "no on-screen window for $app" >&2; exit 1; }
echo "window ${W}x${H} at $X,$Y on ${CW}x${CH} display"
VW=$(obs GetVideoSettings '{}' | field baseWidth)
VH=$(obs GetVideoSettings '{}' | field baseHeight)
id=$(obs GetSceneItemId "{\"sceneName\":\"$scene\",\"sourceName\":\"$source\"}" | field sceneItemId)
obs SetSceneItemTransform "{\"sceneName\":\"$scene\",\"sceneItemId\":$id,\"sceneItemTransform\":{\"cropLeft\":$X,\"cropTop\":$Y,\"cropRight\":$((CW-X-W)),\"cropBottom\":$((CH-Y-H)),\"boundsType\":\"OBS_BOUNDS_SCALE_INNER\",\"boundsWidth\":$VW,\"boundsHeight\":$VH,\"boundsAlignment\":0,\"positionX\":$((VW/2)),\"positionY\":$((VH/2)),\"alignment\":0}}" >/dev/null
obs SetCurrentProgramScene "{\"sceneName\":\"$scene\"}" >/dev/null
sleep 1
obs StartRecord '{}' >/dev/null
sleep "$secs"
raw=$(obs StopRecord '{}' | field outputPath)
sleep 3
read SW SH OX OY <<< "$(python3 -c "
W,H,VW,VH=$W,$H,$VW,$VH; s=min(VW/W,VH/H); sw=int(W*s)//2*2; sh=int(H*s)//2*2
print(sw, sh, (VW-sw)//2, (VH-sh)//2)")"
ffmpeg -y -loglevel error -i "$raw" -vf "crop=$SW:$SH:$OX:$OY,fps=30,format=yuv420p" -an \
  -c:v libx264 -preset slow -crf 18 -movflags +faststart "$out"
mv "$raw" "${out%.*}_raw.${raw##*.}"
ffprobe -v error -show_entries stream=width,height:format=duration -of compact "$out"
