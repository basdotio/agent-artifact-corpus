"""Ground truth for the tasks, fetched directly from the public services.

Every fact comes from a plain HTTP call to the GA4GH Implementation Registry or to a service it
lists, never through the Agentic Harness, so the system under test does not grade itself. A
snapshot is a dated JSON file; tasks name facts by dotted path into it (``beacon.variants.
hbb_rs334.exists``). Services change, so a model run is scored against the snapshot taken with
it, and the snapshot records when each fact was fetched.

The probes below (variants, TRS tools, how many DRS objects per service) are the only choices
made here; everything else is what the services say.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import httpx

REGISTRY = "https://implementation-registry.ga4gh.org/api/services"

# GRCh38, 1-based. Chosen to cover present, absent, wrong-allele, non-autosomal and wrong-assembly
# cases for a Beacon that holds an African reference panel.
VARIANTS: dict[str, dict[str, Any]] = {
    "hbb_rs334": {"label": "HBB sickle-cell allele", "rsid": "rs334", "gene": "HBB",
                  "chrom": "11", "pos": 5227002, "ref": "T", "alt": "A"},
    "hbb_rs334_wrong_alt": {"label": "HBB rs334 position with the wrong alternate allele",
                            "rsid": "rs334", "gene": "HBB", "chrom": "11", "pos": 5227002,
                            "ref": "T", "alt": "G"},
    "hbb_rs334_grch37_coords": {"label": "rs334 at its GRCh37 position, queried as GRCh38",
                                "rsid": "rs334", "gene": "HBB", "chrom": "11", "pos": 5248232,
                                "ref": "T", "alt": "A"},
    "ackr1_rs2814778": {"label": "ACKR1 (Duffy) null allele", "rsid": "rs2814778", "gene": "ACKR1",
                        "chrom": "1", "pos": 159204893, "ref": "T", "alt": "C"},
    "apol1_g1_rs73885319": {"label": "APOL1 G1 allele", "rsid": "rs73885319", "gene": "APOL1",
                            "chrom": "22", "pos": 36265860, "ref": "A", "alt": "G"},
    "lct_rs4988235": {"label": "LCT -13910 lactase persistence", "rsid": "rs4988235", "gene": "LCT",
                      "chrom": "2", "pos": 135851076, "ref": "G", "alt": "A"},
    "cyp2c19_rs4244285": {"label": "CYP2C19*2", "rsid": "rs4244285", "gene": "CYP2C19",
                          "chrom": "10", "pos": 94781859, "ref": "G", "alt": "A"},
    "braf_v600e": {"label": "BRAF V600E", "rsid": "rs113488022", "gene": "BRAF",
                   "chrom": "7", "pos": 140753336, "ref": "A", "alt": "T"},
    "g6pd_rs1050828": {"label": "G6PD A- (chrX)", "rsid": "rs1050828", "gene": "G6PD",
                       "chrom": "X", "pos": 154536002, "ref": "C", "alt": "T"},
    "chr1_1000_control": {"label": "chr1:1000 A>T, a position no panel holds", "rsid": None,
                          "gene": None, "chrom": "1", "pos": 1000, "ref": "A", "alt": "T"},
}

TRS_TOOLS: dict[str, dict[str, str]] = {
    "bamstats": {"registry": "org.dockstore", "id": "quay.io/collaboratory/dockstore-tool-bamstats/bam-stats"},
    "gatk_hc_gvcf": {"registry": "org.dockstore",
                     "id": "#workflow/github.com/gatk-workflows/gatk4-germline-snps-indels/haplotypecaller-gvcf-gatk4"},
    "read_coverage": {"registry": "org.dockstore", "id": "#workflow/github.com/jmonlong/read_coverage_wf/read_coverage"},
    "warp_wgs": {"registry": "org.dockstore",
                 "id": "#workflow/github.com/broadinstitute/warp/WholeGenomeGermlineSingleSample"},
    "workflowhub_2": {"registry": "eu.workflowhub", "id": "2"},
}
TRS_BASES = {
    "org.dockstore": "https://dockstore.org/api/ga4gh/trs/v2",
    "eu.workflowhub": "https://workflowhub.eu/ga4gh/trs/v2",
    # Yevis serves a static TRS from GitHub Pages; its paths end in a slash.
    "io.github.ddbj.workflow-registry": "https://ddbj.github.io/workflow-registry",
}
DRS_OBJECTS_PER_SERVICE = 3
ACCEPT_MANIFESTS = ", ".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


async def _json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> tuple[int | None, Any]:
    try:
        response = await client.get(url, **kwargs)
    except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
        return None, {"error": exc.__class__.__name__}
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, None


# Registry and reachability -------------------------------------------------------------------


async def registry(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    _, items = await _json(client, REGISTRY)
    out = []
    for item in items:
        version = item.get("standardVersion") or {}
        org = item.get("organisation") or {}
        geo = item.get("geolocation") or {}
        drs = (item.get("implData") or {}).get("drs") or {}
        out.append({
            "id": item["id"],
            "key": slug(f"{item.get('implementationId') or item['name']}_{item['id'][:4]}"),
            "implementation_id": item.get("implementationId"),
            "name": item.get("name"),
            "product": version.get("ga4ghProduct"),
            "standard_version": version.get("version"),
            "organization": org.get("name"),
            # Kept as registered: a malformed URL is itself a fact a model should notice.
            "url": item.get("url"),
            "service_info_url": item.get("serviceInfoUrl"),
            "documentation_url": item.get("documentationUrl"),
            "environment": item.get("environment"),
            "country": geo.get("country"),
            "city": geo.get("city"),
            "drs_objects": drs.get("objectsCount"),
            "drs_storage_gb": drs.get("storageFootprintGb"),
            "hosting": drs.get("hostingInfra"),
            "created": (item.get("createdAt") or "")[:10] or None,
        })
    return out


async def reachability(client: httpx.AsyncClient, service: dict[str, Any]) -> dict[str, Any]:
    """live: service-info answered 2xx JSON; dead: no HTTP answer at all; unclear: anything else."""
    url = service["service_info_url"] or (service["url"] or "").rstrip("/") + "/service-info"
    status, body = await _json(client, url)
    if status is None:
        return {"status": "dead", "live_bool": False, "detail": (body or {}).get("error")}
    if 200 <= status < 300 and isinstance(body, dict):
        declared = body.get("type") if isinstance(body.get("type"), dict) else {}
        return {"status": "live", "live_bool": True, "declared_artifact": declared.get("artifact"),
                "declared_version": declared.get("version"), "declared_name": body.get("name")}
    return {"status": "unclear", "detail": f"HTTP {status}"}


# Beacon --------------------------------------------------------------------------------------


async def beacon(client: httpx.AsyncClient, service: dict[str, Any]) -> dict[str, Any]:
    base = service["url"].rstrip("/")
    _, info = await _json(client, base + "/info")
    _, datasets = await _json(client, base + "/datasets")
    sets = (((datasets or {}).get("response") or {}).get("resultSets") or [{}])[0].get("results") or []
    variants = {}
    for key, v in VARIANTS.items():
        params = {"referenceName": v["chrom"], "start": v["pos"] - 1, "referenceBases": v["ref"],
                  "alternateBases": v["alt"], "assemblyId": "GRCh38"}
        status, body = await _json(client, base + "/g_variants", params=params)
        exists = ((body or {}).get("responseSummary") or {}).get("exists") if isinstance(body, dict) else None
        throttled = status == 429 or "throttled" in json.dumps(body or {}).lower()
        variants[key] = {**v, "exists": exists, **({"throttled": True} if throttled else {})}
    response = (info or {}).get("response") or {}
    return {
        "service_id": service["id"],
        "name": response.get("name"),
        "organization": (response.get("organization") or {}).get("name"),
        "api_version": response.get("apiVersion"),
        "granularity": ((info or {}).get("meta") or {}).get("returnedGranularity"),
        "datasets": [{"id": d.get("id"), "name": d.get("name"), "assembly": d.get("assemblyId"),
                      "description": d.get("description")} for d in sets],
        "variants": variants,
    }


# DRS -----------------------------------------------------------------------------------------


async def drs(client: httpx.AsyncClient, service: dict[str, Any]) -> dict[str, Any] | None:
    host = httpx.URL(service["url"]).host
    _, index = await _json(client, f"https://{host}/index/index", params={"limit": DRS_OBJECTS_PER_SERVICE})
    records = (index or {}).get("records") if isinstance(index, dict) else None
    if not records:
        return None
    objects = []
    for record in records[:DRS_OBJECTS_PER_SERVICE]:
        oid = record["did"]
        status, body = await _json(client, f"https://{host}/ga4gh/drs/v1/objects/{oid}")
        if status != 200 or not isinstance(body, dict):
            continue
        methods = body.get("access_methods") or []
        access = None
        first = next((m for m in methods if m.get("access_id")), None)
        if first:
            code, _ = await _json(client, f"https://{host}/ga4gh/drs/v1/objects/{oid}/access/{first['access_id']}")
            # A server error says nothing about whether a login is needed: no truth then.
            access = {"access_id": first["access_id"], "http_status": code,
                      "public": None if code is None or code >= 500 else 200 <= code < 300}
        objects.append({
            "id": oid, "name": body.get("name"), "size": body.get("size"),
            "checksums": {c.get("type"): c.get("checksum") for c in body.get("checksums") or []},
            "access_types": sorted({m.get("type") for m in methods if m.get("type")}),
            "access": access,
        })
    return {"service_id": service["id"], "name": service["name"], "host": host, "objects": objects}


# TRS -----------------------------------------------------------------------------------------


async def manifest_format(client: httpx.AsyncClient, image: str) -> str:
    name, _, digest = image.partition("@")
    first, _, rest = name.partition("/")
    registry_host, path = (first, rest) if rest and ("." in first or ":" in first) else ("registry-1.docker.io", name)
    tag = None
    if ":" in path.rsplit("/", 1)[-1]:
        path, tag = path.rsplit(":", 1)
    if registry_host == "registry-1.docker.io" and "/" not in path:
        path = "library/" + path
    ref = digest or tag
    if not ref:
        return "untagged"
    url = f"https://{registry_host}/v2/{path}/manifests/{ref}"
    headers = {"Accept": ACCEPT_MANIFESTS}
    response = await client.get(url, headers=headers)
    if response.status_code == 401:
        fields = dict(re.findall(r'(\w+)="([^"]*)"', response.headers.get("www-authenticate", "")))
        realm = fields.pop("realm", "")
        if realm:
            fields.setdefault("scope", f"repository:{path}:pull")
            token = (await client.get(realm, params=fields)).json().get("token")
            response = await client.get(url, headers={**headers, "Authorization": f"Bearer {token}"})
    if response.status_code == 404:
        return "missing"
    kind = response.headers.get("content-type", "").split(";")[0]
    return {"application/vnd.docker.distribution.manifest.v1+prettyjws": "docker-v1",
            "application/vnd.docker.distribution.manifest.v1+json": "docker-v1"}.get(
        kind, "oci" if "oci" in kind else "docker-v2" if "v2" in kind else f"other ({response.status_code})")


async def trs(client: httpx.AsyncClient) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, spec in TRS_TOOLS.items():
        base = TRS_BASES[spec["registry"]]
        status, tool = await _json(client, f"{base}/tools/{_quote(spec['id'])}")
        if status != 200 or not isinstance(tool, dict):
            out[key] = {"registry": spec["registry"], "id": spec["id"], "found": False}
            continue
        versions = []
        for version in tool.get("versions") or []:
            name = str(version.get("name") or version.get("id"))
            images = [i.get("image_name") for i in version.get("images") or [] if i.get("image_name")]
            versions.append({"name": name, "descriptor_types": sorted(version.get("descriptor_type") or []),
                             "images": images})
        out[key] = {"registry": spec["registry"], "id": spec["id"], "found": True,
                    "name": tool.get("name"), "organization": tool.get("organization"),
                    "toolclass": (tool.get("toolclass") or {}).get("name"),
                    "version_names": sorted(v["name"] for v in versions), "versions": versions}
    # Images of the BAMStats WDL version the demo used, whose registry serves only v1 manifests.
    bam = next((v for v in out["bamstats"].get("versions", []) if v["name"] == "2"), None)
    if bam:
        _, descriptor = await _json(client, f"{TRS_BASES['org.dockstore']}/tools/{_quote(TRS_TOOLS['bamstats']['id'])}/versions/2/WDL/descriptor")
        found = re.findall(r'docker:\s*"([^"]+)"', (descriptor or {}).get("content", ""))
        bam["descriptor_images"] = {img: await manifest_format(client, img) for img in found}
    for version in out["read_coverage"].get("versions", []):
        _, descriptor = await _json(client, f"{TRS_BASES['org.dockstore']}/tools/{_quote(TRS_TOOLS['read_coverage']['id'])}/versions/{version['name']}/WDL/descriptor")
        found = re.findall(r'docker:\s*"([^"]+)"', (descriptor or {}).get("content", ""))
        version["descriptor_images"] = {img: await manifest_format(client, img) for img in found}
    # Catalogue sizes, from the TRS pagination links.
    sizes = {}
    for registry_id, base in TRS_BASES.items():
        if registry_id == "io.github.ddbj.workflow-registry":
            _, listing = await _json(client, f"{base}/tools/")
            sizes[registry_id] = len(listing) if isinstance(listing, list) else None
            continue
        response = await client.get(f"{base}/tools", params={"limit": 1})
        last = response.headers.get("last_page", "")
        match = re.search(r"offset=(\d+)", last)
        sizes[registry_id] = int(match.group(1)) + 1 if match else None
    names = {"org.dockstore": "dockstore", "eu.workflowhub": "workflowhub", "io.github.ddbj.workflow-registry": "yevis"}
    out["catalogue_sizes"] = {names[k]: v for k, v in sizes.items()}
    _, yevis = await _json(client, f"{TRS_BASES['io.github.ddbj.workflow-registry']}/tools/")
    out["yevis_tools"] = sorted(t.get("name") for t in yevis or [] if isinstance(t, dict))
    return out


def _quote(tool_id: str) -> str:
    from urllib.parse import quote
    return quote(tool_id, safe="")


# TES -----------------------------------------------------------------------------------------


async def tes(client: httpx.AsyncClient, service: dict[str, Any]) -> dict[str, Any]:
    base = (service["url"] or "").rstrip("/") + "/ga4gh/tes/v1"
    status, info = await _json(client, base + "/service-info")
    tasks_status, tasks = await _json(client, base + "/tasks", params={"page_size": 5})
    return {
        "service_id": service["id"], "name": service["name"],
        "service_info_status": status,
        "declared_name": (info or {}).get("name") if isinstance(info, dict) else None,
        "declared_organization": ((info or {}).get("organization") or {}).get("name") if isinstance(info, dict) else None,
        "declared_version": ((info or {}).get("type") or {}).get("version") if isinstance(info, dict) else None,
        "tasks_listable_anonymously": tasks_status == 200 and isinstance(tasks, dict) and "tasks" in tasks,
    }


# Derived facts -------------------------------------------------------------------------------


def derive(services: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregates a task can ask about, computed from the registry records and reachability."""
    def names(pred: Any) -> list[str]:
        return sorted(s["name"] for s in services if pred(s))

    by_country: dict[str, int] = {}
    by_org: dict[str, int] = {}
    by_url: dict[str, list[str]] = {}
    for s in services:
        by_country[s["country"] or "unknown"] = by_country.get(s["country"] or "unknown", 0) + 1
        by_org[s["organization"] or "unknown"] = by_org.get(s["organization"] or "unknown", 0) + 1
        by_url.setdefault((s["url"] or "").strip().rstrip("/").lower(), []).append(s["name"])
    drs_counted = [s for s in services if s["product"] == "DRS" and s["drs_objects"]]
    most = max(drs_counted, key=lambda s: s["drs_objects"]) if drs_counted else None
    top_org = max(by_org.items(), key=lambda item: item[1])
    mismatched = [
        {"name": s["name"], "registry": s["standard_version"], "declared": s["reachability"].get("declared_version")}
        for s in services
        if s["reachability"]["status"] == "live" and s["reachability"].get("declared_version")
        and s["standard_version"] and not str(s["reachability"]["declared_version"]).startswith(
            ".".join(str(s["standard_version"]).split(".")[:2]))
    ]
    return {
        "products": sorted({s["product"] for s in services if s["product"]}),
        "live_names": names(lambda s: s["reachability"]["status"] == "live"),
        "dead_names": names(lambda s: s["reachability"]["status"] == "dead"),
        "unclear_names": names(lambda s: s["reachability"]["status"] == "unclear"),
        "live_by_product": {p: names(lambda s, p=p: s["product"] == p and s["reachability"]["status"] == "live")
                            for p in sorted({s["product"] for s in services if s["product"]})},
        "registered_by_product": {p: names(lambda s, p=p: s["product"] == p)
                                  for p in sorted({s["product"] for s in services if s["product"]})},
        "products_without_live": sorted(
            p for p in {s["product"] for s in services if s["product"]}
            if not any(s["product"] == p and s["reachability"]["status"] == "live" for s in services)),
        "countries": sorted(c for c in by_country if c != "unknown"),
        "services_by_country": by_country,
        "us_count": by_country.get("US", 0),
        "organization_with_most_services": {"name": top_org[0], "count": top_org[1]},
        "drs_most_objects": {"name": most["name"], "objects": most["drs_objects"]} if most else None,
        "drs_total_objects": sum(s["drs_objects"] for s in drs_counted),
        "drs_commercial_cloud": names(lambda s: s["product"] == "DRS" and s["hosting"] == "COMMERCIAL_CLOUD"),
        "declared_version_mismatches": mismatched,
        "duplicate_urls": [sorted(v) for k, v in by_url.items() if k and len(v) > 1],
        "malformed_urls": names(lambda s: (s["url"] or "") != (s["url"] or "").strip()),
        "private_address_urls": names(lambda s: bool(re.match(r"https?://(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.", (s["url"] or "").strip()))),
        "terra_hosted": names(lambda s: "data.terra.bio" in (s["url"] or "")),
    }


