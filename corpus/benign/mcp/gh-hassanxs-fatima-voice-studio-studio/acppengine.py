"""The fourth voice engine: audio.cpp's server, for the models with runtime "acpp" (Chatterbox, Kokoro, MOSS-TTS Nano).

One server serves all of them: its config lists the downloaded models, it loads one on first use and keeps one at a
time (max_loaded_models 1). Each part is one POST /v1/audio/speech: the model, the text, the language and a seed,
plus the voice. Cloning models get the voice's clip inline (and what it says, for those that need the words, heard
by Whisper once and kept in voice.json); Kokoro gets one of its own voices, named in the voice's voice.json
("kokoro_voice"). The server is stopped after a few idle minutes, before another voice engine runs, when a part is
stopped, and when the app closes. On small cards it unloads its model while Whisper uses the card.
"""
import base64
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
from pathlib import Path

from . import config, hardware, runtime, s2engine, text as textmod

log = logging.getLogger("studio.acppengine")

IDLE_STOP_S = 300   # free the graphics card after this long without a part
SHARE_GB = 12       # below this much graphics memory, the model is unloaded while Whisper uses the card (VoxCPM2: ~7 GB)
START_TIMEOUT_S = 60
DEVICE = re.compile(r"^Vulkan:(\d+) .*\[(GPU|IGPU)\]", re.M)
MAX_LOG = 2_000_000  # bytes: audiocpp.log is started afresh (the old one kept as audiocpp.old.log) when bigger
NOISE = re.compile(r"CUDA graph warmup complete|^\[TIMING|^\[TRACE")


class AcppError(Exception):
    pass


class AcppCancelled(Exception):
    pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def kokoro_voice(voice: Path | None, language: str, seed: int) -> str:
    """The Kokoro voice for a part: the one the library voice names, or (no voice: Find a new voice) one of Kokoro's
    voices for the language, picked by the seed."""
    if voice is None:
        pool = [v for v, _, lang, _ in config.KOKORO_VOICES if lang == language] or [config.KOKORO_VOICES[0][0]]
        return pool[int(seed) % len(pool)]
    meta_path = Path(voice).parent / "voice.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    if not meta.get("kokoro_voice"):
        raise AcppError("Kokoro speaks only with its own voices. Pick one marked Kokoro on the Voices page, or another "
                        "voice model for this voice.")
    return meta["kokoro_voice"]


def kokoro_language(voice_id: str, language: str) -> str:
    """Kokoro's language code: the voice's own accent when it speaks its language (British English for b…), else
    the script's language."""
    own = config.KOKORO_LANG.get(voice_id[:1], "en-us")
    by_lang = {"en": "en-us", "fr": "fr-fr", "pt": "pt-br"}.get(language, language)
    return own if own.split("-")[0] == language else by_lang


