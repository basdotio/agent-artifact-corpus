"""Transparent, label-isolated evaluation with resumable per-case records."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .agents import ChatModel, LLMAgents, ModelConfig
from .core import MemoryStore, WorkflowEngine
from .gateway import LocalGateway, MCPGateway


def normalize(text: str) -> str:
    return re.sub(r"[\s，,。!！?？:：;；、（）()\[\]]", "", text.casefold().replace("％", "%"))


def contains_term(text: str, term: str) -> bool:
    value = normalize(term)
    if re.search(r"\d", value):
        # 12 must not match 112 or 12.5. Preserve sign and unit in labels.
        left = r"(?<![\d.\-])" if value[0].isdigit() else ""
        right = r"(?![\d.])" if value[-1].isdigit() else ""
        return re.search(left + re.escape(value) + right, text) is not None
    return value in text


def score_answer(case: dict, result: dict) -> dict:
    """Rule score is NOT an LLM/human semantic judge.

    Requirements are explicit in the public labels. For numerical answers,
    punctuation is normalized but magnitudes and signs remain meaningful.
    Multiple required terms must all occur; aliases are alternatives.
    """
    answer = result.get("answer") or {}
    completed = result.get("state", "").lower() in {"completed", "complete"}
    answerable = case["answerable"]
    if not answerable:
        correct = completed and answer.get("status") == "insufficient"
    else:
        terms = case.get("required_terms") or [case["expected_answer"]]
        text = normalize(answer.get("answer", ""))
        terms_match = all(contains_term(text, str(term)) for term in terms)
        aliases = case.get("answer_aliases", [])
        correct = completed and answer.get("status") == "answered" and (
            terms_match or any(contains_term(text, alias) for alias in aliases)
        )
    predicted = {item["id"] for item in answer.get("evidence", []) if "id" in item}
    expected = set(case.get("expected_evidence_ids", []))
    evidence_recall = len(predicted & expected) / len(expected) if expected else None
    return {
        "rule_correct": bool(correct),
        "completed": completed,
        "expected_evidence_recall": evidence_recall,
        "all_expected_evidence": expected <= predicted if expected else None,
        "unanswerable_false_answer": (not answerable) and answer.get("status") == "answered",
        "citation_count": len(predicted),
        "scoring_method": "public_required_terms_and_status_v1",
    }


def wilson(successes: int, n: int) -> list[float]:
    if not n:
        return [0.0, 0.0]
    z = 1.96
    p = successes / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [round(center-margin, 4), round(center+margin, 4)]


def summarize(records: list[dict]) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for record in records:
        groups[record["mode"]].append(record)
    summary = {}
    for mode, rows in groups.items():
        correct = sum(row["scores"]["rule_correct"] for row in rows)
        elapsed = [row["result"].get("metrics", {}).get("elapsed_seconds", 0) for row in rows]
        recalls = [row["scores"]["expected_evidence_recall"] for row in rows
                   if row["scores"]["expected_evidence_recall"] is not None]
        categories = {}
        for category in sorted({row["category"] for row in rows}):
            subset = [row for row in rows if row["category"] == category]
            categories[category] = {"n": len(subset), "correct": sum(r["scores"]["rule_correct"] for r in subset)}
        summary[mode] = {
            "n": len(rows), "rule_correct": correct, "rule_accuracy": correct/len(rows),
            "accuracy_wilson_95": wilson(correct, len(rows)),
            "completion_rate": sum(row["scores"]["completed"] for row in rows)/len(rows),
            "mean_evidence_recall": statistics.mean(recalls) if recalls else None,
            "mean_elapsed_seconds": statistics.mean(elapsed),
            "median_elapsed_seconds": statistics.median(elapsed),
            "p95_elapsed_seconds": sorted(elapsed)[max(0, math.ceil(0.95*len(elapsed))-1)],
            "mean_tool_calls": statistics.mean(row["result"].get("metrics", {}).get("tool_calls", 0) for row in rows),
            "model_requests": sum(row.get("usage", {}).get("requests", 0) for row in rows),
            "prompt_tokens": sum(row.get("usage", {}).get("prompt_tokens", 0) for row in rows),
            "completion_tokens": sum(row.get("usage", {}).get("completion_tokens", 0) for row in rows),
            "categories": categories,
        }
    return summary


async def evaluate(data_dir: Path, questions_path: Path, output_dir: Path,
                   modes: list[str], limit: int | None = None, concurrency: int = 3,
                   config: ModelConfig | None = None, resume: bool = False) -> dict:
    """Each sample gets frozen empty memory: evaluation cannot learn test labels."""
    config = config or ModelConfig.from_env()
    questions_bytes = questions_path.read_bytes()
    loaded = json.loads(questions_bytes)
    cases = loaded["questions"] if isinstance(loaded, dict) else loaded
    if limit:
        cases = cases[:limit]
    if not cases:
        raise ValueError("Evaluation requires at least one question.")
    output_dir.mkdir(parents=True, exist_ok=True)
    cases_dir = output_dir / "cases"
    cases_dir.mkdir(exist_ok=True)
    semaphore = asyncio.Semaphore(concurrency)
    config_fingerprint = hashlib.sha256(json.dumps({
        "model": config.model, "base_url": config.base_url, "vision": config.vision,
        "max_turns": config.max_turns, "max_tokens": config.max_tokens,
        "questions_sha256": hashlib.sha256(questions_bytes).hexdigest(),
        "documents": sorted((p.name, hashlib.sha256(p.read_bytes()).hexdigest())
                            for p in data_dir.glob("*.json")),
    }, sort_keys=True).encode()).hexdigest()

    async def one(case: dict, mode: str) -> dict:
        file = cases_dir / f"{mode}_{case['id']}.json"
        if resume and file.exists():
            existing = json.loads(file.read_text(encoding="utf-8"))
            if existing.get("config_fingerprint") == config_fingerprint:
                return existing
        async with semaphore:
            gateway_type = LocalGateway if mode == "baseline" else MCPGateway
            async with gateway_type(data_dir) as gateway, ChatModel(config) as model:
                agents = LLMAgents(model)
                engine = WorkflowEngine(agents.actor, agents.reviewer, gateway,
                                        memory_store=MemoryStore(frozen=True),
                                        max_revisions=1, max_tool_calls=32, tool_timeout=30)
                result = await engine.run(case["question"], case["doc_id"], mode=mode,
                                          task_id=f"{mode}-{case['id']}")
                record = {
                    "id": case["id"], "mode": mode, "category": case["category"],
                    "question": case["question"], "doc_id": case["doc_id"],
                    "expected_answer": case["expected_answer"],
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "config_fingerprint": config_fingerprint,
                    "requested_model": config.model, "returned_models": sorted(model.returned_models),
                    "usage": model.usage, "agent_tool_trace": agents.trace,
                    "result": result, "scores": score_answer(case, result),
                }
                file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"{mode:10} {case['id']:8} {result['state']:10} rule_correct={record['scores']['rule_correct']}", flush=True)
                return record

    # Rotate mode order by question to reduce an all-baseline-first timing bias.
    tasks = [one(case, mode) for index, case in enumerate(cases)
             for mode in modes[index % len(modes):] + modes[:index % len(modes)]]
    records = await asyncio.gather(*tasks)
    report = {
        "benchmark": "Synthetic educational set; not a published DocAgent benchmark",
        "model": config.model, "vision": config.vision,
        "protocol": "2025-06-18", "mcp_sdk": "1.12.4",
        "config_fingerprint": config_fingerprint,
        "memory_policy": "empty and frozen separately for each question",
        "concurrency": concurrency,
        "limitations": ["Rule scoring is not semantic entailment evaluation.",
                        "Single trial per question; small synthetic sample.",
                        "Latency includes provider variation and concurrent load.",
                        "Baseline is an independent educational reconstruction, not the authors' exact implementation."],
        "summary": summarize(records), "records": records,
    }
    (output_dir / "evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
