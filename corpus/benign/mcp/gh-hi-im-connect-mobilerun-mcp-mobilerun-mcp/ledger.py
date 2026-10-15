"""In-memory run ledger: plan checklist, recorded findings, and the honest-finish rule."""

from __future__ import annotations

from dataclasses import dataclass, field

STATUSES = ("pending", "in_progress", "done", "skipped", "failed")


@dataclass
class Step:
    text: str
    status: str = "pending"
    note: str = ""


@dataclass
class Finding:
    item: str
    quote: str


@dataclass
class Ledger:
    goal: str = ""
    deliverable: str = ""
    target_count: int = 0
    steps: list[Step] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    ended: str | None = None

    def set_plan(
        self,
        steps: list[str],
        goal: str = "",
        deliverable: str = "",
        target_count: int = 0,
    ) -> None:
        self.goal, self.deliverable = goal, deliverable
        self.target_count = max(0, target_count)
        self.steps = [Step(text) for text in steps]
        self.findings = []
        self.ended = None

    def mark_step(self, index: int, status: str, note: str = "") -> Step:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        if not 0 <= index < len(self.steps):
            raise IndexError(f"no step {index}; plan has {len(self.steps)} steps")
        step = self.steps[index]
        step.status = status
        if note:
            step.note = note
        return step

    def record_finding(self, item: str, quote: str) -> int:
        self.findings.append(Finding(item, quote))
        return len(self.findings)

    def missing_findings(self) -> int:
        return max(0, self.target_count - len(self.findings))

    def end(self, outcome: str) -> str | None:
        """Return an error message when ending with success is not allowed, else None."""
        if outcome == "success" and self.missing_findings():
            return (
                f"only {len(self.findings)} of {self.target_count} findings recorded; "
                'finish with outcome="partial" or record the rest'
            )
        self.ended = outcome
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "goal": self.goal,
            "deliverable": self.deliverable,
            "target_count": self.target_count,
            "steps": [
                {"index": i, "text": s.text, "status": s.status, "note": s.note}
                for i, s in enumerate(self.steps)
            ],
            "findings": [{"item": f.item, "quote": f.quote} for f in self.findings],
            "ended": self.ended,
        }
