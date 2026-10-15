"""Taste Match: the composite agent behind the `taste_match` MCP tool.

An independent artist describes one work from their catalog (an art print or a
song). The agent:

1. Plans: turns the description into taste seeds (named influences and style
   keywords). If an OpenAI-compatible LLM is configured via TASTE_MATCH_LLM_URL
   it asks the LLM to propose seeds, otherwise it uses a deterministic keyword
   extractor. Artist-supplied influences and keywords always win.
2. Resolves: looks every seed up in Qloo (/search for entities, /v2/tags for
   tags) in parallel to get real Qloo IDs.
3. Fans out: runs Qloo /v2/insights in parallel for artists, places, brands,
   books and movies, plus urn:demographics (who) and urn:tag (what words
   describe that taste).
4. Synthesizes: returns ranked matches, an audience profile, and a short
   plain-text pitch the artist can use to reach those people.

Every Qloo call is isolated: one failing branch becomes a note, not a crash.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

import httpx

from .client import QlooAPIError, QlooClient
from .schemas import (
    GetDemographicsInput,
    GetInsightsInput,
    GetTasteAnalysisInput,
    SearchEntitiesInput,
    SearchTagsInput,
    TasteMatchInput,
)

LLM_URL_ENV = "TASTE_MATCH_LLM_URL"
LLM_MODEL_ENV = "TASTE_MATCH_LLM_MODEL"
LLM_KEY_ENV = "TASTE_MATCH_LLM_API_KEY"

SEED_ENTITY_TYPES = [
    "urn:entity:artist",
    "urn:entity:person",
    "urn:entity:movie",
    "urn:entity:book",
    "urn:entity:brand",
    "urn:entity:place",
]

MATCH_TYPES = {
    "artists": "urn:entity:artist",
    "places": "urn:entity:place",
    "brands": "urn:entity:brand",
    "books": "urn:entity:book",
    "movies": "urn:entity:movie",
}

AGE_LABELS = {
    "24_and_younger": "24 and younger",
    "25_to_29": "25 to 29",
    "30_to_34": "30 to 34",
    "35_to_44": "35 to 44",
    "45_to_54": "45 to 54",
    "55_and_older": "55 and older",
}

_STOPWORDS = set(
    """a about above after again against all also am an and any are as at be because been before being below
    between both but by can could did do does doing down during each few for from further had has have having
    he her here hers herself him himself his how i if in into is it its itself just like made make makes me more
    most my myself no nor not now of off on once only or other our ours out over own piece print same she should
    so some song such than that the their theirs them themselves then there these they this those through to too
    track under until up very was we were what when where which while who whom why will with work would you your
    yours feel feels feeling vibe vibes using used one two three into onto kind sort lots really""".split()
)


def extract_keywords(text: str, limit: int = 4) -> list[str]:
    """Deterministic fallback planner: ordered, de-duplicated content words."""
    words = re.findall(r"[A-Za-z][A-Za-z\-']{3,}", text.lower())
    seen: list[str] = []
    for w in words:
        w = w.strip("-'")
        if w in _STOPWORDS or w in seen or len(w) < 4:
            continue
        seen.append(w)
        if len(seen) >= limit:
            break
    return seen


async def _llm_plan(inp: TasteMatchInput) -> dict[str, list[str]] | None:
    """Ask an OpenAI-compatible LLM for seeds. Returns None when not configured or on any failure."""
    base = os.environ.get(LLM_URL_ENV, "").rstrip("/")
    if not base:
        return None
    headers = {"Content-Type": "application/json"}
    key = os.environ.get(LLM_KEY_ENV)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            model = os.environ.get(LLM_MODEL_ENV)
            if not model:
                r = await http.get(f"{base}/models", headers=headers)
                r.raise_for_status()
                model = r.json()["data"][0]["id"]
            prompt = (
                "You help an independent artist find their audience using a taste graph. "
                f"The {inp.work_kind} is titled '{inp.work_title}'. Description: {inp.description}\n\n"
                "Return ONLY JSON with two arrays: "
                '{"influences": [up to 5 well-known real artists, films, books, brands or places whose fans would likely love this work], '
                '"keywords": [up to 5 short genre or style words, e.g. synthwave, surrealism, lofi]}'
            )
            r = await http.post(
                f"{base}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 400,
                },
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"] or ""
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    infl = [str(x).strip() for x in data.get("influences", []) if str(x).strip()][:5]
    kws = [str(x).strip() for x in data.get("keywords", []) if str(x).strip()][:5]
    return {"influences": infl, "keywords": kws}


async def plan_seeds(inp: TasteMatchInput) -> tuple[list[str], list[str], str]:
    """Merge artist-supplied seeds with planner seeds. Returns (influences, keywords, planner_name)."""
    influences = list(inp.influences)
    keywords = list(inp.keywords)
    planner = "artist"
    if len(influences) < 3 or len(keywords) < 3:
        llm = await _llm_plan(inp)
        if llm:
            planner = "llm"
            influences += [x for x in llm["influences"] if x not in influences]
            keywords += [x for x in llm["keywords"] if x not in keywords]
        elif len(keywords) < 3:
            planner = "keywords"
            keywords += [x for x in extract_keywords(inp.description) if x not in keywords]
    return influences[:6], keywords[:6], planner


async def _safe(coro, notes: list[str], label: str) -> Any:
    try:
        return await coro
    except QlooAPIError as exc:
        notes.append(f"{label}: Qloo API error {exc.status_code}: {exc.message}")
    except Exception as exc:  # noqa: BLE001 - one failed branch must not sink the whole match
        notes.append(f"{label}: {type(exc).__name__}: {exc}")
    return None


def _search_results(payload: Any) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    res = payload.get("results")
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        for k in ("entities", "results"):
            if isinstance(res.get(k), list):
                return res[k]
    return []


def _nested_list(payload: Any, key: str) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    res = payload.get("results")
    if isinstance(res, dict) and isinstance(res.get(key), list):
        return res[key]
    return []


def _slim_entity(e: dict) -> dict:
    props = e.get("properties") or {}
    out = {
        "name": e.get("name"),
        "entity_id": e.get("entity_id"),
        "type": e.get("subtype") or e.get("type") or (e.get("types") or [None])[0],
        "affinity": (e.get("query") or {}).get("affinity"),
        "popularity": e.get("popularity"),
    }
    for k in ("address", "short_description", "description", "website"):
        v = props.get(k)
        if v:
            out[k] = v if len(str(v)) < 240 else str(v)[:237] + "..."
    return {k: v for k, v in out.items() if v is not None}


def _summarize_demographics(rows: list[dict]) -> dict:
    ages: dict[str, list[float]] = {}
    genders: dict[str, list[float]] = {}
    for row in rows:
        q = row.get("query") or {}
        for k, v in (q.get("age") or {}).items():
            if isinstance(v, (int, float)):
                ages.setdefault(k, []).append(float(v))
        for k, v in (q.get("gender") or {}).items():
            if isinstance(v, (int, float)):
                genders.setdefault(k, []).append(float(v))
    age_avg = {k: round(sum(v) / len(v), 3) for k, v in ages.items()}
    gender_avg = {k: round(sum(v) / len(v), 3) for k, v in genders.items()}
    top_age = max(age_avg, key=age_avg.get) if age_avg else None
    lean = max(gender_avg, key=gender_avg.get) if gender_avg else None
    return {
        "age_affinity": age_avg,
        "gender_affinity": gender_avg,
        "strongest_age_group": AGE_LABELS.get(top_age, top_age) if top_age else None,
        "gender_lean": lean,
    }


def build_pitch(inp: TasteMatchInput, matches: dict, audience: dict, tags: list[dict]) -> str:
    kind = "print" if inp.work_kind == "artwork" else "track"
    parts = [f'"{inp.work_title}" is a {kind} for people whose taste already runs toward']
    artists = [m["name"] for m in matches.get("artists", [])[:3] if m.get("name")]
    if artists:
        parts.append(", ".join(artists) + ".")
    else:
        parts.append("the influences listed above.")
    tag_names = [t["name"] for t in tags[:4] if t.get("name")]
    if tag_names:
        parts.append("Their taste reads as " + ", ".join(tag_names) + ".")
    if audience.get("strongest_age_group"):
        parts.append(f"The strongest age affinity is {audience['strongest_age_group']}.")
    places = [m["name"] for m in matches.get("places", [])[:3] if m.get("name")]
    if places:
        where = f" in {inp.location}" if inp.location else ""
        parts.append(f"Places to show it or find these people{where}: " + ", ".join(places) + ".")
    brands = [m["name"] for m in matches.get("brands", [])[:3] if m.get("name")]
    if brands:
        parts.append("Brands this audience already buys from: " + ", ".join(brands) + ".")
    return " ".join(parts)


async def run_taste_match(client: QlooClient, inp: TasteMatchInput) -> dict:
    notes: list[str] = []
    influences, keywords, planner = await plan_seeds(inp)

    entity_lookups = [
        _safe(client.search_entities(SearchEntitiesInput(query=name, types=SEED_ENTITY_TYPES, take=1)), notes, f"search '{name}'")
        for name in influences
    ]
    tag_lookups = [
        _safe(client.search_tags(SearchTagsInput(query=kw, take=1)), notes, f"tag '{kw}'")
        for kw in keywords
    ]
    entity_payloads, tag_payloads = await asyncio.gather(
        asyncio.gather(*entity_lookups), asyncio.gather(*tag_lookups)
    )

    seed_entities: list[dict] = []
    for name, payload in zip(influences, entity_payloads):
        hits = _search_results(payload)
        if hits and hits[0].get("entity_id"):
            seed_entities.append({"query": name, **_slim_entity(hits[0])})
        elif payload is not None:
            notes.append(f"no Qloo entity found for '{name}'")

    seed_tags: list[dict] = []
    for kw, payload in zip(keywords, tag_payloads):
        hits = _nested_list(payload, "tags")
        if hits:
            t = hits[0]
            tid = t.get("id") or t.get("tag_id")
            if tid:
                seed_tags.append({"query": kw, "tag_id": tid, "name": t.get("name")})
                continue
        if payload is not None:
            notes.append(f"no Qloo tag found for '{kw}'")

    entity_ids = [e["entity_id"] for e in seed_entities]
    tag_ids = [t["tag_id"] for t in seed_tags]

    result: dict[str, Any] = {
        "work": {"title": inp.work_title, "kind": inp.work_kind, "location": inp.location},
        "planner": planner,
        "seeds": {"entities": seed_entities, "tags": seed_tags},
        "audience": {},
        "matches": {k: [] for k in MATCH_TYPES},
        "taste_tags": [],
        "pitch": "",
        "notes": notes,
    }
    if not entity_ids and not tag_ids:
        notes.append("no seeds resolved in Qloo; add influences (artists, films, brands) the work is close to")
        result["pitch"] = "Not enough taste signal yet. Add two or three influences the work sits next to."
        return result

    insight_calls = []
    for key, etype in MATCH_TYPES.items():
        exclude = set(entity_ids)
        kwargs: dict[str, Any] = {
            "entity_type": etype,
            "entity_ids": entity_ids,
            "tag_ids": tag_ids,
            "take": min(inp.take + len(exclude), 50),
        }
        if inp.location:
            if etype == "urn:entity:place":
                kwargs["filter_location"] = inp.location
            else:
                kwargs["signal_location"] = inp.location
        insight_calls.append(_safe(client.get_insights(GetInsightsInput(**kwargs)), notes, f"insights {key}"))

    demo_call = _safe(
        client.get_demographics(GetDemographicsInput(entity_ids=entity_ids, tag_ids=tag_ids)),
        notes,
        "demographics",
    )
    taste_call = _safe(
        client.get_taste_analysis(
            GetTasteAnalysisInput(entity_ids=entity_ids, tag_ids=tag_ids, location=inp.location, take=15)
        ),
        notes,
        "taste analysis",
    )
    *insight_payloads, demo_payload, taste_payload = await asyncio.gather(*insight_calls, demo_call, taste_call)

    seed_set = set(entity_ids)
    for key, payload in zip(MATCH_TYPES, insight_payloads):
        ents = [e for e in _nested_list(payload, "entities") if e.get("entity_id") not in seed_set]
        result["matches"][key] = [_slim_entity(e) for e in ents[: inp.take]]

    result["audience"] = _summarize_demographics(_nested_list(demo_payload, "demographics"))

    seed_tag_set = set(tag_ids)
    tags = []
    for t in _nested_list(taste_payload, "tags"):
        tid = t.get("tag_id") or t.get("id")
        if tid in seed_tag_set:
            continue
        tags.append({"tag_id": tid, "name": t.get("name"), "affinity": (t.get("query") or {}).get("affinity")})
    result["taste_tags"] = tags[:12]

    result["pitch"] = build_pitch(inp, result["matches"], result["audience"], result["taste_tags"])
    return result
