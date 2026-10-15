"""Tool annotations: what each tool says about itself.

Under the MCP spec a tool with no annotations is not unclassified. The defaults are
`readOnlyHint: false`, `destructiveHint: true`, `idempotentHint: false`,
`openWorldHint: true`, so a tool that declares nothing has declared itself the most
dangerous kind: a destructive, non-idempotent write that reaches outside the server. A
host that asks the user before destructive calls will ask before every unannotated read.

Every tool here carries one of three annotation sets. `open_world_hint` is false on all of
them because the server only ever touches its own bookmarks.
"""

from mcp.types import ToolAnnotations

READS = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
"""Changes nothing."""

ADDS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=False,
)
"""A write that only adds. Calling it again adds again."""

CHANGES = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)
"""A write that overwrites or removes what is there. The same arguments again leave the
same bookmark, give or take its `updated_at`."""
