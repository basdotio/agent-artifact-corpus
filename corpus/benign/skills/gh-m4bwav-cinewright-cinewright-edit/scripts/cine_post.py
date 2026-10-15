#!/usr/bin/env python3
# copied from shared/lib/cine_post.py sha256:3a4c97a577f657b640050d4588594ce4f56e4fbe3016b3ef15302c8d1177a1b7; edit the source
"""cinewright post tools: animatic before any video spend, and one grade across every shot after.

Run it; do not read it. Python 3.9+, standard library only, ffmpeg and ffprobe on PATH.

  python scripts/cine_post.py animatic PROJECT --stills DIR [--audio WAV] [--size 960x540] [--out FILE]
  python scripts/cine_post.py grade measure FILE ...
  python scripts/cine_post.py grade match --ref STILL FILE ... [--luma N] [--strength S] [--cube-dir DIR]
                                         [--apply DIR [--look LOOK.cube] [--grain N]]

animatic: one still per card (DIR/<card id>.png|jpg|webp, e.g. the approved first frames), held for the
card's duration with its camera move suggested by a slow push or drift, over a scratch audio track; a
card with no still shows a grey frame. Writes the video and a timing sheet (<out>.timing.md) with each
card's in and out point, beat and lines, which lock the cut before a render is paid for.

grade: measure prints each file's mean and spread per RGB channel and its luma; match fits every file to
a hero still (per-channel mean and spread, scaled by --strength) and writes one 3D LUT per file
(.cube, 17 points, readable by ffmpeg lut3d, Resolve and Premiere); --luma also sets a mean luma target,
for light that falls scene by scene; --apply writes graded copies with ffmpeg lut3d: the match, then the
film's one look LUT (--look), then grain (--grain, ffmpeg noise strength; 4 to 8 reads as fine film grain).
Stats are pooled over up to 12 frames a shot, so the correction is one fixed transform and cannot flicker.
"""
import argparse
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("cine_runtime", HERE / "cine.py")
cine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cine)

STILL_EXT = (".png", ".jpg", ".jpeg", ".webp")
# a card's camera move as a zoompan over a still: (zoom start, zoom end, x drift as a share of the width)
MOVE_PAN = {"dolly-in": (1.0, 1.12, 0), "zoom-in": (1.0, 1.12, 0), "dolly-out": (1.12, 1.0, 0), "zoom-out": (1.12, 1.0, 0),
            "truck-left": (1.08, 1.08, -0.06), "truck-right": (1.08, 1.08, 0.06), "pan-left": (1.08, 1.08, -0.06),
            "pan-right": (1.08, 1.08, 0.06), "track": (1.06, 1.06, 0.04), "crane-up": (1.06, 1.1, 0),
            "crane-down": (1.1, 1.06, 0)}
FPS = 24


def ts(seconds):
    m, s = divmod(seconds, 60)
    return "%02d:%06.3f" % (m, s)


def find_still(stills, cid):
    for ext in STILL_EXT:
        f = stills / (cid + ext)
        if f.is_file():
            return f
    return None


def segment(ff, still, card, w, h, out):
    """One card as a clip: the still scaled to cover the frame, its move as a slow zoompan, or grey."""
    dur = float(card["duration_s"])
    n = max(1, int(round(dur * FPS)))
    if still is None:
        args = [ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x404040:s=%dx%d:r=%d:d=%.3f" % (w, h, FPS, dur)]
    else:
        z0, z1, dx = MOVE_PAN.get(card["camera"].get("move"), (1.0, 1.0, 0))
        # work at 2x so zoompan's integer crop steps do not judder
        zoom = "%.4f+(%.4f)*on/%d" % (z0, z1 - z0, n)
        x = "(iw-iw/zoom)/2+(%.4f)*iw*(on/%d-0.5)" % (dx, n)
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
              "zoompan=z='%s':x='%s':y='(ih-ih/zoom)/2':d=%d:s=%dx%d:fps=%d") % (w * 2, h * 2, w * 2, h * 2, zoom, x, n, w, h, FPS)
        args = [ff, "-y", "-loglevel", "error", "-loop", "1", "-i", str(still), "-vf", vf, "-frames:v", str(n)]
    cine.run_tool(args + ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "20", "-r", str(FPS), str(out)])


