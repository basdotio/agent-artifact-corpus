"""Per-tool PCA enforcement middleware for FastMCP.

A ``tools/call`` is the #1 place an agent's authority turns into a side effect, so this middleware
verifies a proof-carrying action *before* the tool runs and fails closed otherwise:

* no proof, or an undecodable one                      -> reject (the tool never runs)
* a proof that does not verify under the core verifier -> reject (bad signature / chain / validity /
  wrong audience / unknown grant / replay counter)
* a valid proof whose authorized action does not satisfy the tool's required capability -> reject
* an optional ``policy`` hook that returns a reason    -> reject
* otherwise                                            -> run the real tool

``audience`` is this server's RFC 8707 resource identifier: a proof minted for another audience is
rejected by the core verifier's ``audience`` check, so a token for a *different* MCP server cannot be
replayed here.

FastMCP is imported optionally/duck-typed, so the package imports and the pure decision logic
(:meth:`PCAMiddleware.decide`) are testable with FastMCP absent.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Awaitable, Callable, Optional, Tuple

from atlas_pca.pca import Verdict

from .capability import Capability, ToolCapability, capability_satisfies, parse_capability, resolve_required
from .extract import PCA_META_KEY, extract_pcactn
from .registry import DEFAULT_REGISTRY, CapabilityRegistry
from .verifier import GrantResolver, Verifier

# A policy hook: given the verified proof, the tool name and the allowing verdict, return a rejection
# reason (deny) or ``None`` (allow). Runs only after the proof and capability already passed.
PolicyHook = Callable[[dict, str, Verdict], Optional[str]]


@dataclass
class PCADecision:
    """The outcome of enforcing one ``tools/call``. ``allow`` is the field a caller branches on."""

    allow: bool
    tool: str
    reason: Optional[str] = None
    required: Optional[Capability] = None
    verdict: Optional[Verdict] = None
    pcactn: Optional[dict] = None


# PCAAccessDenied subclasses FastMCP's ``ToolError`` when FastMCP is installed, so a rejection surfaces
# to the client as a normal MCP tool error (whose message FastMCP forwards); with FastMCP absent it is a
# plain exception. Static checkers always see the ``Exception`` base (via TYPE_CHECKING), so this stays
# statically typed with no suppression and no class redefinition — the base is chosen once, at import.
if TYPE_CHECKING:
    _DeniedBase = Exception
else:
    try:  # pragma: no cover - exercised only when fastmcp is installed
        from fastmcp.exceptions import ToolError as _DeniedBase
    except Exception:  # pragma: no cover - the dependency-free path
        _DeniedBase = Exception


class PCAAccessDenied(_DeniedBase):
    """Raised to reject a ``tools/call``. Carries the denying :class:`PCADecision`."""

    def __init__(self, decision: "PCADecision") -> None:
        self.decision = decision
        super().__init__(decision.reason or "proof-carrying authority required")


# Base the middleware on FastMCP's Middleware when present; otherwise a plain object with the same hook.
# Static checkers see the ``object`` base (via TYPE_CHECKING), so no type suppression is needed.
if TYPE_CHECKING:
    _MiddlewareBase = object
else:
    try:  # pragma: no cover - import shape depends on whether fastmcp is installed
        from fastmcp.server.middleware import Middleware as _MiddlewareBase
    except Exception:  # pragma: no cover
        _MiddlewareBase = object


CallNext = Callable[[object], Awaitable[object]]


def _request_meta(context: object) -> object:
    """The request ``_meta`` as FastMCP surfaces it on the call context.

    In FastMCP 4.x a per-call ``_meta`` sent by the client is **not** mirrored onto
    ``message.meta``; it lives on ``context.fastmcp_context.request_context.meta`` (a dict that also
    holds protocol keys we ignore). We read that first, then fall back to ``message.meta`` / ``_meta``.
    """
    fastmcp_context = getattr(context, "fastmcp_context", None)
    request_context = getattr(fastmcp_context, "request_context", None)
    return getattr(request_context, "meta", None)


def _read_call(context: object) -> Tuple[str, object, object]:
    """Extract ``(tool_name, meta, arguments)`` from a FastMCP middleware context, defensively.

    Different FastMCP versions expose the call params as ``context.message`` (a
    ``CallToolRequestParams``) possibly wrapped one level deeper in ``.params``; the request ``_meta``
    may be on the call context (see :func:`_request_meta`) or on the message as ``.meta`` / ``._meta``.
    Unknown shapes yield an empty name, which fails closed.
    """
    message = getattr(context, "message", context)
    message = getattr(message, "params", message)
    name = getattr(message, "name", "")
    if not isinstance(name, str):
        name = ""
    arguments = getattr(message, "arguments", None)
    meta = _request_meta(context)
    if meta is None:
        meta = getattr(message, "meta", None)
    if meta is None:
        meta = getattr(message, "_meta", None)
    return name, meta, arguments


class PCAMiddleware(_MiddlewareBase):
    """FastMCP middleware enforcing a PCActn on every ``tools/call``.

    Construct it with :func:`pca_guard`. The pure decision is in :meth:`decide`; :meth:`on_call_tool`
    is the FastMCP hook that raises :class:`PCAAccessDenied` on a deny and otherwise proceeds.
    """

    def __init__(
        self,
        *,
        audience: str,
        verifier: Verifier,
        policy: Optional[PolicyHook] = None,
        tool_capability: Optional[ToolCapability] = None,
        registry: CapabilityRegistry = DEFAULT_REGISTRY,
        now: Optional[int] = None,
        meta_key: str = PCA_META_KEY,
    ) -> None:
        if _MiddlewareBase is not object:
            super().__init__()
        if not audience:
            raise ValueError("pca_guard requires a non-empty audience (this server's RFC 8707 resource)")
        self.audience = audience
        self.verifier = verifier
        self.policy = policy
        self.tool_capability = tool_capability
        self.registry = registry
        self.now = now
        self.meta_key = meta_key

    def _required_for(self, tool_name: str) -> Optional[Capability]:
        """Required capability for a tool: an explicit ``tool_capability`` rule wins, else the registry."""
        explicit = resolve_required(self.tool_capability, tool_name)
        if explicit is not None:
            return explicit
        return self.registry.get(tool_name)

    def decide(self, tool_name: str, *, meta: object = None, arguments: object = None) -> PCADecision:
        """Decide one ``tools/call`` without any FastMCP types. Pure and fail-closed."""
        pcactn, err = extract_pcactn(meta, arguments, meta_key=self.meta_key)
        if pcactn is None:
            reason = "no PCActn presented" if err == "absent" else "PCActn could not be decoded"
            return PCADecision(allow=False, tool=tool_name, reason=reason)

        verdict = self.verifier.verify(pcactn, audience=self.audience, now=self.now)
        if not verdict.allow:
            return PCADecision(
                allow=False, tool=tool_name, reason=verdict.reason or "proof did not verify",
                verdict=verdict, pcactn=pcactn,
            )

        required = self._required_for(tool_name)
        if required is not None:
            action = pcactn.get("action")
            verb = action.get("verb") if isinstance(action, dict) else None
            resource = action.get("resource") if isinstance(action, dict) else None
            if not (isinstance(verb, str) and isinstance(resource, str)
                    and capability_satisfies(required, verb, resource)):
                authorized = "%s:%s" % (verb, resource)
                return PCADecision(
                    allow=False, tool=tool_name, required=required, verdict=verdict, pcactn=pcactn,
                    reason="insufficient_capability: tool %r requires %r, proof authorizes %r"
                    % (tool_name, str(required), authorized),
                )

        if self.policy is not None:
            policy_reason = self.policy(pcactn, tool_name, verdict)
            if policy_reason:
                return PCADecision(
                    allow=False, tool=tool_name, required=required, verdict=verdict, pcactn=pcactn,
                    reason="policy_denied: %s" % policy_reason,
                )

        return PCADecision(allow=True, tool=tool_name, required=required, verdict=verdict, pcactn=pcactn)

    async def on_call_tool(self, context: object, call_next: CallNext) -> object:
        """FastMCP hook: verify before the tool runs; raise on deny, else proceed."""
        name, meta, arguments = _read_call(context)
        decision = self.decide(name, meta=meta, arguments=arguments)
        if not decision.allow:
            raise PCAAccessDenied(decision)
        # A proof carried in the tool arguments is not part of the tool's own schema: strip it so the
        # (schema-validating) tool never sees an undeclared argument.
        if isinstance(arguments, dict):
            arguments.pop(self.meta_key, None)
        return await call_next(context)


def pca_guard(
    *,
    audience: str,
    policy: Optional[PolicyHook] = None,
    tool_capability: Optional[ToolCapability] = None,
    verifier: Optional[Verifier] = None,
    resolve_grant: Optional[GrantResolver] = None,
    registry: CapabilityRegistry = DEFAULT_REGISTRY,
    now: Optional[int] = None,
    meta_key: str = PCA_META_KEY,
) -> PCAMiddleware:
    """Build the FastMCP middleware that enforces a PCActn on every ``tools/call``.

    ``audience``        — this server's RFC 8707 resource identifier; a proof minted for another
                          audience is rejected (resource-server-correct).
    ``tool_capability`` — a ``{tool_name: "verb:resource"}`` mapping or a ``tool_name -> spec`` callable.
                          A tool with no entry needs only a valid proof; otherwise the proof's action
                          must satisfy the capability. The :func:`pca_tool` decorator feeds the shared
                          registry, which is consulted when no explicit rule matches.
    ``verifier``        — a :class:`~atlas_pca_fastmcp.verifier.Verifier`. Omit it and pass
                          ``resolve_grant`` to use the default :class:`CoreVerifier`.
    ``policy``          — optional extra check run after the proof and capability pass.
    ``now``             — fixed validity clock (epoch ms); handy for tests.

    Wire it in one line::

        mcp.add_middleware(pca_guard(audience="mcp://orders", resolve_grant=my_resolver,
                                     tool_capability={"transfer_funds": "write:db/orders"}))
    """
    if verifier is None:
        if resolve_grant is None:
            raise ValueError("pca_guard needs a verifier or a resolve_grant callback")
        from .verifier import CoreVerifier
        verifier = CoreVerifier(resolve_grant=resolve_grant, now=now)
    elif resolve_grant is not None:
        raise ValueError("pass either verifier or resolve_grant, not both")
    return PCAMiddleware(
        audience=audience, verifier=verifier, policy=policy, tool_capability=tool_capability,
        registry=registry, now=now, meta_key=meta_key,
    )


F = Callable[..., object]


def pca_tool(
    *,
    require: str,
    name: Optional[str] = None,
    registry: CapabilityRegistry = DEFAULT_REGISTRY,
) -> Callable[[F], F]:
    """Declare the capability one tool's call requires, e.g. ``@pca_tool(require="write:db/orders")``.

    Stack it with FastMCP's ``@mcp.tool`` (either order); it records the requirement in the shared
    registry under the tool name (``name`` if given, else the function's ``__name__``) and returns the
    function unchanged, also tagging it ``func.__pca_require__`` for introspection::

        @mcp.tool
        @pca_tool(require="write:db/orders")
        def transfer_funds(amount: int) -> str:
            ...
    """
    parse_capability(require)  # fail fast at decoration time on a malformed spec

    def decorator(func: F) -> F:
        tool_name = name if name is not None else getattr(func, "__name__", None)
        if not tool_name:
            raise ValueError("pca_tool could not determine a tool name; pass name=...")
        registry.register(tool_name, require)
        setattr(func, "__pca_require__", require)
        return func

    return decorator
