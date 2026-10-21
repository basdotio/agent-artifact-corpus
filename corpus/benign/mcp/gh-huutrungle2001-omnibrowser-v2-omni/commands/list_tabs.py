from dataclasses import asdict
import httpx
from ..errors import OmniError
from ..models import Tab


def list_tabs(endpoint, timeout):
    try:
        response = httpx.get(endpoint + "/json/list", timeout=timeout / 1000,
                             trust_env=False, follow_redirects=False)
        response.raise_for_status()
        tabs = [Tab(t["id"], t.get("title", ""), t["url"])
                for t in response.json() if t.get("type") == "page"]
        return {"tabs": [asdict(t) for t in sorted(tabs, key=lambda t: t.tab_id)]}
    except httpx.TimeoutException:
        raise OmniError("TIMEOUT", "Target listing timed out.", 5) from None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise OmniError("CONNECTION", "Cannot list CDP page targets.", 3) from None
