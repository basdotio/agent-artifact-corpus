"""Transport-independent rules. Evidence is fictional and never claim approval."""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "appliances.json"
DISCLAIMER = "Date-based assessment only; claim approval and fault coverage are not determined."


class InputError(ValueError):
    """A caller supplied an invalid or unknown value."""


def text_input(value: object, field: str, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise InputError(f"{field} must be a non-empty string of at most {limit} characters.")
    return value.strip()


class ApplianceCatalog:
    def __init__(self, path: Path = DATA_PATH) -> None:
        self._records: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["appliances"]

    def _get(self, appliance_id: str) -> dict[str, Any]:
        appliance_id = text_input(appliance_id, "appliance_id", 80)
        for record in self._records:
            if record["id"] == appliance_id:
                return record
        raise InputError(f"Unknown appliance_id: {appliance_id}. Use find_appliance first.")

    def find(self, query: str) -> dict[str, Any]:
        tokens = text_input(query, "query").casefold().split()
        matches = []
        for record in self._records:
            details = {key: record[key] for key in ("id", "name", "category", "brand", "model", "serial", "household")}
            searchable = " ".join(details.values()).casefold()
            if all(token in searchable for token in tokens):
                matches.append(details)
        return {"synthetic_demo": True, "matches": matches, "count": len(matches)}

    def evidence(self, appliance_id: str) -> dict[str, Any]:
        record = self._get(appliance_id)
        # Return a copy so callers cannot modify catalog state.
        purchase = json.loads(json.dumps(record["purchase"]))
        return {"synthetic_demo": True, "appliance_id": record["id"], **purchase,
                "warranty_evidence": json.loads(json.dumps(record["warranty"]))}

    def warranty(self, appliance_id: str, evaluation_date: str | None = None) -> dict[str, Any]:
        record = self._get(appliance_id)
        if evaluation_date is None:
            evaluated = date.today()
        else:
            if not isinstance(evaluation_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", evaluation_date):
                raise InputError("evaluation_date must be a valid YYYY-MM-DD date.")
            try:
                evaluated = date.fromisoformat(evaluation_date)
            except ValueError as exc:
                raise InputError("evaluation_date must be a valid YYYY-MM-DD date.") from exc
        purchase, warranty = record["purchase"], record["warranty"]
        result: dict[str, Any] = {
            "synthetic_demo": True, "appliance_id": record["id"],
            "evaluation_date": evaluated.isoformat(), "status": "unknown",
            "reason": "Insufficient verified demo purchase or warranty evidence.",
            "claim_approval": "not_determined", "disclaimer": DISCLAIMER,
            "source_refs": purchase["source_refs"] + warranty["source_refs"],
        }
        if (purchase["evidence_status"] != "verified_demo" or
                warranty["evidence_status"] != "verified_demo" or
                not purchase["purchase_date"] or not warranty["start_date"] or not warranty["end_date"]):
            return result
        start, end = date.fromisoformat(warranty["start_date"]), date.fromisoformat(warranty["end_date"])
        if start != date.fromisoformat(purchase["purchase_date"]) or end < start:
            result["reason"] = "Recorded purchase and warranty dates are inconsistent."
            return result
        result.update(period_start=start.isoformat(), period_end=end.isoformat())
        if evaluated < start:
            result["reason"] = "Evaluation date precedes the recorded purchase and coverage start."
        elif evaluated <= end:
            result.update(status="active", reason="Recorded date-based coverage period is active (inclusive end date).")
        else:
            result.update(status="expired", reason="Recorded date-based coverage period has expired.")
        return result
