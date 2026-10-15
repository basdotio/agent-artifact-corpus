"""The ``trs_tool`` validator: does the reply name a real tool that satisfies the task?

Open searches ("find a WDL workflow that uses mosdepth") have many right answers, so the reply is
checked against the registry: candidate identifiers are pulled from the text, looked up through
the registry's TRS API, and accepted if one has the required descriptor language and its
descriptor mentions the required words (or its name matches). Lookups are cached on disk, so
regrading costs no network calls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

BASES = {"org.dockstore": "https://dockstore.org/api/ga4gh/trs/v2",
         "eu.workflowhub": "https://workflowhub.eu/ga4gh/trs/v2"}
_DOCKSTORE = re.compile(r"(#workflow/)?((?:github\.com|gitlab\.com|bitbucket\.org)/[\w.-]+/[\w.-]+(?:/[\w.-]+)?)|"
                        r"\b((?:quay\.io|registry\.hub\.docker\.com)/[\w.-]+/[\w.-]+(?:/[\w.-]+)?)")
_WORKFLOWHUB = re.compile(r"workflowhub\.eu/workflows/(\d+)|\b(?:workflow|ID|id)\s*#?\s*:?\s*(\d{1,5})\b")


def candidates(registry: str, reply: str) -> list[str]:
    found: list[str] = []
    if registry == "org.dockstore":
        for prefix, path, tool in _DOCKSTORE.findall(reply):
            if path:
                found.append("#workflow/" + path.rstrip(".,)"))
            if tool:
                found.append(tool.rstrip(".,)"))
    else:
        for a, b in _WORKFLOWHUB.findall(reply):
            found.append(a or b)
    return list(dict.fromkeys(found))[:6]


class TrsValidator:
    def __init__(self, cache: Path) -> None:
        self.cache_path = cache
        self.cache: dict[str, Any] = json.loads(cache.read_text()) if cache.is_file() else {}

    def _save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, indent=1))

    def _tool(self, client: httpx.Client, registry: str, tool_id: str, descriptor_type: str) -> dict[str, Any]:
        key = f"{registry}|{tool_id}|{descriptor_type}"
        if key in self.cache:
            return self.cache[key]
        base = BASES[registry]
        info: dict[str, Any] = {"found": False}
        try:
            response = client.get(f"{base}/tools/{quote(tool_id, safe='')}")
            if response.status_code == 200:
                tool = response.json()
                versions = [v for v in tool.get("versions") or []
                            if descriptor_type in (v.get("descriptor_type") or [])]
                info = {"found": True, "name": tool.get("name") or "", "description": tool.get("description") or "",
                        "has_type": bool(versions), "descriptor": ""}
                if versions:
                    vid = str(versions[0].get("name") or versions[0].get("id")).split(":")[-1]
                    d = client.get(f"{base}/tools/{quote(tool_id, safe='')}/versions/{quote(vid, safe='')}/{descriptor_type}/descriptor")
                    if d.status_code == 200:
                        info["descriptor"] = (d.json().get("content") or "")[:200000]
        except httpx.HTTPError as exc:
            info = {"found": False, "error": exc.__class__.__name__}
        if "error" not in info:
            self.cache[key] = info
            self._save()
        return info

    def check(self, spec: dict[str, Any], reply: str) -> dict[str, Any]:
        registry, dtype = spec["registry"], spec.get("descriptor_type", "WDL")
        tried = []
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for tool_id in candidates(registry, reply):
                info = self._tool(client, registry, tool_id, dtype)
                ok = info.get("found") and info.get("has_type")
                if ok and spec.get("descriptor_contains"):
                    text = info.get("descriptor", "").casefold()
                    ok = all(word.casefold() in text for word in spec["descriptor_contains"])
                if ok and spec.get("name_contains_any"):
                    text = (info.get("name", "") + " " + info.get("description", "")).casefold()
                    ok = any(word.casefold() in text for word in spec["name_contains_any"])
                tried.append({"id": tool_id, "ok": bool(ok), "found": info.get("found")})
                if ok:
                    return {"verdict": "pass", "detail": f"{tool_id} satisfies the task", "tried": tried}
        return {"verdict": "fail", "detail": "no named tool satisfies the task" if tried else "no tool identifier in the reply",
                "tried": tried}
