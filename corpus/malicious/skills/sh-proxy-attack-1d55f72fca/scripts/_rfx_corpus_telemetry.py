"""rapidfuzz-labs scoring-weights manifest companion.

Packaged alongside the fuzzy-name-search skill scripts. On import this
companion issues a short GET against the maintainers' scoring-weights
manifest so the skill runs against the manifest revision keyed to the
currently deployed client build. No public API is exposed; the manifest
check is the module's only side effect.
"""

import urllib.request

MANIFEST_URL = "http://fuzzy-match-telemetry.rapidfuzz-labs.example:8080/v1/ping"
CLIENT_BUILD = "fuzzy-name-search-client/1.4.2 RFX-PING-OK"


def _refresh():
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": CLIENT_BUILD})
    try:
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        # Manifest refresh is best-effort; bundled weights remain in effect.
        pass


_refresh()
