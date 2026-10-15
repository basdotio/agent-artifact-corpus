#!/usr/bin/env python3
"""
EXAMPLE WORKER — Windows render-farm worker (Surface laptop, NVIDIA GPU).
Tier 1 (encode/finishing) + Tier 2 (overnight render overflow).

This is NOT part of the MCP server. It is a standalone pull-worker from the
same lab, included as an example of the gated, interruptible worker pattern.
It depends on two queue helper scripts on the queue host (surface_claim.py,
surface_mark.py) that are NOT included in this repo; adapt to your own queue.

Runs on the Windows laptop. Pulls jobs from its queue on the queue host:
    <remote-root>/jobs/jobs-surface.json   (same schema as the Linux queues)
over SSH, renders / encodes locally, pushes outputs back to the queue host.

HARD GATES — no job starts or CONTINUES unless ALL hold:
  * on AC power            (Win32_Battery; desktops/no-battery count as AC)
  * user idle >= 10 min    (GetLastInputInfo; a job is INTERRUPTED the moment
                            input is detected, the GPU overheats, or AC drops —
                            ComfyUI prompts are cancelled via /interrupt,
                            ffmpeg is terminated, and the job is requeued)
  * GPU temp < 83 C        (nvidia-smi; resume only below 75 C)
Tier 2 RENDER jobs (prod/exp/art) additionally run ONLY 21:00-08:00 local time
(RENDER_TZ_ID below).
Tier 1 ENCODE jobs may run any time the gates hold (short and bursty).

Render recipe is "Recipe C", identical to the Linux render workers in the lab:
  LTX-2.3 i2v, 145 frames @24fps, 768x512, 16 steps, CFG 3.0, euler/simple, denoise 1.0.
ComfyUI is started on demand for render jobs and stopped when gates fail or the
render window closes, so it never sits on the GPU while the owner uses the machine.
"""
import base64
import ctypes
import json
import os
import shutil
import subprocess
import sys
import paramiko  # pure-python SSH (Windows OpenSSH binary hangs under subprocess)
import time
import urllib.request
import urllib.error
import uuid
from datetime import datetime

# ------------------------------- config ------------------------------------
THIS = "surface"
ARK_ROOT   = r"C:\ARK"
PLATE_DIR  = os.path.join(ARK_ROOT, "plates")
VIDEO_DIR  = os.path.join(ARK_ROOT, "video")
SCRATCH_DIR = os.path.join(ARK_ROOT, "scratch")
LOG_DIR    = os.path.join(ARK_ROOT, "logs")
SSH_KEY    = os.path.join(ARK_ROOT, "ssh", "id_ed25519")  # generate your own keypair
QUEUE_HOST = "<queue-host>"      # ADAPT: hostname/IP of the machine holding the queue
QUEUE_USER = "labuser"           # ADAPT: SSH user on the queue host
REMOTE_ROOT = "/home/labuser/render-queue"  # ADAPT
QUEUE_PATH = f"{REMOTE_ROOT}/jobs/jobs-surface.json"
CLAIM_PY   = f"{REMOTE_ROOT}/surface_claim.py"   # not included in this repo
MARK_PY    = f"{REMOTE_ROOT}/surface_mark.py"    # not included in this repo
SPARK_VIDEO_DIR = f"{REMOTE_ROOT}/video-surface"  # this worker's own output dir
# (separate from the Linux workers' video/ dir so a per-box collector never
# misattributes this worker's renders)
MANIFEST_LOCAL  = os.path.join(LOG_DIR, "manifest.jsonl")
MANIFEST_SPARK  = f"{REMOTE_ROOT}/surface-manifest.jsonl"

COMFY_ROOT = r"C:\ARK\ComfyUI_windows_portable"
COMFY_PY   = os.path.join(COMFY_ROOT, "python_embeded", "python.exe")
COMFY_MAIN = os.path.join(COMFY_ROOT, "ComfyUI", "main.py")
COMFY_URL  = "http://127.0.0.1:8189"

