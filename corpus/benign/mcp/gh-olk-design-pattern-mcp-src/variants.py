"""§2.4 variant discovery payload and §8.4 realization binding.

Two responsibilities, both pure functions over catalog data:

* the ``design-patterns://variants`` payload (§2.4) — grouped by language, then pattern, carrying
  only the choice surface (``variant_id``, ``name``, ``paradigm``, ``min_standard``,
  ``requires_features``, ``default``, a one-line distinguishing note taken from existing catalog
  text);
* the §8.4 ladder that binds exactly one realization: entry resolution (effective language, else
  ``generic``) and the four-layer variant precedence (explicit ``variant_id`` → paradigm hint →
  capability floor → ``default_variant``).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import Any

from src.patterns.loader import PatternLoader, JoinedPattern, LanguageEntry, LanguageVariant
from src.errors import ERROR_CATALOG_INVALID, DesignPatternError
from src.schemas.variants import VariantSummary

logger = logging.getLogger(__name__)

NOTE_MAX_LENGTH = 160
MAX_VARIANT_SUMMARIES = 5

_WORD_RE = re.compile(r"[a-z0-9]+")
_VERSION_RE = re.compile(r"^(?P<family>[a-z#+.]+?)(?P<version>[0-9][0-9.]*)$")

#: Version strings that denote the same release under the pre-Java-9 numbering (``Java1.8`` = Java 8).
_JAVA_LEGACY_MINORS: dict[tuple[int, ...], tuple[int, ...]] = {
    (1, 5): (5,),
    (1, 6): (6,),
    (1, 7): (7,),
    (1, 8): (8,),
}


def _variant_note(variant: LanguageVariant) -> str:
    """One-line distinguishing note: the variant's idiom name, else its first sentences."""
    if variant.idiom_name:
        return _truncate(variant.idiom_name, NOTE_MAX_LENGTH)
    text = " ".join(variant.implementation_notes.split())
    first = re.split(r"(?<=[.;:])\s", text, maxsplit=1)[0]
    return _truncate(first, NOTE_MAX_LENGTH)


