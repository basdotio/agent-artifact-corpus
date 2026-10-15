import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse


class SchemaValidationError(ValueError):
    """Raised when model or evidence payloads do not satisfy the response contract."""


class Verdict(str, Enum):
    supported = "SUPPORTED"
    contradicted = "CONTRADICTED"
    unverified = "UNVERIFIED"


@dataclass(frozen=True)
class Citation:
    source: str
    url: str
    date: str
    excerpt: str

    @classmethod
    def validate(cls, payload: dict[str, Any]) -> "Citation":
        source = str(payload.get("source", "")).strip()
        url = str(payload.get("url", "")).strip()
        date = str(payload.get("date", "")).strip()
        excerpt = str(payload.get("excerpt", "")).strip()

        parsed = urlparse(url)
        if not source or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SchemaValidationError("Citation requires source and absolute URL")
        if not date:
            raise SchemaValidationError("Citation requires date")
        if not excerpt or len(excerpt) > 600:
            raise SchemaValidationError("Citation excerpt must be 1-600 characters")

        return cls(source=source, url=url, date=date, excerpt=excerpt)


@dataclass(frozen=True)
class VerdictResponse:
    verdict: Verdict
    confidence: float
    reasoning: str
    citations: list[Citation] = field(default_factory=list)

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "VerdictResponse":
        try:
            verdict = Verdict(str(payload.get("verdict", "")).strip())
        except ValueError as exc:
            raise SchemaValidationError("Unknown verdict") from exc

        confidence = float(payload.get("confidence"))
        reasoning = str(payload.get("reasoning", "")).strip()
        citations = [Citation.validate(item) for item in payload.get("citations", [])]

        if not 0.0 <= confidence <= 1.0:
            raise SchemaValidationError("Confidence must be between 0 and 1")
        if not reasoning or len(reasoning) > 1500:
            raise SchemaValidationError("Reasoning must be 1-1500 characters")
        if verdict in {Verdict.supported, Verdict.contradicted} and not citations:
            raise SchemaValidationError("SUPPORTED and CONTRADICTED verdicts require citations")

        return cls(verdict=verdict, confidence=confidence, reasoning=reasoning, citations=citations)

    @classmethod
    def model_validate_json(cls, payload: str) -> "VerdictResponse":
        return cls.model_validate(json.loads(payload))

    def model_dump(self) -> dict[str, Any]:
        data = asdict(self)
        data["verdict"] = self.verdict.value
        return data

    def model_dump_json(self, indent: int | None = None) -> str:
        return json.dumps(self.model_dump(), indent=indent)


@dataclass(frozen=True)
class EvidencePassage:
    title: str
    body: str
    source_name: str
    source_url: str
    published_date: str

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "EvidencePassage":
        return cls(
            title=str(payload.get("title", "")).strip(),
            body=str(payload.get("body", "")).strip(),
            source_name=str(payload.get("source_name", "")).strip(),
            source_url=str(payload.get("source_url", "")).strip(),
            published_date=str(payload.get("published_date", "")).strip(),
        )
