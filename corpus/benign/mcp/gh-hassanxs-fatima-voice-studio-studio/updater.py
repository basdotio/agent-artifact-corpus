"""Updates from GitHub releases: a quick update (only the app's own files) or a full one (the installer).

Each release carries update.json:
  {"version": "1.0.2", "runtime": "<fingerprint>", "notes": "...",
   "full": {"file": "FatimaVoiceStudio-Setup-1.0.2.exe", "size": ..., "sha256": "..."},
   "app":  {"file": "FatimaVoiceStudio-app-1.0.2.zip",   "size": ..., "sha256": "..."}}
The runtime fingerprint covers the bundled Python, its packages, the launcher and the installer. When it
matches the installed one, swapping the app's files (studio/ and a few top-level files) is enough;
otherwise only the full update is offered. Every download is checked against its SHA-256 first.
"""
import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

from . import REPO_URL, __version__, config

log = logging.getLogger("studio.updater")

API_LATEST = REPO_URL.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
CHANGELOG_URL = REPO_URL.replace("https://github.com/", "https://raw.githubusercontent.com/") + "/main/CHANGELOG.md"
CHECK_EVERY = 6 * 3600
LAUNCHER = "FatimaVoiceStudio.exe"
RUNTIME_FILE = config.ROOT / "runtime.txt"  # written into installed copies by the build
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

request_exit = None  # set by __main__: closes the app cleanly (tray + server) so the update can replace it


def parse_version(v: str) -> tuple:
    return tuple(int(p) for p in v.lstrip("vV").split("-")[0].split(".") if p.isdigit())


def whats_new(changelog: str, current: str, latest: str) -> list[dict]:
    """CHANGELOG.md -> [{"version", "items"}] for the versions after `current` up to `latest`, newest first."""
    out, section = [], None
    for line in changelog.splitlines():
        if line.startswith("## "):
            v = line[3:].strip().lstrip("vV")
            ok = bool(parse_version(v)) and parse_version(current) < parse_version(v) <= parse_version(latest)
            section = {"version": v, "items": []} if ok else None
            if section:
                out.append(section)
        elif section is not None and line.lstrip().startswith(("- ", "* ")):
            section["items"].append(line.strip()[2:].strip())
    return [s for s in out if s["items"]]


def installed_runtime() -> str | None:
    try:
        return RUNTIME_FILE.read_text(encoding="ascii").strip() or None
    except OSError:
        return None


