"""
Query formulation engine for Preflight.
Translates unstructured technical claims into targeted search queries.
"""

import re
from typing import Optional, List, Tuple
from preflight.models import ClaimAnalysis, Ecosystem
from preflight.trusted_domains import ECOSYSTEM_SIGNALS


# Common package name extraction patterns
PACKAGE_PATTERNS = [
    r"(?:in|for|from|import|package|library|module|using|with)\s+([a-zA-Z0-9_\-\.]+)",
    r"([a-zA-Z0-9_\-]+)\s+(?:library|package|module|framework|sdk|version|v\d+)",
    r"`([a-zA-Z0-9_\-\.]+)`",
]

SYMBOL_PATTERNS = [
    r"[`'\"]([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)[`'\"]",
    r"`([a-zA-Z0-9_]+(?:\(\))?)`",
    r"\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\b",  # dotted symbols (e.g. session.verify, Session.get)
    r"\b([a-zA-Z]+_[a-zA-Z0-9_]+)\b",  # snake_case symbols/methods (e.g. on_event, lifespan_handler)
    r"\b([a-z]+[A-Z][a-zA-Z0-9_]*)\b",  # camelCase functions/hooks (e.g. forwardRef, useState)
    r"\b([A-Z][a-zA-Z0-9_]+)\b",  # PascalCase class names (e.g. BaseSettings)
    r"(?:method|function|class|symbol|attribute|parameter|kwarg|argument|property|hook|component|prop)\s+[`'\"]?([a-zA-Z0-9_\.]+)[`'\"]?",
]

# Version patterns (e.g. v2, v2.0, 15, 2.32)
VERSION_PATTERNS = [
    r"\b(?:version|v)\s*([0-9]+(?:\.[0-9]+)*)\b",
    r"\b([0-9]+(?:\.[0-9]+)+)\b",
    r"\bNext\.?js\s*([0-9]+)\b",
    r"\bPydantic\s*v?([0-9]+)\b",
    r"\bReact\s*([0-9]+)\b",
]

# Well-known package canonical documentation map
CANONICAL_DOC_SITES = {
    "pydantic": "site:docs.pydantic.dev OR site:pypi.org/project/pydantic",
    "fastapi": "site:fastapi.tiangolo.com OR site:pypi.org/project/fastapi",
    "requests": "site:requests.readthedocs.io OR site:pypi.org/project/requests",
    "django": "site:docs.djangoproject.com",
    "flask": "site:flask.palletsprojects.com",
    "next": "site:nextjs.org/docs",
    "nextjs": "site:nextjs.org/docs",
    "next.js": "site:nextjs.org/docs",
    "react": "site:react.dev",
    "vue": "site:vuejs.org",
    "langchain": "site:python.langchain.com OR site:js.langchain.com",
    "openai": "site:platform.openai.com/docs OR site:pypi.org/project/openai",
    "anthropic": "site:docs.anthropic.com OR site:pypi.org/project/anthropic",
    "tailwindcss": "site:tailwindcss.com/docs",
    "prisma": "site:prisma.io/docs",
    "zod": "site:zod.dev OR site:npmjs.com/package/zod",
}


