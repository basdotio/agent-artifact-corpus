"""End-to-end tests against the REAL FastMCP (skipped when it is not installed).

A real ``FastMCP`` server with the PCA middleware is called through a real in-memory ``Client``. Run with
``make test-real`` (or ``sdks/scripts/test-adapters-real.sh``). Proofs are the shared conformance vectors.
"""
import asyncio
import copy
import json
import os
from typing import Any, Awaitable, Callable, List

import pytest

pytest.importorskip("fastmcp")

from fastmcp import Client, FastMCP  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

from atlas_pca.pca import b64u, canonical_bytes_strict  # noqa: E402
from atlas_pca_fastmcp import CapabilityRegistry, pca_guard, pca_tool  # noqa: E402

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "conformance")
with open(os.path.join(_DIR, "vectors.json"), encoding="utf-8") as _f:
    _VEC = next(v for v in json.load(_f)["vectors"] if v["name"] == "valid-in-plan-action")
PCACTN = _VEC["pcactn"]
GRANT = _VEC["grant"]
NOW = _VEC["context"]["now"]
AUD = _VEC["context"]["aud"]
CAP = "%s:%s" % (PCACTN["action"]["verb"], PCACTN["action"]["resource"])
RAN: List[int] = []


def _resolver(ref: Any) -> Any:
    return GRANT if ref == PCACTN["grant_ref"] else None


def _wire(p: Any) -> str:
    return b64u(canonical_bytes_strict(p))


def _tampered() -> Any:
    bad = copy.deepcopy(PCACTN)
    bad["sig"] = ("B" if bad["sig"][0] != "B" else "C") + bad["sig"][1:]
    return bad


def _server(**guard_kw: Any) -> FastMCP:
    opts = dict(audience=AUD, resolve_grant=_resolver, now=NOW)
    opts.update(guard_kw)
    mcp = FastMCP("orders")
    mcp.add_middleware(pca_guard(**opts))

    @mcp.tool
    def transfer(amount: int) -> str:
        RAN.append(amount)
        return "transferred %d" % amount

    return mcp


def _call(mcp: FastMCP, *, meta: Any = None, args: Any = None) -> Any:
    async def go() -> Any:
        async with Client(mcp) as client:
            return await client.call_tool("transfer", args or {"amount": 10}, meta=meta)

    return asyncio.run(go())


@pytest.fixture(autouse=True)
def _clear() -> None:
    RAN.clear()


def test_allows_with_proof_in_meta() -> None:
    res = _call(_server(tool_capability={"transfer": CAP}), meta={"PCA-Action": _wire(PCACTN)})
    assert "transferred 10" in str(res)
    assert RAN == [10]


def test_allows_with_proof_in_arguments_fallback_channel() -> None:
    mcp = FastMCP("orders")
    mcp.add_middleware(pca_guard(audience=AUD, resolve_grant=_resolver, now=NOW, tool_capability={"transfer": CAP}))

    @mcp.tool
    def transfer(amount: int) -> str:
        RAN.append(amount)
        return "ok"

    async def go() -> Any:
        async with Client(mcp) as client:
            return await client.call_tool("transfer", {"amount": 3, "PCA-Action": _wire(PCACTN)})

    asyncio.run(go())  # the middleware strips the carried proof, so the tool's strict schema accepts the call
    assert RAN == [3]


@pytest.mark.parametrize("meta,msg", [
    (None, "no PCActn presented"),
    ({"PCA-Action": "!!not-base64url!!"}, "could not be decoded"),
])
def test_denies_absent_or_undecodable_proof(meta: Any, msg: str) -> None:
    with pytest.raises(ToolError) as ei:
        _call(_server(), meta=meta)
    assert msg in str(ei.value)
    assert RAN == []


def test_denies_tampered_proof() -> None:
    with pytest.raises(ToolError) as ei:
        _call(_server(), meta={"PCA-Action": _wire(_tampered())})
    assert str(ei.value)
    assert RAN == []


def test_denies_wrong_audience() -> None:
    with pytest.raises(ToolError) as ei:
        _call(_server(audience="mcp://other"), meta={"PCA-Action": _wire(PCACTN)})
    assert "audience" in str(ei.value).lower() or "aud" in str(ei.value).lower()
    assert RAN == []


def test_denies_insufficient_capability() -> None:
    with pytest.raises(ToolError) as ei:
        _call(_server(tool_capability={"transfer": "delete:db/orders"}), meta={"PCA-Action": _wire(PCACTN)})
    assert "insufficient_capability" in str(ei.value)
    assert RAN == []


def test_pca_tool_decorator_registry_with_real_mcp_tool() -> None:
    reg = CapabilityRegistry()
    mcp = FastMCP("orders")
    mcp.add_middleware(pca_guard(audience=AUD, resolve_grant=_resolver, now=NOW, registry=reg))

    @mcp.tool
    @pca_tool(require="delete:db/orders", registry=reg)
    def transfer(amount: int) -> str:
        RAN.append(amount)
        return "no"

    async def go() -> Any:
        async with Client(mcp) as client:
            return await client.call_tool("transfer", {"amount": 1}, meta={"PCA-Action": _wire(PCACTN)})

    with pytest.raises(ToolError) as ei:
        asyncio.run(go())
    assert "insufficient_capability" in str(ei.value)
    assert RAN == []


def test_policy_hook_denies_after_valid_proof() -> None:
    with pytest.raises(ToolError) as ei:
        _call(_server(policy=lambda p, t, v: "over limit"), meta={"PCA-Action": _wire(PCACTN)})
    assert "policy_denied: over limit" in str(ei.value)
    assert RAN == []