class AcppServer:
    def __init__(self, cfg: dict, job=None):
        self.cfg = cfg
        self.job = job              # Windows job object: the server dies with the app
        self.proc: subprocess.Popen | None = None
        self.port = 0
        self.loaded: tuple | None = None  # (models, build, backend, device) the running server has
        self.progress = 0.0         # 0-1 of the part being spoken (estimated from time: the server reports none)
        self.last_used = 0.0
        self.log_path = config.DATA / "logs" / "audiocpp.log"
        self._conn: http.client.HTTPConnection | None = None
        self._cancel = False
        self._lock = threading.RLock()
        self._held = 0
        threading.Thread(target=self._idle_watch, daemon=True).start()

    # ---- the server process ----

    def running(self) -> bool:
        return bool(self.proc and self.proc.poll() is None)

    def stop(self) -> None:
        proc, self.proc, self.loaded = self.proc, None, None
        if proc and proc.poll() is None:
            log.info("Stopping the audio.cpp server")
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
        """Whisper's turn on the graphics card. On cards under SHARE_GB the model is unloaded first (after the part
        being spoken); the next part loads it again. The server itself keeps running."""
        gpu = hardware.main_gpu(hardware.detect())
        if not gpu or gpu["vram_gb"] >= SHARE_GB:
            yield
            return
        with self._lock:
            self._held += 1
            try:
                if self.running():
                    log.info("audio.cpp makes room on the graphics card for Whisper")
                    try:
                        self._request("POST", "/v1/tasks/unload_all_models", {}, timeout=60)
                    except (OSError, http.client.HTTPException, AcppError):
                        self.stop()
                yield
            finally:
                self._held -= 1

    def _env(self, build: str) -> dict:
        env = os.environ.copy()
        if build == "cuda":  # cuBLAS and cudart come from the voice engine's folder
            env["PATH"] = str(config.engine_dir(self.cfg, "cuda")) + os.pathsep + env.get("PATH", "")
        es = config.espeak_dir()
        if (es / "libespeak-ng.dll").exists():  # Kokoro's pronunciation
            env["AUDIOCPP_ESPEAK_LIBRARY"] = str(es / "libespeak-ng.dll")
            env["AUDIOCPP_ESPEAK_DATA"] = str(es / "espeak-ng-data")
        return env

    def _vulkan_device(self, folder: Path, build: str) -> int:
        """The Vulkan device of the graphics card (not a chip built into the processor), found once and remembered."""
        if self.cfg.get("acpp_vk_device") is not None:
            return int(self.cfg["acpp_vk_device"])
        try:
            out = subprocess.run([str(folder / config.ACPP_EXE), "--list-devices"], capture_output=True, cwd=folder,
                                 env=self._env(build), timeout=60,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.decode("utf-8", "replace")
        except (OSError, subprocess.TimeoutExpired):
            return 0
        found = DEVICE.findall(out)
        device = next((int(n) for n, kind in found if kind == "GPU"), int(found[0][0]) if found else 0)
        self.cfg["acpp_vk_device"] = device
        config.save(self.cfg)
        return device

    def ensure(self, model: str) -> None:
        """A server with every downloaded audio.cpp model, on the engine in use (already locked by speak). A card with
        less memory than the model runs it on the processor."""
        build = config.acpp_build(self.cfg)
        if not build:
            raise AcppError("Download an engine on Setup first.")
        folder = config.acpp_dir(build)
        if not (folder / config.ACPP_EXE).exists():
            raise AcppError(f"{config.MODELS[model]['label']}'s engine part is missing. Open Models and click Get it.")
        backend, device = {"cuda": ("cuda", 0), "vulkan": ("vulkan", None), "cpu": ("cpu", 0)}[build]
        gpu = hardware.main_gpu(hardware.detect())
        if backend != "cpu" and gpu and 0 < gpu["vram_gb"] < config.MODELS[model].get("vram_gb", 0):
            log.info("%s runs on the CPU: the graphics card has %s GB", config.MODELS[model]["label"], gpu["vram_gb"])
            backend, device = "cpu", 0
        if backend == "vulkan":
            device = self._vulkan_device(folder, build)
        installed = config.installed_models(self.cfg)
        models = tuple(k for k, m in config.MODELS.items() if m.get("runtime") == "acpp" and k in installed)
        wanted = (models, build, backend, device)
        if self.running() and self.loaded == wanted:
            return
        self.stop()
        self._start(folder, build, backend, device, models)
        self.loaded = wanted

    def _start(self, folder: Path, build: str, backend: str, device: int, models: tuple) -> None:
        models_dir = Path(self.cfg["models_dir"]).resolve()
        self.port = _free_port()
        server_cfg = {
            "host": "127.0.0.1", "port": self.port, "backend": backend, "device": device,
            "threads": max(1, min(12, (os.cpu_count() or 4) // 2)), "lazy_load": True, "max_loaded_models": 1,
            "ui": False, "models": [{"id": k, "family": config.MODELS[k]["family"],
                                     "path": str(models_dir / config.MODELS[k]["files"][0]),
                                     "task": "tts" if not config.MODELS[k].get("clone") else "clon",
                                     "mode": "offline"} for k in models]}
        cfg_path = config.DATA / "audiocpp-server.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(server_cfg, indent=1), encoding="utf-8")
        runtime.prepare(folder)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self.log_path.stat().st_size > MAX_LOG:
                self.log_path.replace(self.log_path.with_name("audiocpp.old.log"))
        except OSError:
            pass
        log.info("Starting the audio.cpp server (%s, %s%s)", build, backend, f" {device}" if backend == "vulkan" else "")
        self.proc = subprocess.Popen([str(folder / config.ACPP_EXE), "--config", str(cfg_path)], cwd=folder,
                                     env=self._env(build), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if self.job:
            self.job.add(self.proc)
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()
        deadline = time.monotonic() + START_TIMEOUT_S
        while time.monotonic() < deadline:
            if self._cancel:
                self.stop()
                raise AcppCancelled()
            if self.proc.poll() is not None:
                raise AcppError(self._start_problem())
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                    return
            except OSError:
                time.sleep(0.2)
        self.stop()
        raise AcppError("audio.cpp took too long to start and was stopped.")

    def _pump(self, proc: subprocess.Popen) -> None:
        with open(self.log_path, "a", encoding="utf-8", errors="replace") as logf:
            for raw in proc.stdout:
                line = raw.decode("utf-8", "replace").rstrip()
                if line and not NOISE.search(line):
                    logf.write(line + "\n")
            logf.flush()

    def _start_problem(self) -> str:
        code = self.proc.returncode if self.proc else None
        try:
            tail = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
        except OSError:
            tail = []
        detail = next((l for l in reversed(tail) if "rror" in l or "ailed" in l), "")
        return runtime.load_problem(code) or f"audio.cpp couldn't start: {detail or f'code {code}'}"

    # ---- speaking ----

    def cancel(self) -> None:
        """Stop the part being spoken now: the server is ended (the next part starts it again)."""
        self._cancel = True
        proc = self.proc
        if self._conn is not None and proc and proc.poll() is None:
            log.info("Stopping the audio.cpp server: the part was stopped")
            proc.kill()

    def _request(self, method: str, path: str, body: dict, dest: Path | None = None, timeout: float | None = None) -> bytes:
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=timeout or float(self.cfg.get("timeout_s") or 900))
        self._conn = conn
        try:
            conn.request(method, path, body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                         headers={"Content-Type": "application/json"})
            r = conn.getresponse()
            if r.status != 200:
                detail = r.read().decode("utf-8", "replace")
                try:
                    detail = json.loads(detail)["error"]["message"]
                except (ValueError, KeyError, TypeError):
                    pass
                raise AcppError(f"audio.cpp couldn't speak this part: {detail[:300]}")
            if dest is None:
                return r.read()
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
            return b""
        finally:
            self._conn = None
            conn.close()

    def speak(self, model: str, text: str, language: str, voice: Path | None, seed: int, out: Path,
              preset: str | None = None) -> None:
        """Speak `text` into the WAV file `out` (blocking; run it in a thread). `preset`: a Kokoro voice id, for a
        voice that isn't in the library yet."""
        with self._lock:
            self._held += 1
            try:
                self._speak(model, text, language, voice, seed, out, preset)
            finally:
                self._held -= 1

    def _speak(self, model, text, language, voice, seed, out, preset) -> None:
        if self._cancel:
            raise AcppCancelled()
        m = config.MODELS[model]
        body = {"model": model, "input": text, "seed": int(seed) % 2**31, "response_format": "wav"}
        # the language goes both ways: Chatterbox reads only the top-level field (and quietly ignores it in
        # options), Kokoro and MOSS-TTS Nano take either
        if m["family"] == "kokoro_tts":
            vid = preset or kokoro_voice(voice, language, seed)
            body["voice"] = vid
            body["language"] = kokoro_language(vid, language)
        else:
            body["language"] = language
        if m.get("lang_options", True):  # CosyVoice 3 refuses it in options
            body["options"] = {"language": body["language"]}
        if m["family"] != "kokoro_tts":
            if voice:
                if m.get("words"):  # Whisper before the server takes the card
                    body["reference_text"] = s2engine.transcript(self.cfg, voice, m["label"])
                body["voice_ref"] = {"type": "base64", "data": base64.b64encode(Path(voice).read_bytes()).decode("ascii")}
        self.ensure(model)
        if self._cancel:
            raise AcppCancelled()
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.unlink(missing_ok=True)
        expected = max(1.0, textmod.estimate_seconds(text) / float(m.get("x_rt") or 2))
        started, done = time.monotonic(), threading.Event()

        def tick():  # the server reports no progress: estimate it from the model's usual speed
            while not done.wait(0.25):
                self.progress = min(0.95, (time.monotonic() - started) / expected)
        self.progress = 0.0
        threading.Thread(target=tick, daemon=True).start()
        try:
            self._request("POST", "/v1/audio/speech", body, out)
        except (OSError, http.client.HTTPException) as e:
            out.unlink(missing_ok=True)
            if self._cancel:
                raise AcppCancelled()
            try:
                self.proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, AttributeError):
                pass
            if not self.running():
                self.stop()
                raise AcppError("audio.cpp stopped while speaking. It starts again for the next part.") from e
            raise AcppError(f"audio.cpp couldn't speak this part: {e}") from e
        finally:
            done.set()
            self.last_used = time.monotonic()
        if self._cancel:
            out.unlink(missing_ok=True)
            raise AcppCancelled()