# Snapshot ------------------------------------------------------------------------------------


async def snapshot() -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent": "ga4gh-harness-benchmark/0.1"}) as client:
        services = await registry(client)
        sem = asyncio.Semaphore(10)

        async def reach(s: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                return await reachability(client, s)

        for s, r in zip(services, await asyncio.gather(*(reach(s) for s in services))):
            s["reachability"] = r
        beacons = [await beacon(client, s) for s in services if s["product"] == "Beacon"]
        drs_live = [s for s in services if s["product"] == "DRS" and s["reachability"]["status"] == "live"]
        drs_results = [r for r in await asyncio.gather(*(drs(client, s) for s in drs_live)) if r]
        # Several registry entries share one host; keep one per host.
        seen, drs_unique = set(), []
        for r in drs_results:
            if r["host"] not in seen and r["objects"]:
                seen.add(r["host"])
                drs_unique.append(r)
        tes_results = [await tes(client, s) for s in services if s["product"] == "TES"]
        trs_results = await trs(client)
    products: dict[str, dict[str, int]] = {}
    for s in services:
        entry = products.setdefault(s["product"] or "unknown", {"registered": 0, "live": 0})
        entry["registered"] += 1
        entry["live"] += s["reachability"]["status"] == "live"
    drs_flat = {}
    for r in drs_unique:
        for i, obj in enumerate(r["objects"]):
            drs_flat[f"{slug(r['host'])}_{i}"] = {**obj, "host": r["host"], "service": r["name"],
                                                    "md5": obj["checksums"].get("md5")}
    return {
        "fetched_at": started,
        "derived": derive(services),
        "drs_objects": drs_flat,
        "registry_url": REGISTRY,
        "registry": {"total": len(services), "products": products,
                     "services": {s["key"]: s for s in services}},
        "beacon": beacons[0] if len(beacons) == 1 else {"all": beacons},
        "drs": {r["host"]: r for r in drs_unique},
        "tes": {slug(t["name"] + "_" + t["service_id"][:4]): t for t in tes_results},
        "trs": trs_results,
    }


async def refresh_beacon(path: Path) -> dict[str, Any]:
    """Refetch only the Beacon section of an existing snapshot (the Beacon allows 50 requests/hour)."""
    data = json.loads(path.read_text())
    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent": "ga4gh-harness-benchmark/0.1"}) as client:
        service = next(s for s in data["registry"]["services"].values() if s["product"] == "Beacon")
        data["beacon"] = await beacon(client, service)
    data["beacon_fetched_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(data, indent=1) + "\n")
    return data


def main() -> None:
    import sys

    if "--beacon-only" in sys.argv:
        path = sorted((Path(__file__).resolve().parents[1] / "snapshots").glob("*/facts.json"))[-1]
        data = asyncio.run(refresh_beacon(path))
        answers = {k: v.get("exists") for k, v in data["beacon"]["variants"].items()}
        print(f"refreshed Beacon facts in {path}: {answers}")
        return
    data = asyncio.run(snapshot())
    day = data["fetched_at"][:10]
    folder = Path(__file__).resolve().parents[1] / "snapshots" / day
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "facts.json").write_text(json.dumps(data, indent=1, sort_keys=False) + "\n")
    print(f"wrote {folder / 'facts.json'}: {data['registry']['total']} services, "
          f"{len(data['drs'])} DRS hosts with public objects, {len(data['trs']) - 1} TRS tools")


if __name__ == "__main__":
    main()
