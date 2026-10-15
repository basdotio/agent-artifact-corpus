"""Reproducible scripted fault injection, separate from real model evaluation.

All actors/reviewers in this experiment are deterministic scripts. The experiment
measures enforcement of explicit safeguards under specified faults, not an LLM's
probability of making those mistakes. Every variant receives the same fault.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .core import EvidenceGate, GateResult, MemoryStore, WorkflowEngine
from .documents import DocumentStore
from .gateway import LocalGateway

VARIANTS = (
    "baseline", "engineered", "optimized", "optimized_no_gate", "optimized_no_memory_filter"
)

SCENARIOS = (
    {"id": "normal", "description": "Authoritative source; actor extracts the pilot size; reviewer accepts."},
    {"id": "forged_page", "description": "Correct answer with citation page changed to 99."},
    {"id": "cross_document", "description": "Correct answer cites a real passage from a different document."},
    {"id": "forged_excerpt", "description": "Answer and cited excerpt replace source value 2000 with 9000."},
    {"id": "missing_citation", "description": "Correct answer contains no source evidence."},
    {"id": "wrong_answer_real_citation", "description": "Incorrect answer 9000 cites the intact passage stating 2000; semantic gate limitation."},
    {"id": "transient_timeout", "description": "First section-read attempt raises TimeoutError; later attempts succeed."},
    {"id": "persistent_tool_error", "description": "Every section-read attempt raises ConnectionError."},
    {"id": "unvalidated_memory", "description": "Unvalidated advisory memory says 9000; susceptible actor follows it while citing current source."},
    {"id": "stale_validated_memory", "description": "Historically marked validated memory has an obsolete excerpt stating 9000; susceptible actor follows it while citing current source."},
    {"id": "reviewer_memory_pollution", "description": "Reviewer repeatedly changes correct 2000 to 9000, forges supporting excerpt, and proposes a memory write."},
)

QUESTION = "港湾资料借阅系统的试点规模是多少名读者？"
DOC_ID = "harbor"
SECTION_ID = "s1"
EXPECTED_VALUE = "2000"
INJECTED_VALUE = "9000"


class _FaultGateway:
    """Wrap real LocalGateway; inject transport failures before its reads."""

    def __init__(self, local: LocalGateway, scenario: str) -> None:
        self.local = local
        self.scenario = scenario
        self.attempts = 0
        self.injected_failures = 0

    async def list_tools(self) -> list[dict]:
        return await self.local.list_tools()

    async def call(self, name: str, arguments: dict) -> dict:
        self.attempts += 1
        if name == "get_section_content":
            if self.scenario == "transient_timeout" and self.injected_failures == 0:
                self.injected_failures += 1
                raise TimeoutError("Injected transient read timeout")
            if self.scenario == "persistent_tool_error":
                self.injected_failures += 1
                raise ConnectionError("Injected persistent read failure")
        return await self.local.call(name, arguments)


class _IndependentSource:
    """Clean evaluation-only source, bypassing all injected transport faults."""

    def __init__(self, store: DocumentStore) -> None:
        self.store = store

    async def call(self, name: str, arguments: dict) -> dict:
        return self.store.call(name, arguments)


class _AllowAllGate:
    """Explicitly remove provenance checks, including history revalidation."""

    async def validate(self, answer: dict, doc_id: str, tools: Any) -> GateResult:
        return GateResult(True, [], copy.deepcopy(answer.get("evidence", [])))


class _NoMemoryFilterEngine(WorkflowEngine):
    async def _prepare_memory(self, ctx: Any) -> list[dict]:
        # Only the trusted marker and history provenance revalidation disappear;
        # document scoping and final answer provenance validation remain enabled.
        return self.memory_store.snapshot(ctx.doc_id, validated_only=False)


def _extract_size(text: str) -> str:
    found = re.search(r"试点规模为\s*(\d+)\s*名读者", text)
    if found is None:
        raise ValueError("Robustness fixture lacks the expected pilot-size sentence")
    return found.group(1)


def _response(value: str, evidence: list[dict]) -> dict:
    return {"answer": f"试点规模为{value}名读者。", "evidence": evidence, "status": "answered"}


class _ScriptedAgents:
    """A fixed susceptible policy, never corrected by the evaluator's oracle."""

    def __init__(self, scenario: str, other_document_evidence: dict) -> None:
        self.scenario = scenario
        self.other_document_evidence = copy.deepcopy(other_document_evidence)
        self.memory_seen: list[dict] = []

    async def actor(self, question: str, doc_id: str, tools: Any, memory: list[dict]) -> dict:
        result = await tools.call("get_section_content", {"doc_id": doc_id, "section_id": SECTION_ID})
        citations = copy.deepcopy(result["evidence"])
        value = _extract_size(citations[0]["text"])
        # Ephemeral reviewer feedback is not a stored memory and never counted
        # as one. The scripted agent deliberately remains vulnerable to stored
        # misleading numeric advice, equally in every variant.
        stored = [item for item in memory if item.get("source") != "current_task_review"]
        self.memory_seen = [{"source": item.get("source"), "validated": item.get("validated"),
                             "content": item.get("content")} for item in stored]
        if self.scenario in {"unvalidated_memory", "stale_validated_memory"} and stored:
            value = _extract_size(stored[-1]["content"])
        if self.scenario == "forged_page":
            citations[0]["page"] = 99
        elif self.scenario == "cross_document":
            citations = [copy.deepcopy(self.other_document_evidence)]
        elif self.scenario == "forged_excerpt":
            value = INJECTED_VALUE
            citations[0]["text"] = citations[0]["text"].replace(EXPECTED_VALUE, INJECTED_VALUE)
        elif self.scenario == "missing_citation":
            citations = []
        elif self.scenario == "wrong_answer_real_citation":
            value = INJECTED_VALUE
        return _response(value, citations)

    async def reviewer(self, question: str, doc_id: str, draft: dict, tools: Any) -> dict:
        if self.scenario == "reviewer_memory_pollution":
            corrected = copy.deepcopy(draft)
            corrected["answer"] = _response(INJECTED_VALUE, [])["answer"]
            for item in corrected["evidence"]:
                item["text"] = item["text"].replace(EXPECTED_VALUE, INJECTED_VALUE)
            return {
                "verdict": "revise", "answer": corrected,
                "reason": "Injected reviewer error: prefer the unsupported value 9000.",
                "memory_candidate": _response(INJECTED_VALUE, [])["answer"],
            }
        return {"verdict": "accept", "answer": copy.deepcopy(draft),
                "reason": "Scripted pass-through review; no semantic oracle correction.",
                "memory_candidate": None}


