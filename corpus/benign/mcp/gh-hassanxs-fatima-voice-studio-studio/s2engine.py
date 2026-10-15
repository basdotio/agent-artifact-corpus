"""The second voice engine: Fish Audio S2 Pro through s2.cpp's HTTP server.

The server is started once with the model and stays loaded (the start costs about 5 s), so each part is one
POST /generate: the text, the voice's clip and its transcript (s2.cpp clones a voice from both), a seed and a length
cap (with Vulkan, in pieces of about 10 s: see VULKAN_PIECE). The transcript is made once with Whisper and kept in
the voice's voice.json. The server is stopped after a few idle minutes, before Qwen3-TTS runs (both won't fit on an
8 GB card), when a part is stopped, and when the app closes.
"""
import contextlib
import http.client
import json
import logging
import os
import re
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from . import config, hardware, runtime, subtitles, text as textmod

log = logging.getLogger("studio.s2engine")

FRAME_RATE = 44100 / 2048  # S2 Pro's codec frames per second of audio
IDLE_STOP_S = 300          # free the graphics card after this long without a part
SHARE_GB = 12              # below this much graphics memory, S2 Pro and Whisper take turns on the card
START_TIMEOUT_S = 240
# The codec turns a whole request into audio in one go and its working memory grows with the length: with Vulkan,
# 15 s don't fit beside the Q8 model on an 8 GB card. There a part is spoken in pieces of this size (about 10 s).
VULKAN_PIECE = 120
PROGRESS = re.compile(r"\[Generate\]\s+(\d+)\s*/\s*(\d+)\s+tokens")
VK_DEVICE = re.compile(r"ggml_vulkan: (\d+) = .*?\| uma: (\d)")  # uma 1 = built into the processor
CRLF = bytes([13, 10])  # multipart line break
NOISE = re.compile(r"CUDA Graph id \d+ reused")  # ggml's CUDA build says this for every step
MAX_LOG = 2_000_000  # bytes: s2.log is started afresh (the old one kept as s2.old.log) when it's bigger


class S2Error(Exception):
    pass


