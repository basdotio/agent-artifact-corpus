"""
Curated registry of trusted developer domains and ecosystem heuristics.
Explicit-host trust registry. Exact-host match for Tier 1; bounded subdomain
inheritance for Tier 2/3 only. Everything else is Tier 0 (untrusted).
"""

from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse

from preflight.models import Ecosystem, TrustTier

TIER_1_EXACT_HOSTS: Set[str] = {
    # Package Registries
    "pypi.org",
    "npmjs.com",
    "crates.io",
    "pkg.go.dev",
    "rubygems.org",
    "packagist.org",
    "nuget.org",

    # Language Specifications & Core Docs
    "docs.python.org",
    "developer.mozilla.org",
    "typescriptlang.org",
    "nodejs.org",
    "go.dev",
    "rust-lang.org",
    "docs.rs",

    # Major Framework Documentation
    "docs.pydantic.dev",
    "pydantic-docs.helpmanual.io",
    "fastapi.tiangolo.com",
    "flask.palletsprojects.com",
    "docs.djangoproject.com",
    "requests.readthedocs.io",
    "sqlalchemy.org",
    "pandas.pydata.org",
    "numpy.org",
    "scipy.org",
    "pytest.org",
    "nextjs.org",
    "react.dev",
    "reactjs.org",
    "vuejs.org",
    "angular.dev",
    "svelte.dev",
    "expressjs.com",
    "tailwindcss.com",
    "python.langchain.com",
    "js.langchain.com",
    "platform.openai.com",
    "docs.anthropic.com",
    "ai.google.dev",
}

TIER_2_EXACT_HOSTS: Set[str] = {
    "github.com",
    "gitlab.com",
    "stackoverflow.com",
    "stackexchange.com",
    "news.ycombinator.com",
    "dev.to",
    "reddit.com",
}

TIER_3_EXACT_HOSTS: Set[str] = {
    "geeksforgeeks.org",
    "w3schools.com",
    "tutorialspoint.com",
    "medium.com",
    "javatpoint.com",
    "freecodecamp.org",
    "towardsdatascience.com",
}

# Compatibility aliases
TIER_1_DOMAINS = TIER_1_EXACT_HOSTS
TIER_2_DOMAINS = TIER_2_EXACT_HOSTS
TIER_3_DOMAINS = TIER_3_EXACT_HOSTS

TIER_1_SCORE = 1.00
TIER_2_SCORE = 0.75
TIER_3_SCORE = 0.30
UNTRUSTED_SCORE = 0.50

# Ecosystem keyword indicators
ECOSYSTEM_SIGNALS: Dict[Ecosystem, List[str]] = {
    "python": [
        "python", "pip", "pypi", "def ", "import ", "from ", "class ",
        "pydantic", "fastapi", "django", "flask", "requests", "pandas",
        "numpy", "asyncio", "pytest", "sqlalchemy", "celery", "poetry"
    ],
    "javascript": [
        "javascript", "js", "npm", "yarn", "pnpm", "node", "nodejs",
        "const ", "let ", "function", "require(", "import from",
        "react", "vue", "svelte", "express", "lodash", "axios"
    ],
    "typescript": [
        "typescript", "ts", "interface ", "type ", "<T>", "as const",
        "nextjs", "next.js", "nest.js", "prisma", "zod", "trpc"
    ],
    "rust": [
        "rust", "cargo", "crates.io", "fn ", "impl ", "trait ",
        "struct ", "pub ", "tokio", "actix", "serde", "axum"
    ],
    "go": [
        "golang", "go get", "pkg.go.dev", "func ", "goroutine",
        "struct {", "gin", "gorm", "echo", "fiber"
    ],
    "general": []
}


def normalize_host(url_or_host: str) -> str:
    """Return the normalized full hostname: lowercase, no scheme, no userinfo,
    no port, no trailing dot, no leading 'www.'. This is the value stored in
    EvidenceItem.domain and the value get_domain_tier() matches against."""
    raw = (url_or_host or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = parsed.netloc or parsed.path.split("/")[0]
    host = host.rsplit("@", 1)[-1]  # drop userinfo
    host = host.split(":", 1)[0]  # drop port
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[len("www."):]
    return host


def _is_same_or_subdomain(host: str, base: str) -> bool:
    """Boundary-safe subdomain test. 'notstackoverflow.com' must NOT match
    base 'stackoverflow.com'; 'gist.github.com' must."""
    return host == base or host.endswith("." + base)


def get_domain_tier(domain: str) -> Tuple[TrustTier, float]:
    """
    Returns (tier, base_trust_score) for a given domain/URL.
    Tier 1 is exact-host only. No prefix/suffix rules, no subdomain inheritance.
    Tier 2 and 3 support boundary-safe subdomain inheritance.
    Everything else is Tier 0 (untrusted).
    """
    host = normalize_host(domain)

    if host in TIER_1_EXACT_HOSTS:
        return 1, TIER_1_SCORE

    for base in TIER_2_EXACT_HOSTS:
        if _is_same_or_subdomain(host, base):
            return 2, TIER_2_SCORE

    for base in TIER_3_EXACT_HOSTS:
        if _is_same_or_subdomain(host, base):
            return 3, TIER_3_SCORE

    # Everything else — including unlisted *.github.io, *.readthedocs.io, *.gitbook.io
    # is untrusted (Tier 0).
    return 0, UNTRUSTED_SCORE


def get_domain_weight(domain: str) -> float:
    """Convenience helper returning just the trust weight float (0.0 to 1.0)."""
    return get_domain_tier(domain)[1]
