"""
Audit Logger

Enterprise-grade audit logging with tamper-evident capabilities.

Features:
- Structured JSON logging
- Cryptographic signatures for tamper detection
- Log rotation with configurable retention
- Compliance-ready output (SOC2, ISO27001, HIPAA)
"""

import hashlib
import hmac
import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any
import uuid


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Connection events
    CONNECTION_OPENED = "connection_opened"
    CONNECTION_CLOSED = "connection_closed"
    CONNECTION_FAILED = "connection_failed"

    # Query events
    QUERY_SUBMITTED = "query_submitted"
    QUERY_EXECUTED = "query_executed"
    QUERY_FAILED = "query_failed"

    # LLM events
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    LLM_ERROR = "llm_error"

    # Security events
    PII_DETECTED = "pii_detected"
    POLICY_VIOLATION = "policy_violation"
    ACCESS_DENIED = "access_denied"
    DATA_BOUNDARY_VIOLATION = "data_boundary_violation"

    # System events
    SERVER_STARTED = "server_started"
    SERVER_STOPPED = "server_stopped"
    VALIDATION_RUN = "validation_run"
    CONFIG_CHANGED = "config_changed"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Individual audit event."""
    event_type: AuditEventType
    severity: AuditSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    # Data (should never contain PII or actual data)
    details: dict = field(default_factory=dict)

    # For tamper detection
    previous_hash: Optional[str] = None
    signature: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "signature": self.signature,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Enterprise audit logger with tamper-evident capabilities.

    All operations are logged for compliance and security review.
    Logs are cryptographically signed to detect tampering.
    """

    def __init__(
        self,
        log_directory: str = "./logs/audit",
        signing_key: Optional[str] = None,
        max_file_size_mb: int = 10,
        max_files: int = 100,
        sign_entries: bool = True,
    ):
        """
        Initialize the audit logger.

        Args:
            log_directory: Directory for audit logs
            signing_key: Key for HMAC signatures (generated if not provided)
            max_file_size_mb: Maximum size per log file
            max_files: Maximum number of log files to retain
            sign_entries: Whether to sign each entry
        """
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

        self.signing_key = (signing_key or os.urandom(32).hex()).encode()
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.max_files = max_files
        self.sign_entries = sign_entries

        self._lock = threading.Lock()
        self._current_file: Optional[Path] = None
        self._previous_hash: Optional[str] = None
        self._event_count = 0

        # Initialize with server start event
        self._initialize_log()

    def _initialize_log(self) -> None:
        """Initialize a new log file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self._current_file = self.log_directory / f"audit_{timestamp}.jsonl"

        # Write header
        header = {
            "log_version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "server_version": "3.0.0",
            "signing_enabled": self.sign_entries,
        }

        with open(self._current_file, "w") as f:
            f.write(json.dumps(header) + "\n")

        self._previous_hash = self._hash_content(json.dumps(header))

    def log(
        self,
        event_type: AuditEventType,
        message: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            severity: Event severity
            user_id: Optional user identifier
            session_id: Optional session identifier
            request_id: Optional request identifier
            details: Additional details (must not contain PII)

        Returns:
            The logged AuditEvent
        """
        with self._lock:
            # Create event
            event = AuditEvent(
                event_type=event_type,
                severity=severity,
                message=message,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                details=details or {},
                previous_hash=self._previous_hash,
            )

            # Sign the event
            if self.sign_entries:
                event.signature = self._sign_event(event)

            # Write to file
            self._write_event(event)

            # Update chain
            self._previous_hash = self._hash_content(event.to_json())
            self._event_count += 1

            # Check if rotation needed
            self._check_rotation()

            return event

    def _sign_event(self, event: AuditEvent) -> str:
        """Generate HMAC signature for event."""
        # Create canonical string for signing (excludes signature field)
        canonical = json.dumps({
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "message": event.message,
            "previous_hash": event.previous_hash,
        }, sort_keys=True)

        signature = hmac.new(
            self.signing_key,
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _write_event(self, event: AuditEvent) -> None:
        """Write event to log file."""
        if not self._current_file:
            self._initialize_log()

        with open(self._current_file, "a") as f:
            f.write(event.to_json() + "\n")

    def _check_rotation(self) -> None:
        """Check if log rotation is needed."""
        if not self._current_file or not self._current_file.exists():
            return

        if self._current_file.stat().st_size >= self.max_file_size:
            self._rotate_logs()

    def _rotate_logs(self) -> None:
        """Rotate log files."""
        # Get all log files
        log_files = sorted(
            self.log_directory.glob("audit_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Delete excess files
        while len(log_files) >= self.max_files:
            oldest = log_files.pop()
            oldest.unlink()

        # Start new log
        self._initialize_log()

    def verify_integrity(self, log_file: Optional[Path] = None) -> dict:
        """
        Verify the integrity of a log file.

        Checks the hash chain and signatures to detect tampering.

        Args:
            log_file: Log file to verify (defaults to current)

        Returns:
            Dictionary with verification results
        """
        target_file = log_file or self._current_file
        if not target_file or not target_file.exists():
            return {"valid": False, "error": "Log file not found"}

        results = {
            "file": str(target_file),
            "valid": True,
            "events_checked": 0,
            "signature_failures": [],
            "chain_failures": [],
        }

        previous_hash = None

        with open(target_file, "r") as f:
            for i, line in enumerate(f):
                try:
                    data = json.loads(line)

                    # Skip header
                    if "log_version" in data:
                        previous_hash = self._hash_content(line.strip())
                        continue

                    results["events_checked"] += 1

                    # Verify hash chain
                    if data.get("previous_hash") != previous_hash:
                        results["chain_failures"].append(i)
                        results["valid"] = False

                    # Verify signature
                    if self.sign_entries and data.get("signature"):
                        expected_sig = self._compute_signature_for_verification(data)
                        if data["signature"] != expected_sig:
                            results["signature_failures"].append(i)
                            results["valid"] = False

                    previous_hash = self._hash_content(line.strip())

                except json.JSONDecodeError:
                    results["valid"] = False
                    results["error"] = f"Invalid JSON at line {i}"
                    break

        return results

    def _compute_signature_for_verification(self, data: dict) -> str:
        """Recompute signature for verification."""
        canonical = json.dumps({
            "event_id": data["event_id"],
            "event_type": data["event_type"],
            "timestamp": data["timestamp"],
            "message": data["message"],
            "previous_hash": data["previous_hash"],
        }, sort_keys=True)

        return hmac.new(
            self.signing_key,
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()

    # Convenience methods for common events

    def log_query(
        self,
        query: str,
        request_id: str,
        user_id: Optional[str] = None,
        tables_accessed: Optional[list[str]] = None,
    ) -> AuditEvent:
        """Log a query execution."""
        return self.log(
            event_type=AuditEventType.QUERY_EXECUTED,
            message="DAX query executed",
            request_id=request_id,
            user_id=user_id,
            details={
                "query_hash": self._hash_content(query)[:16],
                "query_length": len(query),
                "tables_accessed": tables_accessed or [],
            },
        )

    def log_llm_request(
        self,
        request_id: str,
        provider: str,
        schema_hash: str,
        user_intent: str,
    ) -> AuditEvent:
        """Log an LLM request."""
        return self.log(
            event_type=AuditEventType.LLM_REQUEST,
            message="LLM inference request",
            request_id=request_id,
            details={
                "provider": provider,
                "schema_hash": schema_hash,
                "intent_length": len(user_intent),
                "data_included": False,  # Always false - schema only
            },
        )

    def log_llm_response(
        self,
        request_id: str,
        provider: str,
        latency_ms: float,
        tokens: Optional[int] = None,
    ) -> AuditEvent:
        """Log an LLM response."""
        return self.log(
            event_type=AuditEventType.LLM_RESPONSE,
            message="LLM inference completed",
            request_id=request_id,
            details={
                "provider": provider,
                "latency_ms": latency_ms,
                "tokens": tokens,
            },
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        message: str,
        request_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditEvent:
        """Log a security event."""
        return self.log(
            event_type=event_type,
            message=message,
            severity=AuditSeverity.WARNING,
            request_id=request_id,
            details=details,
        )

    def get_stats(self) -> dict:
        """Get audit log statistics."""
        log_files = list(self.log_directory.glob("audit_*.jsonl"))
        total_size = sum(f.stat().st_size for f in log_files)

        return {
            "log_directory": str(self.log_directory),
            "current_file": str(self._current_file) if self._current_file else None,
            "total_files": len(log_files),
            "total_size_bytes": total_size,
            "events_in_session": self._event_count,
            "signing_enabled": self.sign_entries,
        }
