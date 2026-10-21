"""Evidence storage: JSON-based, auditable, git-diffable."""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from fathom.models import EvidenceRecord


class EvidenceStore:
    """
    File-based evidence persistence.
    Each run → one JSON file (auditable, git-diffable).
    Index file for quick lookups.
    """

    def __init__(self, evidence_dir: str = ".fathom_evidence"):
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(exist_ok=True)
        self.index_file = self.evidence_dir / "index.json"

    def _load_index(self) -> dict:
        """Load or create index."""
        if self.index_file.exists():
            with open(self.index_file) as f:
                return json.load(f)
        return {"records": []}

    def _save_index(self, index: dict) -> None:
        """Save index."""
        with open(self.index_file, "w") as f:
            json.dump(index, f, indent=2, default=str)

    def save_evidence(self, evidence: EvidenceRecord) -> str:
        """
        Save evidence record to JSON file.
        Returns file path.
        """
        record_file = self.evidence_dir / f"{evidence.id}.json"

        with open(record_file, "w") as f:
            json.dump(
                json.loads(evidence.model_dump_json()),
                f,
                indent=2,
                default=str,
            )

        # Update index
        index = self._load_index()
        index["records"].append({
            "id": evidence.id,
            "system_id": evidence.system_profile.system_id,
            "skill_id": evidence.skill_result.skill_id,
            "created_at": str(evidence.created_at),
            "file": str(record_file),
        })
        self._save_index(index)

        return str(record_file)

    def load_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Load a single evidence record."""
        record_file = self.evidence_dir / f"{evidence_id}.json"
        if not record_file.exists():
            return None

        with open(record_file) as f:
            data = json.load(f)

        return EvidenceRecord.model_validate(data)

    def load_all_evidence(self, system_id: Optional[str] = None) -> list[EvidenceRecord]:
        """Load all evidence, optionally filtered by system."""
        index = self._load_index()
        evidence_list = []

        for entry in index.get("records", []):
            if system_id and entry["system_id"] != system_id:
                continue

            record = self.load_evidence(entry["id"])
            if record:
                evidence_list.append(record)

        return evidence_list

    def clear_evidence(self) -> None:
        """Clear all evidence (for testing)."""
        import shutil
        if self.evidence_dir.exists():
            shutil.rmtree(self.evidence_dir)
        self.evidence_dir.mkdir()
