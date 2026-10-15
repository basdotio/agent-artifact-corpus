"""Return types for the sonic-kb retrieval library.

Frozen dataclasses -- lightweight, hashable, no Pydantic dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SonicRetrievalResult:
    """Wrapper for all retrieval results with anti-hallucination metadata."""

    found: bool
    kb_coverage: str  # "indexed", "partial", "not_indexed"
    coverage_note: str
    data: dict | None = None
    sonic_version: str = "202511"
    source_refs: tuple = ()


@dataclass(frozen=True)
class ProtocolSummary:
    id: str
    name: str
    family: str
    category: str
    tags: tuple = ()


@dataclass(frozen=True)
class ProtocolDetail:
    protocol_id: str
    protocol_name: str
    protocol_family: str
    standard: str
    category: str
    purpose: str
    operates_at: str
    transport: str = ""
    states: tuple = ()
    transitions: tuple = ()
    timers: tuple = ()
    messages: tuple = ()
    failure_modes: tuple = ()
    dependencies: tuple = ()
    sonic_notes: tuple = ()
    config_db_tables: tuple = ()
    sonic_frr_mapping: dict = field(default_factory=dict)
    key_commands: tuple = ()
    related_protocols: tuple = ()
    tags: tuple = ()
    def_refs: tuple = ()


@dataclass(frozen=True)
class DaemonInfo:
    daemon_id: str
    process_name: str
    container: str
    purpose: str
    subscribes_to: tuple = ()
    writes_to: tuple = ()
    restart_command: str = ""
    restart_warning: str = ""
    health_check_commands: tuple = ()
    source_path: str = ""
    repo: str = ""


@dataclass(frozen=True)
class SubsystemInfo:
    subsystem_id: str
    display_name: str
    container_name: str
    purpose: str
    daemons: tuple = ()
    startup_order: int = 0
    depends_on_containers: tuple = ()
    restart_impact: str = ""
    health_check_commands: tuple = ()
    log_location: str = ""


@dataclass(frozen=True)
class CodePathDetail:
    path_id: str
    display_name: str
    trigger: str
    version: str = "202511"
    steps: tuple = ()
    failure_injection_points: tuple = ()
    related_paths: tuple = ()


@dataclass(frozen=True)
class HumanError:
    error_id: str
    display_name: str
    severity: str
    pattern: str
    what_goes_wrong: str
    symptoms: tuple = ()
    detection_commands: tuple = ()
    correct_procedure: str = ""
    related_errors: tuple = ()
    ref_daemons: tuple = ()
    ref_dbs: tuple = ()


@dataclass(frozen=True)
class LogMessage:
    log_id: str
    daemon: str
    pattern: str
    meaning: str
    severity: str
    likely_causes: tuple = ()
    next_steps: tuple = ()
    related_code_path: str = ""
    source_ref: str = ""


@dataclass(frozen=True)
class DiagnosticNode:
    node_id: str
    node_type: str  # "branch" or "leaf"
    question: str = ""
    commands: tuple = ()
    branches: dict = field(default_factory=dict)
    finding: str = ""
    action: str = ""


@dataclass(frozen=True)
class DiagnosticTree:
    tree_id: str
    display_name: str
    entry_symptom: str
    nodes: tuple = ()
    related_protocol: str = ""
    related_errors: tuple = ()
    related_code_paths: tuple = ()


@dataclass(frozen=True)
class ConfigDbTable:
    table_name: str
    db_name: str
    key_pattern: str = ""
    fields: tuple = ()
    written_by: tuple = ()
    read_by: tuple = ()
    relevant_protocols: tuple = ()
    human_error_risk: str = ""
    verify_command: str = ""
    redis_command: str = ""


@dataclass(frozen=True)
class ProcedureDetail:
    procedure_id: str
    procedure_name: str
    category: str
    risk_level: str
    purpose: str = ""
    prerequisites: tuple = ()
    warnings: tuple = ()
    steps: tuple = ()
    verification: tuple = ()
    rollback: tuple = ()
    daemon_impact: tuple = ()


@dataclass(frozen=True)
class BestPractice:
    topic: str
    title: str
    content: str
    category: str = ""
    source: str = ""
    tags: tuple = ()


@dataclass(frozen=True)
class ContainerInfo:
    name: str
    startup_order: int
    depends_on: tuple = ()
    daemons: tuple = ()
    purpose: str = ""
    health_check: str = ""
