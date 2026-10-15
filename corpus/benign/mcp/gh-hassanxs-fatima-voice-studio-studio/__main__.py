"""Start Fatima Voice Studio.

  python -m studio                 console mode (logs in the window), opens the browser
  pythonw -m studio --tray         background app with a tray icon (what the shortcuts run)
  --no-browser                     don't open the browser on start
  python -m studio --install       create the Start menu entry and the launcher in this folder
  --check                          import everything and exit 0 (the installer build's smoke test)

An installed copy starts through FatimaVoiceStudio.exe, which runs `python -m studio` with its arguments
(just `--tray` when it has none).
"""
import json
import logging
import sys
import threading
import urllib.request
import webbrowser

import uvicorn

from . import config
from .app import create_app


def already_running(cfg: dict) -> bool:
    try:
        with urllib.request.urlopen(f"http://{cfg['host']}:{cfg['port']}/v1/health", timeout=2) as r:
            return json.load(r).get("status") == "ok"
    except Exception:
        return False


def main() -> None:
    args = set(sys.argv[1:])
    if "--check" in args:
        from . import tray, mcp_server  # noqa: F401  (app is already imported)
        sys.exit(0)
    cfg = config.load()
    if "--install" in args:
        from . import autostart
        autostart.install_launchers()
        print(f"Created {autostart.START_MENU_LINK}\nCreated {autostart.PROJECT_LINK}")
        return

    url = f"http://{cfg['host']}:{cfg['port']}/"
    if already_running(cfg):  # second launch: just bring up the UI
        if "--no-browser" not in args:
            webbrowser.open(url)
        return

    (config.DATA / "logs").mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(config.DATA / "logs" / "studio.log", encoding="utf-8")]
    if sys.stderr:  # pythonw has no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", handlers=handlers)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    from . import runtime
    runtime.quiet_loader_errors()  # a missing DLL gets the app's own message, not a Windows pop-up per engine run

    server = uvicorn.Server(uvicorn.Config(create_app(cfg), host=cfg["host"], port=cfg["port"],
                                           log_level="warning", log_config=None))
    if "--no-browser" not in args:
        threading.Timer(1.5, webbrowser.open, args=[url]).start()

    if "--tray" in args:
        from .tray import Tray
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        def stop_server():
            server.should_exit = True
            thread.join(timeout=20)

        tray = Tray(cfg, stop_server)
        from . import updater
        updater.request_exit = lambda: threading.Thread(target=tray.quit, daemon=True).start()
        tray.run()
    else:
        from . import updater
        updater.request_exit = lambda: setattr(server, "should_exit", True)
        server.run()


if __name__ == "__main__":
    main()