class Updater:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.state = {"status": "idle", "current": __version__, "installed": config.INSTALLED,
                      "latest": None, "notes": "", "whats_new": [], "url": None, "checked": None, "error": None,
                      "full": None, "app": None, "quick_ok": False, "progress": None}
        self._release = None
        self._task: asyncio.Task | None = None

    @property
    def folder(self) -> Path:
        return config.DATA / "updates"

    def feed(self) -> str:
        return self.cfg.get("update_feed") or API_LATEST  # update_feed: only for testing a local feed

    # ---- checking ------------------------------------------------------------

    async def check(self) -> dict:
        if self.state["status"] in ("downloading", "applying"):
            return self.state
        self.state.update(status="checking", error=None)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=20,
                                         headers={"Accept": "application/vnd.github+json"}) as client:
                r = await client.get(self.feed())
                if r.status_code == 404:  # no releases yet
                    self.state.update(status="up_to_date", checked=int(time.time()))
                    return self.state
                r.raise_for_status()
                release = r.json()
                assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
                if "update.json" not in assets:  # a release from before the updater: no in-app update possible
                    manifest = {"version": release.get("tag_name", "0").lstrip("vV")}
                else:
                    manifest = (await client.get(assets["update.json"])).raise_for_status().json()
                changes = []
                if parse_version(manifest["version"]) > parse_version(__version__):
                    try:  # a short "what's new" list; the release page itself is written for people downloading it
                        text = (await client.get(self.cfg.get("update_changelog") or CHANGELOG_URL)).raise_for_status().text
                        changes = whats_new(text, __version__, manifest["version"])
                    except Exception as e:
                        log.info("No changelog: %s", e)
        except Exception as e:
            log.warning("Update check failed: %s", e)
            self.state.update(status="error", error=f"Couldn't check for updates: {e}", checked=int(time.time()))
            return self.state
        newer = parse_version(manifest["version"]) > parse_version(__version__)
        quick_ok = bool(config.INSTALLED and manifest.get("app") and installed_runtime()
                        and manifest.get("runtime") == installed_runtime())
        self._release = {"manifest": manifest, "assets": assets}
        if newer and not (manifest.get("full") or manifest.get("app")):
            self.state.update(status="manual", latest=manifest["version"], url=release.get("html_url"),
                              notes=release.get("body") or "", whats_new=changes, checked=int(time.time()), error=None,
                              full=None, app=None)
            return self.state
        self.state.update(status="available" if newer else "up_to_date", latest=manifest["version"],
                          notes=release.get("body") or manifest.get("notes") or "", whats_new=changes,
                          url=release.get("html_url"),
                          full=manifest.get("full"), app=manifest.get("app"), quick_ok=quick_ok,
                          checked=int(time.time()), error=None)
        if newer:
            log.info("Update available: %s -> %s (quick update %s)", __version__, manifest["version"],
                     "possible" if quick_ok else "not possible")
        return self.state

    async def watch(self) -> None:
        """Check soon after start, then every few hours (unless switched off in Settings)."""
        await asyncio.sleep(20)
        for old in self.folder.glob("FatimaVoiceStudio-*"):  # downloads from an update that already ran
            try:
                old.unlink()
            except OSError:
                pass  # the installer may still be closing; next start
        while True:
            if self.cfg.get("check_updates", True) and config.INSTALLED:
                await self.check()
            await asyncio.sleep(CHECK_EVERY)

    # ---- updating ------------------------------------------------------------

    def start(self, kind: str) -> None:
        if kind not in ("quick", "full"):
            raise ValueError("Unknown update type")
        if not config.INSTALLED:
            raise ValueError("This copy runs from source; update it with git pull instead.")
        if self.state["status"] != "available" or not self._release:
            raise ValueError("No update is available. Check for updates first.")
        if kind == "quick" and not self.state["quick_ok"]:
            raise ValueError("This update changes the bundled runtime, so it needs the full update.")
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(kind))

    async def _run(self, kind: str) -> None:
        item = self._release["manifest"]["app" if kind == "quick" else "full"]
        url = self._release["assets"].get(item["file"])
        try:
            if not url:
                raise ValueError(f"{item['file']} is missing from the release")
            path = await self._download(url, item)
            self.state.update(status="applying", progress=None)
            if kind == "quick":
                self._apply_quick(path)
            else:
                self._apply_full(path)
        except Exception as e:
            log.exception("Update failed")
            self.state.update(status="available", progress=None, error=f"Update failed: {e}")

    async def _download(self, url: str, item: dict) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / item["file"]
        self.state.update(status="downloading", progress={"done": 0, "total": item["size"]}, error=None)
        digest = hashlib.sha256()
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(30, read=120)) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    async for chunk in r.aiter_bytes(1 << 18):
                        f.write(chunk)
                        digest.update(chunk)
                        self.state["progress"]["done"] += len(chunk)
        if digest.hexdigest() != item["sha256"].lower():
            path.unlink(missing_ok=True)
            raise ValueError("the download doesn't match its published SHA-256, so it wasn't installed")
        return path

    def _apply_full(self, installer: Path) -> None:
        """Run the installer silently; it stops this app, updates it and starts it again (/relaunch=1)."""
        log.info("Starting full update with %s", installer.name)
        subprocess.Popen([str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/relaunch=1"],
                         creationflags=DETACHED, close_fds=True)
        self.state["status"] = "restarting"

    def _apply_quick(self, archive: Path) -> None:
        """Hand over to a small helper (run by the bundled Python) that swaps the files once the app has
        closed, then starts it again. The app closes itself a moment later."""
        helper = self.folder / "apply_update.py"
        helper.write_text(HELPER, encoding="utf-8")
        python = config.ROOT / "python" / "pythonw.exe"
        log.info("Starting quick update to %s", self.state["latest"])
        subprocess.Popen([str(python), str(helper), str(os.getpid()), str(config.ROOT), str(archive),
                          self.state["latest"], str(self.folder / "update.log")],
                         creationflags=DETACHED, close_fds=True, cwd=str(self.folder))
        self.state["status"] = "restarting"
        threading.Timer(1.0, lambda: (request_exit or (lambda: os._exit(0)))()).start()


# Runs with the bundled Python's stdlib only, outside the app's own files (which it replaces).
HELPER = r'''
import ctypes, os, shutil, subprocess, sys, time, winreg, zipfile

pid, app, archive, version, log_path = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
APP_ID = "{D5B6B025-A1AD-411E-AE1F-EE64746C2739}_is1"  # must match AppId in packaging/installer.iss (the build checks)


def log(msg):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def wait_for_exit(pid, seconds):
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x00100000 | 0x0001, False, pid)  # SYNCHRONIZE | TERMINATE
    if not h:
        return
    if k32.WaitForSingleObject(h, seconds * 1000) != 0:
        log("app still running; stopping it")
        k32.TerminateProcess(h, 1)
        k32.WaitForSingleObject(h, 10000)
    k32.CloseHandle(h)


def retry(fn, *args):
    for attempt in range(30):  # files can stay locked for a moment after the app exits
        try:
            return fn(*args)
        except PermissionError:
            time.sleep(1)
    return fn(*args)


try:
    log(f"quick update to {version}")
    wait_for_exit(pid, 120)
    staging = os.path.join(app, "_update_new")
    shutil.rmtree(staging, ignore_errors=True)
    with zipfile.ZipFile(archive) as z:
        z.extractall(staging)
    for name in os.listdir(staging):
        src, dst = os.path.join(staging, name), os.path.join(app, name)
        if os.path.isdir(src):
            old = dst + ".old"
            shutil.rmtree(old, ignore_errors=True)
            if os.path.exists(dst):
                retry(os.replace, dst, old)
            retry(os.replace, src, dst)
            shutil.rmtree(old, ignore_errors=True)
        else:
            retry(os.replace, src, dst)
    shutil.rmtree(staging, ignore_errors=True)
    try:  # keep Windows' Installed apps in step
        key = "/".join(["Software", "Microsoft", "Windows", "CurrentVersion", "Uninstall", APP_ID]).replace("/", chr(92))
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, version)
    except OSError as e:
        log(f"couldn't update the version in Installed apps: {e}")
    os.remove(archive)
    log("done")
except Exception as e:
    log(f"FAILED: {e!r}")
finally:
    subprocess.Popen([os.path.join(app, "FatimaVoiceStudio.exe"), "--tray", "--no-browser"], cwd=app,
                     creationflags=0x00000008)
'''
