"""Downloads models and engine builds (resumable, SHA-256 checked), reports progress, and removes them again."""
import asyncio
import hashlib
import logging
import shutil
import zipfile
from pathlib import Path

import httpx

from . import config

log = logging.getLogger("studio.downloads")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


class Downloads:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.jobs: dict[str, dict] = {}  # key -> {status, done, total, error}
        self._tasks: dict[str, asyncio.Task] = {}
        self.on_done: list = []  # called with a model key, or "<runtime>-runtime", after its download finishes

    @property
    def folder(self) -> Path:
        return Path(self.cfg["models_dir"])

    def missing(self, key: str) -> list[str]:
        return [f for f in config.model_files(key) if not (self.folder / f).exists()]

    def _whisper_missing(self) -> bool:
        return not (config.whisper_dir() / config.WHISPER_EXE).exists()

    # The voice models that run on their own program, not llama.cpp: S2 Pro (s2.cpp, one build per graphics card
    # engine), OmniVoice (omnivoice.cpp) and audio.cpp's models (one build per kind of engine). The config functions
    # are looked up each time, since the Linux and macOS layers replace them.

    def _rt_build(self, rt: str) -> str | None:
        """The build of runtime `rt` ("s2", "omni" or "acpp") the engine in use needs (None: no engine can run it)."""
        return {"s2": config.s2_engine, "omni": config.omni_build, "acpp": config.acpp_build}[rt](self.cfg)

    @staticmethod
    def _rt_zips(rt: str, build: str) -> list[tuple[str, int, str]]:
        """The zips of a runtime's build: one for s2.cpp and omnivoice.cpp, more for audio.cpp's CUDA build."""
        z = {"s2": config.S2_RUNTIME, "omni": config.OMNI_RUNTIME, "acpp": config.ACPP_RUNTIME}[rt][build]
        return list(z) if isinstance(z, list) else [z]

    @classmethod
    def _rt_size(cls, rt: str, build: str) -> int:
        return sum(size for _, size, _ in cls._rt_zips(rt, build))

    @staticmethod
    def _rt_place(rt: str, build: str) -> tuple[Path, str]:
        return {"s2": (config.s2_dir, config.S2_EXE), "omni": (config.omni_dir, config.OMNI_EXE),
                "acpp": (config.acpp_dir, config.ACPP_EXE)}[rt][0](build), \
            {"s2": config.S2_EXE, "omni": config.OMNI_EXE, "acpp": config.ACPP_EXE}[rt]

    @staticmethod
    def _espeak_missing(m: dict) -> bool:
        """Kokoro pronounces most languages with eSpeak NG, fetched with it."""
        return bool(m.get("espeak")) and not (config.espeak_dir() / "libespeak-ng.dll").exists()

    def _rt_missing(self, rt: str) -> str | None:
        """The build a download of this runtime's model still needs (None: it's there, or no engine can run it)."""
        build = self._rt_build(rt)
        if not build:
            return None
        folder, exe = self._rt_place(rt, build)
        if not (folder / exe).exists():
            return build
        # audio.cpp's builds say which download they came from: a changed one (a new release, the portable builds)
        # is fetched again
        source = folder / "source.txt"
        wanted = [u for u, _, _ in self._rt_zips(rt, build)]
        if rt == "acpp" and (not source.exists() or source.read_text(encoding="utf-8").split() != wanted):
            return build
        return None

    def _extra(self, m: dict) -> int:
        """What a model's download also fetches: Whisper with the first Whisper model, s2.cpp with S2 Pro,
        omnivoice.cpp with OmniVoice, audio.cpp (and eSpeak NG for Kokoro) with audio.cpp's models."""
        if m["kind"] == "subtitles" and self._whisper_missing():
            return config.WHISPER_ZIP[1]
        extra = config.ESPEAK_MSI[1] if self._espeak_missing(m) else 0
        if (rt := m.get("runtime")) and (build := self._rt_missing(rt)):
            extra += self._rt_size(rt, build)
        return extra

    def _engine_note(self, m: dict) -> str | None:
        """Why this model can't run on the engine in use, for its card (None: it can)."""
        if not m.get("runtime") or self._rt_build(m["runtime"]):
            return None
        if m["runtime"] == "s2":
            return "Needs the NVIDIA · CUDA or AMD / Intel · Vulkan engine"
        return "Doesn't run on this engine yet" if config.installed_engines(self.cfg) else "Needs an engine (Setup)"

    def status(self) -> list[dict]:
        installed = config.installed_models(self.cfg)
        out = []
        for key, m in config.MODELS.items():
            extra = self._extra(m)
            out.append({
                "key": key, "kind": m["kind"], "label": m["label"], "short": m["short"], "about": m["about"],
                "license": m["license"], "noncommercial": bool(m.get("noncommercial")), "page": m["page"],
                "installed": key in installed and not (m["kind"] == "subtitles" and self._whisper_missing()),
                # S2 Pro needs a CUDA or Vulkan engine in use, OmniVoice an engine its builds cover; "runtime_ready"
                # says that build (s2.cpp, omnivoice.cpp) is there too
                "engines": m.get("engines"), "engine_ok": not self._engine_note(m), "engine_note": self._engine_note(m),
                "runtime_ready": not (rt := m.get("runtime")) or (bool(self._rt_build(rt)) and not self._rt_missing(rt)
                                                                  and not self._espeak_missing(m)),
                "runtime_job": (self.jobs.get(f"{rt}-runtime:{self._rt_build(rt) or ''}") or
                                (self.jobs.get("espeak") if m.get("espeak") else None)) if rt else None,
                # what's missing when runtime_ready is false: its "engine" part, or Kokoro's "pronunciation" part
                "runtime_part": "pronunciation" if rt and not self._rt_missing(rt) and self._espeak_missing(m) else "engine",
                "in_use": m["kind"] == "subtitles" and key == config.subtitles_model(self.cfg),
                "size": sum(config.FILES[f][1] for f in config.model_files(key)),
                "to_download": sum(config.FILES[f][1] for f in self.missing(key)) + extra,
                "partial": self.partial_bytes(key),
                "shared": [f for f in config.model_files(key)
                           if sum(f in config.model_files(k) for k in config.MODELS) > 1],
                "job": self.jobs.get(key),
            })
        return out

    def _done(self, key: str) -> None:
        for callback in self.on_done:
            try:
                callback(key)
            except Exception:
                log.exception("After the download of %s", key)

    def partial_bytes(self, key: str) -> int:
        parts = (self.folder / (f + ".part") for f in self.missing(key))
        return sum(p.stat().st_size for p in parts if p.exists())

    def start(self, key: str) -> None:
        if key not in config.MODELS:
            raise ValueError("Unknown model")
        m = config.MODELS[key]
        if rt := m.get("runtime"):
            build = self._rt_build(rt)
            if not build and rt == "s2":
                raise ValueError(f"{m['label']} runs on the NVIDIA · CUDA or AMD / Intel · Vulkan engine. "
                                 "Download one on Setup and use it, then download this model.")
            if not build:
                raise ValueError(f"{m['label']} doesn't run on this engine yet." if config.installed_engines(self.cfg)
                                 else "Download an engine on Setup first, then this model.")
            # size 0: no download for this build. Fine once it's there (Linux and macOS install s2.cpp with their
            # setup scripts); only then is there nothing to fetch it from.
            if not self._rt_size(rt, build) and self._rt_missing(rt):
                raise ValueError(f"{m['label']} isn't available to download yet.")
        self._launch(key, self._run(key))

    def _launch(self, key: str, coro) -> None:
        if key in self._tasks and not self._tasks[key].done():
            coro.close()
            return
        self.jobs[key] = {"status": "downloading", "done": 0, "total": 0, "error": None}
        self._tasks[key] = asyncio.create_task(coro)

    def busy(self, key: str) -> bool:
        t = self._tasks.get(key)
        return bool(t and not t.done())

    def cancel(self, key: str) -> None:
        task = self._tasks.get(key)
        if task and not task.done():
            task.cancel()

    async def _run(self, key: str) -> None:
        job = self.jobs[key]
        files = self.missing(key)
        need_whisper = config.MODELS[key]["kind"] == "subtitles" and self._whisper_missing()
        rt = config.MODELS[key].get("runtime")
        need_rt = self._rt_missing(rt) if rt else None
        job["total"] = sum(config.FILES[f][1] for f in files) + self._extra(config.MODELS[key])
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30, read=300)) as client:
                for name in files:
                    url, size, sha = config.FILES[name]
                    await self._fetch(client, url, size, sha, self.folder / name, job)
                if need_whisper:
                    await self._install_zips(client, [config.WHISPER_ZIP], config.whisper_dir(), config.WHISPER_EXE, job)
                if need_rt:
                    await self._install_zips(client, self._rt_zips(rt, need_rt), *self._rt_place(rt, need_rt), job)
                if self._espeak_missing(config.MODELS[key]):
                    await self._install_espeak(client, job)
            job["status"] = "done"
            log.info("Downloaded %s", key)
            self._done(key)
            m = config.MODELS[key]
            if m["kind"] == "subtitles":
                self.ensure_whisper_gpu()
            if (m["kind"] == "voice" and not m.get("noncommercial")
                    and self.cfg["default_model"] not in config.installed_models(self.cfg)):
                self.cfg["default_model"] = key  # first voice model: make it the default (never a non-commercial one)
                config.save(self.cfg)
        except asyncio.CancelledError:
            job["status"] = "cancelled"  # the .part file stays, so the next download resumes
        except Exception as e:
            log.exception("Download of %s failed", key)
            job.update(status="failed", error=str(e) or e.__class__.__name__)

    def _headers(self, url: str) -> dict:
        t = (self.cfg.get("hf_token") or "").strip()
        return {"Authorization": f"Bearer {t}"} if t and url.startswith("https://huggingface.co/") else {}

    async def _fetch(self, client: httpx.AsyncClient, url: str, size: int, sha: str, final: Path, job: dict) -> None:
        part = final.with_name(final.name + ".part")
        have = part.stat().st_size if part.exists() else 0
        if have > size:
            part.unlink()
            have = 0
        if have < size:
            headers = ({"Range": f"bytes={have}-"} if have else {}) | self._headers(url)
            async with client.stream("GET", url, headers=headers) as r:
                r.raise_for_status()
                if have and r.status_code != 206:  # server ignored the range; start over
                    have = 0
                job["done"] += have
                with open(part, "ab" if have else "wb") as f:
                    async for chunk in r.aiter_bytes(1 << 20):
                        f.write(chunk)
                        job["done"] += len(chunk)
        else:
            job["done"] += have
        if part.stat().st_size != size:
            raise IOError(f"{final.name} is incomplete ({part.stat().st_size} of {size} bytes); try again.")
        job["status"] = "checking"
        digest = await asyncio.to_thread(_sha256, part)
        if digest != sha:
            part.unlink()
            raise IOError(f"{final.name} didn't match its published checksum, so it was deleted. Download it again.")
        job["status"] = "downloading"
        part.replace(final)

    async def _install_zips(self, client, zips: list[tuple[str, int, str]], target: Path, exe: str, job: dict) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        paths = []
        for url, size, sha in zips:
            path = target.parent / url.rsplit("/", 1)[1]
            if path.exists():
                job["done"] += size
            else:
                await self._fetch(client, url, size, sha, path, job)
            paths.append(path)
        job["status"] = "installing"
        await asyncio.to_thread(self._unpack, paths, target, exe)
        if target.name.startswith("audiocpp-"):  # NVIDIA's cuFFT zip keeps its DLL in <folder>/bin
            await asyncio.to_thread(self._hoist_dlls, target)
            (target / "source.txt").write_text(" ".join(url for url, _, _ in zips), encoding="utf-8")

    @staticmethod
    def _hoist_dlls(target: Path) -> None:
        """Move DLLs from unpacked subfolders next to the program (where Windows looks), then drop those folders."""
        for sub in [d for d in target.iterdir() if d.is_dir() and d.name not in ("model_specs", "tools")]:
            for dll in sub.rglob("*.dll"):
                shutil.move(str(dll), target / dll.name)
            shutil.rmtree(sub, ignore_errors=True)

    async def _install_espeak(self, client, job: dict) -> None:
        """eSpeak NG's official Windows installer, unpacked (msiexec /a: nothing is installed on the PC)."""
        url, size, sha = config.ESPEAK_MSI
        target = config.espeak_dir()
        msi = target.parent / "espeak-ng.msi"
        await self._fetch(client, url, size, sha, msi, job)
        job["status"] = "installing"
        await asyncio.to_thread(self._unpack_msi, msi, target)

    @staticmethod
    def _unpack_msi(msi: Path, target: Path) -> None:
        import subprocess
        staging = target.with_name(target.name + ".new")
        shutil.rmtree(staging, ignore_errors=True)
        # one command line: msiexec wants TARGETDIR="path with spaces", not the whole argument quoted
        try:
            r = subprocess.run(f'msiexec.exe /a "{msi}" /qn TARGETDIR="{staging}"', capture_output=True, timeout=300,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            shutil.rmtree(staging, ignore_errors=True)
            raise IOError("eSpeak NG couldn't be unpacked (msiexec didn't finish).")
        found = next(staging.rglob("libespeak-ng.dll"), None) if staging.exists() else None
        if r.returncode or not found:
            shutil.rmtree(staging, ignore_errors=True)
            raise IOError(f"eSpeak NG couldn't be unpacked (msiexec {r.returncode}).")
        shutil.rmtree(target, ignore_errors=True)
        shutil.move(str(found.parent), target)
        shutil.rmtree(staging, ignore_errors=True)
        msi.unlink(missing_ok=True)

    @staticmethod
    def _unpack(zips: list[Path], target: Path, exe: str) -> None:
        staging = target.with_name(target.name + ".new")
        shutil.rmtree(staging, ignore_errors=True)
        for z in zips:
            with zipfile.ZipFile(z) as f:
                f.extractall(staging)
        found = next(staging.rglob(exe), None)  # some builds keep their files in a subfolder (Release/)
        if not found:
            raise IOError(f"The download doesn't contain {exe}")
        if found.parent != staging:
            inner = found.parent
            for item in inner.iterdir():
                shutil.move(str(item), staging / item.name)
            while inner != staging and not any(inner.iterdir()):  # the now-empty Release/ folder(s)
                inner.rmdir()
                inner = inner.parent
        if target.exists():
            shutil.rmtree(target)
        staging.replace(target)
        for z in zips:
            z.unlink()

    # ---- engine builds (job key "engine:<id>") ----

    def engine_zips(self, key: str) -> list[tuple[str, int, Path]]:
        root = config.engine_dir(self.cfg, key).parent
        return [(url, size, root / url.rsplit("/", 1)[1]) for url, size, _ in config.ENGINES[key]["zips"]]

    def engine_partial(self, key: str) -> int:
        parts = (z.with_name(z.name + ".part") for _, _, z in self.engine_zips(key))
        return sum(p.stat().st_size for p in parts if p.exists())

    def start_engine(self, key: str) -> None:
        if key not in config.ENGINES:
            raise ValueError("Unknown engine")
        self._launch("engine:" + key, self._run_engine(key))

    async def _run_engine(self, key: str) -> None:
        job = self.jobs["engine:" + key]
        zips = config.ENGINES[key]["zips"]
        job["total"] = sum(size for _, size, _ in zips)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30, read=300)) as client:
                await self._install_zips(client, zips, config.engine_dir(self.cfg, key), config.ENGINE_EXE, job)
            job["status"] = "done"
            log.info("Installed engine %s", key)
            if self.cfg["engine"] not in config.installed_engines(self.cfg):  # first engine: use it
                self.cfg["engine"] = key
                config.save(self.cfg)
            self.ensure_whisper_gpu()
            self.ensure_runtimes()
        except asyncio.CancelledError:
            job["status"] = "cancelled"
        except Exception as e:
            log.exception("Engine %s download failed", key)
            job.update(status="failed", error=str(e) or e.__class__.__name__)

    def discard_engine(self, key: str) -> None:
        if self.busy("engine:" + key):
            raise RuntimeError("That engine is downloading right now. Cancel it first.")
        for _, _, z in self.engine_zips(key):
            for p in (z, z.with_name(z.name + ".part")):
                p.unlink(missing_ok=True)
        self.jobs.pop("engine:" + key, None)

    def delete_engine(self, key: str) -> None:
        self.discard_engine(key)
        shutil.rmtree(config.engine_dir(self.cfg, key), ignore_errors=True)
        if key in config.WHISPER_GPU:  # its Whisper build can't run without it
            shutil.rmtree(config.whisper_gpu_dir(key), ignore_errors=True)
            self.jobs.pop("whisper-gpu:" + key, None)
        if key in config.S2_RUNTIME:  # nor can its s2.cpp build
            shutil.rmtree(config.s2_dir(key), ignore_errors=True)
            self.jobs.pop("s2-runtime:" + key, None)
        for rt, builds, folder in (("omni", config.OMNI_BUILD, config.omni_dir), ("acpp", config.ACPP_BUILD, config.acpp_dir)):
            build = builds.get(key)  # nor its omnivoice.cpp / audio.cpp build, unless another engine uses it (Vulkan)
            if build and not any(builds.get(k) == build for k in config.installed_engines(self.cfg)):
                shutil.rmtree(folder(build), ignore_errors=True)
                self.jobs.pop(f"{rt}-runtime:{build}", None)

    # ---- Whisper on the graphics card (job key "whisper-gpu:<engine>") ----

    def whisper_gpu(self) -> dict | None:
        """Where Whisper runs: None with no graphics card engine in use, else that engine and its build's state."""
        key = config.whisper_gpu_engine(self.cfg)
        if not key:
            return None
        url, size, _ = config.WHISPER_GPU[key]
        part = config.whisper_gpu_dir(key).parent / (url.rsplit("/", 1)[1] + ".part")
        return {"engine": key, "label": config.ENGINES[key]["label"], "size": size,
                "ready": (config.whisper_gpu_dir(key) / config.WHISPER_EXE).exists(),
                "partial": part.stat().st_size if part.exists() else 0, "job": self.jobs.get("whisper-gpu:" + key)}

    def ensure_whisper_gpu(self, retry: bool = False) -> None:
        """Fetch Whisper's build for the graphics card engine in use, once there's a Whisper model to run. It happens
        by itself (also after an update); a failed download waits for retry=True instead of trying in a loop."""
        key = config.whisper_gpu_engine(self.cfg)
        if not key or (config.whisper_gpu_dir(key) / config.WHISPER_EXE).exists() or self.busy("whisper-gpu:" + key):
            return
        if not any(config.MODELS[k]["kind"] == "subtitles" for k in config.installed_models(self.cfg)):
            return
        if not retry and (self.jobs.get("whisper-gpu:" + key) or {}).get("status") in ("failed", "cancelled"):
            return
        self._launch("whisper-gpu:" + key, self._run_whisper_gpu(key))

    async def _run_whisper_gpu(self, key: str) -> None:
        job = self.jobs["whisper-gpu:" + key]
        job["total"] = config.WHISPER_GPU[key][1]
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30, read=300)) as client:
                await self._install_zips(client, [config.WHISPER_GPU[key]], config.whisper_gpu_dir(key),
                                         config.WHISPER_EXE, job)
            job["status"] = "done"
            log.info("Whisper now runs on the graphics card (%s)", key)
        except asyncio.CancelledError:
            job["status"] = "cancelled"
        except Exception as e:
            log.exception("Whisper for the graphics card (%s) failed to download", key)
            job.update(status="failed", error=str(e) or e.__class__.__name__)

    # ---- s2.cpp for S2 Pro, omnivoice.cpp for OmniVoice, audio.cpp (job key "<runtime>-runtime:<build>") ----

    def ensure_runtimes(self) -> None:
        """Fetch the s2.cpp / omnivoice.cpp / audio.cpp build for the engine in use when one of its models is there
        but the build isn't (after switching or reinstalling engines, or an update). Fails quietly; the model card's
        download brings it too."""
        installed = config.installed_models(self.cfg)
        for rt in ("s2", "omni", "acpp"):
            build = self._rt_missing(rt)
            if not build or not self._rt_size(rt, build) or self.busy(f"{rt}-runtime:{build}"):
                continue
            if not any(config.MODELS[k].get("runtime") == rt for k in installed):
                continue
            if (self.jobs.get(f"{rt}-runtime:{build}") or {}).get("status") in ("failed", "cancelled"):
                continue
            self._launch(f"{rt}-runtime:{build}", self._run_runtime(rt, build))
        if (any(self._espeak_missing(config.MODELS[k]) for k in installed) and not self.busy("espeak")
                and (self.jobs.get("espeak") or {}).get("status") not in ("failed", "cancelled")):
            self._launch("espeak", self._run_espeak())

    async def _run_espeak(self) -> None:
        job = self.jobs["espeak"]
        job["total"] = config.ESPEAK_MSI[1]
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30, read=300)) as client:
                await self._install_espeak(client, job)
            job["status"] = "done"
            log.info("eSpeak NG installed")
            self._done("espeak")
        except asyncio.CancelledError:
            job["status"] = "cancelled"
        except Exception as e:
            log.exception("eSpeak NG failed to download")
            job.update(status="failed", error=str(e) or e.__class__.__name__)

    async def _run_runtime(self, rt: str, build: str) -> None:
        job = self.jobs[f"{rt}-runtime:{build}"]
        job["total"] = self._rt_size(rt, build)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30, read=300)) as client:
                await self._install_zips(client, self._rt_zips(rt, build), *self._rt_place(rt, build), job)
            job["status"] = "done"
            log.info("%s installed for %s", {"s2": "s2.cpp", "omni": "omnivoice.cpp", "acpp": "audio.cpp"}[rt], build)
            self._done(f"{rt}-runtime")
        except asyncio.CancelledError:
            job["status"] = "cancelled"
        except Exception as e:
            log.exception("The %s build for %s failed to download", rt, build)
            job.update(status="failed", error=str(e) or e.__class__.__name__)

    # ---- tools (job key "tool:<id>"), e.g. ffmpeg for video files ----

    def tools(self) -> list[dict]:
        from .media import ffmpeg_source
        out = []
        for key, t in config.TOOLS.items():
            url, size, _ = t["zip"]
            part = config.tool_dir(key).parent / (url.rsplit("/", 1)[1] + ".part")
            # ffmpeg may also be on the PC already; other tools only count when the app has them
            source = ffmpeg_source() if key == "ffmpeg" else ("app" if (config.tool_dir(key) / t["exe"]).exists() else None)
            out.append({"key": key, "label": t["label"], "about": t["about"], "license": t["license"], "size": size,
                        "installed": source == "app", "on_pc": source == "system", "ready": bool(source),
                        "partial": part.stat().st_size if part.exists() else 0, "job": self.jobs.get("tool:" + key)})
        return out

    def start_tool(self, key: str) -> None:
        if key not in config.TOOLS:
            raise ValueError("Unknown tool")
        self._launch("tool:" + key, self._run_tool(key))

    async def _run_tool(self, key: str) -> None:
        job = self.jobs["tool:" + key]
        t = config.TOOLS[key]
        job["total"] = t["zip"][1]
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30, read=300)) as client:
                await self._install_zips(client, [t["zip"]], config.tool_dir(key), t["exe"], job)
            job["status"] = "done"
        except asyncio.CancelledError:
            job["status"] = "cancelled"
        except Exception as e:
            log.exception("Tool %s download failed", key)
            job.update(status="failed", error=str(e) or e.__class__.__name__)

    def delete_tool(self, key: str) -> None:
        if self.busy("tool:" + key):
            raise RuntimeError("That download is still running. Cancel it first.")
        url = config.TOOLS[key]["zip"][0]
        (config.tool_dir(key).parent / (url.rsplit("/", 1)[1] + ".part")).unlink(missing_ok=True)
        shutil.rmtree(config.tool_dir(key), ignore_errors=True)
        self.jobs.pop("tool:" + key, None)

    # ---- removing models ----

    def discard(self, key: str) -> list[str]:
        """Abandon a paused download: delete its unfinished .part files."""
        busy = {f for k, t in self._tasks.items() if not t.done() and k in config.MODELS for f in config.model_files(k)}
        if any(name in busy for name in self.missing(key)):
            raise RuntimeError("Another download is using this file right now. Cancel it first.")
        removed = []
        for name in self.missing(key):
            part = self.folder / (name + ".part")
            if part.exists():
                part.unlink()
                removed.append(part.name)
        self.jobs.pop(key, None)
        return removed

    def delete(self, key: str) -> list[str]:
        """Remove a model's files, keeping any another installed model still uses."""
        others = {f for k in config.installed_models(self.cfg) if k != key for f in config.model_files(k)}
        removed = []
        for name in config.model_files(key):
            if name in others:
                continue
            for path in (self.folder / name, self.folder / (name + ".part")):
                if path.exists():
                    path.unlink()
                    removed.append(path.name)
        self.jobs.pop(key, None)
        return removed
