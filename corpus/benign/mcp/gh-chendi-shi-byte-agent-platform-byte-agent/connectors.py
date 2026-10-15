"""Explicit local-file knowledge and read-only SQLite data connections.

The connector reads existing operator-provided data. It does not manufacture
observations or silently fall back to the synthetic benchmark.
"""
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileSQLiteConnector:
    knowledge_root: Path
    metrics_database: Path

    @classmethod
    def from_config(cls, config_path):
        config_path = Path(config_path).resolve()
        value = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != {"knowledge_root", "metrics_database"}:
            raise ValueError("connection config requires exactly knowledge_root and metrics_database")
        def resolve(key):
            if not isinstance(value[key], str) or not value[key]:
                raise ValueError(key + " must be a nonempty path")
            path = Path(value[key]).expanduser()
            return (config_path.parent / path).resolve() if not path.is_absolute() else path.resolve()
        connector = cls(resolve("knowledge_root"), resolve("metrics_database"))
        connector.validate()
        return connector

    def validate(self):
        if not self.knowledge_root.is_dir():
            raise ValueError("knowledge_root must be an existing directory")
        if not self.metrics_database.is_file():
            raise ValueError("metrics_database must be an existing SQLite file")
        connection = sqlite3.connect(self.metrics_database.as_uri() + "?mode=ro", uri=True)
        try:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(metrics)")}
            required = {"service", "minute", "requests", "errors", "p95_ms"}
            if not required <= columns:
                raise ValueError("metrics table requires service, minute, requests, errors, p95_ms")
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='changes'").fetchone():
                change_columns = {row[1] for row in connection.execute("PRAGMA table_info(changes)")}
                if not {"service", "kind", "recorded_minute", "summary", "status", "evidence_id"} <= change_columns:
                    raise ValueError("changes table has incompatible columns")
            invalid = connection.execute("SELECT service FROM metrics WHERE requests<0 OR errors<0 OR errors>requests OR p95_ms<0 OR requests IS NULL OR errors IS NULL OR p95_ms IS NULL OR service IS NULL OR minute IS NULL LIMIT 1").fetchone()
            if invalid:
                raise ValueError("metrics contain invalid counts or latency")
        finally:
            connection.close()
        return self

    def ingest_into(self, knowledge, embed=None):
        self.validate()
        return knowledge.ingest(self.knowledge_root, embed)


def load_sources(config_path):
    """Load and validate a connection without writing to its source database."""
    return FileSQLiteConnector.from_config(config_path)
