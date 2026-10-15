"""Resolve which release of a data source a result came from.

Without this, replay can tell you a result changed but not why. With it you get
"OT 26.06 -> OT 26.09", which is the difference between an alarm and an
explanation.

Best-effort by design. Return None rather than guess — a wrong release string is
worse than a missing one. Resolution is a side channel (a separate HTTP call to
the source's own metadata endpoint), so it says what release the source was
serving *around* the time of the call, not what the downstream MCP server used.
A server that caches or bundles data can be behind the live release; that is a
property of the server, and exactly what replay would surface.

Presets. Every one below was verified against the live endpoint on 2026-09-20;
the example is what it returned that day. If an endpoint changes shape the
resolver returns None and logs, it does not invent.

  Preset          Mechanism                                       Example
  --------------  ----------------------------------------------  ------------------------------
  geo             NCBI einfo dbbuild, db=gds                      GEO gds Build260919-1942.1
  eutils          NCBI einfo dbbuild for any db (source_options.db)
                    pubmed                                        PubMed Build-2026.09.20.06.18
                    clinvar                                       ClinVar Build260914-0050.1
  opentargets     GraphQL meta.dataVersion                        OT 26.06
  clinicaltrials  API v2 /version dataTimestamp                   CT.gov 2026-09-18T09:00:04
  uniprot         X-UniProt-Release response header               UniProt 2026_03
  ensembl         REST /info/data releases[0]                     Ensembl 116
  chembl          /chembl/api/data/status chembl_db_version       ChEMBL_37
  string          /api/json/version string_version                STRING 12.0
  reactome        ContentService /data/database/version           Reactome 97
  hgnc            /info lastModified                              HGNC 2026-09-18T12:19:06.043Z
  ols             OLS4 ontology config.version (source_options.ontology)
                    mondo                                         mondo 2026-09-01
                    go                                            go 2026-07-26
  kegg            /info/<db> "Last update" line (source_options.db, default pathway)
                                                                  KEGG pathway 2026/09/17
  http-json       generic: url + dotted path                      whatever you point it at
  http-header     generic: url + response header name
  field           read a key out of the tool result itself        DepMap 24Q2
  static          a fixed string from config                      a pinned local dataset

Not resolvable, checked and rejected: DepMap (no API; use `field` or `static`),
Europe PMC (reports API version, not a data release), RCSB PDB (no release
endpoint found), gnomAD (versions live in dataset ids, not a meta endpoint).
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

Resolver = Callable[[dict[str, Any], object], Awaitable[str | None]]
CACHE_TTL_S = 900  # a release does not change mid-session; do not hammer the source
HTTP_TIMEOUT_S = 10.0
USER_AGENT = "provmcp-release-resolver (+https://github.com/AbhiAdhikari/provmcp)"


def _dig(obj: Any, path: str) -> Any:
    """Follow a dotted path through dicts and lists. None if any step is missing."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
        if cur is None:
            return None
    return cur


@dataclass
class _Cached:
    value: str | None
    at: float


_cache: dict[str, _Cached] = {}


async def _http(url: str, *, method: str = "GET", json_body: Any = None,
                params: dict | None = None, headers: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT_S, follow_redirects=True,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
    ) as http:
        r = await http.request(method, url, json=json_body, params=params)
        r.raise_for_status()
        return r


async def _http_json(url: str, **kw: Any) -> Any:
    return (await _http(url, **kw)).json()


async def _cached(key: str, fetch: Callable[[], Awaitable[str | None]]) -> str | None:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit.at < CACHE_TTL_S:
        return hit.value
    try:
        value = await fetch()
    except Exception as exc:  # resolution is best-effort, never fatal
        log.warning("release resolution failed for %s: %s", key, exc)
        value = None
    if value is None:
        log.warning("release unresolved for %s", key)
    _cache[key] = _Cached(value, time.monotonic())
    return value


def clear_cache() -> None:
    _cache.clear()


def _nonempty(prefix: str, v: Any) -> str | None:
    return f"{prefix}{v}" if v not in (None, "") else None


# ---------- NCBI ----------

_EUTILS_LABEL = {"gds": "GEO gds", "pubmed": "PubMed", "clinvar": "ClinVar", "sra": "SRA",
                 "gene": "NCBI Gene", "snp": "dbSNP", "nucleotide": "Nucleotide",
                 "protein": "NCBI Protein", "bioproject": "BioProject", "biosample": "BioSample"}


async def resolve_eutils(opts: dict[str, Any], _result: object) -> str | None:
    db = opts.get("db", "gds")
    label = opts.get("prefix") or _EUTILS_LABEL.get(db, f"NCBI {db}")

    async def fetch() -> str | None:
        data = await _http_json(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi",
            params={"db": db, "retmode": "json"},
        )
        return _nonempty(f"{label} ", _dig(data, "einforesult.dbinfo.0.dbbuild"))

    return await _cached(f"eutils:{db}", fetch)