class QueryEngine:
    """Decomposes code claims into precise multi-vector search queries."""

    @staticmethod
    def infer_ecosystem(claim: str, hint: Optional[Ecosystem] = None) -> Ecosystem:
        """Infer programming language/ecosystem from claim content."""
        if hint and hint != "general":
            return hint

        claim_lower = claim.lower()
        scores: dict[Ecosystem, int] = {eco: 0 for eco in ECOSYSTEM_SIGNALS}

        for eco, signals in ECOSYSTEM_SIGNALS.items():
            for sig in signals:
                if sig in claim_lower:
                    scores[eco] += 1

        best_eco, best_score = max(scores.items(), key=lambda item: item[1])
        return best_eco if best_score > 0 else "general"

    @classmethod
    def extract_package(cls, claim: str, hint: Optional[str] = None) -> Optional[str]:
        """Extract primary target package name."""
        if hint and hint.strip():
            return hint.strip().lower()

        # Check against known packages
        claim_lower = claim.lower()
        for known in CANONICAL_DOC_SITES:
            # Word boundary check
            if re.search(r"\b" + re.escape(known) + r"\b", claim_lower):
                return known

        # Fallback to regex matches
        for pattern in PACKAGE_PATTERNS:
            match = re.search(pattern, claim, re.IGNORECASE)
            if match:
                pkg = match.group(1).strip().lower()
                # filter false positives like common english words
                if pkg not in {"the", "a", "an", "this", "that", "latest", "version", "new"}:
                    return pkg

        return None

    STOPWORDS = {
        "in", "the", "a", "an", "is", "for", "with", "when", "using", "how", "to",
        "if", "not", "but", "and", "or", "from", "on", "at", "by", "as", "into",
        "true", "false", "none", "null", "all", "any", "this", "that", "these",
        "those", "what", "which", "where", "why", "there", "here", "can", "could",
        "should", "would", "must", "will", "may", "might", "new", "old", "latest",
        # Language names shouldn't be extracted as symbols
        "python", "javascript", "typescript", "rust", "golang", "java", "ruby", "c++",
    }

    @classmethod
    def extract_symbol(cls, claim: str, package: Optional[str] = None) -> Optional[str]:
        """Extract function, method, class, or parameter symbol."""
        pkg_lower = package.lower() if package else ""
        for pattern in SYMBOL_PATTERNS:
            for match in re.finditer(pattern, claim):
                symbol = match.group(1).strip()
                s_lower = symbol.lower()
                if s_lower in cls.STOPWORDS:
                    continue
                if pkg_lower and (s_lower == pkg_lower or s_lower in pkg_lower):
                    continue
                # If it's a generic word like "Version" or "Package", skip
                if s_lower in {"version", "package", "library", "module", "code", "file", "method", "function", "class"}:
                    continue
                return symbol
        return None

    @classmethod
    def extract_version(cls, claim: str) -> Optional[str]:
        """Extract target version number if stated."""
        for pattern in VERSION_PATTERNS:
            match = re.search(pattern, claim, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def analyze_claim(
        cls,
        claim: str,
        ecosystem_hint: Optional[Ecosystem] = None,
        package_hint: Optional[str] = None,
    ) -> ClaimAnalysis:
        """Deconstruct claim and produce a set of targeted search queries."""
        ecosystem = cls.infer_ecosystem(claim, ecosystem_hint)
        package = cls.extract_package(claim, package_hint)
        symbol = cls.extract_symbol(claim, package=package)
        version = cls.extract_version(claim)

        queries: List[str] = []

        # Vector 1: Canonical documentation & registry
        if package and package in CANONICAL_DOC_SITES:
            doc_filter = CANONICAL_DOC_SITES[package]
            sym_part = f'"{symbol}"' if symbol else ""
            ver_part = f"v{version}" if version else ""
            queries.append(f"{doc_filter} {sym_part} {ver_part}".strip())
        elif package:
            sym_part = f'"{symbol}"' if symbol else ""
            eco_tag = f"site:pypi.org OR site:npmjs.com" if ecosystem in ("python", "javascript", "typescript") else ""
            queries.append(f'"{package}" documentation {sym_part} {eco_tag}'.strip())
        else:
            queries.append(f"{claim} official documentation")

        # Vector 2: Deprecation / breaking change / migration
        if package and symbol:
            queries.append(f'"{package}" "{symbol}" (deprecated OR removed OR "breaking change" OR "migration guide")')
        elif package:
            ver_str = f"v{version}" if version else "latest"
            queries.append(f'"{package}" {ver_str} (deprecated OR removed OR "breaking changes")')
        else:
            queries.append(f"{claim} deprecated OR removed OR breaking change")

        # Vector 3: API signature / usage verification
        if package and symbol:
            queries.append(f'"{package}" "{symbol}" usage example')
        elif package:
            queries.append(f'"{package}" API reference')

        return ClaimAnalysis(
            raw_claim=claim,
            inferred_ecosystem=ecosystem,
            package_name=package,
            symbol_name=symbol,
            claimed_version=version,
            search_queries=queries,
        )
