"""
_capabilities.py — how the gateway groups your tools for discovery.

_registry.py says what tools EXIST and how to call them. This file only says
how they're grouped and described, so a model can browse a handful of group
descriptions (list_capabilities) instead of reading every tool's schema up
front, then pull in one group's schemas on demand (load_capability).

Rules — enforced at gateway startup and by `python gateway_server.py --validate`:

  * Every tool in _registry._TOOLS appears in exactly one capability.
  * Every name listed here exists in _TOOLS.

A startup failure is deliberate: a tool that isn't in any group is a tool
the model will never find by browsing.

Writing good group descriptions
-------------------------------
The description is the ONLY thing the model sees before choosing a group, so
it should answer "would the tool I need be in here?" Name the kinds of tasks
the group serves ("anything touching git or code review"), not just the tool
names. Aim for groups of roughly 5–25 related tools; a group the model has to
load to find out what's in it isn't doing its job.

Adding your own group
---------------------
    "my-group": {
        "description": "What kinds of requests this group serves, in a sentence or two.",
        "tools": ["my_tool", "my_other_tool"],
    },
"""

CAPABILITIES: dict[str, dict] = {
    # -- Built-ins: the gateway's own plumbing. Keep these. ------------------
    "gateway": {
        "description": (
            "The gateway's own plumbing: the audit trail of every tool call "
            "(audit_log) and the admin surface for the result cache "
            "(result_cache). Use to answer 'what ran?', 'when?', or to "
            "refresh a cached answer."
        ),
        "tools": ["audit_log", "result_cache"],
    },

    # -- Examples: universal starter tools. Keep, replace, or delete. --------
    "examples": {
        "description": (
            "General-purpose starter tools: git working-tree status and "
            "JMESPath querying of JSON. Also the reference implementations "
            "to copy when adding your own tools."
        ),
        "tools": ["git_status", "json_query"],
    },

    # -- Your groups go here. ------------------------------------------------
}


# ---------------------------------------------------------------------------
# Result-cache allowlist
# ---------------------------------------------------------------------------
# A tool is result-cached by the gateway only if BOTH:
#   1. its _TOOLS entry carries "cache_ttl_s": <seconds>, and
#   2. its name is listed here.
# Startup validation enforces that the two always agree, so turning caching
# on is always a deliberate, reviewable two-file change rather than a key
# that slips in unnoticed.
#
# NEVER cache a tool with side effects (send/create/update/delete/sync) or
# one whose answer depends on state it also changes. Only pure or slowly
# changing reads belong here: reference data, expensive reports.
CACHEABLE_TOOLS: frozenset[str] = frozenset({
    # "my_expensive_report",
})
