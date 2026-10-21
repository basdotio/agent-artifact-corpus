"""Design-pattern view of the variant catalog (§2.4): provider for the ``design-patterns://`` resources.

The payload itself is assembled by :mod:`src.variants` from the joined records; this provider adds
the URI-addressed lookup shape the MCP resource handlers need. It is built once at startup, AFTER
the §2.3 integrity gate, so the resource can never expose a catalog state that failed validation.
"""

from __future__ import annotations

from typing import Any

from src.patterns.loader import PatternLoader
from src.variants import variants_for_pattern, variants_payload


class VariantsResource:
    """Provider for ``design-patterns://variants`` and ``design-patterns://variants/{pattern}``."""

    def __init__(self, catalog: PatternLoader) -> None:
        self._catalog = catalog
        self._payload: dict[str, dict[str, dict[str, Any]]] = variants_payload(catalog)

    def list_resources(self) -> list[dict[str, str]]:
        """The static resource plus the per-pattern template, for ``list_resources`` clients."""
        return [
            {
                "uri": "design-patterns://variants",
                "name": "design-pattern-variants",
                "description": (
                    "Per-language realization variants of every pattern whose language entry "
                    "declares more than one realization (language -> pattern -> variants)."
                ),
            },
            {
                "uri_template": "design-patterns://variants/{pattern}",
                "name": "design-pattern-variants-pattern",
                "description": (
                    "Per-pattern slice of the variant catalog across languages, for targeted reads."
                ),
            },
        ]

    def payload(self) -> dict[str, dict[str, dict[str, Any]]]:
        """The grouped variant catalog (language → pattern → variants)."""
        return self._payload

    def load(self, pattern: str) -> dict[str, Any] | None:
        """Per-pattern slice across languages, or ``None`` for an unknown pattern name/alias."""
        return variants_for_pattern(self._catalog, pattern)
