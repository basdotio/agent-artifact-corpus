"""
Verdict synthesizer for Preflight.
Combines weighted evidence, detects semantic signals, and produces the final PreflightVerdict.
"""

import re
import time
from typing import List, Optional, Tuple, Dict
from preflight.models import PreflightVerdict, EvidenceItem, ClaimAnalysis, VerdictType, CorrectionVariant
from preflight.ranker import unwrap_untrusted

TEMPLATE_ACTIONS: Dict[VerdictType, str] = {
    "CONFIRMED": "Proceed with this implementation. The syntax and usage are verified against authoritative documentation.",
    "OUTDATED": "Do not use this deprecated pattern. Update your implementation to the recommended correction.",
    "CONFLICTING": "Check your targeted major library version explicitly before finalizing implementation.",
    "UNVERIFIABLE": "Verify syntax against the official repository directly or test in an isolated sandbox.",
}

_STOPWORDS = {
    "the", "a", "an", "this", "our", "their", "new", "instead",
    "to", "from", "and", "or", "in", "it", "with",
}
_FALLBACK_RE = re.compile(r"(?:use|moved to|renamed to|replaced with)\s+([a-zA-Z0-9_\-\.]+)")


def extract_correction_symbol(text: str) -> Optional[str]:
    """Fallback correction extraction. Returns None on English filler."""
    m = _FALLBACK_RE.search(text or "")
    if not m:
        return None
    val = m.group(1).strip().strip(".")
    if not val or not re.fullmatch(r"[a-zA-Z0-9_\.\-]+", val):
        return None
    if val.lower() in _STOPWORDS:
        return None
    return val


def build_summary(verdict: str, evidence: List[EvidenceItem], deprecate_score: float, confirm_score: float) -> str:
    """Deterministic template output. Untrusted web text never enters this string."""
    tier1_count = sum(1 for e in evidence if e.trust_tier == 1)
    return (
        f"{verdict}: Verified against {len(evidence)} sources ({tier1_count} authoritative Tier-1). "
        f"Deprecation signal score: {deprecate_score:.2f}, Confirmation signal score: {confirm_score:.2f}."
    )


def guard_canonical_reference(url: Optional[str]) -> Optional[str]:
    """Enforces strict https:// scheme on canonical URLs."""
    if url and url.lower().startswith("https://"):
        return url
    return None


def build_nextjs_15_corrections() -> Tuple[str, List[CorrectionVariant]]:
    """Verified against https://nextjs.org/docs/messages/sync-dynamic-apis:
    params/searchParams are async Promises; await on server, use() in client
    components wrapped in Suspense; codemod provided for automated migration."""
    server_code = (
        "export default async function Page({ params }: { params: Promise<{ id: string }> }) {\n"
        "  const { id } = await params;\n"
        "  return <div>Item ID: {id}</div>;\n"
        "}"
    )
    metadata_code = (
        "export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {\n"
        "  const { id } = await params;\n"
        "  return { title: `Item ${id}` };\n"
        "}"
    )
    route_handler_code = (
        "export async function GET(\n"
        "  request: Request,\n"
        "  { params }: { params: Promise<{ id: string }> }\n"
        ") {\n"
        "  const { id } = await params;\n"
        "  return Response.json({ id });\n"
        "}"
    )
    client_code = (
        "'use client';\n"
        "import { use, Suspense } from 'react';\n\n"
        "function ItemContent({ params }: { params: Promise<{ id: string }> }) {\n"
        "  const { id } = use(params);\n"
        "  return <div>Item ID: {id}</div>;\n"
        "}\n\n"
        "export default function Page({ params }: { params: Promise<{ id: string }> }) {\n"
        "  return (\n"
        "    <Suspense fallback={<div>Loading...</div>}>\n"
        "      <ItemContent params={params} />\n"
        "    </Suspense>\n"
        "  );\n"
        "}"
    )
    codemod_code = "npx @next/codemod@canary next-async-request-api ."

    variants = [
        CorrectionVariant(
            context="server_component",
            code=server_code,
            description="Server Component: await the params promise",
        ),
        CorrectionVariant(
            context="generateMetadata",
            code=metadata_code,
            description="Metadata API receives params as a Promise",
        ),
        CorrectionVariant(
            context="route_handler",
            code=route_handler_code,
            description="Route handlers receive params as a Promise",
        ),
        CorrectionVariant(
            context="client_component",
            code=client_code,
            description="Client Component: use(params) inside a Suspense boundary",
        ),
        CorrectionVariant(
            context="codemod",
            code=codemod_code,
            description="Official automated migration",
        ),
    ]
    return server_code, variants


