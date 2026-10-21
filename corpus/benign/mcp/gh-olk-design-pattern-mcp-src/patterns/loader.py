"""PatternLoader loading, join (§2.3 rule 4) and integrity gate (§2.3 rule 5).

The catalog is the decision vocabulary of the whole pipeline: 486 ``DesignPattern`` records stored
in layout V8 — a language-neutral main record ``pattern/<name>.json`` plus 14 colocated realization
files (``<name>.generic.json`` and one per concrete language), joined in memory into a single
record whose ``language_implementations`` mapping is ordered ``generic`` first, then the concrete
languages in enum order.

Everything structural is derived from ``docs/pattern-schema.json`` and
``docs/pattern-language-schema.json`` (single source of truth, §15): the enums are parsed from the
schema definitions and cross-checked against the ``Literal`` types in :mod:`src.schemas`, and the
canonical catalog order (§8.1 tie-break) is parsed from ``docs/design-patterns.md``.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field, replace
from itertools import combinations
from pathlib import Path
from typing import Any, get_args

from jsonschema import Draft7Validator
from referencing import Registry
from referencing.jsonschema import DRAFT7

from src.errors import ERROR_CATALOG_INVALID, DesignPatternError
from src.schemas.enums import (
    Language,
    Paradigm,
    PatternCategory,
    PatternScope,
    Provenance,
    SupportLevel,
)

logger = logging.getLogger(__name__)

PATTERN_SCHEMA_FILE = "pattern-schema.json"
LANGUAGE_SCHEMA_FILE = "pattern-language-schema.json"
CATALOG_DOC_FILE = "design-patterns.md"

#: The catalog's out-of-scope marker inside the Background section (§5 rule 5).
OUT_OF_SCOPE_MARKER = "Out of scope by design:"

#: The marker that introduces the locally implementable parts of those out-of-scope names.
LOCAL_PART_MARKER = "for example"

# --------------------------------------------------------------------------------------
# Schema enums (single source of truth)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemaEnums:
    """Enum tuples parsed from ``docs/pattern-schema.json`` ``definitions``."""

    categories: tuple[str, ...]
    scopes: tuple[str, ...]
    languages: tuple[str, ...]
    support_levels: tuple[str, ...]
    paradigms: tuple[str, ...]
    provenances: tuple[str, ...]


def load_schema_enums(docs_dir: Path) -> SchemaEnums:
    """Parse the enum definitions out of the pattern schema (never hand-maintained)."""
    schema = _read_json(docs_dir / PATTERN_SCHEMA_FILE)
    definitions = schema.get("definitions", {})

    def enum_of(definition: str) -> tuple[str, ...]:
        values = definitions.get(definition, {}).get("enum")
        if not values:
            raise DesignPatternError(
                ERROR_CATALOG_INVALID,
                f"{PATTERN_SCHEMA_FILE} definitions.{definition} carries no enum",
                hint="the catalog schema is the enum source of truth; restore the definition",
            )
        return tuple(str(v) for v in values)

    return SchemaEnums(
        categories=enum_of("patternCategory"),
        scopes=enum_of("patternScope"),
        languages=enum_of("language"),
        support_levels=enum_of("supportLevel"),
        paradigms=enum_of("paradigm"),
        provenances=enum_of("provenance"),
    )


def assert_enums_in_sync(enums: SchemaEnums) -> None:
    """Fail fast when the ``Literal`` enums in :mod:`src.schemas` drifted from the schema (§15)."""
    expected: dict[str, tuple[str, ...]] = {
        "Language": get_args(Language),
        "SupportLevel": get_args(SupportLevel),
        "Paradigm": get_args(Paradigm),
        "PatternScope": get_args(PatternScope),
        "PatternCategory": get_args(PatternCategory),
        "Provenance": get_args(Provenance),
    }
    actual: dict[str, tuple[str, ...]] = {
        "Language": enums.languages,
        "SupportLevel": enums.support_levels,
        "Paradigm": enums.paradigms,
        "PatternScope": enums.scopes,
        "PatternCategory": enums.categories,
        "Provenance": enums.provenances,
    }
    drifted = {name: (expected[name], actual[name]) for name in expected if expected[name] != actual[name]}
    if drifted:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            f"enum drift between src/schemas.py and {PATTERN_SCHEMA_FILE}: {drifted}",
            hint="the schema is the single source of truth — update src/schemas.py literals",
        )


# --------------------------------------------------------------------------------------
# Joined record shape
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LanguageVariant:
    """One realization of a pattern within a single language (§8.4 ladder)."""

    variant_id: str
    name: str
    paradigm: str
    implementation_notes: str
    min_standard: str | None = None
    requires_features: tuple[str, ...] = ()
    idiom_name: str | None = None
    code_sketch: str | None = None
    pitfalls: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class LanguageEntry:
    """Joined ``language_implementations`` entry (file-level fields stripped)."""

    language: str
    support: str
    implementation_notes: str
    idiom_name: str | None = None
    code_sketch: str | None = None
    pitfalls: tuple[str, ...] = ()
    alternative: str | None = None
    sources: tuple[str, ...] = ()
    variants: tuple[LanguageVariant, ...] = ()
    default_variant: str | None = None

    @property
    def variant_ids(self) -> tuple[str, ...]:
        """All ``variant_id`` slugs of this entry, in file order."""
        return tuple(v.variant_id for v in self.variants)

    def variant(self, variant_id: str) -> LanguageVariant | None:
        """The variant with ``variant_id``, or ``None``."""
        for variant in self.variants:
            if variant.variant_id == variant_id:
                return variant
        return None


@dataclass(frozen=True)
class JoinedPattern:
    """A design pattern record after the layout-V8 join (§2.3 rule 4)."""

    name: str
    category: str
    subgroup: str
    intent: str
    problem: str
    context: str
    aliases: tuple[str, ...]
    benefits: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    quality_attributes: dict[str, float]
    language_implementations: dict[str, LanguageEntry]
    participants: tuple[tuple[str, str], ...] = ()
    suitable_scopes: tuple[str, ...] = ()
    unsuitable_scopes: tuple[str, ...] = ()
    use_cases: tuple[str, ...] = ()
    avoid_when: tuple[str, ...] = ()
    related_patterns: tuple[str, ...] = ()
    related_patterns_notes: dict[str, str] = field(default_factory=dict)
    anti_patterns: tuple[str, ...] = ()
    migration_from: tuple[str, ...] = ()
    migration_to: tuple[str, ...] = ()
    design_principles: tuple[str, ...] = ()
    best_practices: tuple[str, ...] = ()
    pitfalls: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    paradigms: tuple[str, ...] = ()
    scope: str | None = None
    provenance: tuple[str, ...] = ()
    version: str | None = None
    language_files: dict[str, str] = field(default_factory=dict)

    def entry(self, language: str) -> LanguageEntry | None:
        """The joined entry for ``language``, or ``None`` when the record has no such entry."""
        return self.language_implementations.get(language)

    @property
    def document_text(self) -> str:
        """Dense-leg document text (§2.2): name, aliases, intent, problem, context, use cases."""
        parts: list[str] = [self.name, *self.aliases, self.intent, self.problem, self.context]
        parts.extend(self.use_cases)
        return "\n".join(part for part in parts if part)

    @property
    def capsule_text(self) -> str:
        """Compact rerank text (§14 ``rerank_text: capsule``): name, intent, problem, first two use cases.

        Roughly a third of ``document_text`` on the 486-record catalog; ranking
        equivalence with the full text is NOT guaranteed (measured divergence,
        §6 step 4) — opt-in only.
        """
        parts: list[str] = [self.name, self.intent, self.problem, *self.use_cases[:2]]
        return "\n".join(part for part in parts if part)

    @property
    def bm25_text(self) -> str:
        """BM25-leg text (§2.2): name, aliases and problem."""
        parts: list[str] = [self.name, *self.aliases, self.problem]
        return " ".join(part for part in parts if part)

    @property
    def name_tokens(self) -> frozenset[str]:
        """Token set of the canonical name plus resolved aliases (negative-signal veto, §6)."""
        return _tokens(" ".join((self.name, *self.aliases)))


@dataclass
class PatternLoader:
    """The loaded catalog plus its canonical order and alias index."""

    records: dict[str, JoinedPattern]
    order: dict[str, int]
    subgroups: dict[str, str]
    alias_map: dict[str, str]
    ambiguous_aliases: tuple[str, ...]
    enums: SchemaEnums

    def get_by_name(self, name: str) -> JoinedPattern | None:
        """Record by canonical name."""
        return self.records.get(name)

    def resolve(self, name: str) -> str | None:
        """Canonical name for ``name`` (itself or a resolved alias), or ``None``."""
        if name in self.records:
            return name
        return self.alias_map.get(name.lower())

    def order_index(self, name: str) -> int:
        """Canonical catalog order index; names absent from the catalog document get stable tail positions."""
        if name in self.order:
            return self.order[name]
        # Sentinel headroom: real rows are category_rank*1e6 + subgroup*1e3 + row (max observed
        # 9_004_007 for category 9), so unknown names must start above 10_000_000, not at
        # len(records)+… — that range is BELOW every real row and inverted the tie-break.
        return 10_000_000 + _fallback_order(name)


def _fallback_order(name: str) -> int:
    """Stable tail offset for records absent from the catalog document (not a name sort)."""
    return sum(ord(ch) for ch in name)


# --------------------------------------------------------------------------------------
# Canonical catalog order (§8.1 tie-break)
# --------------------------------------------------------------------------------------

_FOOTNOTE_RE = re.compile(r"\[\^[^\]]+\]")
_ROW_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*")
_SECTION_RE = re.compile(r"^##\s+(\d)\.\s+(.*)$")
_SUBSECTION_RE = re.compile(r"^###\s+(.*)$")
_BACKGROUND_RE = re.compile(r"^##\s+Background")


def _kebab(text: str) -> str:
    """Kebab-case normalization: strip footnotes/parentheses, lowercase, non-alnum runs to '-'."""
    cleaned = _FOOTNOTE_RE.sub("", text)
    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", cleaned).strip("-")
    return cleaned.lower()


def _tokens(text: str) -> frozenset[str]:
    """Lower-cased alphanumeric word tokens of ``text``."""
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def _row_candidates(row_name: str) -> list[str]:
    """Record-name candidates for one catalog row, longest match first.

    Handles the catalog's composite rows: ``Aggregate / Aggregate Root`` (slash alternatives) and
    ``Contravariant / `Decidable` validators`` (alternatives plus a shared trailing word). We try
    the full kebab form, the slash alternatives, then every token pair in order — the longest,
    most specific name that exists as a record wins.
    """
    kebab = _kebab(row_name)
    alternatives = [_kebab(part) for part in row_name.split("/") if _kebab(part)]
    candidates: list[str] = []
    for candidate in (kebab, *alternatives):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    tokens = [tok for tok in kebab.split("-") if tok]
    for combo in combinations(range(len(tokens)), 2):
        candidate = "-".join(tokens[index] for index in combo)
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def parse_catalog_order(
    catalog_doc: Path, record_names: frozenset[str]
) -> tuple[dict[str, int], dict[str, str], list[str]]:
    """Parse ``docs/design-patterns.md`` into ``(order, subgroups, unmatched_rows)``.

    Only rows inside the nine numbered category sections participate; the Background section and
    the facet views are not selectable (§2.1) and are skipped.
    """
    order: dict[str, int] = {}
    subgroups: dict[str, str] = {}
    unmatched: list[str] = []
    category_rank = 0
    subgroup_index = 0
    row_index = 0
    in_category_section = False
    current_subgroup = ""

    for line in catalog_doc.read_text(encoding="utf-8").splitlines():
        section = _SECTION_RE.match(line)
        if section is not None:
            category_rank = int(section.group(1))
            in_category_section = 1 <= category_rank <= 9
            subgroup_index = 0
            row_index = 0
            current_subgroup = ""
            continue
        if line.startswith("## "):
            in_category_section = False
            continue
        subsection = _SUBSECTION_RE.match(line)
        if subsection is not None:
            subgroup_index += 1
            row_index = 0
            current_subgroup = subsection.group(1).strip()
            continue
        if not in_category_section:
            continue
        row = _ROW_RE.match(line)
        if row is None:
            continue
        row_index += 1
        name = _FOOTNOTE_RE.sub("", row.group(1)).strip()
        matched = next((cand for cand in _row_candidates(name) if cand in record_names), None)
        if matched is None:
            unmatched.append(name)
            continue
        if matched not in order:
            order[matched] = category_rank * 1_000_000 + subgroup_index * 1_000 + row_index
            subgroups[matched] = current_subgroup

    if not order and not unmatched:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            f"no catalog rows parsed from {catalog_doc}",
            hint="the canonical order (§8.1) requires the catalog document's numbered sections",
        )
    return order, subgroups, unmatched


def parse_out_of_scope_terms(catalog_doc: Path) -> tuple[str, ...]:
    """Parse the "Out of scope by design" term list from the Background section (§5 rule 5)."""
    text = catalog_doc.read_text(encoding="utf-8")
    marker = text.find(OUT_OF_SCOPE_MARKER)
    if marker < 0:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            f"out-of-scope marker {OUT_OF_SCOPE_MARKER!r} missing from {catalog_doc}",
            hint="the anti-scope guard (§5 rule 5) derives its term set from this sentence",
        )
    tail = text[marker + len(OUT_OF_SCOPE_MARKER) :]
    sentence = tail.split("Where a name")[0]
    terms: list[str] = []
    for raw in sentence.split(","):
        term = re.sub(r"^[^A-Za-z0-9]+", "", _FOOTNOTE_RE.sub("", raw)).strip().strip(".").strip()
        term = re.sub(r"^(?:and|or)\s+", "", term, flags=re.IGNORECASE).strip()
        if not term:
            continue
        for alternative in re.split(r"\s+versus\s+", term):
            cleaned = alternative.strip()
            if cleaned and cleaned not in terms:
                terms.append(cleaned)
    if not terms:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            "out-of-scope term list parsed to empty",
            hint=f"check the {OUT_OF_SCOPE_MARKER!r} sentence in {catalog_doc}",
        )
    return tuple(terms)


def parse_locally_implementable_names(catalog_doc: Path) -> tuple[str, ...]:
    """Parse the "for example ..." names of the out-of-scope sentence (§5 rule 5 keep list).

    These are the names the catalog hosts as locally implementable parts of an architecture-level
    choice; whether one of them is really usable is decided by record resolution, never by this
    prose list (a name without a record is dropped by the guard).
    """
    text = catalog_doc.read_text(encoding="utf-8")
    marker = text.find(OUT_OF_SCOPE_MARKER)
    if marker < 0:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            f"out-of-scope marker {OUT_OF_SCOPE_MARKER!r} missing from {catalog_doc}",
        )
    tail = text[marker:]
    start = tail.find(LOCAL_PART_MARKER)
    if start < 0:
        return ()
    clause = tail[start + len(LOCAL_PART_MARKER) :]
    clause = re.split(r"\n\s*\n|## ", clause, maxsplit=1)[0]
    names: list[str] = []
    for raw in re.split(r",|\s+and\s+", clause):
        cleaned = _FOOTNOTE_RE.sub("", raw).strip().strip(".").strip()
        cleaned = re.sub(r"^[^A-Za-z0-9]+", "", cleaned).strip()
        if cleaned and cleaned not in names:
            names.append(cleaned)
    return tuple(names)


# --------------------------------------------------------------------------------------
# Loader + integrity gate
# --------------------------------------------------------------------------------------


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            payload: dict[str, Any] = json.load(fh)
    except json.JSONDecodeError as exc:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID, f"{path} is not valid JSON: {exc}"
        ) from exc
    return payload


def _validators(docs_dir: Path) -> tuple[Draft7Validator, Draft7Validator]:
    """Draft-7 validators for the main record and the language file, sharing one registry.

    The language schema references ``pattern-schema.json#/definitions/...``; the registry serves
    that file under exactly the relative name the ``$ref`` uses.
    """
    pattern_schema = _read_json(docs_dir / PATTERN_SCHEMA_FILE)
    language_schema = _read_json(docs_dir / LANGUAGE_SCHEMA_FILE)
    language_schema.pop("$id", None)
    registry = Registry().with_resource(
        PATTERN_SCHEMA_FILE, DRAFT7.create_resource(pattern_schema)
    )
    return (
        Draft7Validator(pattern_schema, registry=registry),
        Draft7Validator(language_schema, registry=registry),
    )


def _strip_file_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop the language file's own identity/version fields during the join (§2.3 rule 4)."""
    return {k: v for k, v in payload.items() if k not in ("pattern", "version")}


