"""Tests for FastMCP per-tool PCA enforcement.

The valid PCActn fixture is the known-good ``valid-in-plan-action`` vector from the shared conformance
set (same source as ``sdks/python-pca/test_server.py``), so the signed bytes are real — no crypto is
minted here, no network. The vector's action is ``verb="write"`` over ``resource="db/orders"``, i.e. it
authorizes the capability ``write:db/orders``.
"""
import asyncio
import json
import os

import pytest

from atlas_pca.pca import b64u, canonical_bytes_strict
from atlas_pca_fastmcp import (
    CapabilityRegistry,
    PCAAccessDenied,
    capability_satisfies,
    parse_capability,
    pca_guard,
    pca_tool,
)

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "conformance")


def _valid_vector():
    with open(os.path.join(DIR, "vectors.json"), encoding="utf-8") as f:
        doc = json.load(f)
    return next(x for x in doc["vectors"] if x["name"] == "valid-in-plan-action")


VEC = _valid_vector()
PCACTN = VEC["pcactn"]
GRANT = VEC["grant"]
NOW = VEC["context"]["now"]
AUD = VEC["context"]["aud"]
# The capability this proof authorizes: action.verb:action.resource == "write:db/orders".
CAP = "%s:%s" % (PCACTN["action"]["verb"], PCACTN["action"]["resource"])


def _resolver(grant_ref):
    return GRANT if grant_ref == PCACTN["grant_ref"] else None


def _header_value(pcactn):
    return b64u(canonical_bytes_strict(pcactn))


def _meta(pcactn=PCACTN):
    return {"PCA-Action": _header_value(pcactn)}


def _guard(*, audience=AUD, tool_capability=None, registry=None, policy=None):
    kwargs = dict(audience=audience, resolve_grant=_resolver, now=NOW,
                  tool_capability=tool_capability, policy=policy)
    if registry is not None:
        kwargs["registry"] = registry
    return pca_guard(**kwargs)


# ---- capability matching (pure) ------------------------------------------------------

def test_capability_exact_and_wildcards():
    assert capability_satisfies(parse_capability("write:db/orders"), "write", "db/orders")
    assert capability_satisfies(parse_capability("write:db/*"), "write", "db/orders")
    assert capability_satisfies(parse_capability("write:db/*"), "write", "db/orders/line/1")
    assert capability_satisfies(parse_capability("*:db/orders"), "write", "db/orders")
    assert not capability_satisfies(parse_capability("write:db/*"), "write", "db")  # subtree, not the prefix itself
    assert not capability_satisfies(parse_capability("delete:db/orders"), "write", "db/orders")  # wrong verb
    assert not capability_satisfies(parse_capability("write:db/secrets"), "write", "db/orders")  # wrong resource


@pytest.mark.parametrize("bad", ["noseparator", ":resource", "verb:", ""])
def test_parse_capability_rejects_malformed(bad):
    with pytest.raises(ValueError):
        parse_capability(bad)


# ---- decide(): the pure decision ----------------------------------------------------

def test_valid_proof_allows_via_meta():
    d = _guard(tool_capability={"transfer": CAP}).decide("transfer", meta=_meta())
    assert d.allow is True
    assert d.verdict is not None and d.verdict.allow is True
    assert str(d.required) == CAP
    assert d.pcactn["aud"] == AUD


def test_valid_proof_allows_via_arguments_string():
    # fallback channel: base64url proof in the tool arguments
    d = _guard().decide("transfer", arguments={"PCA-Action": _header_value(PCACTN)})
    assert d.allow is True


def test_valid_proof_allows_via_arguments_inline_object():
    # fallback channel: the PCActn object inline in arguments
    d = _guard().decide("transfer", arguments={"PCA-Action": PCACTN})
    assert d.allow is True


def test_tool_without_capability_requirement_allows_any_valid_proof():
    d = _guard().decide("read_only_tool", meta=_meta())
    assert d.allow is True
    assert d.required is None


def test_missing_proof_is_rejected():
    d = _guard().decide("transfer", meta={}, arguments=None)
    assert d.allow is False
    assert d.reason == "no PCActn presented"
    assert d.verdict is None  # never got as far as verifying


def test_undecodable_proof_is_rejected():
    d = _guard().decide("transfer", meta={"PCA-Action": "!!!not-base64url!!!"})
    assert d.allow is False
    assert d.reason == "PCActn could not be decoded"


def test_wrong_audience_is_rejected():
    d = _guard(audience="mcp://some-other-server").decide("transfer", meta=_meta())
    assert d.allow is False
    assert d.verdict is not None and d.verdict.allow is False
    assert d.verdict.checks["audience"] is False


def test_unknown_grant_is_rejected():
    guard = pca_guard(audience=AUD, resolve_grant=lambda ref: None, now=NOW)
    d = guard.decide("transfer", meta=_meta())
    assert d.allow is False
    assert d.reason == "unknown_grant"


