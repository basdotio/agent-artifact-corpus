"""Thin typed client for the Metricairn API, configured via environment."""

from __future__ import annotations

import os
import time

import httpx


def env(name, default=""):
    return os.environ.get(f"METRICAIRN_{name}", default)


API_URL = env("API_URL", "http://localhost:8000").rstrip("/")
READ_KEY = env("READ_KEY")
MANAGEMENT_KEY = env("MANAGEMENT_KEY")
WRITE_KEY = env("WRITE_KEY")


class MetricairnClient:
    def __init__(
        self,
        api_url: str = API_URL,
        read_key: str = READ_KEY,
        write_key: str = WRITE_KEY,
        management_key: str = MANAGEMENT_KEY,
    ):
        self.api_url = api_url.rstrip("/")
        self.read_key = read_key
        self.write_key = write_key
        self.management_key = management_key
        self._project_id: str | None = None
        self._http = httpx.Client(
            timeout=30, trust_env=False
        )  # bypass env proxies for localhost API

    # -- read helpers -----------------------------------------------------
    @staticmethod
    def _json(response: httpx.Response) -> dict | list:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type != "application/json" and not content_type.endswith("+json"):
            raise ValueError(
                "The API returned a non-JSON response. Check METRICAIRN_API_URL and the API/proxy configuration."
            )
        try:
            return response.json()
        except ValueError:
            raise ValueError(
                "The API returned invalid JSON. Check the API logs, then retry."
            ) from None

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        r = self._http.get(
            f"{self.api_url}{path}",
            params=params or {},
            headers={"X-Read-Key": self.read_key},
        )
        return self._json(r)

    def _post(self, path: str, body: dict) -> dict | list:
        r = self._http.post(
            f"{self.api_url}{path}",
            json=body,
            headers={"X-Read-Key": self.read_key},
        )
        return self._json(r)

    def metrics_catalog(self):
        return self._get("/api/v1/query/metrics")

    def run_query(self, plan: dict):
        return self._post("/api/v1/query/run", plan)

    def investigate(self, plan: dict):
        return self._post("/api/v1/investigations/run", plan)

    def goals(self):
        return self._get("/api/v1/goals")

    def goal_report(
        self, goal_id: str, days: int, date_from: str | None = None, date_to: str | None = None
    ):
        return self._get(f"/api/v1/goals/{goal_id}/report", _range(days, date_from, date_to))

    def retention(
        self,
        days: int,
        event_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ):
        return self._get(
            "/api/v1/query/retention",
            _range(days, date_from, date_to) | ({"event_name": event_name} if event_name else {}),
        )

    def investigations(self):
        return self._get("/api/v1/investigations")

    def investigation(self, investigation_id: str):
        return self._get(f"/api/v1/investigations/{investigation_id}")

    def _manage(self, method: str, path: str, body: dict):
        if not self.management_key:
            raise ValueError("METRICAIRN_MANAGEMENT_KEY is required")
        response = self._http.request(
            method,
            f"{self.api_url}{path}",
            json=body,
            headers={"X-Management-Key": self.management_key},
        )
        return self._json(response)

    def save_investigation(self, title: str, plan: dict):
        return self._manage("POST", "/api/v1/investigations", {"title": title, "plan": plan})

    def review_investigation(self, investigation_id: str, status: str, note: str):
        return self._manage(
            "PATCH", f"/api/v1/investigations/{investigation_id}", {"status": status, "note": note}
        )

    def timeseries(self, metric: str, days: int, interval: str = "day"):
        return self._get(
            "/api/v1/query/timeseries", {"metric": metric, "interval": interval, **_range(days)}
        )

    def breakdown(self, dimension: str, days: int, limit: int = 10):
        return self._get(
            "/api/v1/query/breakdown", {"dimension": dimension, "limit": limit, **_range(days)}
        )

    def dimension_values(self, dimension: str, days: int):
        return self._get("/api/v1/query/dimensions", {"dimension": dimension, **_range(days)})

    def realtime(self):
        return self._get("/api/v1/query/realtime")

    def revenue(self, days: int):
        return self._get("/api/v1/query/revenue", _range(days))

    def compare(self, days: int):
        return self._get("/api/v1/query/compare", _range(days))

    def anomalies(self, days: int):
        return self._get("/api/v1/query/anomalies", _range(days))

    def mcp_usage(self, days: int):
        return self._get("/api/v1/query/mcp-usage", _range(days))

    def funnels(self):
        return self._get("/api/v1/funnels")

    def funnel_report(self, funnel_id: str, days: int, segment_by: str | None = None):
        params = _range(days)
        if segment_by:
            params["segment_by"] = segment_by
        return self._get(f"/api/v1/funnels/{funnel_id}/report", params)

    def ask(self, question: str, days: int):
        return self._post("/api/v1/ask", {"question": question, **_range(days)})

    def integration_health(self):
        return self._get(f"/api/v1/projects/{self.project_id()}/data/health")

    # -- timeline notes ------------------------------------------------------
    # Reading uses the read key. Writing additionally requires the private
    # management key and an opt-in tool registration in server.py.
    def project_id(self) -> str:
        if not self._project_id:
            me = self._get("/api/v1/projects/me")
            self._project_id = me["project_id"]
        return self._project_id

    def list_notes(self, limit: int = 20) -> list:
        notes = self._get(f"/api/v1/projects/{self.project_id()}/notes")
        return notes[:limit]

    def add_note(self, text: str) -> dict:
        text = " ".join(text.split())  # collapse whitespace/newlines
        if not text:
            raise ValueError("note text is empty")
        if len(text) > 500:
            raise ValueError("note too long (max 500 chars)")
        if not self.management_key:
            raise ValueError("METRICAIRN_MANAGEMENT_KEY is required to write notes")
        r = self._http.post(
            f"{self.api_url}/api/v1/projects/{self.project_id()}/notes",
            json={"text": text},
            headers={"X-Management-Key": self.management_key},
        )
        return self._json(r)

    # -- direction-2: the server observes its own usage --------------------
    def report_tool_call(self, tool: str, duration_ms: float, success: bool) -> None:
        """Best-effort: log this MCP tool call as an analytics event."""
        if not self.write_key:
            return
        try:
            self._http.post(
                f"{self.api_url}/api/v1/ingest",
                json={
                    "events": [
                        {
                            "name": "mcp_tool_call",
                            "url": "mcp://metricairn",
                            "props": {
                                "tool": tool,
                                "duration_ms": round(duration_ms, 1),
                                "success": success,
                            },
                        }
                    ]
                },
                headers={"X-Write-Key": self.write_key},
                timeout=3,
            )
        except Exception:
            pass  # usage reporting must never break the tool call


def _range(days: int, date_from: str | None = None, date_to: str | None = None) -> dict:
    from datetime import datetime, timedelta, timezone

    if bool(date_from) != bool(date_to):
        raise ValueError("Provide both date_from and date_to, or neither")
    if date_from:
        return {"date_from": date_from, "date_to": date_to}
    if not 1 <= days <= 366:
        raise ValueError("days must be between 1 and 366")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return {"date_from": start.isoformat(), "date_to": end.isoformat()}


def timed_report(client: MetricairnClient, tool: str, fn, *args, **kwargs):
    """Run fn, report usage, re-raise on error."""
    start = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        client.report_tool_call(tool, (time.perf_counter() - start) * 1000, True)
        return result
    except Exception:
        client.report_tool_call(tool, (time.perf_counter() - start) * 1000, False)
        raise