def _language_entry_from_file(payload: dict[str, Any], language: str) -> LanguageEntry:
    variants = tuple(
        LanguageVariant(
            variant_id=str(v["variant_id"]),
            name=str(v["name"]),
            paradigm=str(v["paradigm"]),
            implementation_notes=str(v["implementation_notes"]),
            min_standard=v.get("min_standard"),
            requires_features=tuple(v.get("requires_features", ())),
            idiom_name=v.get("idiom_name"),
            code_sketch=v.get("code_sketch"),
            pitfalls=tuple(v.get("pitfalls", ())),
            sources=tuple(v.get("sources", ())),
        )
        for v in payload.get("variants", ())
    )
    stripped = _strip_file_fields(payload)
    return LanguageEntry(
        language=str(stripped.get("language", language)),
        support=str(stripped.get("support", "")),
        implementation_notes=str(stripped.get("implementation_notes", "")),
        idiom_name=stripped.get("idiom_name"),
        code_sketch=stripped.get("code_sketch"),
        pitfalls=tuple(stripped.get("pitfalls", ())),
        alternative=stripped.get("alternative"),
        sources=tuple(stripped.get("sources", ())),
        variants=variants,
        default_variant=stripped.get("default_variant"),
    )


def _check_variants(name: str, language: str, payload: dict[str, Any], problems: list[str]) -> None:
    """Language-file variant invariants (§2.3 rule 5): defaults resolve, ids unique, flat fields match."""
    variants = payload.get("variants")
    if not variants:
        return
    ids = [str(v.get("variant_id", "")) for v in variants]
    duplicates = sorted({vid for vid in ids if ids.count(vid) > 1})
    if duplicates:
        problems.append(f"{name}.{language}: duplicate variant_id(s) {duplicates}")
    default = payload.get("default_variant")
    if default not in ids:
        problems.append(
            f"{name}.{language}: default_variant {default!r} matches no variant_id {ids}"
        )
        return
    default_variant = next(v for v in variants if v.get("variant_id") == default)
    for flat_key in ("idiom_name", "implementation_notes", "code_sketch", "pitfalls", "sources"):
        flat_value: Any = payload.get(flat_key)
        variant_value: Any = default_variant.get(flat_key)
        if flat_key in ("pitfalls", "sources"):
            flat_value = list(flat_value or [])
            variant_value = list(variant_value or [])
        if flat_value != variant_value:
            problems.append(
                f"{name}.{language}: flat field {flat_key!r} differs from the default variant's "
                f"({flat_value!r} != {variant_value!r})"
            )


