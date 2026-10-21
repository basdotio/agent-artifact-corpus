"""In-memory scoped cookies, bounded HTTP streaming, atomic publication."""
from http.cookiejar import Cookie, CookieJar, DefaultCookiePolicy
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request

import httpx

from ..cdp import http_url
from ..errors import OmniError


HTML_START = re.compile(
    br"\A(?:\xef\xbb\xbf)?\s*(?:(?:<!--.*?-->|<\?xml.*?\?>)\s*)*"
    br"<(?:!doctype\s+html|html|head|body|form)(?:\s|/?>)", re.I | re.S)


def failure(message, code="DOWNLOAD"):
    return OmniError(code, message, 6)


def cookie_jar(cookies):
    jar = CookieJar(DefaultCookiePolicy(strict_ns_domain=DefaultCookiePolicy.DomainStrictNonDomain))
    for c in cookies:
        # Partitioned cookies need a browser partition key; don't broaden their scope.
        if c.get("partitionKey"):
            continue
        domain = c["domain"]
        jar.set_cookie(Cookie(0, c["name"], c["value"], None, False,
                              domain, domain.startswith("."), domain.startswith("."),
                              c["path"], True, c["secure"],
                              int(c["expires"]) if c.get("expires", -1) > 0 else None,
                              False, None, None, {}, False))
    return jar


def destination(output, mkdir, overwrite):
    path = Path(output).absolute()
    if path.exists() and (not overwrite or not path.is_file()):
        raise failure("Output already exists; use --overwrite for an existing file.")
    if path.is_symlink():
        raise failure("Symlink output paths are not supported.")
    if not path.parent.is_dir() and not mkdir:
        raise failure("Output parent must exist; use --mkdir to create it.")
    return path


def download(context, url, output, timeout, max_bytes, mkdir=False, overwrite=False):
    path = destination(output, mkdir, overwrite)
    jar = cookie_jar(context.cookies())
    deadline = time.monotonic() + timeout / 1000
    temporary = None
    expected_pdf = path.suffix.lower() == ".pdf" or Path(urlsplit(url).path).suffix.lower() == ".pdf"
    expected_file = expected_pdf or path.suffix.lower() not in (".html", ".htm")
    try:
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(follow_redirects=False, trust_env=False) as client:
            current = url
            for redirects in range(11):
                http_url(current)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise OmniError("TIMEOUT", "Download timed out.", 5)
                # Recompute cookies for every hop. Never copy a previous Cookie header.
                request = Request(current)
                jar.add_cookie_header(request)
                headers = {"Accept-Encoding": "identity"}
                if request.has_header("Cookie"):
                    headers["Cookie"] = request.get_header("Cookie")
                with client.stream("GET", current, headers=headers, timeout=remaining) as response:
                    # In-memory Set-Cookie state also obeys domain/path/secure policy.
                    jar.extract_cookies(_CookieResponse(response), request)
                    client.cookies.clear()  # Only our stricter jar controls subsequent requests.
                    if response.status_code in (301, 302, 303, 307, 308):
                        if redirects == 10 or not response.headers.get("location"):
                            raise failure("Redirect limit exceeded or missing redirect location.")
                        current = urljoin(current, response.headers["location"])
                        http_url(current)
                        if re.search(r"/(?:login|signin|sign-in|authenticate)(?:[/.?]|$)", current, re.I):
                            raise failure("Resource redirected to authentication.", "AUTH_REQUIRED")
                        continue
                    if response.status_code in (401, 403):
                        raise failure("Browser cookies did not authorize this resource.", "AUTH_REQUIRED")
                    if response.status_code == 405:
                        raise OmniError("UNSUPPORTED", "Resource does not support GET; POST download flows are unsupported.", 2)
                    if response.status_code < 200 or response.status_code >= 300:
                        raise failure("Resource returned an unsuccessful HTTP status.")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    expected_pdf = expected_pdf or content_type == "application/pdf"
                    expected_file = expected_file or expected_pdf
                    if expected_file and content_type in ("text/html", "application/xhtml+xml"):
                        raise failure("Received HTML instead of a file; authentication may be required.", "AUTH_REQUIRED")
                    length = response.headers.get("content-length", "")
                    if length.isdigit() and int(length) > max_bytes:
                        raise failure("Resource exceeds --max-bytes.")
                    count = 0
                    prefix = bytearray()
                    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".omni-", delete=False) as stream:
                        temporary = Path(stream.name)
                        for chunk in response.iter_bytes():
                            if time.monotonic() > deadline:
                                raise OmniError("TIMEOUT", "Download timed out.", 5)
                            count += len(chunk)
                            if count > max_bytes:
                                raise failure("Resource exceeds --max-bytes.")
                            if len(prefix) < 1024:
                                prefix.extend(chunk[:1024 - len(prefix)])
                            stream.write(chunk)
                        start = bytes(prefix).lstrip()
                        if expected_file and HTML_START.match(start):
                            raise failure("Received HTML instead of a file; authentication may be required.", "AUTH_REQUIRED")
                        if expected_pdf and not bytes(prefix).startswith(b"%PDF-"):
                            raise failure("Response does not contain PDF magic bytes.")
                        stream.flush()
                        os.fsync(stream.fileno())
                    if overwrite:
                        os.replace(temporary, path)
                    else:
                        # Atomic no-clobber publication even if another process created output.
                        os.link(temporary, path)
                        temporary.unlink()
                    temporary = None
                    return {"ok": True, "status": response.status_code, "path": str(path),
                            "bytes": count, "content_type": content_type, "final_url": str(response.url)}
    except httpx.TimeoutException:
        raise OmniError("TIMEOUT", "Download timed out.", 5) from None
    except (httpx.HTTPError, OSError, ValueError):
        raise failure("Download failed; output was not replaced.") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class _CookieResponse:
    def __init__(self, response):
        from email.message import Message
        self.headers = Message()
        for value in response.headers.get_list("set-cookie"):
            self.headers.add_header("Set-Cookie", value)

    def info(self):
        return self.headers
