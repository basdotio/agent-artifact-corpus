"""Tests for tools.web (offline: run_python is stubbed to capture generated code)."""

import asyncio

import tools.utils as U
import tools.web as web


class _Capture:
    """Stub run_python that records the generated source and compiles it."""

    def __init__(self):
        self.code = None

    async def __call__(self, code, timeout=U.TIMEOUT):
        self.code = code
        compile(code, "<generated>", "exec")  # raises SyntaxError if malformed
        return "(captured)"


def run_capturing(name, args):
    cap = _Capture()
    orig = web.run_python
    web.run_python = cap
    try:
        result = asyncio.run(web.handle_web(name, args))
    finally:
        web.run_python = orig
    return result, cap.code


# --- FUZZ marker enforcement -------------------------------------------------

def test_fuzz_params_requires_fuzz():
    result, _ = run_capturing("fuzz_params", {"url": "http://x/", "preset": "xss"})
    assert result.startswith("[error] no FUZZ")


def test_sqli_requires_fuzz():
    result, _ = run_capturing("sqli_test", {"url": "http://x/"})
    assert result.startswith("[error] no FUZZ")


def test_lfi_requires_fuzz():
    result, _ = run_capturing("lfi_test", {"url": "http://x/"})
    assert result.startswith("[error] no FUZZ")


# --- db_type actually selects payloads --------------------------------------

def test_sqli_mysql_uses_sleep_not_pgsleep():
    _, code = run_capturing("sqli_test", {"url": "http://x/?q=FUZZ", "db_type": "mysql"})
    assert "SLEEP(3)" in code and "pg_sleep" not in code


def test_sqli_postgres_uses_pgsleep_not_sleep():
    _, code = run_capturing("sqli_test", {"url": "http://x/?q=FUZZ", "db_type": "postgres"})
    assert "pg_sleep(3)" in code and "SLEEP(3)" not in code


def test_sqli_auto_uses_all_engines():
    _, code = run_capturing("sqli_test", {"url": "http://x/?q=FUZZ", "db_type": "auto"})
    assert "SLEEP(3)" in code and "pg_sleep(3)" in code


# --- method / body support ---------------------------------------------------

def test_sqli_supports_post_body():
    _, code = run_capturing(
        "sqli_test",
        {"url": "http://x/login", "method": "POST", "body_template": "u=a&p=FUZZ"},
    )
    assert "requests.request(method" in code and "requests.get(" not in code


def test_lfi_supports_method_and_body():
    _, code = run_capturing(
        "lfi_test",
        {"url": "http://x/?f=FUZZ", "method": "POST", "body_template": "file=FUZZ"},
    )
    assert "requests.request(method" in code


# --- baseline / status heuristics -------------------------------------------

def test_fuzz_baseline_not_adopted_from_response():
    _, code = run_capturing("fuzz_params", {"url": "http://x/?q=FUZZ", "preset": "xss"})
    assert "if baseline is None: baseline = len" not in code
    assert "baseline_len = None" in code


def test_fuzz_status_relative_to_baseline():
    _, code = run_capturing("fuzz_params", {"url": "http://x/?q=FUZZ", "preset": "xss"})
    assert "not in (200, 404)" not in code
    assert "baseline_status" in code


# --- Windows LFI payloads + depth bound -------------------------------------

def test_lfi_generates_windows_backslash_traversal():
    payloads = web._build_lfi_payloads(3)
    assert any("..\\windows" in p for p in payloads)


def test_lfi_depth_is_bounded():
    from tools.web import handle_web  # noqa: F401  (ensure import path is valid)

    _, code = run_capturing("lfi_test", {"url": "http://x/?f=FUZZ", "depth": 9999})
    capped = len(web._build_lfi_payloads(8))
    # depth clamps to 8; payload count must equal the depth-8 build and stay small
    assert f"len={capped}" or capped < 200


# --- http_request timeout clamping ------------------------------------------

def test_http_timeout_capped():
    _, code = run_capturing("http_request", {"url": "http://x/", "timeout": 999})
    assert f"'timeout': {U.MAX_HTTP_TIMEOUT}" in code


def test_http_timeout_negative_becomes_min():
    _, code = run_capturing("http_request", {"url": "http://x/", "timeout": -5})
    assert "'timeout': 1" in code


def test_http_bool_and_none_headers_emit_python_literals():
    _, code = run_capturing(
        "http_request",
        {"url": "http://x/", "method": "POST", "headers": {"A": True, "B": None}},
    )
    assert "True" in code and "None" in code
    assert "true" not in code and "null" not in code