def load_catalog(pattern_dir: Path, docs_dir: Path) -> PatternLoader:
    """Load, join and integrity-check every record; raise ``ERR_CATALOG_INVALID`` on any violation."""
    pattern_dir = Path(pattern_dir)
    docs_dir = Path(docs_dir)
    if not pattern_dir.is_dir():
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            f"pattern directory not found: {pattern_dir}",
            hint="point DESIGN_PATTERN_PATTERN_DIRECTORY at the catalog directory",
        )
    enums = load_schema_enums(docs_dir)
    assert_enums_in_sync(enums)
    main_validator, language_validator = _validators(docs_dir)

    main_paths = sorted(p for p in pattern_dir.glob("*.json") if "." not in p.stem)
    if not main_paths:
        raise DesignPatternError(ERROR_CATALOG_INVALID, f"no main records found in {pattern_dir}")

    problems: list[str] = []
    records: dict[str, JoinedPattern] = {}
    for path in main_paths:
        record = _load_one_record(path, pattern_dir, enums, main_validator, language_validator, problems)
        if record is not None:
            records[record.name] = record
    _raise_if_problems(problems)

    _check_orphans(pattern_dir, set(records), set(enums.languages), problems)
    _raise_if_problems(problems)

    catalog_doc = docs_dir / CATALOG_DOC_FILE
    order, subgroups, unmatched_rows = parse_catalog_order(catalog_doc, frozenset(records))
    for name, subgroup in subgroups.items():
        records[name] = replace(records[name], subgroup=subgroup)

    aliases, ambiguous = _build_alias_index(records)
    unplaced = sorted(set(records) - set(order))
    if not order and unmatched_rows:
        logger.warning(
            "No catalog row matched a record; canonical order falls back to name order",
            extra={"catalog_doc": str(catalog_doc), "rows": len(unmatched_rows)},
        )
    logger.info(
        "PatternLoader loaded",
        extra={
            "records": len(records),
            "language_entries": sum(len(r.language_implementations) for r in records.values()),
            "aliases": len(aliases),
            "ambiguous_aliases": list(ambiguous),
            "unmatched_catalog_rows": unmatched_rows,
            "records_without_row": unplaced,
        },
    )
    return PatternLoader(
        records=records,
        order=order,
        subgroups=subgroups,
        alias_map=aliases,
        ambiguous_aliases=ambiguous,
        enums=enums,
    )