def _seed_memory(scenario: str, citation: dict) -> MemoryStore:
    memory = MemoryStore()
    if scenario in {"unvalidated_memory", "stale_validated_memory"}:
        previous = copy.deepcopy(citation)
        validated = scenario == "stale_validated_memory"
        if validated:
            previous["text"] = previous["text"].replace(EXPECTED_VALUE, INJECTED_VALUE)
        memory.add(DOC_ID, _response(INJECTED_VALUE, [])["answer"], [previous],
                   source="injected_obsolete_history" if validated else "injected_unvalidated_history",
                   validated=validated)
    return memory


async def _score(result: dict, source: _IndependentSource, source_available: bool) -> dict:
    final = result.get("answer") or {}
    answered = result["state"] == "completed" and final.get("status") == "answered"
    abstained = result["state"] == "completed" and final.get("status") == "insufficient"
    # All scripted answers have the fixed numeric form; token-set scoring also
    # rejects "2000 or 9000", so mentioning the gold value alone is insufficient.
    values = re.findall(r"(?<!\d)\d+(?!\d)", final.get("answer", ""))
    semantic_correct = answered and values == [EXPECTED_VALUE]
    checked = await EvidenceGate().validate(final, DOC_ID, source) if answered else None
    provenance_valid = checked.valid if checked is not None else None
    successful_safe_answer = bool(answered and semantic_correct and provenance_valid)
    execution_failed = result["state"] == "failed"
    return {
        "answered": answered, "semantic_correct": semantic_correct,
        "provenance_applicable": answered, "provenance_valid": provenance_valid,
        "provenance_failures": checked.failures if checked is not None else [],
        "successful_safe_answer": successful_safe_answer,
        "abstained": abstained, "false_refusal": bool(abstained and source_available),
        "execution_failed": execution_failed,
        "unsafe_answer": bool(answered and not successful_safe_answer),
        "safe_response": bool(abstained or successful_safe_answer),
    }


def _aggregate(rows: list[dict]) -> dict:
    summary = {}
    fields = (
        "answered", "semantic_correct", "successful_safe_answer", "abstained",
        "false_refusal", "execution_failed", "unsafe_answer", "safe_response",
    )
    for variant in VARIANTS:
        records = [item for item in rows if item["variant"] == variant]
        counts = {field: sum(int(item["assessment"][field]) for item in records) for field in fields}
        answered = counts["answered"]
        provenance_valid = sum(item["assessment"]["provenance_valid"] is True for item in records)
        summary[variant] = {
            "runs": len(records), "counts": {**counts, "provenance_valid": provenance_valid},
            "rates_over_all_runs": {field: round(counts[field] / len(records), 6) for field in fields},
            "provenance_valid_rate_among_answered": round(provenance_valid / answered, 6) if answered else None,
            "memory_writes": sum(item["workflow"]["metrics"]["memory_writes"] for item in records),
            "tool_attempts": sum(item["workflow"]["metrics"]["tool_calls"] for item in records),
            "retries": sum(item["workflow"]["metrics"]["retries"] for item in records),
        }
    return summary