def cmd_animatic(a):
    p = cine.Project(a.project)
    ff = cine.need_tool("ffmpeg")
    stills = Path(a.stills)
    w, h = (int(x) for x in a.size.lower().split("x"))
    out = Path(a.out or Path(a.project) / "animatic.mp4")
    work = out.parent / (out.stem + "_parts")
    work.mkdir(parents=True, exist_ok=True)
    rows, missing, t = [], [], 0.0
    lst = []
    for c in p.cards:
        still = find_still(stills, c["id"])
        if still is None:
            missing.append(c["id"])
        part = work / ("%03d_%s.mp4" % (len(lst), c["id"]))
        segment(ff, still, c, w, h, part)
        lst.append("file '%s'" % part.resolve().as_posix())
        lines = " / ".join("%s: %s" % (p.chars[d["character"]]["name"], d["line"]) for d in c.get("dialogue", []))
        rows.append((c["id"], t, t + c["duration_s"], c.get("beat", ""), lines, still.name if still else "(grey)"))
        t += c["duration_s"]
    (work / "list.txt").write_text("\n".join(lst) + "\n", encoding="utf-8")
    args = [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "list.txt")]
    if a.audio:
        # the scratch track sets nothing: the cards' durations are the cut, the audio is trimmed or padded to it
        args += ["-i", a.audio, "-map", "0:v", "-map", "1:a", "-af", "apad", "-t", "%.3f" % t, "-c:a", "aac"]
    cine.run_tool(args + ["-c:v", "copy", str(out)])
    sheet = ["# Animatic timing: %s" % p.style.get("title", ""), "",
             "%d cards, %s total. Stills from `%s`." % (len(rows), ts(t), stills.as_posix()), "",
             "| card | in | out | s | beat | lines | still |", "|---|---|---|---|---|---|---|"]
    for cid, a0, a1, beat, lines, still in rows:
        sheet.append("| %s | %s | %s | %g | %s | %s | %s |" % (cid, ts(a0), ts(a1), a1 - a0, beat.replace("|", "/"), lines.replace("|", "/"), still))
    timing = out.with_suffix(".timing.md")
    timing.write_text("\n".join(sheet) + "\n", encoding="utf-8")
    print("wrote %s (%s) and %s" % (out, ts(t), timing))
    if missing:
        print("no still for %s: grey frames; put <card id>.png in %s" % (", ".join(missing), stills))
    return 0


# ---------- grade ----------

