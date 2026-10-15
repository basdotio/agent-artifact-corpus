"""Lazy JSON loading with LRU caching for all sonic-kb data sources.

Every loader returns raw dicts/lists -- retrieval modules handle typed conversion.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
KB_DIR = BASE_DIR / "knowledge-base"
DEF_DIR = KB_DIR / "definitions"
PROTO_DIR = KB_DIR / "protocols"
SUB_DIR = KB_DIR / "subsystems"
CODE_DIR = KB_DIR / "code-paths"
HERR_DIR = KB_DIR / "human-errors"
LOG_DIR = KB_DIR / "logs"
DIAG_DIR = KB_DIR / "diagnostics"
PROC_DIR = KB_DIR / "procedures"
BP_DIR = KB_DIR / "best-practices"
IDX_DIR = KB_DIR / "indexes"

SONIC_VERSION = "202511"


def _read_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)


# --- Definitions (Layer 1) ---

@lru_cache(maxsize=1)
def load_all_definitions() -> dict[str, dict]:
    """Load all definition files into one flat map: def_id -> definition."""
    defs: dict[str, dict] = {}
    if not DEF_DIR.exists():
        return defs
    for path in DEF_DIR.glob("*.json"):
        data = _read_json(path)
        items = data if isinstance(data, list) else data.values() if isinstance(data, dict) else []
        for item in items:
            if isinstance(item, dict) and "def_id" in item:
                defs[item["def_id"]] = item
    return defs


# --- Protocols ---

_PROTO_PATHS: dict[str, Path] = {}


@lru_cache(maxsize=1)
def load_protocol_index() -> dict[str, dict]:
    path = PROTO_DIR / "_index.json"
    if not path.exists():
        return {}
    index = _read_json(path)
    _PROTO_PATHS.clear()
    for proto_id, meta in index.items():
        _PROTO_PATHS[proto_id] = PROTO_DIR / f"{proto_id}.json"
    return index


@lru_cache(maxsize=24)
def load_protocol(protocol_id: str) -> dict | None:
    if not _PROTO_PATHS:
        load_protocol_index()
    path = _PROTO_PATHS.get(protocol_id)
    if path is None or not path.exists():
        return None
    return _read_json(path)


# --- Subsystems ---

@lru_cache(maxsize=1)
def load_subsystem_index() -> dict[str, dict]:
    path = SUB_DIR / "_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=20)
def load_subsystem(subsystem_id: str) -> dict | None:
    path = SUB_DIR / f"{subsystem_id}.json"
    if not path.exists():
        return None
    return _read_json(path)


# --- Code Paths ---

@lru_cache(maxsize=1)
def load_code_path_index() -> dict[str, dict]:
    path = CODE_DIR / "_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=20)
def load_code_path(path_id: str) -> dict | None:
    path = CODE_DIR / f"{path_id}.json"
    if not path.exists():
        return None
    return _read_json(path)


# --- Human Errors ---

@lru_cache(maxsize=1)
def load_human_error_index() -> dict[str, dict]:
    path = HERR_DIR / "_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=20)
def load_human_error(error_id: str) -> dict | None:
    path = HERR_DIR / f"{error_id}.json"
    if not path.exists():
        return None
    return _read_json(path)


# --- Log Messages ---

@lru_cache(maxsize=10)
def load_log_catalog(daemon: str) -> dict | None:
    path = LOG_DIR / f"{daemon}.json"
    if not path.exists():
        return None
    return _read_json(path)


@lru_cache(maxsize=1)
def load_all_log_catalogs() -> list[dict]:
    if not LOG_DIR.exists():
        return []
    catalogs = []
    for path in sorted(LOG_DIR.glob("*.json")):
        catalogs.append(_read_json(path))
    return catalogs


# --- Diagnostics ---

@lru_cache(maxsize=1)
def load_diagnostic_index() -> dict[str, dict]:
    path = DIAG_DIR / "_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=10)
def load_diagnostic_tree(tree_id: str) -> dict | None:
    path = DIAG_DIR / f"{tree_id}.json"
    if not path.exists():
        return None
    return _read_json(path)


# --- Procedures ---

@lru_cache(maxsize=1)
def load_procedure_index() -> dict[str, dict]:
    path = PROC_DIR / "_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=10)
def load_procedure(procedure_id: str) -> dict | None:
    path = PROC_DIR / f"{procedure_id}.json"
    if not path.exists():
        return None
    return _read_json(path)


# --- Best Practices ---

@lru_cache(maxsize=1)
def load_best_practices() -> dict | None:
    path = BP_DIR / "index.json"
    if not path.exists():
        return None
    return _read_json(path)


# --- Indexes (Layer 3) ---

@lru_cache(maxsize=1)
def load_db_table_index() -> dict[str, dict]:
    path = IDX_DIR / "_db_table_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=1)
def load_daemon_index() -> dict[str, dict]:
    path = IDX_DIR / "_daemon_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=1)
def load_log_message_index() -> list[dict]:
    path = IDX_DIR / "_log_message_index.json"
    if not path.exists():
        return []
    return _read_json(path)


@lru_cache(maxsize=1)
def load_human_error_search_index() -> dict[str, list[str]]:
    path = IDX_DIR / "_human_error_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=1)
def load_source_refs_index() -> dict[str, dict]:
    path = IDX_DIR / "_source_refs_index.json"
    if not path.exists():
        return {}
    return _read_json(path)


@lru_cache(maxsize=1)
def load_vector_index() -> dict | None:
    path = IDX_DIR / "_vector_index.json"
    if not path.exists():
        return None
    return _read_json(path)


ARTIFACT_DIR = BASE_DIR / "build" / "artifacts"


@lru_cache(maxsize=1)
def load_source_functions_artifact() -> list[dict] | None:
    """Load the full source_functions.json artifact (18965 entries) if present locally."""
    path = ARTIFACT_DIR / "source_functions.json"
    if not path.exists():
        return None
    return _read_json(path)


# --- Methodology ---

@lru_cache(maxsize=1)
def load_methodology() -> dict:
    path = KB_DIR / "methodology.json"
    if not path.exists():
        return {"phases": []}
    return _read_json(path)


# --- Grounding Rules ---

@lru_cache(maxsize=1)
def load_grounding_rules() -> dict:
    path = KB_DIR / "grounding-rules.json"
    if not path.exists():
        return {"rules": []}
    return _read_json(path)


# --- Cache management ---

def clear_caches() -> None:
    load_all_definitions.cache_clear()
    load_protocol_index.cache_clear()
    load_protocol.cache_clear()
    load_subsystem_index.cache_clear()
    load_subsystem.cache_clear()
    load_code_path_index.cache_clear()
    load_code_path.cache_clear()
    load_human_error_index.cache_clear()
    load_human_error.cache_clear()
    load_log_catalog.cache_clear()
    load_all_log_catalogs.cache_clear()
    load_diagnostic_index.cache_clear()
    load_diagnostic_tree.cache_clear()
    load_procedure_index.cache_clear()
    load_procedure.cache_clear()
    load_best_practices.cache_clear()
    load_db_table_index.cache_clear()
    load_daemon_index.cache_clear()
    load_log_message_index.cache_clear()
    load_human_error_search_index.cache_clear()
    load_source_refs_index.cache_clear()
    load_source_functions_artifact.cache_clear()
    load_vector_index.cache_clear()
    load_grounding_rules.cache_clear()
    load_methodology.cache_clear()
    _PROTO_PATHS.clear()