def test_tampered_proof_fails_signature():
    tampered = dict(PCACTN)
    tampered["counter"] = PCACTN["counter"] + 1  # changes the signed body -> leaf signature must fail
    d = _guard().decide("transfer", meta=_meta(tampered))
    assert d.allow is False
    assert d.verdict is not None and d.verdict.checks["leaf_signature"] is False


def test_insufficient_capability_is_rejected():
    # proof authorizes write:db/orders; the tool demands a stronger/different capability
    d = _guard(tool_capability={"delete_orders": "delete:db/orders"}).decide("delete_orders", meta=_meta())
    assert d.allow is False
    assert d.required is not None and str(d.required) == "delete:db/orders"
    assert d.reason.startswith("insufficient_capability")
    assert d.verdict is not None and d.verdict.allow is True  # the proof was valid; only the capability failed


def test_policy_hook_can_deny_after_proof_passes():
    def deny_everything(pcactn, tool, verdict):
        return "out of hours"

    d = _guard(policy=deny_everything).decide("transfer", meta=_meta())
    assert d.allow is False
    assert d.reason == "policy_denied: out of hours"


# ---- the @pca_tool decorator form ---------------------------------------------------

def test_decorator_registers_requirement_and_guard_enforces_it():
    reg = CapabilityRegistry()

    @pca_tool(require=CAP, registry=reg)
    def transfer(amount):
        return amount

    # the decorator leaves the function callable and tags it
    assert transfer(5) == 5
    assert transfer.__pca_require__ == CAP

    guard = _guard(registry=reg)
    assert guard.decide("transfer", meta=_meta()).allow is True

    @pca_tool(require="delete:db/orders", registry=reg)
    def wipe():
        return None

    assert guard.decide("wipe", meta=_meta()).allow is False  # insufficient capability from the registry


def test_decorator_explicit_name():
    reg = CapabilityRegistry()

    @pca_tool(require=CAP, name="renamed_tool", registry=reg)
    def fn():
        return None

    assert reg.get("renamed_tool") is not None
    assert _guard(registry=reg).decide("renamed_tool", meta=_meta()).allow is True


# ---- on_call_tool(): the FastMCP hook, exercised with a fake context (no fastmcp needed) ----

class _FakeMessage:
    def __init__(self, name, meta=None, arguments=None):
        self.name = name
        self.meta = meta
        self.arguments = arguments


class _FakeContext:
    def __init__(self, message):
        self.message = message


def _run_tool(guard, message):
    """Drive on_call_tool with a recording call_next; return (ran, result_or_exc)."""
    state = {"ran": False}

    async def call_next(ctx):
        state["ran"] = True
        return "tool-result"

    async def go():
        return await guard.on_call_tool(_FakeContext(message), call_next)

    try:
        result = asyncio.run(go())
        return state["ran"], result
    except PCAAccessDenied as exc:
        return state["ran"], exc


def test_on_call_tool_runs_tool_on_valid_proof():
    guard = _guard(tool_capability={"transfer": CAP})
    ran, result = _run_tool(guard, _FakeMessage("transfer", meta=_meta()))
    assert ran is True
    assert result == "tool-result"


def test_on_call_tool_rejects_and_does_not_run_tool():
    cases = [
        _FakeMessage("transfer", meta={}),                                   # missing
        _FakeMessage("transfer", meta={"PCA-Action": "!!!bad!!!"}),          # undecodable
    ]
    for msg in cases:
        ran, outcome = _run_tool(_guard(), msg)
        assert ran is False
        assert isinstance(outcome, PCAAccessDenied)
        assert outcome.decision.allow is False


def test_on_call_tool_rejects_wrong_audience_without_running():
    guard = _guard(audience="mcp://other")
    ran, outcome = _run_tool(guard, _FakeMessage("transfer", meta=_meta()))
    assert ran is False
    assert isinstance(outcome, PCAAccessDenied)


def test_on_call_tool_rejects_insufficient_capability_without_running():
    guard = _guard(tool_capability={"transfer": "delete:db/orders"})
    ran, outcome = _run_tool(guard, _FakeMessage("transfer", meta=_meta()))
    assert ran is False
    assert isinstance(outcome, PCAAccessDenied)
    assert outcome.decision.reason.startswith("insufficient_capability")


# ---- real FastMCP integration (skipped unless installed) ----------------------------

def test_fastmcp_server_integration():
    pytest.importorskip("fastmcp")
    import fastmcp
    from fastmcp import Client, FastMCP

    mcp = FastMCP("orders-server")
    mcp.add_middleware(_guard(tool_capability={"transfer": CAP}))

    @mcp.tool
    def transfer(amount: int) -> str:
        return "transferred %d" % amount

    async def scenario():
        async with Client(mcp) as client:
            ok = await client.call_tool("transfer", {"amount": 10}, meta=_meta())
            assert "transferred 10" in str(ok)
            with pytest.raises(Exception):
                await client.call_tool("transfer", {"amount": 10})  # no proof -> rejected

    asyncio.run(scenario())
    _ = fastmcp  # keep the import referenced