def frames_rgb(path, size=(64, 36), fps=1.0, max_frames=12):
    """Small RGB frames from a still or a clip, as one flat byte string per frame."""
    ff = cine.need_tool("ffmpeg")
    w, h = size
    vf = "scale=%d:%d" % (w, h)
    args = [ff, "-v", "error", "-i", str(path)]
    if Path(path).suffix.lower() not in STILL_EXT:
        vf = "fps=%g,%s" % (fps, vf)
        args += ["-frames:v", str(max_frames)]
    r = subprocess.run(args + ["-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise SystemExit("ffmpeg could not read %s: %s" % (path, r.stderr.decode(errors="replace")[-300:]))
    n = w * h * 3
    return [r.stdout[i:i + n] for i in range(0, len(r.stdout) - n + 1, n)]


def stats(path):
    """Mean and standard deviation per channel (0..1) and Rec.709 mean luma (0..255 full range)."""
    sums, sq, count = [0.0] * 3, [0.0] * 3, 0
    for fr in frames_rgb(path):
        for c in range(3):
            ch = fr[c::3]
            sums[c] += sum(ch)
            sq[c] += sum(v * v for v in ch)
        count += len(fr) // 3
    mean = [s / count / 255 for s in sums]
    sd = [math.sqrt(max(0.0, q / count / 65025 - m * m)) for q, m in zip(sq, mean)]
    luma = 255 * (0.2126 * mean[0] + 0.7152 * mean[1] + 0.0722 * mean[2])
    return {"mean": mean, "sd": sd, "luma": luma}


def fit(src, ref, strength=1.0, luma=None):
    """Per-channel gain and offset that move src's mean and spread toward ref's (Reinhard, in RGB),
    blended by strength; then one shared gain so the mean luma lands on `luma` when given."""
    gains, offs = [], []
    for c in range(3):
        g = ref["sd"][c] / src["sd"][c] if src["sd"][c] > 1e-4 else 1.0
        g = min(2.5, max(0.4, g))  # a near-flat shot would otherwise blow up its noise
        o = ref["mean"][c] - g * src["mean"][c]
        gains.append(1 + strength * (g - 1))
        offs.append(strength * o)
    if luma is not None:
        now = 255 * sum(k * (g * m + o) for k, g, m, o in zip((0.2126, 0.7152, 0.0722), gains, src["mean"], offs))
        k = luma / now if now > 1 else 1.0
        gains = [g * k for g in gains]
        offs = [o * k for o in offs]
    return gains, offs


def write_cube(path, gains, offs, n=17, title="cinewright match"):
    lines = ['TITLE "%s"' % title, "LUT_3D_SIZE %d" % n, "DOMAIN_MIN 0 0 0", "DOMAIN_MAX 1 1 1"]
    for b in range(n):  # .cube order: red changes fastest
        for g in range(n):
            for r in range(n):
                v = [x / (n - 1) for x in (r, g, b)]
                lines.append(" ".join("%.6f" % min(1.0, max(0.0, gains[i] * v[i] + offs[i])) for i in range(3)))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_grade(a):
    if a.cmd == "measure":
        for f in a.files:
            s = stats(f)
            print("%s  luma %.1f  mean %s  sd %s" % (f, s["luma"], " ".join("%.3f" % x for x in s["mean"]), " ".join("%.3f" % x for x in s["sd"])))
        return 0
    ref = stats(a.ref)
    print("ref %s  luma %.1f" % (a.ref, ref["luma"]))
    cube_dir = Path(a.cube_dir or Path(a.files[0]).parent / "grade")
    cube_dir.mkdir(parents=True, exist_ok=True)
    report = {"ref": str(a.ref), "strength": a.strength, "luma": a.luma, "files": {}}
    ff = cine.need_tool("ffmpeg") if a.apply else None
    for f in a.files:
        s = stats(f)
        gains, offs = fit(s, ref, a.strength, a.luma)
        cube = cube_dir / (Path(f).stem + ".cube")
        write_cube(cube, gains, offs, title="match %s to %s" % (Path(f).name, Path(a.ref).name))
        row = {"luma": round(s["luma"], 1), "gain": [round(x, 3) for x in gains], "offset": [round(x, 4) for x in offs], "cube": cube.name}
        if a.apply:
            dest = Path(a.apply) / Path(f).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            # lut3d wants a path ffmpeg can parse inside a filter string: forward slashes, colon escaped
            lut = cube.resolve().as_posix().replace(":", r"\:")
            chain = ["lut3d=file='%s'" % lut]
            if a.look:
                chain.append("lut3d=file='%s'" % Path(a.look).resolve().as_posix().replace(":", r"\:"))
            if a.grain:
                chain.append("noise=alls=%d:allf=t" % a.grain)
            args = [ff, "-y", "-loglevel", "error", "-i", str(f), "-vf", ",".join(chain)]
            if Path(f).suffix.lower() not in STILL_EXT:
                args += ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy"]
            cine.run_tool(args + [str(dest)])
            row["after_luma"] = round(stats(dest)["luma"], 1)
        report["files"][str(f)] = row
        print("%s  luma %.1f -> %s  gain %s" % (f, s["luma"], row.get("after_luma", "(not applied)"), " ".join("%.2f" % x for x in gains)))
    (cube_dir / "grade.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("cubes and grade.json in %s" % cube_dir)
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="cine_post.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_subparsers(dest="group", required=True)
    s = g.add_parser("animatic", help="stills timed to the cards, over scratch audio, plus a timing sheet")
    s.add_argument("project")
    s.add_argument("--stills", required=True, help="folder of <card id>.png|jpg|webp")
    s.add_argument("--audio", help="scratch track (temp voices, music) laid under the stills")
    s.add_argument("--size", default="960x540")
    s.add_argument("--out", help="default PROJECT/animatic.mp4")
    gr = g.add_parser("grade", help="measure shots, match them to a hero still").add_subparsers(dest="cmd", required=True)
    s = gr.add_parser("measure")
    s.add_argument("files", nargs="+")
    s = gr.add_parser("match")
    s.add_argument("files", nargs="+")
    s.add_argument("--ref", required=True, help="the hero still every shot is matched to")
    s.add_argument("--strength", type=float, default=0.7, help="0 = no change, 1 = full match (default 0.7)")
    s.add_argument("--luma", type=float, help="mean luma target 0-255 (full range), e.g. darker for night scenes")
    s.add_argument("--cube-dir", help="where the .cube files and grade.json go (default <first file's folder>/grade)")
    s.add_argument("--apply", metavar="DIR", help="write graded copies here")
    s.add_argument("--look", metavar="CUBE", help="the film's one look LUT, applied after the match (with --apply)")
    s.add_argument("--grain", type=int, default=0, help="film grain after the look, ffmpeg noise strength (with --apply)")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    return cmd_animatic(a) if a.group == "animatic" else cmd_grade(a)


if __name__ == "__main__":
    sys.exit(main())