class S2Cancelled(Exception):
    pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class S2Server:
    def __init__(self, cfg: dict, job=None):
        self.cfg = cfg
        self.job = job              # Windows job object: the server dies with the app
        self.proc: subprocess.Popen | None = None
        self.port = 0
        self.loaded: tuple | None = None  # (model, engine, device) the running server has
        self.frames = 0             # progress of the part being spoken
        self.last_used = 0.0
        self.log_path = config.DATA / "logs" / "s2.log"
        self._ready = threading.Event()
        self._uma: dict[int, bool] = {}
        self._conn: http.client.HTTPConnection | None = None
        self._frames_before = 0     # frames of the part's earlier pieces (progress)
        self._cancel = False
        self._lock = threading.RLock()  # re-entrant: a part's voice transcript runs Whisper through gpu_turn
        self._held = 0
        threading.Thread(target=self._idle_watch, daemon=True).start()

    # ---- the server process ----

    def running(self) -> bool:
        return bool(self.proc and self.proc.poll() is None)

    def stop(self) -> None:
        proc, self.proc, self.loaded = self.proc, None, None
        if proc and proc.poll() is None:
            log.info("Stopping the S2 Pro server")
            proc.kill()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass

    def _idle_watch(self) -> None:
        while True:
            time.sleep(15)
            if self.running() and not self._held and time.monotonic() - self.last_used > IDLE_STOP_S:
                self.stop()

    @contextlib.contextmanager
    def gpu_turn(self):
        """Whisper's turn on the graphics card. On cards under SHARE_GB, S2 Pro (about 7 GB) and Whisper don't fit
        together: wait for the part being spoken to finish, unload the server, and let the next part load it again
        (about 5 s). Bigger cards run both side by side."""
        gpu = hardware.main_gpu(hardware.detect())
        if not gpu or gpu["vram_gb"] >= SHARE_GB:
            yield
            return
        with self._lock:
            self._held += 1
            try:
                if self.running():
                    log.info("S2 Pro makes room on the graphics card for Whisper")
                    self.stop()
                yield
            finally:
                self._held -= 1

    def _device(self) -> int | None:
        """Vulkan device to use: the one remembered (also found by Whisper: the same order), else let it start on 0
        and move to the dedicated card if 0 turns out to be built into the processor."""
        for key in ("s2_vk_device", "whisper_vk_device"):
            if self.cfg.get(key) is not None:
                return int(self.cfg[key])
        return 0

    def ensure(self, model: str) -> None:
        """A server with this model on the engine in use, started if needed (already locked by speak)."""
        engine = config.s2_engine(self.cfg)
        if not engine:
            raise S2Error("S2 Pro runs on the NVIDIA · CUDA or AMD / Intel · Vulkan engine. Switch to one on Setup.")
        device = self._device() if engine == "vulkan" else 0
        if self.running() and self.loaded == (model, engine, device):
            return
        self.stop()
        for _ in range(2):
            better = self._start(model, engine, device)
            if better is None:
                return
            log.info("S2 Pro started on the built-in graphics; using Vulkan device %s (the graphics card)", better)
            self.cfg["s2_vk_device"] = device = better
            config.save(self.cfg)

    def _start(self, model: str, engine: str, device: int) -> int | None:
        """Start the server; returns a better Vulkan device if it picked a built-in chip (then it's stopped)."""
        folder = config.s2_dir(engine)
        exe = folder / config.S2_EXE
        if not exe.exists():
            raise S2Error("S2 Pro's engine part for this graphics card is missing. Open Models and click Get it.")
        gguf = Path(self.cfg["models_dir"]).resolve() / config.MODELS[model]["files"][0]
        self.port = _free_port()
        # A card with less memory than the model needs runs it on the CPU: s2.cpp's own "auto" still puts all 36
        # layers on the card and runs out of memory, and on a 2 GB card (Quadro M1000M) 12 layers on the card were
        # slower than none.
        gpu = hardware.main_gpu(hardware.detect())
        on_cpu = bool(gpu) and 0 < gpu["vram_gb"] < config.MODELS[model].get("vram_gb", 0)
        args = [str(exe), "--server", "-H", "127.0.0.1", "-P", str(self.port), "--model", str(gguf),
                "--tokenizer", str(folder / "tokenizer.json"), "--gpu-layers", "0" if on_cpu else "36",
                "--log-level", "info"]
        # s2.cpp's Metal backend (this build) has no PAD op, which the audio codec's decode path needs: the
        # codec stays on the CPU with --codec-cpu while the transformer still runs on Metal.
        if on_cpu:
            args += ["--metal", "--codec-cpu"] if engine == "metal" else ["--cuda" if engine == "cuda" else "--vulkan", "-1"]
            log.info("S2 Pro runs on the CPU: the graphics card has %s GB", gpu["vram_gb"])
        else:
            args += (["--metal", "--codec-cpu"] if engine == "metal"
                     else ["--cuda", "0"] if engine == "cuda" else ["--vulkan", str(device)])
        env = os.environ.copy()
        if engine == "cuda":  # cuBLAS and cudart come from the voice engine's folder
            env["PATH"] = str(config.engine_dir(self.cfg, "cuda")) + os.pathsep + env.get("PATH", "")
        runtime.prepare(folder)
        self._ready.clear()
        self._uma = {}
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self.log_path.stat().st_size > MAX_LOG:
                self.log_path.replace(self.log_path.with_name("s2.old.log"))
        except OSError:  # no log yet, or the last server's output is still being written
            pass
        log.info("Starting the S2 Pro server (%s, %s)", config.MODELS[model]["label"], engine)
        self.proc = subprocess.Popen(args, cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if self.job:
            self.job.add(self.proc)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()
        deadline = time.monotonic() + START_TIMEOUT_S
        while time.monotonic() < deadline:
            if self._ready.wait(0.5):
                break
            if self._cancel:  # Stop while loading: don't make it wait for the model
                self.stop()
                raise S2Cancelled()
            if self.proc.poll() is not None:
                raise S2Error(self._start_problem())
        else:
            self.stop()
            raise S2Error("S2 Pro took too long to start and was stopped.")
        if engine == "vulkan" and self._uma.get(device) and not all(self._uma.values()):
            self.stop()
            return min(d for d, built_in in self._uma.items() if not built_in)
        while time.monotonic() < deadline:  # "Server starting" comes just before it listens
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                    break
            except OSError:
                if self.proc.poll() is not None:
                    raise S2Error(self._start_problem())
                time.sleep(0.2)
        self.loaded = (model, engine, device)
        return None

    def _pump(self, proc: subprocess.Popen) -> None:
        """The server's output: to s2.log, and the bits the app watches (ready, devices, progress)."""
        with open(self.log_path, "a", encoding="utf-8", errors="replace") as logf:
            for raw in proc.stdout:
                line = NOISE.sub("", raw.decode("utf-8", "replace")).rstrip()
                if line:
                    logf.write(line + "\n")
                if "Server starting on" in line:
                    self._ready.set()
                elif m := VK_DEVICE.search(line):
                    self._uma[int(m[1])] = m[2] == "1"
                elif m := PROGRESS.search(line):
                    self.frames = self._frames_before + int(m[1])
            logf.flush()

    def _start_problem(self) -> str:
        code = self.proc.returncode if self.proc else None
        try:
            tail = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
        except OSError:
            tail = []
        if any("ErrorOutOfDeviceMemory" in l or "out of memory" in l.lower() for l in tail):
            return ("S2 Pro didn't fit in the graphics card's memory. Close other programs that use it, or use the "
                    "smaller Q6 model.")
        detail = next((l for l in reversed(tail) if "rror" in l or "ailed" in l), "")
        return runtime.load_problem(code) or f"S2 Pro couldn't start: {detail or f'code {code}'}"

    # ---- speaking ----

    def cancel(self) -> None:
        """Stop the part being spoken now. s2.cpp finishes a request even when the app hangs up, so the server is
        ended (the next part starts it again): the graphics card is free at once and nothing queues behind it."""
        self._cancel = True
        proc = self.proc
        if self._conn is not None and proc and proc.poll() is None:
            log.info("Stopping the S2 Pro server: the part was stopped")
            proc.kill()

    def _post(self, fields: dict, files: dict, dest: Path) -> None:
        """POST /generate as multipart (the server sends nothing until the audio is ready; Stop ends the server)."""
        boundary = uuid.uuid4().hex
        body = bytearray()
        for name, value in fields.items():
            body += f'--{boundary}'.encode() + CRLF + f'Content-Disposition: form-data; name="{name}"'.encode() + CRLF * 2
            body += value.encode("utf-8") + CRLF
        for name, (filename, data, ctype) in files.items():
            body += f'--{boundary}'.encode() + CRLF + f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode()
            body += CRLF + f'Content-Type: {ctype}'.encode() + CRLF * 2 + data + CRLF
        body += f'--{boundary}--'.encode() + CRLF
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=float(self.cfg.get("timeout_s") or 900))
        self._conn = conn
        try:
            conn.request("POST", "/generate", body=bytes(body),
                         headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            r = conn.getresponse()
            if r.status != 200:
                raise S2Error(f"S2 Pro couldn't speak this part: {r.read().decode('utf-8', 'replace')[:300]}")
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
        finally:
            self._conn = None
            conn.close()

    def speak(self, model: str, text: str, voice: Path | None, seed: int, out: Path) -> None:
        """Speak `text` into the WAV file `out` (blocking; run it in a thread)."""
        with self._lock:
            self._held += 1
            try:
                self._speak(model, text, voice, seed, out)
            finally:
                self._held -= 1

    def _speak(self, model: str, text: str, voice: Path | None, seed: int, out: Path) -> None:
        if self._cancel:  # Stop while waiting for the graphics card (the engine clears this when a part starts)
            raise S2Cancelled()
        ref = (voice, transcript(self.cfg, voice)) if voice else None  # before the server takes the card
        self.ensure(model)
        if self._cancel:
            raise S2Cancelled()
        pieces = _pieces(text) if self.loaded[1] == "vulkan" else [text]
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.unlink(missing_ok=True)
        tmps = [out.with_name(f"{out.name}.{k}.part") for k in range(len(pieces))]
        self.frames = self._frames_before = 0
        try:
            for piece, tmp in zip(pieces, tmps):
                if self._cancel:  # Stop between two pieces
                    raise S2Cancelled()
                self._generate(piece, ref, seed, tmp)
                self._frames_before += round(sf.info(str(tmp)).frames / 2048)
            if len(tmps) == 1:
                tmps[0].replace(out)
            else:  # one part, as if spoken in one go
                sr = sf.info(str(tmps[0])).samplerate
                sf.write(str(out), _join([sf.read(str(t), dtype="float32")[0] for t in tmps], sr), sr, subtype="FLOAT")
        finally:
            for tmp in tmps:
                tmp.unlink(missing_ok=True)
            self.last_used = time.monotonic()
        if self._cancel:
            out.unlink(missing_ok=True)
            raise S2Cancelled()

    def _generate(self, text: str, ref: tuple | None, seed: int, dest: Path) -> None:
        expected = textmod.estimate_seconds(text) * FRAME_RATE
        params = {"seed": int(seed) % 2**31, "max_new_tokens": int(min(4096, expected * 3 + 150))}
        fields = {"text": text, "params": json.dumps(params)}
        files = {}
        if ref:
            fields["reference_text"] = ref[1]
            files["reference"] = ("voice.wav", Path(ref[0]).read_bytes(), "audio/wav")
        try:
            self._post(fields, files, dest)
        except (OSError, http.client.HTTPException) as e:
            if self._cancel:
                raise S2Cancelled()
            try:  # a dropped connection is usually the server going down: give Windows a moment to say so
                self.proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, AttributeError):
                pass
            if not self.running():
                self.stop()
                raise S2Error("S2 Pro stopped while speaking. It starts again for the next part.") from e
            raise S2Error(f"S2 Pro couldn't speak this part: {e}") from e