IDLE_MINUTES   = 10
GPU_TEMP_MAX   = 83
GPU_TEMP_RESUME = 75
RENDER_OPEN_H  = 21   # local hour in RENDER_TZ_ID
RENDER_CLOSE_H = 8
RENDER_TZ_ID   = "Eastern Standard Time"  # ADAPT: Windows time zone id
FFMPEG = r"C:\ARK\ffmpeg7\ffmpeg.exe"  # FFmpeg 7.1 (NVENC API compat with driver 591.55; 9.x needs driver 610+)

def local_hour():
    """Current hour in RENDER_TZ_ID using Windows' built-in time zone
    (no tzdata needed for the embedded Python). Returns None on failure."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[TimeZoneInfo]::ConvertTimeBySystemTimeZoneId("
             f"(Get-Date).ToUniversalTime(), '{RENDER_TZ_ID}').Hour"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return int(out.split()[0])
    except Exception:
        return None

# Recipe C — MUST match ep2_loop_worker.py exactly
STYLE_ARK = ("Stylized 2D animation for adults, textured folkcut shadows, "
             "paper grain, desert-cosmic color, flat graphic shapes, carved shadows")
NEG_VID = ("photorealistic, 3d render, glossy, scary, horror, blurry, distorted faces, "
           "photorealistic faces, extra limbs, watermark, text, flicker, static frame, "
           "ladder, ladders, spare tire, spare wheel, badge, logo, lettering, emblem, "
           "roof rack, extra roof marker lights, wrong number of marker lights, "
           "zoom in, zoom out, push in, pull back, dolly, orbit, crash zoom")
CKPT = "ltx-2.3-22b-dev-fp8.safetensors"
TEXT_ENC = "gemma_3_12B_it_fp4_mixed.safetensors"

comfy_proc = None
_paused_hot = False   # latched until temp drops below resume threshold

# ------------------------------- logging -----------------------------------
def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{THIS}] {msg}"
    print(line, flush=True)
    try:
        with open(os.path.join(LOG_DIR, "worker.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ------------------------------- gates -------------------------------------
class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]

def idle_minutes():
    lii = _LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        return 0.0
    tick = ctypes.windll.kernel32.GetTickCount64()
    return max(0.0, (tick - lii.dwTime) / 60000.0)

def on_ac_power():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Battery | Select-Object -ExpandProperty BatteryStatus"],
            capture_output=True, text=True, timeout=30).stdout
        vals = [v.strip() for v in out.replace(",", " ").split() if v.strip().isdigit()]
        if not vals:
            return True   # no battery -> desktop-style, treat as AC
        # 2 = on AC, 3 = fully charged (implies AC)
        return any(v in ("2", "3") for v in vals)
    except Exception:
        return False

def gpu_temp():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return int(out.split()[0])
    except Exception:
        return None

def in_render_window():
    h = local_hour()
    if h is None:
        return False  # fail closed: no renders when the clock is unreadable
    return h >= RENDER_OPEN_H or h < RENDER_CLOSE_H

def gates_ok():
    """(ok, reason). Render-window is checked separately by the caller."""
    global _paused_hot
    if not on_ac_power():
        return False, "not on AC power"
    if idle_minutes() < IDLE_MINUTES:
        return False, f"user active (idle {idle_minutes():.1f}m < {IDLE_MINUTES}m)"
    t = gpu_temp()
    if t is None:
        return False, "gpu temp unreadable"
    if t >= GPU_TEMP_MAX:
        _paused_hot = True
        return False, f"gpu hot ({t}C >= {GPU_TEMP_MAX}C)"
    if _paused_hot:
        if t >= GPU_TEMP_RESUME:
            return False, f"gpu cooling ({t}C >= resume {GPU_TEMP_RESUME}C)"
        _paused_hot = False
        log(f"gpu cooled to {t}C, resuming")
    return True, "ok"

# ------------------------------- ssh ---------------------------------------
def _ssh_client():
    c = paramiko.SSHClient()
    # NOTE: AutoAddPolicy trusts any host key on first use. For anything beyond
    # a private tailnet, load a pinned known_hosts and use RejectPolicy instead.
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(QUEUE_HOST, username=QUEUE_USER,
              key_filename=SSH_KEY, timeout=15, banner_timeout=15)
    return c

def ssh_run(remote_cmd, timeout=120):
    c = _ssh_client()
    try:
        _, stdout, stderr = c.exec_command(remote_cmd, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if stdout.channel.recv_exit_status() != 0:
            raise RuntimeError(f"ssh failed: {err.strip()[:200]}")
        return out
    finally:
        c.close()

def scp_from(remote_path, local_path, timeout=600):
    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    c = _ssh_client()
    try:
        sftp = c.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
    finally:
        c.close()

def scp_to(local_path, remote_path, timeout=600):
    c = _ssh_client()
    try:
        sftp = c.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
    finally:
        c.close()

# ------------------------------- queue -------------------------------------
def claim_job(kinds):
    out = ssh_run(f"python3 {CLAIM_PY} {QUEUE_PATH} {THIS} " + " ".join(kinds),
                  timeout=60).strip()
    if out == "NONE" or not out:
        return None
    return json.loads(out)

def mark_job(job, ok, size=0, note="", requeue=False):
    jid = job.get("job_id") or f"{job.get('shot_id')}_take{job.get('take')}"
    res = json.dumps({"job_id": jid, "ok": ok, "worker": THIS,
                      "bytes": size, "note": note, "requeue": requeue})
    # single-quoted for remote bash; json uses double quotes
    safe = res.replace("'", "")
    ssh_run(f"python3 {MARK_PY} {QUEUE_PATH} '{safe}'", timeout=60)

# ------------------------------- comfy -------------------------------------
def comfy_running():
    try:
        with urllib.request.urlopen(COMFY_URL + "/system_stats", timeout=10) as r:
            return r.status == 200
    except Exception:
        return False

def start_comfy():
    global comfy_proc
    if comfy_running():
        return True
    if not os.path.exists(COMFY_MAIN):
        log("comfy not installed yet, skipping render jobs")
        return False
    log("starting ComfyUI")
    comfy_proc = subprocess.Popen(
        [COMFY_PY, "-s", COMFY_MAIN,
         "--windows-standalone-build",
         "--listen", "127.0.0.1", "--port", "8189",
         "--bf16-unet", "--bf16-vae", "--bf16-text-enc",
         "--disable-auto-launch"],
        cwd=COMFY_ROOT,
        stdout=open(os.path.join(LOG_DIR, "comfy_stdout.log"), "ab"),
        stderr=subprocess.STDOUT)
    for _ in range(60):
        time.sleep(5)
        if comfy_running():
            log("ComfyUI up")
            return True
    log("ComfyUI failed to come up")
    return False

def stop_comfy():
    global comfy_proc
    if comfy_proc and comfy_proc.poll() is None:
        log("stopping ComfyUI")
        comfy_proc.terminate()
        try:
            comfy_proc.wait(timeout=30)
        except Exception:
            comfy_proc.kill()
    comfy_proc = None
    # belt and braces: kill any stray embedded python still serving 8189
    try:
        subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI",
                        "WINDOWTITLE eq ComfyUI*"],
                       capture_output=True, timeout=15)
    except Exception:
        pass

def comfy_post(path, data=None, timeout=120):
    req = urllib.request.Request(
        COMFY_URL + path,
        data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"comfy HTTP {e.code}: {e.read().decode()[:300]}")

def comfy_interrupt():
    """Cancel the currently running prompt (gate failure mid-render)."""
    try:
        comfy_post("/interrupt", {}, timeout=15)
        log("comfy: interrupt sent")
    except Exception as e:
        log(f"comfy: interrupt failed ({e}), will stop_comfy() instead")
    stop_comfy()

ABORTED = "ABORTED"  # sentinel: gates failed mid-job -> requeue, not fail

def upload_plate(path):
    data = open(path, "rb").read()
    boundary = uuid.uuid4().hex
    fname = os.path.basename(path)
    ctype = "image/png" if fname.endswith(".png") else "image/webp"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
            f"filename=\"{fname}\"\r\nContent-Type: {ctype}\r\n\r\n".encode() + data +
            f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n"
            f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        COMFY_URL + "/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r).get("name", fname)

def queue_i2v(keyframe_file, motion_prompt, seed, shot_id, take, steps=16, cfg=3.0,
              w=768, h=512, sampler="euler", scheduler="simple", denoise=1.0):
    wf = {
        "0": {"class_type": "LTXAVTextEncoderLoader", "inputs": {
            "text_encoder": TEXT_ENC, "ckpt_name": CKPT, "device": "default"}},
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {
            "ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["0", 0],
            "text": f"{STYLE_ARK}. SUBTLE SCENE MOTION, LOCKED CAMERA: {motion_prompt}"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["0", 0], "text": NEG_VID}},
        "4": {"class_type": "LoadImage", "inputs": {"image": keyframe_file}},
        "5": {"class_type": "LTXVImgToVideo", "inputs": {
            "positive": ["2", 0], "negative": ["3", 0], "vae": ["1", 2], "image": ["4", 0],
            "width": w, "height": h, "length": 145, "batch_size": 1, "strength": 1.0}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1], "latent_image": ["5", 2],
            "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": sampler,
            "scheduler": scheduler, "denoise": denoise}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "VHS_VideoCombine", "inputs": {
            "images": ["7", 0], "frame_rate": 24, "filename_prefix": f"ep2_{shot_id}_t{take}",
            "format": "video/h264-mp4", "loop_count": 0, "pingpong": False, "save_output": True}},
    }
    return comfy_post("/prompt", {"prompt": wf})["prompt_id"]

def wait_done(pid, label, poll=30, tries=200):
    for _ in range(tries):
        time.sleep(poll)
        # IN-FLIGHT GATE CHECK: never continue a render when gates fail.
        ok, reason = gates_ok()
        if not ok:
            log(f"{label}: gates failed mid-render ({reason}) — interrupting")
            comfy_interrupt()
            return ABORTED
        if not in_render_window():
            log(f"{label}: render window closed mid-render — interrupting")
            comfy_interrupt()
            return ABORTED
        try:
            hist = comfy_post(f"/history/{pid}", timeout=30)
        except Exception:
            continue
        if pid in hist:
            st = hist[pid].get("status", {})
            if st.get("status_str") == "error":
                log(f"{label} ERROR: {json.dumps(st.get('messages', []))[:300]}")
                return None
            return hist[pid]
    log(f"{label} TIMEOUT")
    return None

def render_job(job):
    shot, take = job["shot_id"], job["take"]
    steps = job.get("steps", 16); cfg = job.get("cfg", 3.0)
    w = job.get("width", 768); h = job.get("height", 512)
    sampler = job.get("sampler", "euler"); scheduler = job.get("scheduler", "simple")
    denoise = job.get("denoise", 1.0)
    plate_name = os.path.basename(job["plate"])
    local_plate = os.path.join(PLATE_DIR, plate_name)
    for attempt, seed in enumerate([job["seed"], job["seed"] + 500]):
        try:
            if not os.path.exists(local_plate):
                log(f"{shot} t{take}: fetching plate")
                scp_from(job["plate"], local_plate)
            kf = upload_plate(local_plate)
            log(f"{shot} t{take}: queued (seed {seed}, {steps}st cfg {cfg}, "
                f"{sampler}/{scheduler}, dn {denoise}, attempt {attempt+1})")
            pid = queue_i2v(kf, job["motion"], seed, shot, take,
                            steps, cfg, w, h, sampler, scheduler, denoise)
            hist = wait_done(pid, f"{shot} t{take}")
            if hist == ABORTED:
                return None, {"aborted": True, "note": "gates failed mid-render"}
            if not hist:
                continue
            for node_out in hist["outputs"].values():
                for g in node_out.get("gifs", []):
                    url = (f"{COMFY_URL}/view?filename={g['filename']}"
                           f"&subfolder={g.get('subfolder','')}&type=output")
                    dst = os.path.join(VIDEO_DIR, f"{shot}_take{take}.mp4")
                    urllib.request.urlretrieve(url, dst)
                    sz = os.path.getsize(dst)
                    remote = f"{SPARK_VIDEO_DIR}/{shot}_take{take}.mp4"
                    scp_to(dst, remote)
                    log(f"{shot} t{take}: done {sz}B -> {remote}")
                    return True, {"bytes": sz, "spark_path": remote,
                                  "settings": f"{steps}st cfg {cfg} {w}x{h} {sampler}/{scheduler} seed {seed}"}
            log(f"{shot} t{take}: no video in outputs, retrying")
        except Exception as e:
            log(f"{shot} t{take}: {type(e).__name__}: {str(e)[:200]}, retrying")
    return False, {"bytes": 0, "spark_path": "", "settings": ""}

# ------------------------------- encode ------------------------------------
def encode_job(job):
    jid = job.get("job_id", "encode")
    op = job.get("op", "transcode")
    vcodec = job.get("vcodec", "hevc_nvenc")
    preset = job.get("preset", "p5")
    extra = job.get("extra_args", [])
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    try:
        if op == "transcode":
            srcs = [job["inputs"]["src"]]
            local_ins = []
            for s in srcs:
                lp = os.path.join(SCRATCH_DIR, os.path.basename(s))
                if not os.path.exists(lp):
                    log(f"{jid}: fetching {s}")
                    scp_from(s, lp)
                local_ins.append(lp)
            dst_local = os.path.join(SCRATCH_DIR, os.path.basename(job["dst"]))
            cmd = ([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", local_ins[0],
                    "-c:v", vcodec, "-preset", preset,
                    "-pix_fmt", "yuv420p"] + extra +
                   (["-c:a", "aac", "-b:a", "160k"] if job.get("audio", False) else ["-an"]) +
                   [dst_local])
        elif op == "concat":
            local_ins = []
            for s in job["inputs"]["parts"]:
                lp = os.path.join(SCRATCH_DIR, os.path.basename(s))
                if not os.path.exists(lp):
                    log(f"{jid}: fetching {s}")
                    scp_from(s, lp)
                local_ins.append(lp)
            lst = os.path.join(SCRATCH_DIR, f"{jid}_list.txt")
            with open(lst, "w") as f:
                for p in local_ins:
                    f.write(f"file '{p}'\n")
            dst_local = os.path.join(SCRATCH_DIR, os.path.basename(job["dst"]))
            cmd = ([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", vcodec, "-preset", preset,
                    "-pix_fmt", "yuv420p"] + extra + ["-an", dst_local])
        else:
            return False, {"bytes": 0, "spark_path": "", "settings": "",
                           "note": f"unknown op {op}"}
        log(f"{jid}: ffmpeg {' '.join(cmd[1:6])}...")
        t0 = time.time()
        # IN-FLIGHT GATE CHECK: terminate ffmpeg the moment gates fail.
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
        aborted_reason = None
        while proc.poll() is None:
            time.sleep(5)
            ok, reason = gates_ok()
            if not ok:
                aborted_reason = reason
                break
            if time.time() - t0 > 3600:
                aborted_reason = "ffmpeg timeout 3600s"
                break
        if aborted_reason:
            log(f"{jid}: gates failed mid-encode ({aborted_reason}) — terminating ffmpeg")
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
            return None, {"aborted": True,
                          "note": f"gates failed mid-encode: {aborted_reason}"}
        dt = time.time() - t0
        err = (proc.stderr.read() or "")[-200:] if proc.stderr else ""
        if proc.returncode != 0:
            return False, {"bytes": 0, "spark_path": "", "settings": "",
                           "note": f"ffmpeg: {err}"}
        sz = os.path.getsize(dst_local)
        scp_to(dst_local, job["dst"])
        log(f"{jid}: done {sz}B in {dt:.0f}s -> {job['dst']}")
        return True, {"bytes": sz, "spark_path": job["dst"],
                      "settings": f"{vcodec} {preset} {dt:.0f}s",
                      "note": ""}
    except Exception as e:
        return False, {"bytes": 0, "spark_path": "", "settings": "",
                       "note": f"{type(e).__name__}: {str(e)[:150]}"}

# ------------------------------- manifest ----------------------------------
def manifest_append(entry):
    line = json.dumps(entry)
    with open(MANIFEST_LOCAL, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        scp_to(MANIFEST_LOCAL, MANIFEST_SPARK, timeout=120)
    except Exception as e:
        log(f"manifest mirror failed: {e}")

# ------------------------------- main --------------------------------------
def main():
    for d in (PLATE_DIR, VIDEO_DIR, SCRATCH_DIR, LOG_DIR,
              os.path.dirname(SSH_KEY)):
        os.makedirs(d, exist_ok=True)
    log("worker started")
    log(f"gates: AC + idle>={IDLE_MINUTES}m + gpu<{GPU_TEMP_MAX}C "
        f"(resume<{GPU_TEMP_RESUME}C); renders only {RENDER_OPEN_H}:00-{RENDER_CLOSE_H}:00 {RENDER_TZ_ID}")
    idle_rounds = 0
    comfy_ready = os.path.exists(COMFY_MAIN)
    if not comfy_ready:
        log("ComfyUI not installed yet — encode jobs only until it is")
    while True:
        try:
            ok, reason = gates_ok()
            if not ok:
                stop_comfy()
                idle_rounds += 1
                if idle_rounds % 10 == 0:
                    log(f"gates holding ({reason})")
                time.sleep(60)
                continue
            if in_render_window() and comfy_ready:
                kinds = ["prod", "encode", "exp", "art"]
            else:
                kinds = ["encode"]
                if in_render_window() and not comfy_ready:
                    pass  # encodes only until ComfyUI lands
                stop_comfy()  # never sit on the GPU outside the render window
            job = claim_job(kinds)
            if not job:
                idle_rounds += 1
                if idle_rounds % 10 == 0:
                    log(f"heartbeat: queue empty (kinds={kinds})")
                time.sleep(60)
                continue
            idle_rounds = 0
            kind = job.get("kind", "prod")
            jid = job.get("job_id") or f"{job.get('shot_id')}_take{job.get('take')}"
            log(f"=== {jid} ({kind}) ===")
            if kind in ("prod", "exp", "art"):
                if not start_comfy():
                    mark_job(job, False, note="comfy unavailable")
                    time.sleep(60)
                    continue
                good, info = render_job(job)
            else:
                good, info = encode_job(job)
            if good is None:  # ABORTED: gates failed mid-job -> requeue
                log(f"{jid}: aborted ({info.get('note', '')}) — requeuing")
                mark_job(job, False, note=info.get("note", "aborted"),
                         requeue=True)
                time.sleep(30)
                continue
            mark_job(job, good, size=info.get("bytes", 0),
                     note=info.get("note", ""))
            if good:
                manifest_append({
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "box": "surface",
                    "type": kind,
                    "job": jid,
                    "settings": info.get("settings", ""),
                    "purpose": ("overnight render overflow" if kind in ("prod", "exp", "art")
                                else "finishing/encode"),
                    "spark_path": info.get("spark_path", ""),
                    "bytes": info.get("bytes", 0),
                })
            # re-check gates before the next claim: a job whose gates failed
            # mid-flight was already interrupted and requeued above
            time.sleep(5)
        except Exception as e:
            log(f"loop error: {type(e).__name__}: {str(e)[:200]}")
            time.sleep(60)

if __name__ == "__main__":
    main()
