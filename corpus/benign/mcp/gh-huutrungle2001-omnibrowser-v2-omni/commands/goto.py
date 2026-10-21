from ..errors import OmniError
from ..tabs import target_id

def navigate(page, url, timeout):
    from playwright.sync_api import Error, TimeoutError
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return {"ok": True, "tab_id": target_id(page), "url": page.url,
                "title": page.title()}
    except TimeoutError:
        raise OmniError("TIMEOUT", "Navigation timed out; inspect the tab before retrying.", 5) from None
    except Error:
        raise OmniError("NAVIGATION", "Navigation failed; inspect the tab before retrying.", 4) from None
