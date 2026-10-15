"""One place to launch the browser. Google Chrome by default; falls back to Playwright's bundled Chromium.
Set PITCH_BROWSER=chromium to force the bundled one (Docker/CI)."""
import os


def launch(p, **kw):
    if os.environ.get("PITCH_BROWSER", "chrome") == "chrome":
        try:
            return p.chromium.launch(channel="chrome", headless=True, **kw)
        except Exception:  # noqa: BLE001
            pass
    return p.chromium.launch(headless=True, **kw)
