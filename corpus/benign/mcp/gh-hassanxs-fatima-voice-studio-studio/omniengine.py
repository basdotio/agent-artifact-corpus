"""The third voice engine: OmniVoice through omnivoice.cpp's tts-server (OpenAI-style HTTP).

The server is started once with the model and stays loaded (about 1 s to start). Each voice is sent to it once
(POST /v1/audio/voices: the clip and what it says, heard by Whisper and kept in voice.json, as for S2 Pro); the
server keeps the voice's codes in memory. Each part is then one POST /v1/audio/speech with the voice's name, the
language, a seed and, on the CPU, fewer decoding steps (OMNI_CPU_STEPS). The server splits long parts itself and
keeps the voice steady across them. It's stopped after a few idle minutes, before another voice engine runs, when a
part is stopped (it would finish the request otherwise), and when the app closes.
"""
import base64
import contextlib
import hashlib
import http.client
import json
import logging
import os
import re
import socket
import subprocess
import threading
import time
from pathlib import Path

from . import config, hardware, runtime, s2engine

log = logging.getLogger("studio.omniengine")

IDLE_STOP_S = 300   # free the graphics card after this long without a part
SHARE_GB = 6        # below this much graphics memory, OmniVoice and Whisper take turns on the card
START_TIMEOUT_S = 120
CPU_STEPS = 16      # decoding steps on the processor: about twice as fast as the full 32, words as clear
DEVICE = re.compile(r"LM backend: (\S+)")
VK_DEVICE = re.compile(r"ggml_vulkan: (\d+) = .*?\| uma: (\d)")  # uma 1 = built into the processor
CHUNKS = re.compile(r"Chunked: (\d+) chunks")
STEP = re.compile(r"\[MaskGIT-Step\] (\d+)/(\d+)")
MAX_LOG = 2_000_000  # bytes: omnivoice.log is started afresh (the old one kept as omnivoice.old.log) when bigger
NOISE = re.compile(r"^\[(MaskGIT-Step|Prompt|TTS\]|MaskGIT\] Start)")  # per-step chatter: progress only, not logged


class OmniError(Exception):
    pass


