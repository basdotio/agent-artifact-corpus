"""Prometheus MCP server: PromQL queries and active alerts, read-only.

Range queries are summarized per series (first/last/min/max) instead of
returning raw points, which keeps results small enough for the model.
"""

import time
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import SecretStr

from aiops_agent.servers import Access

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
MAX_SERIES = 30
ACCESS: dict[str, Access] = {
    "query": "read",
    "query_range": "read",
    "active_alerts": "read",
}  # ADR 0002


def _num(v: str) -> float | str:
    try:
        return round(float(v), 4)
    except ValueError:
        return v


def build_server(
    url: str, token: SecretStr | None = None, http: httpx.Client | None = None
) -> FastMCP:
    if http is None:
        headers = {"Authorization": f"Bearer {token.get_secret_value()}"} if token else {}
        http = httpx.Client(base_url=url, headers=headers, timeout=15)
    mcp = FastMCP("prometheus", instructions="Query metrics and alerts with PromQL.")

    def api(path: str, params: dict[str, Any]) -> Any:
        try:
            resp = http.get(path, params=params)
        except httpx.HTTPError as e:
            raise ToolError(f"Prometheus unreachable: {e}") from None
        body = (
            resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        if resp.status_code != 200 or body.get("status") != "success":
            raise ToolError(
                f"Prometheus error {resp.status_code}: {body.get('error', resp.text[:300])}"
            )
        return body["data"]

    def trimmed(series: list[Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {"series": rows[:MAX_SERIES]}
        if len(series) > MAX_SERIES:
            out["note"] = f"{len(series)} series, showing {MAX_SERIES}; aggregate with sum/topk"
        return out

    @mcp.tool(annotations=READ)
    def query(promql: str) -> dict[str, Any]:
        """Instant PromQL query (current value). Examples:
        kube_pod_container_status_restarts_total{namespace="shop"}
        sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="shop"}[5m]))"""
        data = api("/api/v1/query", {"query": promql})
        if data["resultType"] != "vector":
            return {"result": data["result"]}
        rows = [{"labels": s["metric"], "value": _num(s["value"][1])} for s in data["result"]]
        return trimmed(data["result"], rows)

    @mcp.tool(annotations=READ)
    def query_range(promql: str, minutes: int = 60, step: str = "1m") -> dict[str, Any]:
        """PromQL over the last N minutes, summarized per series as first/last/min/max.
        Use it to see when something started and whether it is getting worse."""
        minutes = max(1, min(minutes, 24 * 60))
        end = time.time()
        data = api(
            "/api/v1/query_range",
            {"query": promql, "start": end - minutes * 60, "end": end, "step": step},
        )
        rows = []
        for s in data["result"]:
            values = [float(v) for _, v in s["values"]]
            rows.append(
                {
                    "labels": s["metric"],
                    "first": round(values[0], 4),
                    "last": round(values[-1], 4),
                    "min": round(min(values), 4),
                    "max": round(max(values), 4),
                    "points": len(values),
                }
            )
        return trimmed(data["result"], rows)

    @mcp.tool(annotations=READ)
    def active_alerts() -> list[dict[str, Any]]:
        """Alerts currently firing or pending in Prometheus: what else is going on?"""
        alerts = api("/api/v1/alerts", {})["alerts"]
        return [
            {
                "name": a["labels"].get("alertname"),
                "state": a["state"],
                "labels": a["labels"],
                "since": a.get("activeAt"),
            }
            for a in alerts[:50]
        ]

    return mcp
