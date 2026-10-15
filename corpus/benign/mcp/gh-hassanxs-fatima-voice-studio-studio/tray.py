"""System tray icon. It only talks to the running server over HTTP, so it never touches the event loop."""
import json
import os
import subprocess
import threading
import time
import urllib.request
import webbrowser

import pystray
from PIL import ImageDraw

from . import APP_NAME, autostart, config

STATE_COLORS = {"busy": "#f5a524", "error": "#ff3b30"}


class Tray:
    def __init__(self, cfg: dict, on_quit):
        self.cfg, self.on_quit = cfg, on_quit
        self.base = f"http://{cfg['host']}:{cfg['port']}"
        self.state = {}
        self._icons = {}
        self.icon = pystray.Icon("fatima-voice-studio", self._image(None), APP_NAME, menu=pystray.Menu(
            pystray.MenuItem(f"Open {APP_NAME}", self.open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Copy API URL", lambda: copy(f"{self.base}/v1")),
            pystray.MenuItem("Copy API key", lambda: copy(self.cfg["api_key"])),
            pystray.MenuItem("Open batches folder", lambda: os.startfile(self.cfg["batches_dir"])),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start with Windows", self.toggle_autostart, checked=lambda _: autostart.enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit),
        ))

    def run(self) -> None:
        threading.Thread(target=self._watch, daemon=True).start()
        self.icon.run()

    def _image(self, state: str | None):
        if state not in self._icons:
            img = autostart.icon_image(64)
            if state in STATE_COLORS:  # status dot
                ImageDraw.Draw(img).ellipse([40, 40, 62, 62], fill=STATE_COLORS[state], outline="#20221e", width=3)
            self._icons[state] = img
        return self._icons[state]

    def _watch(self) -> None:
        while True:
            try:
                with urllib.request.urlopen(self.base + "/api/state", timeout=5) as r:
                    self.state = json.load(r)
                queued = len(self.state.get("queue", []))
                busy = self.state.get("current") or self.state.get("api_busy") or self.state.get("finishing")
                state = "error" if self.state["engine"]["state"] == "error" else "busy" if busy else None
                self.icon.icon = self._image(state)
                label = "speaking" if busy else "engine problem" if state == "error" else "ready"
                self.icon.title = f"{APP_NAME} — {label}" + (f" · {queued} batch(es) queued" if queued else "")
                self.icon.update_menu()
                self._notify_update()
                self._notify_finished()
            except Exception:
                pass
            time.sleep(3)

    def _notify_update(self) -> None:
        """A Windows notification when a new version is out: once per version (remembered across restarts)."""
        upd = self.state.get("update") or {}
        latest = upd.get("latest")
        if upd.get("status") != "available" or not latest or self.cfg.get("update_notified") == latest:
            return
        self.cfg["update_notified"] = latest
        config.save(self.cfg)
        self.icon.notify(f"Version {latest} is ready to install. Open {APP_NAME} → About "
                         "(your voices, models and audio are kept).", "Update available")

    def _notify_finished(self) -> None:
        """A Windows notification when a batch stops working (finished, partly failed, or cancelled)."""
        with urllib.request.urlopen(self.base + "/api/batches", timeout=5) as r:
            batches = json.load(r)
        busy = ("running", "queued", "finishing")
        seen, self._seen = getattr(self, "_seen", None), {b["id"]: b["status"] for b in batches}
        if seen is None or not self.cfg.get("notify", True):
            return
        for b in batches:
            if seen.get(b["id"]) not in busy or b["status"] in busy or b["status"] == "paused":
                continue
            mins = (b.get("elapsed_seconds") or 0) / 60
            took = f" in {mins:.0f} min" if mins >= 1 else ""
            length = b.get("audio_seconds") or 0
            audio = f" ({length / 60:.1f} min of audio)" if length >= 60 else ""
            n = b["scripts_total"]
            if b["failed"]:
                text = f"{b['scripts_done']} of {n} scripts done{took} — {b['failed']} part(s) failed. Open {APP_NAME} to retry."
            elif b["status"] == "cancelled" or b["cancelled"]:
                text = f"Stopped after {b['done']} of {b['total']} parts."
            else:
                what = "Your audio is ready" if b.get("kind") == "singles" else f"All {n} script{'s' if n != 1 else ''} done"
                text = f"{what}{took}{audio}." + (f" {b['checks']} part(s) worth a listen." if b.get("checks") else "")
            self.icon.notify(text, f"Finished: {b['name']}"[:63])

    def open(self) -> None:
        webbrowser.open(self.base + "/")

    def toggle_autostart(self) -> None:
        autostart.set_enabled(not autostart.enabled())

    def quit(self) -> None:
        self.icon.visible = False
        self.on_quit()
        self.icon.stop()


def copy(text: str) -> None:
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", "Set-Clipboard -Value $env:CLIP"],
                   env=os.environ | {"CLIP": text}, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