class OmniCancelled(Exception):
    pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class OmniServer:
    def __init__(self, cfg: dict, job=None):
        self.cfg = cfg
        self.job = job              # Windows job object: the server dies with the app
        self.proc: subprocess.Popen | None = None
        self.port = 0
        self.loaded: tuple | None = None  # (model, build, device) the running server has
        self.voices: dict[str, str] = {}  # voice name on the server -> fingerprint of the clip and words sent
        self.progress = 0.0         # 0-1 of the part being spoken
        self.last_used = 0.0
        self.log_path = config.DATA / "logs" / "omnivoice.log"
        self._ready = threading.Event()
        self._uma: dict[int, bool] = {}
        self._device_used = ""
        self._chunks = 1
        self._steps_done = 0
        self._conn: http.client.HTTPConnection | None = None
        self._cancel = False
        self._lock = threading.RLock()
        self._held = 0
        threading.Thread(target=self._idle_watch, daemon=True).start()

    # ---- the server process ----

    def running(self) -> bool:
        return bool(self.proc and self.proc.poll() is None)

    def stop(self) -> None:
        proc, self.proc, self.loaded, self.voices = self.proc, None, None, {}
        if proc and proc.poll() is None:
            log.info("Stopping the OmniVoice server")
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
        """Whisper's turn on the graphics card. OmniVoice takes under 2 GB, so it stays loaded beside Whisper except
        on cards under SHARE_GB, where it waits for the part being spoken and unloads (the next part reloads it in
        about a second)."""
        gpu = hardware.main_gpu(hardware.detect())
        if not gpu or gpu["vram_gb"] >= SHARE_GB:
            yield
            return
        with self._lock:
            self._held += 1
            try:
                if self.running():
                    log.info("OmniVoice makes room on the graphics card for Whisper")
                    self.stop()
                yield
            finally:
                self._held -= 1

    def _device(self, build: str, model: str) -> str | None:
        """The --device to use: none for the CPU build or a CUDA card (the server picks it), "CPU" when the card has
        less memory than the model, and for Vulkan the card remembered by S2 Pro or Whisper (same order), if any."""
        if build == "cpu":
            return None
        gpu = hardware.main_gpu(hardware.detect())
        if gpu and 0 < gpu["vram_gb"] < config.MODELS[model].get("vram_gb", 0):
            log.info("OmniVoice runs on the CPU: the graphics card has %s GB", gpu["vram_gb"])
            return "CPU"
        if build == "vulkan":
            for key in ("omni_vk_device", "s2_vk_device", "whisper_vk_device"):
                if self.cfg.get(key) is not None:
                    return f"Vulkan{int(self.cfg[key])}"
        return None

    def ensure(self, model: str) -> None:
        """A server with this model on the engine in use, started if needed (already locked by speak)."""
        build = config.omni_build(self.cfg)
        if not build:
            raise OmniError("Download an engine on Setup first.")
        device = self._device(build, model)
        if self.running() and self.loaded == (model, build, device):
            return
        self.stop()
        for _ in range(2):
            better = self._start(model, build, device)
            if better is None:
                return
            log.info("OmniVoice started on the built-in graphics; using Vulkan device %s (the graphics card)", better)
            self.cfg["omni_vk_device"] = better
            config.save(self.cfg)
            device = f"Vulkan{better}"

    def _start(self, model: str, build: str, device: str | None) -> int | None:
        """Start the server; returns a better Vulkan device if it picked a built-in chip (then it's stopped)."""
        folder = config.omni_dir(build)
        exe = folder / config.OMNI_EXE
        if not exe.exists():
            raise OmniError("OmniVoice's engine part is missing. Open Models and click Get it.")
        models_dir = Path(self.cfg["models_dir"]).resolve()
        base, codec = config.MODELS[model]["files"]
        self.port = _free_port()
        args = [str(exe), "--model", str(models_dir / base), "--codec", str(models_dir / codec),
                "--host", "127.0.0.1", "--port", str(self.port)]
        if device:
            args += ["--device", device]
        env = os.environ.copy()
        if build == "cuda":  # cuBLAS and cudart come from the voice engine's folder
            env["PATH"] = str(config.engine_dir(self.cfg, "cuda")) + os.pathsep + env.get("PATH", "")
        runtime.prepare(folder)
        self._ready.clear()
        self._uma, self._device_used = {}, ""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self.log_path.stat().st_size > MAX_LOG:
                self.log_path.replace(self.log_path.with_name("omnivoice.old.log"))
        except OSError:  # no log yet, or the last server's output is still being written
            pass
        log.info("Starting the OmniVoice server (%s, %s%s)", config.MODELS[model]["label"], build,
                 f", {device}" if device else "")
        self.proc = subprocess.Popen(args, cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if self.job:
            self.job.add(self.proc)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()
        deadline = time.monotonic() + START_TIMEOUT_S
        while time.monotonic() < deadline:
            if self._ready.wait(0.25):
                break
            if self._cancel:  # Stop while loading
                self.stop()
                raise OmniCancelled()
            if self.proc.poll() is not None:
                raise OmniError(self._start_problem())
        else:
            self.stop()
            raise OmniError("OmniVoice took too long to start and was stopped.")
        used = re.fullmatch(r"Vulkan(\d+)", self._device_used)
        if build == "vulkan" and not device and used and self._uma.get(int(used[1])) and not all(self._uma.values()):
            self.stop()
            return min(d for d, built_in in self._uma.items() if not built_in)
        self.loaded = (model, build, device)
        return None

    def _pump(self, proc: subprocess.Popen) -> None:
        """The server's output: to omnivoice.log, and the bits the app watches (ready, devices, progress)."""
        with open(self.log_path, "a", encoding="utf-8", errors="replace") as logf:
            for raw in proc.stdout:
                line = raw.decode("utf-8", "replace").rstrip()
                if m := STEP.search(line):
                    self._steps_done += 1
                    total = int(m[2]) * self._chunks
                    self.progress = min(0.99, self._steps_done / total) if total else 0.0
                elif m := CHUNKS.search(line):
                    self._chunks = int(m[1])
                elif "listening on" in line:
                    self._ready.set()
                elif m := DEVICE.search(line):
                    self._device_used = m[1]
                elif m := VK_DEVICE.search(line):
                    self._uma[int(m[1])] = m[2] == "1"
                if line and not NOISE.match(line):
                    logf.write(line + "\n")
            logf.flush()

    def _start_problem(self) -> str:
        code = self.proc.returncode if self.proc else None
        try:
            tail = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
        except OSError:
            tail = []
        if any("ErrorOutOfDeviceMemory" in l or "out of memory" in l.lower() for l in tail):
            return "OmniVoice didn't fit in the graphics card's memory. Close other programs that use it."
        detail = next((l for l in reversed(tail) if "rror" in l or "ailed" in l), "")
        return runtime.load_problem(code) or f"OmniVoice couldn't start: {detail or f'code {code}'}"

    # ---- speaking ----

    def cancel(self) -> None:
        """Stop the part being spoken now: the server is ended (the next part starts it again in about a second),
        so the graphics card is free at once and nothing queues behind it."""
        self._cancel = True
        proc = self.proc
        if self._conn is not None and proc and proc.poll() is None:
            log.info("Stopping the OmniVoice server: the part was stopped")
            proc.kill()

    def _post(self, path: str, body: dict, dest: Path | None = None) -> bytes:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=float(self.cfg.get("timeout_s") or 900))
        self._conn = conn
        try:
            conn.request("POST", path, body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                         headers={"Content-Type": "application/json"})
            r = conn.getresponse()
            if r.status != 200:
                detail = r.read().decode("utf-8", "replace")
                try:
                    detail = json.loads(detail)["error"]["message"]
                except (ValueError, KeyError, TypeError):
                    pass
                raise OmniError(f"OmniVoice couldn't speak this part: {detail[:300]}")
            if dest is None:
                return r.read()
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
            return b""
        finally:
            self._conn = None
            conn.close()

    def _voice(self, clip: Path) -> str:
        """The voice's name on the server, sent there first if it's new or its clip or words changed."""
        words = s2engine.transcript(self.cfg, clip, "OmniVoice")
        data = Path(clip).read_bytes()
        name = Path(clip).parent.name
        print_ = hashlib.sha1(data + words.encode("utf-8")).hexdigest()
        if self.voices.get(name) != print_:
            self._post("/v1/audio/voices", {"name": name, "ref_text": words,
                                            "wav_b64": base64.b64encode(data).decode("ascii")})
            self.voices[name] = print_
        return name

    def speak(self, model: str, text: str, language: str, voice: Path | None, seed: int, out: Path) -> None:
        """Speak `text` into the WAV file `out` (blocking; run it in a thread)."""
        with self._lock:
            self._held += 1
            try:
                self._speak(model, text, language, voice, seed, out)
            finally:
                self._held -= 1

    def _speak(self, model: str, text: str, language: str, voice: Path | None, seed: int, out: Path) -> None:
        if self._cancel:
            raise OmniCancelled()
        if voice:
            s2engine.transcript(self.cfg, voice, "OmniVoice")  # Whisper before the server takes the card
        self.ensure(model)
        if self._cancel:
            raise OmniCancelled()
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.unlink(missing_ok=True)
        body = {"input": text, "language": config.OMNI_CODES.get(language, language), "response_format": "wav",
                "seed": int(seed) % 2**31}
        if self.loaded[1] == "cpu" or self.loaded[2] == "CPU":
            body["steps"] = CPU_STEPS
        self.progress, self._steps_done, self._chunks = 0.0, 0, 1
        try:
            if voice:
                body["voice"] = self._voice(voice)
            if self._cancel:
                raise OmniCancelled()
            self._post("/v1/audio/speech", body, out)
        except (OSError, http.client.HTTPException) as e:
            out.unlink(missing_ok=True)
            if self._cancel:
                raise OmniCancelled()
            try:  # a dropped connection is usually the server going down: give Windows a moment to say so
                self.proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, AttributeError):
                pass
            if not self.running():
                self.stop()
                raise OmniError("OmniVoice stopped while speaking. It starts again for the next part.") from e
            raise OmniError(f"OmniVoice couldn't speak this part: {e}") from e
        finally:
            self.last_used = time.monotonic()
        if self._cancel:
            out.unlink(missing_ok=True)
            raise OmniCancelled()
