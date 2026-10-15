"""Citations are structural checks, not a semantic truth oracle."""
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Claim(StrictModel):
    text: str = Field(min_length=1, max_length=1800)
    evidence: list[str] = Field(min_length=1, max_length=20)


class Fact(StrictModel):
    record_id: str
    field: str
    value: str | int | float | bool


class Hypothesis(Claim):
    status: Literal["supported", "unlikely", "unresolved"]


class Report(StrictModel):
    synthetic: Literal[True]
    mode: Literal["fixture", "live"]
    question: str
    summary: Claim
    findings: list[Claim] = Field(min_length=1, max_length=20)
    facts: list[Fact] = Field(min_length=1, max_length=40)
    hypotheses: list[Hypothesis] = Field(min_length=2, max_length=10)
    uncertainty: list[Claim] = Field(min_length=1, max_length=10)
    next_steps: list[Claim] = Field(min_length=1, max_length=10)


def claims(report):
    yield report.summary
    yield from report.findings
    yield from report.hypotheses
    yield from report.uncertainty
    yield from report.next_steps


def validate_report(raw, observed, mode):
    report = Report.model_validate(raw)
    if report.mode != mode:
        raise ValueError("Report mode does not match execution mode")
    for claim in claims(report):
        unknown = set(claim.evidence) - observed.keys()
        if unknown:
            raise ValueError(f"Cites evidence not retrieved: {sorted(unknown)}")
    for fact in report.facts:
        value = observed.get(fact.record_id)
        try:
            for part in fact.field.split("."):
                value = value[int(part)] if isinstance(value, list) else value[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid fact path: {fact.record_id}.{fact.field}") from exc
        if type(value) is not type(fact.value) or value != fact.value:
            raise ValueError(f"Fact does not match telemetry: {fact.record_id}.{fact.field}")
    return report


def markdown(report):
    def line(c):
        return c.text + " " + " ".join(f"[{ref}](evidence.json#{ref})" for ref in c.evidence)
    parts = ["# TraceLens incident report", f"**SYNTHETIC DATA · {report.mode.upper()} MODE**", report.question, line(report.summary)]
    for title, rows in [("Findings", report.findings), ("Hypotheses", report.hypotheses), ("Uncertainty", report.uncertainty), ("Recommended next steps", report.next_steps)]:
        parts.extend([f"## {title}", "\n".join("- " + (f"**{c.status}** — " if isinstance(c, Hypothesis) else "") + line(c) for c in rows)])
    parts.extend(["## Exact evidence values", "```json\n" + json.dumps([f.model_dump() for f in report.facts], indent=2) + "\n```", "References are record IDs in evidence.json. Citation presence and exact fact values are checked in code; narrative entailment is not guaranteed."])
    return "\n\n".join(parts) + "\n"