async def run_robustness(data_dir: Path, output_dir: Path) -> dict:
    """Run all fixed scenario/variant pairs and save sanitized full results.

    No model adapter or credential is read. Only public synthetic document text,
    deterministic faults, relative identifiers, and execution traces are saved.
    """
    clean_store = DocumentStore(data_dir)
    source = _IndependentSource(clean_store)
    original = clean_store.call("get_section_content", {"doc_id": DOC_ID, "section_id": SECTION_ID})["evidence"][0]
    if _extract_size(original["text"]) != EXPECTED_VALUE:
        raise ValueError("Robustness experiment requires the unchanged harbor s1 synthetic fixture (2000 readers)")
    other = clean_store.call("get_section_content", {"doc_id": "atlas", "section_id": SECTION_ID})["evidence"][0]
    configuration = {
        "experiment_kind": "deterministic_scripted_fault_injection_not_llm_evaluation",
        "model_calls": 0, "document_id": DOC_ID, "section_id": SECTION_ID,
        "question": QUESTION, "expected_numeric_value": EXPECTED_VALUE,
        "source_sha256": hashlib.sha256(original["text"].encode()).hexdigest(),
        "injected_numeric_value": INJECTED_VALUE, "variants": list(VARIANTS),
        "scenarios": copy.deepcopy(list(SCENARIOS)),
        "engine": {"max_revisions": 1, "max_tool_calls": 12, "max_retries": 1,
                   "tool_timeout": 1, "agent_timeout": 5},
        "protocol": {
            "transport": "LocalGateway for every variant; this isolates scheduling/gate/memory effects from MCP transport",
            "isolation": "Fresh engine, memory store, and fault counter for every scenario/variant pair",
            "actor": "Extract source numeric pilot size, then apply identical specified fault or susceptible memory policy",
            "reviewer": "Pass through unchanged except reviewer_memory_pollution; no oracle correction or repair on revision",
            "source_oracle": "Independent unwrapped DocumentStore plus a fresh real EvidenceGate, even for no_gate variant",
            "semantic_correct": "Completed answered output contains exactly one numeric value and it is 2000",
            "provenance_valid": "Fresh real citation gate against the unmodified source; null when no answer is offered",
            "safe_response": "Completed abstention OR answered output with both semantic_correct and provenance_valid; execution failures excluded",
            "successful_safe_answer": "Answered output with both semantic_correct and provenance_valid; abstention never counts",
            "false_refusal": "Completed abstention although the authoritative section remains accessible in this scenario",
            "availability": "Only persistent_tool_error makes the source persistently inaccessible to the actor",
            "optimized_no_gate": "Replace engine.evidence_gate with an allow-all gate: removes final provenance check AND history revalidation, keeps validated-only memory selection",
            "optimized_no_memory_filter": "Override _prepare_memory with unfiltered document-scoped snapshot: removes trusted-marker filtering AND history revalidation; keeps final provenance gate",
            "memory_writes": "Engine runtime writes only; injected seed records are excluded from the metric",
            "interpretation": "Uniform scenario counts are a diagnostic matrix, not an estimate of production fault prevalence or model accuracy",
        },
    }
    rows = []
    for scenario in SCENARIOS:
        scenario_id = scenario["id"]
        for variant in VARIANTS:
            memory = _seed_memory(scenario_id, original)
            seeded = memory.snapshot(DOC_ID)
            scripted = _ScriptedAgents(scenario_id, other)
            async with LocalGateway(data_dir) as local:
                faulty = _FaultGateway(local, scenario_id)
                engine_class = _NoMemoryFilterEngine if variant == "optimized_no_memory_filter" else WorkflowEngine
                engine = engine_class(scripted.actor, scripted.reviewer, faulty, memory,
                                      **configuration["engine"])
                if variant == "optimized_no_gate":
                    engine.evidence_gate = _AllowAllGate()
                mode = variant if variant in {"baseline", "engineered"} else "optimized"
                result = await engine.run(QUESTION, DOC_ID, mode=mode,
                                          task_id=f"fault-{scenario_id}-{variant}")
                assessment = await _score(result, source, scenario_id != "persistent_tool_error")
                rows.append({
                    "scenario": scenario_id, "variant": variant,
                    "source_available": scenario_id != "persistent_tool_error",
                    "fault": {"underlying_attempts": faulty.attempts,
                              "injected_failures": faulty.injected_failures},
                    "memory_before": seeded, "memory_seen_by_actor": scripted.memory_seen,
                    "memory_after": memory.snapshot(DOC_ID),
                    "assessment": assessment, "workflow": result,
                })
    report = {
        "schema_version": 1, "generated_at": datetime.now(UTC).isoformat(),
        "configuration": configuration, "summary": _aggregate(rows), "results": rows,
    }
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "robustness.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