def _raise_if_problems(problems: list[str]) -> None:
    """Raise a single ``ERR_CATALOG_INVALID`` naming the first violations, or return silently."""
    if problems:
        raise DesignPatternError(
            ERROR_CATALOG_INVALID,
            f"{len(problems)} catalog integrity violation(s): " + "; ".join(problems[:10]),
            hint="run `python3 -B scripts/validate_patterns.py` for the full report",
        )


def _load_one_record(
    path: Path,
    pattern_dir: Path,
    enums: SchemaEnums,
    main_validator: Draft7Validator,
    language_validator: Draft7Validator,
    problems: list[str],
) -> JoinedPattern | None:
    """Validate one main record, join its 14 language files (§2.3 rule 4), collect violations."""
    raw = _read_json(path)
    schema_errors = sorted(main_validator.iter_errors(raw), key=lambda e: list(e.path))
    if schema_errors:
        problems.append(
            f"{path.name}: main record schema errors: "
            + "; ".join(f"{list(e.path)}: {e.message}" for e in schema_errors[:5])
        )
        return None
    if "language_implementations" in raw:
        problems.append(
            f"{path.name}: language_implementations must be absent from stored records "
            "(layout V8; the realizations live in the colocated language files)"
        )
        return None
    name = str(raw["name"])
    language_files: dict[str, str] = dict(raw["language_files"])
    expected_keys = set(enums.languages)
    if set(language_files) != expected_keys:
        missing = sorted(expected_keys - set(language_files))
        extra = sorted(set(language_files) - expected_keys)
        problems.append(
            f"{path.name}: language_files keys must be exactly the {len(expected_keys)} "
            f"language enum values (missing={missing}, extra={extra})"
        )
        return None

    entries: dict[str, LanguageEntry] = {}
    violations: list[str] = []
    for language in enums.languages:
        entry = _load_language_entry(
            path, pattern_dir, name, language, language_files[language], language_validator, violations
        )
        if entry is not None:
            entries[language] = entry
    if violations:
        problems.extend(violations)
        return None
    return _build_record(raw, entries)


