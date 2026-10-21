"""Explicit local approval workflow. Household context is not authentication."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.domain import ApplianceCatalog, InputError, text_input
from backend.repair_repository import RepairRepository


class ConflictError(InputError):
    """An idempotency key or terminal decision conflicts with the request."""


def encoded(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class RepairService:
    def __init__(self, repository: RepairRepository, catalog: ApplianceCatalog | None = None) -> None:
        self.repository = repository
        self.catalog = catalog if catalog is not None else ApplianceCatalog()

    @staticmethod
    def _context(household_id: str) -> str:
        return text_input(household_id, "household_id", 80)

    def _event(self, db: sqlite3.Connection, proposal: dict[str, Any], event: str,
               now: str, case_id: str | None = None) -> None:
        self.repository.insert(db, "audit_events", {
            "household_id": proposal["household_id"], "proposal_id": proposal["proposal_id"],
            "case_id": case_id, "event_type": event, "event_timestamp": now,
            "metadata_json": encoded({"source": "local_explicit_workflow", "status": proposal["status"]}),
        })

    def prepare_repair_proposal(self, household_id: str, appliance_id: str, issue_description: str,
                                idempotency_key: str, evaluation_date: str | None = None) -> dict[str, Any]:
        household = self._context(household_id)
        appliance = text_input(appliance_id, "appliance_id", 80)
        issue = text_input(issue_description, "issue_description", 2000)
        key = text_input(idempotency_key, "idempotency_key", 120)
        evidence = self.catalog.evidence(appliance)  # Existing public API validates existence.
        matches = self.catalog.find(appliance)["matches"]
        if not any(item["id"] == appliance and item["household"] == household for item in matches):
            raise InputError("Appliance does not belong to this fictional household context.")
        warranty = self.catalog.warranty(appliance, evaluation_date)
        request = {"appliance_id": appliance, "issue_description": issue, "evaluation_date": evaluation_date}
        with self.repository.transaction() as db:
            proposal = self.repository.proposal_by_key(db, household, key)
            if proposal is not None:
                if proposal["request_json"] != request:
                    raise ConflictError("Idempotency key already used with a conflicting payload.")
                return proposal  # Original snapshot retained even when today's date changes.
            now = timestamp()
            proposal = {"proposal_id": str(uuid4()), "household_id": household, "appliance_id": appliance,
                        "issue_description": issue, "warranty_evaluation_snapshot": encoded(warranty),
                        "supporting_evidence_references": encoded(warranty["source_refs"]),
                        "purchase_evidence_snapshot": encoded(evidence), "request_json": encoded(request),
                        "status": "pending", "created_at": now, "updated_at": now, "idempotency_key": key}
            self.repository.insert(db, "repair_proposals", proposal)
            self._event(db, proposal, "proposal_prepared", now)
            return self.repository.get(db, "proposal", household, proposal["proposal_id"])

    def get_repair_proposal(self, household_id: str, proposal_id: str) -> dict[str, Any]:
        with self.repository.transaction(write=False) as db:
            return self.repository.get(db, "proposal", self._context(household_id),
                                       text_input(proposal_id, "proposal_id", 80))

    def approve_repair_proposal(self, household_id: str, proposal_id: str, decision: str) -> dict[str, Any]:
        return self._decide(household_id, proposal_id, decision, "APPROVE")

    def reject_repair_proposal(self, household_id: str, proposal_id: str, decision: str) -> dict[str, Any]:
        return self._decide(household_id, proposal_id, decision, "REJECT")

    def _decide(self, household_id: str, proposal_id: str, decision: str, expected: str) -> dict[str, Any]:
        if decision != expected:
            raise InputError(f"Explicit decision must be exactly {expected}.")
        household = self._context(household_id)
        identifier = text_input(proposal_id, "proposal_id", 80)
        target = "approved" if expected == "APPROVE" else "rejected"
        with self.repository.transaction() as db:
            proposal = self.repository.get(db, "proposal", household, identifier)
            if proposal["status"] not in ("pending", target):
                raise ConflictError(f"Cannot {expected.lower()} a {proposal['status']} proposal.")
            if proposal["status"] == target:
                if target == "rejected":
                    return proposal
                case = self.repository.case_for_proposal(db, household, identifier)
                if case is None:
                    raise ConflictError("Approved proposal is missing its case; database requires inspection.")
                return case
            now = timestamp()
            self.repository.set_proposal_status(db, household, identifier, target, now)
            proposal.update(status=target, updated_at=now)
            self._event(db, proposal, f"proposal_{target}", now)
            if target == "rejected":
                return proposal
            case = {"case_id": str(uuid4()), "proposal_id": identifier, "household_id": household,
                    "appliance_id": proposal["appliance_id"], "issue_description": proposal["issue_description"],
                    "status": "open", "created_at": now, "updated_at": now}
            self.repository.insert(db, "repair_cases", case)
            self._event(db, proposal, "case_created", now, case["case_id"])
            return case

    def get_repair_case(self, household_id: str, case_id: str) -> dict[str, Any]:
        with self.repository.transaction(write=False) as db:
            return self.repository.get(db, "case", self._context(household_id), text_input(case_id, "case_id", 80))

    def list_repair_cases(self, household_id: str) -> list[dict[str, Any]]:
        with self.repository.transaction(write=False) as db:
            return self.repository.cases(db, self._context(household_id))

    def list_repair_proposals(self, household_id: str) -> list[dict[str, Any]]:
        with self.repository.transaction(write=False) as db:
            return self.repository.proposals(db, self._context(household_id))

    def get_audit_history(self, household_id: str, proposal_id: str) -> list[dict[str, Any]]:
        household = self._context(household_id)
        identifier = text_input(proposal_id, "proposal_id", 80)
        with self.repository.transaction(write=False) as db:
            self.repository.get(db, "proposal", household, identifier)
            return self.repository.events(db, household, identifier)
