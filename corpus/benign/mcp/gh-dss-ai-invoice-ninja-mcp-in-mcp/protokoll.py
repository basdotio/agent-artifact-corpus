"""Logger des IN-MCP. Handler hängt erst server.main() an, damit Tests nie in eine Datei schreiben.

Format wie das ab_sync.log von DSS-PMS, weil unsere Instanz dorthin schreibt (LOG_DATEI).
WatchedFileHandler: rotiert wird außerhalb (bei uns vom PMS-Sidecar), der Handler folgt der neuen Datei.
"""
import logging
import logging.handlers
import os
import sys

log = logging.getLogger("in_mcp")


def einrichten(datei: str | None = None) -> None:
    if log.handlers:
        return
    log.setLevel(logging.INFO)
    log.propagate = False
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(threadName)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    datei = datei or os.environ.get("LOG_DATEI", "/data/in-mcp.log")
    os.makedirs(os.path.dirname(datei) or ".", exist_ok=True)
    for handler in (logging.handlers.WatchedFileHandler(datei, encoding="utf-8"),
                    logging.StreamHandler(sys.stdout)):
        handler.setFormatter(fmt)
        log.addHandler(handler)
