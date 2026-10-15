"""Server profiles and annotation-driven tool visibility.

A profile is one of two kinds; both coexist and both are selected with
``--profile`` / ``TAXCODE_MCP_PROFILE``:

* **Domain-mount profile** — ``domains`` names the domain sub-servers to mount.
  Use it when a job maps cleanly onto whole domains (``full``, ``system``, ``items``).
* **Allowlist profile** — ``tools`` is an explicit set of client-visible tool names
  applied over the full mounted catalog. Use it for job-shaped profiles that cut
  across domains (``intake``). Filtering is tools-only: prompts and resources stay.

``readonly=True`` keeps only tools whose MCP ``readOnlyHint`` annotation is ``True``.
The annotation is the single source of truth for read-only classification; a missing
annotation or ``readOnlyHint`` other than ``True`` counts as a write (fail closed).
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from fastmcp.server.transforms import GetToolNext, Transform
from fastmcp.tools import Tool
from fastmcp.utilities.versions import VersionSpec
from mcp.types import ToolAnnotations

ALL_DOMAINS: tuple[str, ...] = ("system", "statutes", "compliance")


@dataclass(frozen=True)
class Profile:
    """A named server profile: domain mounts or a tool-name allowlist."""

    name: str
    job: str
    domains: tuple[str, ...] = ALL_DOMAINS
    tools: frozenset[str] | None = None
    readonly: bool = False

    @property
    def is_allowlist(self) -> bool:
        """True when the profile is an explicit tool-name allowlist."""
        return self.tools is not None


PROFILES: dict[str, Profile] = {
    profile.name: profile
    for profile in (
        # Domain-mount profiles
        Profile(
            name="full",
            job="Complete catalog: statutory search, publications, and cross-border calculators.",
        ),
        Profile(name="system", job="System diagnostics and capabilities.", domains=("system",)),
        Profile(
            name="statutes",
            job="Statutory research, lookup, search, and publications.",
            domains=("statutes",),
        ),
        Profile(
            name="compliance",
            job="Cross-border residency evaluation and capital gains sourcing calculators.",
            domains=("compliance",),
        ),
        Profile(
            name="readonly",
            job="Inspect and calculate without mutations: every tool annotated readOnlyHint=True.",
            readonly=True,
        ),
        # Allowlist (job-shaped) profiles
        Profile(
            name="researcher",
            job="Statutory research: health checks, exact statutory lookups, search, circulars.",
            tools=frozenset(
                {
                    "system_get_health_status",
                    "statutes_lookup_statute",
                    "statutes_search_tax_code",
                    "statutes_list_publications",
                }
            ),
        ),
        Profile(
            name="advisor",
            job=(
                "Cross-border tax advisory: statutes, residency testing, "
                "and built-in gain sourcing."
            ),
            tools=frozenset(
                {
                    "system_get_health_status",
                    "statutes_lookup_statute",
                    "compliance_evaluate_pr_bona_fide_residency",
                    "compliance_calculate_built_in_gain_sourcing",
                    "compliance_evaluate_georgia_residency",
                    "compliance_evaluate_state_residency",
                }
            ),
        ),
    )
}

# Tools in no job (allowlist) profile. In pure read-only research mode, all tools are mapped.
FULL_ONLY_TOOLS: frozenset[str] = frozenset()

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def get_profile(name: str) -> Profile:
    """Return the named profile or raise ``ValueError`` listing valid profiles."""
    key = name.lower()
    if key not in PROFILES:
        valid = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown profile {name!r}; valid profiles: {valid}.")
    return PROFILES[key]


def validate_allowlist(profile: Profile, catalog: Collection[str]) -> frozenset[str]:
    """Return the profile allowlist, raising ``ValueError`` on any name not in ``catalog``."""
    allowlist = profile.tools or frozenset()
    unknown = sorted(allowlist - set(catalog))
    if unknown:
        raise ValueError(
            f"Profile {profile.name!r} allowlists tools not in the full catalog: "
            f"{', '.join(unknown)}."
        )
    return allowlist


def is_read_only_tool(tool: Tool | None) -> bool:
    """Return True only for a tool annotated ``readOnlyHint=True`` (fail closed)."""
    if tool is None or tool.annotations is None:
        return False
    return tool.annotations.read_only_hint is True


class ReadOnlyToolFilter(Transform):
    """Keep only tools annotated ``readOnlyHint=True``; other component types pass through."""

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [tool for tool in tools if is_read_only_tool(tool)]

    async def get_tool(
        self, name: str, call_next: GetToolNext, *, version: VersionSpec | None = None
    ) -> Tool | None:
        tool = await call_next(name, version=version)
        return tool if is_read_only_tool(tool) else None


class ReadOnlyAnnotations(Transform):
    """Annotate named synthetic discovery tools as ``readOnlyHint=True``.

    FastMCP's synthetic discovery tools (``search_tools``; Code Mode ``search`` /
    ``get_schema``) ship without annotations. They only read the catalog, so the
    template marks them read-only to keep discovery usable under the readonly gate.
    ``call_tool`` / ``execute`` are deliberately not annotated: the gate classifies
    ``call_tool`` by the tool it proxies, and ``execute`` stays refused under readonly.
    """

    def __init__(self, names: Collection[str]) -> None:
        self.names = frozenset(names)

    def _annotate(self, tool: Tool) -> Tool:
        if tool.name not in self.names:
            return tool
        return tool.model_copy(update={"annotations": READ_ONLY_ANNOTATIONS})

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [self._annotate(tool) for tool in tools]

    async def get_tool(
        self, name: str, call_next: GetToolNext, *, version: VersionSpec | None = None
    ) -> Tool | None:
        tool = await call_next(name, version=version)
        return None if tool is None else self._annotate(tool)