class VerdictSynthesizer:
    """Synthesizes ranked search evidence into a structured verdict."""

    @classmethod
    def extract_correction(cls, claim: str, evidence_list: List[EvidenceItem]) -> Tuple[Optional[str], List[CorrectionVariant]]:
        """Extract recommended modern replacement code and context variants."""
        claim_lower = claim.lower()

        # Specific high-value heuristic for Next.js 15 params
        if "next" in claim_lower and "params" in claim_lower:
            return build_nextjs_15_corrections()

        for ev in evidence_list[:5]:
            raw_snippet = unwrap_untrusted(ev.snippet)
            text = f"{ev.title} {raw_snippet}"
            text_lower = text.lower()

            # Specific high-value heuristic for Pydantic v2
            if "pydantic" in claim_lower and "basesettings" in claim_lower:
                if "pydantic_settings" in text_lower or "pydantic-settings" in text_lower:
                    code = "from pydantic_settings import BaseSettings"
                    return code, [CorrectionVariant(context="server_component", code=code, description="Pydantic Settings library import")]

            # Specific high-value heuristic for React 19 forwardRef
            if "react" in claim_lower and "forwardref" in claim_lower:
                if "prop" in text_lower or "deprecated" in text_lower:
                    code = "In React 19, `ref` can be passed directly as a standard component prop without wrapping in `forwardRef`"
                    return code, [CorrectionVariant(context="client_component", code=code, description="React 19 direct ref prop")]

            # Specific high-value heuristic for FastAPI lifespan / on_event
            if "fastapi" in claim_lower and ("on_event" in claim_lower or "lifespan" in claim_lower or "startup" in claim_lower):
                if "lifespan" in text_lower:
                    code = "@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    yield\n\napp = FastAPI(lifespan=lifespan)"
                    return code, [CorrectionVariant(context="server_component", code=code, description="FastAPI lifespan context manager")]

            # General regex extraction with stopword filtering
            sym = extract_correction_symbol(text)
            if sym:
                code = f"from {sym} import ..." if "_" in sym else f"Use `{sym}` instead"
                return code, [CorrectionVariant(context="server_component", code=code, description=f"Recommended replacement: {sym}")]

        return None, []

    @classmethod
    def synthesize(
        cls,
        claim: str,
        analysis: ClaimAnalysis,
        evidence: List[EvidenceItem],
        queries_executed: List[str],
        start_time_ns: int,
        is_replayed: bool = False,
        unverifiable_missing_key: bool = False,
        api_error: Optional[str] = None,
        fixture_missing: bool = False,
    ) -> PreflightVerdict:
        """Evaluate evidence and return a complete PreflightVerdict."""
        elapsed_ms = int((time.perf_counter_ns() - start_time_ns) / 1_000_000)

        # Handle explicit API error
        if api_error:
            return PreflightVerdict(
                claim=claim,
                verdict="UNVERIFIABLE",
                confidence=0.0,
                summary=f"UNVERIFIABLE: Live SerpApi query failed: {api_error}",
                correction=None,
                correction_variants=[],
                canonical_reference="https://serpapi.com/manage-api-key",
                suggested_action=TEMPLATE_ACTIONS["UNVERIFIABLE"],
                evidence_count=0,
                top_evidence=[],
                queries_executed=queries_executed,
                is_replayed=False,
                response_time_ms=elapsed_ms,
            )

        # Handle missing key in live mode (loud & explicit)
        if unverifiable_missing_key:
            return PreflightVerdict(
                claim=claim,
                verdict="UNVERIFIABLE",
                confidence=0.0,
                summary="UNVERIFIABLE: No SERPAPI_API_KEY set and replay mode was not requested.",
                correction=None,
                correction_variants=[],
                canonical_reference="https://serpapi.com/manage-api-key",
                suggested_action=TEMPLATE_ACTIONS["UNVERIFIABLE"],
                evidence_count=0,
                top_evidence=[],
                queries_executed=queries_executed,
                is_replayed=False,
                response_time_ms=elapsed_ms,
            )

        # Handle missing fixture in replay mode
        if fixture_missing and not evidence:
            return PreflightVerdict(
                claim=claim,
                verdict="UNVERIFIABLE",
                confidence=0.0,
                summary="UNVERIFIABLE: No pre-recorded SerpApi fixture exists for this claim in replay mode.",
                correction=None,
                correction_variants=[],
                canonical_reference="https://serpapi.com",
                suggested_action=TEMPLATE_ACTIONS["UNVERIFIABLE"],
                evidence_count=0,
                top_evidence=[],
                queries_executed=queries_executed,
                is_replayed=True,
                response_time_ms=elapsed_ms,
            )

        if not evidence:
            return PreflightVerdict(
                claim=claim,
                verdict="UNVERIFIABLE",
                confidence=0.2,
                summary=build_summary("UNVERIFIABLE", [], 0.0, 0.0),
                correction=None,
                correction_variants=[],
                canonical_reference=None,
                suggested_action=TEMPLATE_ACTIONS["UNVERIFIABLE"],
                evidence_count=0,
                top_evidence=[],
                queries_executed=queries_executed,
                is_replayed=is_replayed,
                response_time_ms=elapsed_ms,
            )

        # Calculate signal scores weighted by domain trust
        deprecate_score = 0.0
        confirm_score = 0.0

        for item in evidence:
            dep_count = sum(1 for s in item.signals if s.startswith("deprecation:"))
            conf_count = sum(1 for s in item.signals if s.startswith("confirmation:"))

            weight = item.trust_score
            deprecate_score += dep_count * weight
            confirm_score += conf_count * weight

            if item.trust_tier == 1:
                confirm_score += 0.5 * weight

        # Canonical reference must prefer authoritative Tier 1 source, falling back to top evidence
        raw_canonical = next((e.url for e in evidence if e.trust_tier == 1), evidence[0].url if evidence else None)
        canonical_ref = guard_canonical_reference(raw_canonical)
        correction, variants = cls.extract_correction(claim, evidence)

        # Check if claim asserts deprecation
        claim_lower = claim.lower()
        claim_asserts_deprecation = any(
            w in claim_lower
            for w in ["deprecated", "replaced", "obsolete", "removed", "replacement", "no longer"]
        )

        # Decision Thresholds
        if deprecate_score >= 1.0 and (deprecate_score > confirm_score * 0.8 or claim_asserts_deprecation):
            if claim_asserts_deprecation:
                verdict: VerdictType = "CONFIRMED"
                confidence = min(0.98, max(0.85, 0.75 + (deprecate_score * 0.08)))
            else:
                verdict = "OUTDATED"
                confidence = min(0.98, max(0.80, 0.70 + (deprecate_score * 0.08)))

        elif confirm_score >= 1.0 and deprecate_score < 0.8:
            verdict = "CONFIRMED"
            confidence = min(0.96, max(0.75, 0.70 + (confirm_score * 0.06)))

        elif deprecate_score >= 0.8 and confirm_score >= 0.8:
            verdict = "CONFLICTING"
            confidence = 0.65

        else:
            verdict = "UNVERIFIABLE"
            confidence = 0.40

        # Deterministic summary & suggested_action
        summary = build_summary(verdict, evidence, deprecate_score, confirm_score)
        suggested_action = TEMPLATE_ACTIONS[verdict]

        should_emit_correction = verdict == "OUTDATED" or claim_asserts_deprecation

        return PreflightVerdict(
            claim=claim,
            verdict=verdict,
            confidence=round(confidence, 2),
            summary=summary,
            correction=correction if should_emit_correction else None,
            correction_variants=variants if should_emit_correction else [],
            canonical_reference=canonical_ref,
            suggested_action=suggested_action,
            evidence_count=len(evidence),
            top_evidence=evidence[:4],
            queries_executed=queries_executed,
            is_replayed=is_replayed,
            response_time_ms=elapsed_ms,
        )