async def resolve_geo(opts: dict[str, Any], result: object) -> str | None:
    return await resolve_eutils({**opts, "db": opts.get("db", "gds")}, result)


# ---------- EMBL-EBI and friends ----------

async def resolve_opentargets(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://api.platform.opentargets.org/api/v4/graphql")

    async def fetch() -> str | None:
        data = await _http_json(
            url, method="POST",
            json_body={"query": "{ meta { dataVersion { year month iteration } } }"},
        )
        v = _dig(data, "data.meta.dataVersion")
        if not v or not v.get("year") or not v.get("month"):
            return None
        rel = f"{v['year']}.{v['month']}"
        if v.get("iteration"):
            rel += f".{v['iteration']}"
        return f"OT {rel}"

    return await _cached(f"opentargets:{url}", fetch)


async def resolve_uniprot(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://rest.uniprot.org/uniprotkb/search")

    async def fetch() -> str | None:
        r = await _http(url, params={"query": "P69905", "size": 1, "fields": "accession"})
        return _nonempty("UniProt ", r.headers.get("x-uniprot-release"))

    return await _cached(f"uniprot:{url}", fetch)


async def resolve_ensembl(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://rest.ensembl.org/info/data/")

    async def fetch() -> str | None:
        data = await _http_json(url, params={"content-type": "application/json"})
        return _nonempty("Ensembl ", _dig(data, "releases.0"))

    return await _cached(f"ensembl:{url}", fetch)


async def resolve_chembl(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://www.ebi.ac.uk/chembl/api/data/status.json")

    async def fetch() -> str | None:
        return _nonempty("", _dig(await _http_json(url), "chembl_db_version"))

    return await _cached(f"chembl:{url}", fetch)


async def resolve_string(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://string-db.org/api/json/version")

    async def fetch() -> str | None:
        return _nonempty("STRING ", _dig(await _http_json(url), "0.string_version"))

    return await _cached(f"string:{url}", fetch)


async def resolve_reactome(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://reactome.org/ContentService/data/database/version")

    async def fetch() -> str | None:
        text = (await _http(url)).text.strip()
        return f"Reactome {text}" if re.fullmatch(r"\d+", text) else None

    return await _cached(f"reactome:{url}", fetch)


async def resolve_hgnc(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://rest.genenames.org/info")

    async def fetch() -> str | None:
        data = await _http_json(url, headers={"Accept": "application/json"})
        return _nonempty("HGNC ", _dig(data, "lastModified"))

    return await _cached(f"hgnc:{url}", fetch)


async def resolve_ols(opts: dict[str, Any], _result: object) -> str | None:
    ontology = opts.get("ontology")
    if not ontology:
        log.warning("ols resolver needs source_options.ontology (e.g. mondo, go, hp)")
        return None
    url = opts.get("url", f"https://www.ebi.ac.uk/ols4/api/ontologies/{ontology}")

    async def fetch() -> str | None:
        return _nonempty(f"{ontology} ", _dig(await _http_json(url), "config.version"))

    return await _cached(f"ols:{ontology}", fetch)


async def resolve_clinicaltrials(opts: dict[str, Any], _result: object) -> str | None:
    url = opts.get("url", "https://clinicaltrials.gov/api/v2/version")

    async def fetch() -> str | None:
        return _nonempty("CT.gov ", _dig(await _http_json(url), "dataTimestamp"))

    return await _cached(f"clinicaltrials:{url}", fetch)


async def resolve_kegg(opts: dict[str, Any], _result: object) -> str | None:
    db = opts.get("db", "pathway")

    async def fetch() -> str | None:
        text = (await _http(f"https://rest.kegg.jp/info/{db}")).text
        m = re.search(r"Last update\s+(\d{4}/\d{2}/\d{2})", text)
        return f"KEGG {db} {m.group(1)}" if m else None

    return await _cached(f"kegg:{db}", fetch)


# ---------- generic ----------

async def resolve_http_json(opts: dict[str, Any], _result: object) -> str | None:
    """source_options: {url, path, prefix?, method?, body?}"""
    url, path = opts.get("url"), opts.get("path")
    if not url or not path:
        log.warning("http-json resolver needs source_options.url and .path")
        return None

    async def fetch() -> str | None:
        data = await _http_json(url, method=opts.get("method", "GET"), json_body=opts.get("body"))
        return _nonempty(opts.get("prefix", ""), _dig(data, path))

    return await _cached(f"http-json:{url}:{path}", fetch)


async def resolve_http_header(opts: dict[str, Any], _result: object) -> str | None:
    """source_options: {url, header, prefix?}"""
    url, header = opts.get("url"), opts.get("header")
    if not url or not header:
        log.warning("http-header resolver needs source_options.url and .header")
        return None

    async def fetch() -> str | None:
        r = await _http(url, method=opts.get("method", "GET"))
        return _nonempty(opts.get("prefix", ""), r.headers.get(header))

    return await _cached(f"http-header:{url}:{header}", fetch)


async def resolve_field(opts: dict[str, Any], result: object) -> str | None:
    """source_options: {path, prefix?} — read the release out of the result."""
    path = opts.get("path", "release")
    v = _dig(result, path)
    if v in (None, ""):
        # Tool results are content blocks; look inside structuredContent too.
        v = _dig(result, f"structuredContent.{path}")
    return _nonempty(opts.get("prefix", ""), v)


async def resolve_static(opts: dict[str, Any], _result: object) -> str | None:
    return opts.get("release") or None


BUILTIN: dict[str, Resolver] = {
    "geo": resolve_geo,
    "eutils": resolve_eutils,
    "opentargets": resolve_opentargets,
    "clinicaltrials": resolve_clinicaltrials,
    "uniprot": resolve_uniprot,
    "ensembl": resolve_ensembl,
    "chembl": resolve_chembl,
    "string": resolve_string,
    "reactome": resolve_reactome,
    "hgnc": resolve_hgnc,
    "ols": resolve_ols,
    "kegg": resolve_kegg,
    "http-json": resolve_http_json,
    "http-header": resolve_http_header,
    "field": resolve_field,
    "static": resolve_static,
}

# ---------- plugins ----------
#
# Third-party resolvers register under the `provmcp.resolvers` entry-point
# group. A distribution's pyproject.toml declares:
#
#     [project.entry-points."provmcp.resolvers"]
#     depmap = "provmcp_resolver_depmap:resolve"
#
# and the target is an async callable with the same signature as every
# resolver here: (source_options: dict, result: object) -> str | None.
# Plugins are loaded lazily on first use and cannot shadow a built-in name —
# a plugin that tries is skipped with a warning, so a bad install can't
# silently change what "geo" means in someone's ledger.

ENTRY_POINT_GROUP = "provmcp.resolvers"


@dataclass
class ResolverInfo:
    name: str
    resolver: Resolver
    origin: str          # "builtin" or the distribution name


_registry: dict[str, ResolverInfo] | None = None


def _load_plugins() -> dict[str, ResolverInfo]:
    from importlib.metadata import entry_points

    found: dict[str, ResolverInfo] = {}
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        dist = getattr(getattr(ep, "dist", None), "name", None) or "unknown-distribution"
        if ep.name in BUILTIN:
            log.warning("plugin %s from %s tries to shadow built-in resolver %r; skipped",
                        ep.value, dist, ep.name)
            continue
        if ep.name in found:
            log.warning("resolver %r provided by both %s and %s; keeping the first",
                        ep.name, found[ep.name].origin, dist)
            continue
        try:
            fn = ep.load()
        except Exception as exc:  # a broken plugin must not take the proxy down
            log.warning("could not load resolver plugin %r from %s: %s", ep.name, dist, exc)
            continue
        if not callable(fn):
            log.warning("resolver plugin %r from %s is not callable; skipped", ep.name, dist)
            continue
        found[ep.name] = ResolverInfo(ep.name, fn, dist)
    return found


def registry(*, reload: bool = False) -> dict[str, ResolverInfo]:
    """Every resolver by name: built-ins first, then installed plugins."""
    global _registry
    if _registry is None or reload:
        _registry = {n: ResolverInfo(n, r, "builtin") for n, r in BUILTIN.items()}
        _registry.update(_load_plugins())
    return _registry


def register(name: str, resolver: Resolver, origin: str = "runtime") -> None:
    """Register a resolver in-process (tests, notebooks). Built-ins are immutable."""
    if name in BUILTIN:
        raise ValueError(f"{name!r} is a built-in resolver and cannot be replaced")
    registry()[name] = ResolverInfo(name, resolver, origin)


class _ResolverView(dict):
    """Backwards-compatible `RESOLVERS` mapping: name -> callable, plugins included."""

    def __getitem__(self, name: str) -> Resolver:
        return registry()[name].resolver

    def get(self, name: str, default: Any = None) -> Any:  # type: ignore[override]
        info = registry().get(name)
        return info.resolver if info else default

    def __contains__(self, name: object) -> bool:
        return name in registry()

    def __iter__(self):
        return iter(registry())

    def __len__(self) -> int:
        return len(registry())

    def keys(self):  # type: ignore[override]
        return registry().keys()


RESOLVERS: dict[str, Resolver] = _ResolverView()


async def resolve_release(source: str | None, opts: dict[str, Any], result: object) -> str | None:
    """Return a release identifier for this source, or None if unknowable."""
    if source is None:
        return None
    info = registry().get(source)
    if info is None:
        log.warning("unknown source %r; known: %s", source, sorted(registry()))
        return None
    try:
        return await info.resolver(opts, result)
    except Exception as exc:  # a plugin exception is a missing release, not a failed call
        log.warning("resolver %r (%s) raised: %s", source, info.origin, exc)
        return None