def _truncate(text: str, limit: int) -> str:
    """Trim ``text`` to ``limit`` characters at a word boundary."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:.")


def variants_payload(catalog: PatternLoader) -> dict[str, dict[str, dict[str, Any]]]:
    """The §2.4 payload: ``language -> pattern -> {variants, default_variant}``.

    Only patterns whose entry for that language declares variants appear; ordering is language
    (enum order), then catalog order, then name, then file order of the variants.
    """
    payload: dict[str, dict[str, dict[str, Any]]] = {}
    ordered = sorted(catalog.records.values(), key=lambda record: (catalog.order_index(record.name), record.name))
    for language in catalog.enums.languages:
        per_language: dict[str, dict[str, Any]] = {}
        for record in ordered:
            entry = record.entry(language)
            if entry is None or not entry.variants:
                continue
            per_language[record.name] = {
                "default_variant": entry.default_variant,
                "variants": [
                    {
                        "variant_id": variant.variant_id,
                        "name": variant.name,
                        "paradigm": variant.paradigm,
                        "min_standard": variant.min_standard,
                        "requires_features": list(variant.requires_features),
                        "default": variant.variant_id == entry.default_variant,
                        "note": _variant_note(variant),
                    }
                    for variant in entry.variants
                ],
            }
        if per_language:
            payload[language] = per_language
    return payload


def variants_for_pattern(catalog: PatternLoader, pattern: str) -> dict[str, Any] | None:
    """Per-pattern slice across languages for the template resource; ``None`` for unknown names."""
    resolved = catalog.resolve(pattern)
    if resolved is None:
        return None
    record = catalog.get_by_name(resolved)
    if record is None:
        return None
    slice_: dict[str, Any] = {"pattern": record.name, "category": record.category, "languages": {}}
    for language in catalog.enums.languages:
        entry = record.entry(language)
        if entry is None or not entry.variants:
            continue
        slice_["languages"][language] = {
            "default_variant": entry.default_variant,
            "variants": [
                {
                    "variant_id": variant.variant_id,
                    "name": variant.name,
                    "paradigm": variant.paradigm,
                    "min_standard": variant.min_standard,
                    "requires_features": list(variant.requires_features),
                    "default": variant.variant_id == entry.default_variant,
                    "note": _variant_note(variant),
                }
                for variant in entry.variants
            ],
        }
    return slice_


def bind_entry(record: JoinedPattern, language: str) -> LanguageEntry:
    """§8.4 binding resolution: the effective language's entry, else the record's ``generic`` entry."""
    entry = record.entry(language)
    if entry is not None:
        return entry
    generic = record.entry("generic")
    if generic is None:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            f"{record.name}: no entry for {language!r} and no generic entry to fall back to",
            hint="every record must carry exactly one generic entry (§2.1 invariant)",
        )
    return generic


# --------------------------------------------------------------------------------------
# §8.4 ladder
# --------------------------------------------------------------------------------------


def _word_tokens(text: str) -> list[str]:
    """Lower-cased alphanumeric tokens."""
    return _WORD_RE.findall(text.lower())


def _normalized_standard(value: str) -> tuple[str, tuple[int, ...]] | None:
    """``(family, version tuple)`` of a standard string, normalized across spellings.

    ``C++ 20`` → ``("c", (20,))``, ``C# 8`` → ``("c#", (8,))``, ``Java1.8`` → ``("java", (8,))``
    (the pre-Java-9 numbering), ``.NET 6.0`` → ``("net", (6, 0))``, ``netstandard2.1`` →
    ``("netstandard", (2, 1))``. Unknown shapes return ``None`` and simply never match.
    """
    compact = re.sub(r"\s+", "", value.strip().lower())
    if not compact:
        return None
    match = _VERSION_RE.match(compact)
    if match is None:
        return None
    family = match.group("family").lstrip(".")
    version = tuple(int(part) for part in match.group("version").split(".") if part != "")
    if not version:
        return None
    if family == "java" and version in _JAVA_LEGACY_MINORS:
        version = _JAVA_LEGACY_MINORS[version]
    return family, version


def _satisfies(floor: tuple[str, tuple[int, ...]], given: tuple[str, tuple[int, ...]]) -> bool:
    """True when the stated toolchain ``given`` meets or exceeds ``floor`` (same family)."""
    if floor[0] != given[0]:
        return False
    size = max(len(floor[1]), len(given[1]))
    left = floor[1] + (0,) * (size - len(floor[1]))
    right = given[1] + (0,) * (size - len(given[1]))
    return left <= right


def _floor_sort_key(version: tuple[int, ...]) -> tuple[int, ...]:
    """Comparable key for a version tuple (right-padded with zeros to a fixed width)."""
    return version + (0,) * max(0, 4 - len(version))


def _by_explicit_id(entry: LanguageEntry, focus: str | None) -> LanguageVariant | None:
    """Layer 1: ``focus`` quotes a ``variant_id`` verbatim (a paraphrase matches nothing)."""
    if not focus:
        return None
    haystack = focus.lower()
    for variant in entry.variants:
        if re.search(rf"(?<![a-z0-9-]){re.escape(variant.variant_id)}(?![a-z0-9-])", haystack):
            return variant
    return None


def _by_paradigm(entry: LanguageEntry, paradigm: str | None) -> list[LanguageVariant] | None:
    """Layer 2 pool: the variants whose paradigm matches, or ``None`` when no hint applies."""
    if not paradigm:
        return None
    matching = [variant for variant in entry.variants if variant.paradigm == paradigm]
    return matching or None


def _by_capability_floor(
    pool: Sequence[LanguageVariant], technology_tokens: Sequence[str]
) -> LanguageVariant | None:
    """Layer 3: among the variants the stated toolchain satisfies, the highest floor wins."""
    stated = [parsed for token in technology_tokens if (parsed := _normalized_standard(token)) is not None]
    if not stated:
        return None
    satisfiable: list[tuple[tuple[int, ...], int, LanguageVariant]] = []
    for variant in pool:
        if variant.min_standard is None:
            continue
        floor = _normalized_standard(variant.min_standard)
        if floor is None:
            continue
        if any(_satisfies(floor, given) for given in stated):
            satisfiable.append((_floor_sort_key(floor[1]), len(floor[1]), variant))
    if not satisfiable:
        return None
    satisfiable.sort(key=lambda item: (item[0], item[1], item[2].variant_id))
    return satisfiable[-1][2]


def select_variant(
    entry: LanguageEntry,
    *,
    focus: str | None,
    paradigm: str | None,
    technology_tokens: Sequence[str],
) -> LanguageVariant | None:
    """§8.4 precedence ladder: explicit id -> paradigm hint -> capability floor -> default variant.

    A paraphrase never matches layer 1, a paradigm hint only narrows the pool, and a layer without
    data falls through silently; the ladder always ends at the file's ``default_variant``.
    """
    if not entry.variants:
        return None
    explicit = _by_explicit_id(entry, focus)
    if explicit is not None:
        logger.info("Variant bound by explicit naming", extra={"variant_id": explicit.variant_id})
        return explicit
    pool = _by_paradigm(entry, paradigm) or list(entry.variants)
    if len(pool) == 1:
        logger.info("Variant bound by paradigm hint", extra={"variant_id": pool[0].variant_id})
        return pool[0]
    floored = _by_capability_floor(pool, technology_tokens)
    if floored is not None:
        logger.info(
            "Variant bound by capability floor",
            extra={
                "variant_id": floored.variant_id,
                "min_standard": floored.min_standard,
                "stated": list(technology_tokens),
            },
        )
        return floored
    default = entry.variant(entry.default_variant or "")
    return default if default is not None else entry.variants[0]


def variant_summaries(entry: LanguageEntry, bound_variant: str | None) -> list[VariantSummary]:
    """Compact summaries of every NON-bound sibling, capped at the schema's 5 entries."""
    summaries = [
        VariantSummary(
            variant_id=variant.variant_id,
            name=variant.name,
            paradigm=variant.paradigm,  # type: ignore[arg-type]
            min_standard=variant.min_standard,
            requires_features=list(variant.requires_features),
        )
        for variant in entry.variants
        if variant.variant_id != bound_variant
    ]
    return summaries[:MAX_VARIANT_SUMMARIES]
