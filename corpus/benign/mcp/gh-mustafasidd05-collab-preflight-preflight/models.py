"""Core Pydantic schemas for the Preflight verification pipeline."""

from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

Ecosystem = Literal["python", "javascript", "typescript", "rust", "go", "general"]
VerdictType = Literal["CONFIRMED", "OUTDATED", "CONFLICTING", "UNVERIFIABLE"]
TrustTier = Literal[0, 1, 2, 3]

TIER_LABELS = {
    1: "Official/Registry",
    2: "Curated Community",
    3: "SEO/Tutorial Aggregator",
    0: "Untrusted/Unknown",
}


class EvidenceItem(BaseModel):
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Source URL")
    snippet: str = Field(
        ...,
        description="Sanitized excerpt wrapped in <untrusted_search_snippet> delimiters",
    )
    domain: str = Field(
        ...,
        description=(
            "Normalized full hostname (lowercase, no scheme, no port, no userinfo, "
            "no leading www.) — NOT the registrable root domain"
        ),
    )
    trust_tier: TrustTier = Field(
        ...,
        description="1=Official/Registry (1.00), 2=Community (0.75), 3=Aggregator (0.30), 0=Untrusted/Unknown (0.50)",
    )
    trust_score: float = Field(..., ge=0.0, le=1.0, description="Composite trust score, clamped to [0, 1]")
    published_date: Optional[str] = Field(None, description="Raw published-date string as returned by the search engine")
    detected_version: Optional[str] = Field(None, description="Software version detected in the evidence")
    signals: List[str] = Field(default_factory=list, description="Extracted semantic signals")


class CorrectionVariant(BaseModel):
    context: Literal["server_component", "client_component", "codemod", "generateMetadata", "route_handler"]
    code: str
    description: Optional[str] = None


class ClaimAnalysis(BaseModel):
    raw_claim: str
    inferred_ecosystem: Ecosystem
    package_name: Optional[str] = None
    symbol_name: Optional[str] = None
    claimed_version: Optional[str] = None
    target_action: Optional[str] = None
    search_queries: List[str] = Field(default_factory=list)

    @property
    def package(self) -> Optional[str]:
        return self.package_name

    @property
    def symbol(self) -> Optional[str]:
        return self.symbol_name

    @property
    def version(self) -> Optional[str]:
        return self.claimed_version

    @property
    def claim(self) -> str:
        return self.raw_claim

    @property
    def ecosystem(self) -> Ecosystem:
        return self.inferred_ecosystem


class PreflightVerdict(BaseModel):
    claim: str
    verdict: VerdictType
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str = Field(..., description="Deterministic template output; never contains web text")
    correction: Optional[str] = Field(None, description="Primary modern replacement code")
    correction_variants: List[CorrectionVariant] = Field(default_factory=list)
    canonical_reference: Optional[str] = Field(None, description="Must be https:// or it is nulled before emission")
    suggested_action: str = Field(..., description="One of the four TEMPLATE_ACTIONS values; never free text")
    evidence_count: int = Field(..., ge=0)
    top_evidence: List[EvidenceItem] = Field(default_factory=list)
    queries_executed: List[str] = Field(default_factory=list)
    is_replayed: bool = False
    response_time_ms: int = Field(..., ge=0)


class VerifyClaimRequest(BaseModel):
    claim: str = Field(..., description="The code, API, or library assertion to verify against live web docs")
    ecosystem: Optional[Ecosystem] = Field(None, description="Optional programming language or ecosystem hint")
    target_package: Optional[str] = Field(None, description="Optional package name hint (e.g., 'pydantic', 'next')")
    replay: bool = Field(False, description="Explicitly replay from recorded SerpApi cache if available")


class QuickCheckResponse(BaseModel):
    package: str
    symbol: str
    status: VerdictType
    latest_reference: Optional[str] = None
    note: Optional[str] = None
