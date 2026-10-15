"""test_registry.py — the registry you edit stays valid, and the shipped tools work.

These run against the REAL _registry.py / _capabilities.py, so once you add
your own tools they guard those too: a schema typo, a tool missing from every
capability group, or a run() that reads an argument its schema never declares
(which the gateway would then reject on every real call) fails here first.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gateway_server as gw  # noqa: E402
from _registry import _TOOLS, _validate_schemas  # noqa: E402


def test_schemas_are_valid():
    assert _validate_schemas() == []


def test_every_tool_is_in_exactly_one_capability():
    assert gw._validate_capabilities() == []


def test_every_tool_module_imports_and_has_run():
    import importlib
    for name, spec in _TOOLS.items():
        mod = importlib.import_module(spec["module"])
        assert callable(getattr(mod, "run", None)), f"{name}: {spec['module']} has no run()"


def test_every_argument_run_reads_is_declared():
    """Static scan: keys run() reads via args.get("x") / args["x"] must be in
    the schema (or tolerated), or the gateway rejects real calls using them."""
    missing = {}
    for name, spec in _TOOLS.items():
        if spec["input_schema"].get("additionalProperties") is True:
            continue
        f = ROOT / (spec["module"].replace(".", "/") + ".py")
        src = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"def run\(\s*(\w+)", src)
        if not m:
            continue
        names = {m.group(1), "args", "arguments"}
        used = set()
        for n in names:
            for mm in re.finditer(
                    rf'''\b{n}\.get\(\s*["'](\w+)["']|\b{n}\[\s*["'](\w+)["']\s*\]'''
                    rf'''|\b{n}\.pop\(\s*["'](\w+)["']|["'](\w+)["']\s+in\s+{n}\b''', src):
                used.add(next(g for g in mm.groups() if g))
        declared = set(spec["input_schema"].get("properties") or {})
        allowed = declared | gw._GATEWAY_ARGS | gw._UNDECLARED_ARGS_TOLERATED.get(name, set())
        if used - allowed:
            missing[name] = sorted(used - allowed)
    assert not missing, f"declare these in _registry.py (or tolerate in gateway_server): {missing}"


def _run(name, args):
    out, _ = gw._run_tool_raw(name, args)
    return json.loads(out)


class TestShippedTools:
    def test_json_query_through_the_gateway(self):
        r = _run("json_query", {"data": '{"items": [{"n": 1}, {"n": 2}]}', "query": "items[*].n"})
        assert r["success"] is True and r["result"] == [1, 2]

    def test_json_query_bad_expression_is_enriched(self):
        r = _run("json_query", {"data": "{}", "query": "$.a"})
        assert r["error_code"] == "InvalidQuery"
        assert "JMESPath, not JSONPath" in r["hint"]

    def test_git_status_on_a_fresh_repo(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "new.txt").write_text("x")
        r = _run("git_status", {"repo": str(repo)})
        assert r["success"] is True
        assert r["untracked"] == ["new.txt"] and r["clean"] is False

    def test_every_call_is_audited(self):
        _run("json_query", {"data": "[1]", "query": "[0]"})
        tail = _run("audit_log", {"mode": "tail", "count": 5})
        assert any(rec["tool"] == "json_query" for rec in tail["records"])
