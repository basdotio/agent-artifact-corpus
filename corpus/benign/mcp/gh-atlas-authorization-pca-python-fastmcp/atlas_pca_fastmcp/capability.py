"""Tool-capability model for PCA enforcement on an MCP server.

A capability is a ``"verb:resource"`` pair. A tool declares the capability its call *requires*; a
PCActn's signed ``action`` (``action.verb`` / ``action.resource``) says what the proof *authorizes*.
Enforcement allows the call only when the authorized action satisfies the required capability.

Matching is deliberately simple and fail-closed:

* ``verb`` must match exactly, unless the required verb is ``"*"``.
* ``resource`` must match exactly, unless the required resource is ``"*"`` (any resource) or ends in
  ``"/*"`` (a subtree: ``"db/*"`` authorizes ``"db/orders"`` and ``"db/orders/line/1"`` but not ``"db"``).

Nothing here touches crypto; it runs only after :mod:`atlas_pca` has verified the proof.
"""
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Union


@dataclass(frozen=True)
class Capability:
    """A parsed ``verb:resource`` requirement."""

    verb: str
    resource: str

    def __str__(self) -> str:
        return "%s:%s" % (self.verb, self.resource)


def parse_capability(spec: Union[str, "Capability"]) -> Capability:
    """Parse ``"verb:resource"`` into a :class:`Capability`.

    The first ``":"`` separates the verb from the resource, so a resource may itself contain ``":"``.
    Both halves must be non-empty. Raises :class:`ValueError` on a malformed spec.
    """
    if isinstance(spec, Capability):
        return spec
    if not isinstance(spec, str) or ":" not in spec:
        raise ValueError("capability must be a 'verb:resource' string, got %r" % (spec,))
    verb, _, resource = spec.partition(":")
    if not verb or not resource:
        raise ValueError("capability 'verb' and 'resource' must both be non-empty, got %r" % (spec,))
    return Capability(verb=verb, resource=resource)


def _resource_satisfies(required: str, authorized: str) -> bool:
    if required == "*" or required == authorized:
        return True
    if required.endswith("/*"):
        prefix = required[:-1]  # keep the trailing slash: "db/*" -> "db/"
        return authorized.startswith(prefix) and len(authorized) > len(prefix)
    return False


def capability_satisfies(required: Capability, authorized_verb: str, authorized_resource: str) -> bool:
    """True iff an action over ``authorized_verb``/``authorized_resource`` satisfies ``required``."""
    if required.verb != "*" and required.verb != authorized_verb:
        return False
    return _resource_satisfies(required.resource, authorized_resource)


# A rule resolves a tool name to the capability it requires (or ``None`` for "any valid proof").
ToolCapability = Union[Mapping[str, str], Callable[[str], Optional[Union[str, Capability]]]]


def resolve_required(rule: Optional[ToolCapability], tool_name: str) -> Optional[Capability]:
    """Resolve the required capability for ``tool_name`` from a mapping or a callable rule."""
    if rule is None:
        return None
    raw: Optional[Union[str, Capability]]
    if callable(rule):
        raw = rule(tool_name)
    else:
        raw = rule.get(tool_name)
    return None if raw is None else parse_capability(raw)