def _load_language_entry(
    main_path: Path,
    pattern_dir: Path,
    name: str,
    language: str,
    declared: str,
    language_validator: Draft7Validator,
    problems: list[str],
) -> LanguageEntry | None:
    """Validate one colocated language file and enforce the §2.3 rule 3 three-way agreement."""
    expected_name = f"{name}.{language}.json"
    language_path = pattern_dir / declared
    if declared != expected_name:
        problems.append(f"{main_path.name}: language_files[{language!r}] = {declared!r} != {expected_name!r}")
        return None
    if not language_path.is_file():
        problems.append(f"{main_path.name}: {declared} is declared but missing on disk")
        return None
    payload = _read_json(language_path)
    errors = sorted(language_validator.iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        problems.append(
            f"{declared}: schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
        )
        return None
    if str(payload.get("pattern")) != name:
        problems.append(f"{declared}: pattern field {payload.get('pattern')!r} != {name!r}")
        return None
    if str(payload.get("language")) != language:
        problems.append(f"{declared}: language field {payload.get('language')!r} != {language!r}")
        return None
    _check_variants(name, language, payload, problems)
    return _language_entry_from_file(payload, language)


def _check_orphans(
    pattern_dir: Path, main_names: set[str], languages: set[str], problems: list[str]
) -> None:
    """Reject language files with no matching main record or an unresolvable suffix (§2.3 rule 5)."""
    for path in sorted(pattern_dir.glob("*.json")):
        if "." not in path.stem:
            continue
        base, _, suffix = path.stem.rpartition(".")
        if base in main_names and suffix in languages:
            continue
        problems.append(
            f"{path.name}: orphan language file (no main record {base!r} with suffix {suffix!r})"
        )


def _build_record(raw: dict[str, Any], entries: dict[str, LanguageEntry]) -> JoinedPattern:
    """Assemble a :class:`JoinedPattern` from the validated main record and its joined entries."""
    name = str(raw["name"])
    participants = tuple(
        (str(p.get("role", "")), str(p.get("responsibility", ""))) for p in raw.get("participants", ())
    )
    return JoinedPattern(
        name=name,
        category=str(raw["category"]),
        subgroup="",
        intent=str(raw["intent"]),
        problem=str(raw["problem"]),
        context=str(raw["context"]),
        aliases=tuple(str(a) for a in raw.get("aliases", ())),
        benefits=tuple(str(b) for b in raw.get("benefits", ())),
        tradeoffs=tuple(str(t) for t in raw.get("tradeoffs", ())),
        quality_attributes={
            str(k): float(v) for k, v in raw.get("quality_attributes", {}).items()
        },
        language_implementations=entries,
        participants=participants,
        suitable_scopes=tuple(str(s) for s in raw.get("suitable_scopes", ())),
        unsuitable_scopes=tuple(str(s) for s in raw.get("unsuitable_scopes", ())),
        use_cases=tuple(str(u) for u in raw.get("use_cases", ())),
        avoid_when=tuple(str(a) for a in raw.get("avoid_when", ())),
        related_patterns=tuple(str(r) for r in raw.get("related_patterns", ())),
        related_patterns_notes={
            str(k): str(v) for k, v in raw.get("related_patterns_notes", {}).items()
        },
        anti_patterns=tuple(str(a) for a in raw.get("anti_patterns", ())),
        migration_from=tuple(str(m) for m in raw.get("migration_from", ())),
        migration_to=tuple(str(m) for m in raw.get("migration_to", ())),
        design_principles=tuple(str(d) for d in raw.get("design_principles", ())),
        best_practices=tuple(str(b) for b in raw.get("best_practices", ())),
        pitfalls=tuple(str(p) for p in raw.get("pitfalls", ())),
        sources=tuple(str(s) for s in raw.get("sources", ())),
        paradigms=tuple(str(p) for p in raw.get("paradigm", ())),
        scope=raw.get("scope"),
        provenance=tuple(str(p) for p in raw.get("provenance", ())),
        version=raw.get("version"),
        language_files={str(k): str(v) for k, v in raw["language_files"].items()},
    )


def _build_alias_index(
    records: dict[str, JoinedPattern],
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Alias → canonical map; an alias that is itself a catalog name is ambiguous and dropped (§2.1)."""
    index: dict[str, str] = {}
    ambiguous: list[str] = []
    for name, record in records.items():
        for alias in record.aliases:
            key = alias.strip().lower()
            if not key:
                continue
            if key in records and records[key].name != name:
                ambiguous.append(alias)
                continue
            if _names_other_record(key, name, records):
                ambiguous.append(alias)
                continue
            if key in index and index[key] != name:
                ambiguous.append(alias)
                continue
            index[key] = name
    return index, tuple(sorted(set(ambiguous)))


def _names_other_record(key: str, owner: str, records: dict[str, JoinedPattern]) -> bool:
    """True when ``key`` is another record's name or its leading word sequence (§2.1 worked case).

    The guide's ambiguity rule is about an alias that reads as a *distinct catalog pattern name*:
    the Strategy alias ``policy`` collides with the catalog's own ``policy-based-design``, so a
    strict name equality test is not enough — the alias is also ambiguous when another record's
    name starts with the alias' word sequence.
    """
    key_tokens = re.findall(r"[a-z0-9]+", key)
    if not key_tokens:
        return False
    for other in records:
        if other == owner:
            continue
        other_tokens = re.findall(r"[a-z0-9]+", other)
        if len(other_tokens) > len(key_tokens) and other_tokens[: len(key_tokens)] == key_tokens:
            return True
    return False
