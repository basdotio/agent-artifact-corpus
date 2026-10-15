"""Alert input (Alertmanager webhook v4) and the triage report the agent returns."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str]
    annotations: dict[str, str] = {}
    startsAt: datetime | None = None
    generatorURL: str = ""
    fingerprint: str = ""


class AlertGroup(BaseModel):
    """Alertmanager webhook payload: one notification = one alert group."""

    version: str = "4"
    status: Literal["firing", "resolved"]
    receiver: str = ""
    groupKey: str = ""
    groupLabels: dict[str, str] = {}
    commonLabels: dict[str, str] = {}
    commonAnnotations: dict[str, str] = {}
    externalURL: str = ""
    alerts: list[Alert]

    @property
    def title(self) -> str:
        name = self.commonLabels.get("alertname", "alert")
        where = self.commonLabels.get("namespace", "")
        return f"{name} {where}".strip()

    @property
    def firing(self) -> list[Alert]:
        return [a for a in self.alerts if a.status == "firing"]


# Root cause class, not failure mode (docs/adr/0001-category-is-root-cause-class.md).
Category = Literal[
    "bad_rollout",
    "bad_config",
    "app_error",
    "resource_limits",
    "image_unavailable",
    "capacity",
    "node_problem",
    "dependency_failure",
    "unknown",
]


class Evidence(BaseModel):
    source: str = Field(description="Tool that produced it, e.g. kubernetes_pod_logs")
    finding: str = Field(description="What it showed, quoted or summarized, one line")


class TriageReport(BaseModel):
    """Result of investigating one alert group. Every claim must be backed by evidence."""

    summary: str = Field(description="One or two sentences an on-call engineer reads first")
    category: Category = Field(
        description="Why it broke, not how it fails. bad_rollout: a new revision broke a "
        "workload whose earlier revision worked (wins over the other classes). bad_config: "
        "wrong or missing config, command or probe. app_error: bug in the code, including "
        "memory leaks. resource_limits: limits too low for a healthy workload. "
        "image_unavailable: tag or registry problem. capacity: the cluster can't fit the workload."
    )
    probable_root_cause: str
    confidence: Literal["high", "medium", "low"] = Field(
        description="high: direct evidence (e.g. the error in logs); low: inferred"
    )
    severity: Literal["critical", "high", "medium", "low"]
    affected: list[str] = Field(description="Workloads affected, as namespace/kind/name")
    evidence: list[Evidence] = Field(min_length=1)
    recommended_actions: list[str] = Field(description="Ordered, concrete next steps")
    runbook: str | None = Field(None, description="Runbook name used, if one matched")

    def to_markdown(self, executed_actions: list[str] | None = None) -> str:
        """executed_actions come from the system's record, never from the model."""
        lines = [
            f"## {self.summary}",
            "",
            f"**Root cause** ({self.confidence} confidence, `{self.category}`): "
            f"{self.probable_root_cause}",
            f"**Severity:** {self.severity}  ·  **Affected:** {', '.join(self.affected) or '-'}",
            "",
            "**Evidence**",
            *[f"- `{e.source}`: {e.finding}" for e in self.evidence],
            "",
            "**Recommendations**",
            *[f"{i}. {a}" for i, a in enumerate(self.recommended_actions, 1)],
        ]
        if executed_actions:
            lines += ["", "**Executed actions**", *[f"- `{a}`" for a in executed_actions]]
        if self.runbook:
            lines += ["", f"Runbook: `{self.runbook}`"]
        return "\n".join(lines)
