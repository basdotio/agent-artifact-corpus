"""Protocol enums and axis constants of the design-pattern domain (docs/pattern-schema.json).

The ``Literal`` enums are the single source of truth inside the process;
``src.catalog.assert_enums_in_sync`` fails startup when these literals and the schema
``definitions`` drift apart (§15 catalog sync).
"""

from __future__ import annotations

from typing import Literal

Language = Literal[
    "generic",
    "c",
    "cplusplus",
    "csharp",
    "go",
    "java",
    "javascript",
    "kotlin",
    "python",
    "ruby",
    "rust",
    "scala",
    "swift",
    "typescript",
]

SupportLevel = Literal["native", "idiomatic", "library", "manual", "discouraged"]

Paradigm = Literal["oo", "functional", "concurrent", "data-oriented", "declarative", "procedural"]

Provenance = Literal[
    "gof",
    "eaa",
    "eip",
    "ddd",
    "posa1",
    "posa2",
    "posa3",
    "security-patterns",
    "plop",
    "language-idiom",
    "functional-catalog",
    "smalltalk",
    "xunit-test-patterns",
    "game-programming",
    "modern",
]

PatternScope = Literal[
    "value",
    "object",
    "module",
    "boundary",
    "message-flow",
    "persistence-unit",
    "task-lifetime",
]

PatternCategory = Literal[
    "domain-modeling",
    "construction-composition",
    "behavior-selection",
    "interaction-boundary",
    "workflow-messaging",
    "persistence-state",
    "concurrency-resilience",
    "security-verification",
    "specialized-components",
]

#: The eight scoring axes (§2.1, §7.2). Order defines the weight-vector layout.
QUALITY_AXES: tuple[str, ...] = (
    "testability",
    "extensibility",
    "maintainability",
    "simplicity",
    "performance",
    "reliability",
    "security",
    "scalability",
)

#: §12 category fallback primaries; ``specialized-components`` has none (E7 instead).
FALLBACK_PRIMARY: dict[str, str] = {
    "domain-modeling": "transaction-script",
    "construction-composition": "dependency-injection",
    "behavior-selection": "strategy",
    "interaction-boundary": "data-transfer-object",
    "workflow-messaging": "observer",
    "persistence-state": "repository",
    "concurrency-resilience": "timeout",
    "security-verification": "guard-clause",
}
