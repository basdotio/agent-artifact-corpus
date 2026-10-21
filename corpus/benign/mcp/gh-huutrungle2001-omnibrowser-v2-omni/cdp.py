from contextlib import contextmanager
import ipaddress
from urllib.parse import urlsplit

from .errors import OmniError, invalid


def http_url(value):
    try:
        parts = urlsplit(value)
        if (parts.scheme not in ("http", "https") or not parts.hostname
                or parts.username is not None or parts.password is not None):
            raise ValueError
        _ = parts.port
        if any(ord(c) < 33 for c in value):
            raise ValueError
    except ValueError:
        raise invalid("An absolute HTTP(S) URL without embedded credentials is required.") from None
    return parts


def endpoint(value):
    parts = http_url(value)
    host = parts.hostname
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    if not local or parts.path not in ("", "/") or parts.query or parts.fragment:
        raise invalid("CDP requires a loopback HTTP(S) origin.")
    return value.rstrip("/")


@contextmanager
def connect(url, timeout):
    # Lazy import: list-tabs, --help, validation and --version do not start a driver.
    from playwright.sync_api import sync_playwright, Error, TimeoutError
    with sync_playwright() as pw:
        try:
            # Preserve the user's download policy, focus and media defaults.
            browser = pw.chromium.connect_over_cdp(url, timeout=timeout, no_defaults=True)
        except TimeoutError:
            raise OmniError("TIMEOUT", "CDP connection timed out.", 5) from None
        except Error:
            raise OmniError("CONNECTION", "Cannot connect to the CDP endpoint.", 3) from None
        try:
            browser.contexts[0].set_default_timeout(timeout)
            browser.contexts[0].set_default_navigation_timeout(timeout)
            yield browser
        finally:
            # On an attached browser this disconnects, not Browser.close over CDP.
            try:
                browser.close()
            except Error:
                pass  # A dead transport is already disconnected; preserve original error.
