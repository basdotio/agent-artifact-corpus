"""Mix score, voices and sound effects from audio.json on timeline.json.

    python3 scripts/mix_audio.py out/mix.wav                  # score, narrator, sound effects
    python3 scripts/mix_audio.py out/mix_vo.wav --vo main     # plus a voiceover (and the chorus, if generated)

- Score: starts at timeline.json musicStart (trim whole bars), optional intro lift until a time.
- Every cue is matched to its own loudness target (generated files come in at wildly different levels).
- All voices share one bus that ducks the score through a sidechain compressor (~7 dB); the bus is padded to the
  full length, otherwise the ducked score stops when the last voice ends.
- Two-pass loudnorm to -14 LUFS, true peak -1.5 dB.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from timeline import DUR, MUSIC_START, ROOT, resolve  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "audio.json")))
A = lambda p: os.path.join(ROOT, "assets", "audio", p)
FMT = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
_LOUD = {}


def loudness(path):
    if path not in _LOUD:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
        _LOUD[path] = float([l for l in r.stderr.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    return _LOUD[path]


def main(out, vo=None):
    inputs, parts, voices, sfx = [], [], [], []
    music = CFG.get("music", {})
    mfile = A(music.get("file", "music/score.mp3"))
    if os.path.exists(mfile):
        inputs += ["-i", mfile]
    else:  # no score yet: silence, so the rest of the mix still builds
        inputs += ["-f", "lavfi", "-t", str(DUR), "-i", "anullsrc=r=48000:cl=stereo"]
    lift = music.get("introLift", {})
    gain_expr = "1"
    if lift.get("db"):
        g, until, ramp = 10 ** (lift["db"] / 20), resolve(lift["until"]), lift.get("ramp", 0.75)
        gain_expr = f"if(lt(t,{until - ramp:.3f}),{g:.4f},if(lt(t,{until:.3f}),{g:.4f}+(1-{g:.4f})*(t-{until - ramp:.3f})/{ramp},1))"
    parts.append(f"[0:a]{FMT},atrim=start={MUSIC_START:.4f},asetpts=PTS-STARTPTS,volume='{gain_expr}':eval=frame[m]")
    n = 1

    def cue(path, place, target, labels, extra="", seg=None):
        nonlocal n
        gain = 10 ** ((target - loudness(path)) / 20)
        trim, at = "", place
        if seg:
            a, b = seg
            trim = f"atrim=start={a:.3f}" + (f":end={b:.3f}" if b else "") + ",asetpts=PTS-STARTPTS,"
            at = place + a
        ms = max(0, int(round(at * 1000)))
        inputs.extend(["-i", path])
        parts.append(f"[{n}:a]{FMT},{trim}{extra}volume={gain:.4f},adelay={ms}|{ms}[c{n}]")
        labels.append(f"[c{n}]")
        n += 1

    for c in CFG.get("narrator", []):
        cue(A(c["file"]), resolve(c["at"]), c.get("lufs", -16), voices)
    if vo:
        polish = "highpass=f=80,acompressor=threshold=-22dB:ratio=2.2:attack=6:release=140:makeup=1.2,"
        for ln in json.load(open(A(f"vo/{vo}/lines.json"))):
            for p in ln["parts"]:
                seg = (p["from"], p["to"]) if (p["from"] or p["to"]) else None
                cue(A(f"vo/{vo}/{ln['id']}.mp3"), p["place"], CFG["voice"].get("lufs", -16), voices, polish, seg)
        chorus = A("vo/chorus/lines.json")
        if os.path.exists(chorus):
            for i, c in enumerate(json.load(open(chorus))):
                room = f"highpass=f=100,aecho=0.8:0.5:40|70:0.15|0.08,stereotools=balance_out={0.25 if i % 2 else -0.25},"
                cue(A(f"vo/chorus/{c['id']}.mp3"), c["place"], -18.5, voices, room)
    for c in CFG.get("sfx", []):
        if os.path.exists(A(c["file"])):
            cue(A(c["file"]), resolve(c["at"]), c.get("lufs", -27), sfx)

    def bus(labels, name):
        if labels:
            parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,apad=whole_dur={DUR:.3f}[{name}]")
        else:
            parts.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{DUR:.3f},{FMT}[{name}]")

    bus(voices, "vbus")
    bus(sfx, "sfx")
    parts.append("[vbus]asplit=2[vkey][vmix]")
    parts.append("[m][vkey]sidechaincompress=threshold=0.03:ratio=4:attack=25:release=420:knee=4[mduck]")
    parts.append(f"[mduck]apad=whole_dur={DUR:.3f}[mfull]")
    parts.append(f"[mfull][vmix][sfx]amix=inputs=3:normalize=0:duration=longest,atrim=0:{DUR:.3f}[mix]")
    tmp = out.replace(".wav", "_pre.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(parts), "-map", "[mix]", "-ar", "48000", tmp], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
    if m["input_i"] in ("-inf", "inf") or float(m["input_i"]) < -70:  # silence (no score or cues yet): nothing to normalize
        os.replace(tmp, out)
        print("wrote", out, f"({DUR:.2f}s, silent: add a score and cues)")
        return
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", af, "-ar", "48000", out], check=True)
    os.remove(tmp)
    print("wrote", out, f"({DUR:.2f}s, pre-norm {m['input_i']} LUFS)")


if __name__ == "__main__":
    args = sys.argv[1:]
    vo = args[args.index("--vo") + 1] if "--vo" in args else None
    out = next((a for a in args if a.endswith(".wav")), os.path.join(ROOT, "out", "mix.wav"))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    main(out, vo)