def _pieces(text: str) -> list[str]:
    """A part cut at sentences into pieces of about VULKAN_PIECE; a few words left over join their neighbour."""
    out: list[str] = []
    for piece in textmod._pack(text, VULKAN_PIECE):
        if out and (textmod.spoken(piece) < textmod.MIN_SEGMENT or textmod.spoken(out[-1]) < textmod.MIN_SEGMENT):
            out[-1] = textmod.glue(out[-1], piece)
        else:
            out.append(piece)
    return out


def _join(clips: list[np.ndarray], sr: int) -> np.ndarray:
    """The pieces of a part back to back, at the same speaking level (each request comes out a little louder or
    quieter: up to 3 dB, which is heard where they meet)."""
    def level(a: np.ndarray) -> float:
        n = sr // 20
        rms = np.sqrt(np.mean(a[:len(a) // n * n].reshape(-1, n) ** 2, axis=1)) if len(a) >= n else np.zeros(1)
        speech = rms[rms > rms.max() * 0.1]  # the 50 ms windows with speech, not the pauses
        return float(np.sqrt(np.mean(speech ** 2))) if len(speech) else 0.0
    levels = [level(c) for c in clips]
    target = float(np.median([x for x in levels if x > 0] or [1.0]))
    return np.concatenate([c * float(np.clip(target / x, 0.5, 2.0)) if x > 0 else c for c, x in zip(clips, levels)])


def transcript(cfg: dict, clip: Path) -> str:
    """What the voice's clip says (s2.cpp needs it to clone the voice): from voice.json, else heard by Whisper once
    and kept there."""
    meta_path = Path(clip).parent / "voice.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if meta.get("transcript"):
        return meta["transcript"]
    if not subtitles.whisper_available(cfg):
        raise S2Error("S2 Pro needs to know what the voice's clip says: download a Whisper model on Models, or type "
                      "it in the voice's Edit dialog.")
    words = subtitles.transcript(subtitles.run_whisper(cfg, Path(clip), meta.get("language"))).strip()
    if not words:
        raise S2Error("Whisper couldn't hear any words in the voice's clip. Type what it says in the voice's Edit dialog.")
    if meta_path.exists():
        meta["transcript"] = words
        tmp = meta_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(meta_path)
    log.info("Transcribed the clip of %s for S2 Pro", meta.get("name") or clip)
    return words
