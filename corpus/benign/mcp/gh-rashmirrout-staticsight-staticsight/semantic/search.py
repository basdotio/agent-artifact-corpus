"""Hybrid (embedding + keyword) search, similar-code lookup and index reports for the semantic tools."""

from __future__ import annotations

import asyncio
import bisect
import re
import time

from ..config import Config
from ..core import md
from ..core.errors import InvalidArgument, StaticSightError
from ..core.paths import decode_source, matches_glob, read_lines, resolve_in_workspace, split_lines
from ..engines.embedder import SemanticUnavailable, get_embedder, model_id
from ..engines.rg import rg_search
from .chunker import _header, chunk_file
from .files import is_structural, language_of
from .index import SemanticIndex, get_semantic_index

SEMANTIC_TOP = 60        # candidates taken from the vector ranking
LEXICAL_TOP = 60         # candidates taken from the keyword ranking
RRF_K = 60               # reciprocal rank fusion constant
LEXICAL_WEIGHT = 0.5     # keyword evidence counts half: natural-language words are noisy, identifiers are rare
EXCERPT_LINES = 6
_TERM = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*")
_STOP = frozenset("""
a an and are as at be by can code does do for from how in is it its of on or that the this to use used uses using
what when where which who why with without we our you your function functions method methods class find show get
where's there their them then than into over under about some any all each every more most other such only same
""".split())
_FENCE = {"cpp": "cpp", "c": "c", "cuda": "cpp", "csharp": "csharp", "java": "java", "python": "python", "go": "go",
          "rust": "rust", "javascript": "javascript", "typescript": "typescript", "shell": "bash", "powershell": "powershell",
          "markdown": "markdown", "json": "json", "yaml": "yaml", "xml": "xml", "sql": "sql", "ruby": "ruby", "kotlin": "kotlin",
          "swift": "swift", "php": "php", "cmake": "cmake", "make": "make", "toml": "toml", "ini": "ini", "html": "html",
          "css": "css", "lua": "lua", "perl": "perl", "scala": "scala", "dockerfile": "dockerfile", "batch": "bat"}


def query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for t in _TERM.findall(query):
        low = t.lower()
        if low in _STOP or len(t) < 3:
            continue
        if low not in (x.lower() for x in terms):
            terms.append(t)
    return terms[:8]


def _score(x: float) -> float:
    return round(float(x), 4)


def _row_key(r) -> tuple:
    return (r[0], r[1], r[7], r[4], r[5])


def _group_key(r) -> tuple:
    # parts of one long unit collapse into one result; plain windows stay separate
    return (r[0], r[4], r[5]) if r[5] else (r[0], r[1], r[2])


def _filters(rows, path_glob: str, language: str, kind: str) -> list[int]:
    lang = language.strip().lower()
    knd = kind.strip().lower()
    return [i for i, r in enumerate(rows)
            if (not path_glob or matches_glob(r[0], path_glob)) and (not lang or r[3] == lang) and (not knd or r[4].lower() == knd)]


async def _lexical(cfg: Config, rows, allowed: list[int], terms: list[str]) -> list[tuple[int, float]]:
    """Rank chunks by distinct query terms (case-insensitive) found in their line range."""
    if not terms:
        return []
    try:
        res = await rg_search(cfg, terms, fixed=True, ignore_case=True, globs=(), max_count=200)
    except StaticSightError:
        return []
    by_path: dict[str, list[int]] = {}
    for i in allowed:
        by_path.setdefault(rows[i][0], []).append(i)
    lows = [t.lower() for t in terms]
    hits: dict[int, set[str]] = {}
    counts: dict[int, int] = {}
    for path, lines in res.files.items():
        idxs = by_path.get(path)
        if not idxs:
            continue
        starts = [rows[i][1] for i in idxs]
        for ln in lines:
            if not ln.is_match:
                continue
            low = ln.text.lower()
            found = {t for t in lows if t in low}
            if not found:
                continue
            k = bisect.bisect_right(starts, ln.line)
            for j in range(k - 1, max(-1, k - 13), -1):  # chunks overlap a little: look back a few starts
                i = idxs[j]
                if rows[i][1] <= ln.line <= rows[i][2]:
                    hits.setdefault(i, set()).update(found)
                    counts[i] = counts.get(i, 0) + 1
    ranked = sorted(hits, key=lambda i: (-len(hits[i]), -min(counts[i], 20), _row_key(rows[i])))
    return [(i, float(len(hits[i]))) for i in ranked[:LEXICAL_TOP]]


def _fuse(sem: list[tuple[int, float]], lex: list[tuple[int, float]]) -> list[tuple[int, float, str]]:
    fused: dict[int, float] = {}
    for rank, (i, _) in enumerate(sem, 1):
        fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank)
    for rank, (i, _) in enumerate(lex, 1):
        fused[i] = fused.get(i, 0.0) + LEXICAL_WEIGHT / (RRF_K + rank)
    sem_set = {i for i, _ in sem}
    lex_set = {i for i, _ in lex}
    out = []
    for i, f in fused.items():
        how = "semantic+keyword" if i in sem_set and i in lex_set else ("semantic" if i in sem_set else "keyword")
        out.append((i, round(f, 8), how))
    return out


def _excerpt(cfg: Config, row, cache: dict[str, list[str]]) -> list[str]:
    path, start, end = row[0], row[1], row[2]
    if path not in cache:
        try:
            cache[path] = read_lines(cfg.workspace_root / path)
        except (StaticSightError, OSError):
            cache[path] = []
    lines = cache[path]
    if not lines:
        return []
    body = [(n, lines[n - 1]) for n in range(start, min(end, len(lines)) + 1)]
    shown = body[:EXCERPT_LINES]
    width = len(str(shown[-1][0])) if shown else 1
    out = [f"{str(n).rjust(width)} | {md.clip(t, 140)}" for n, t in shown]
    if len(body) > EXCERPT_LINES:
        out.append(f"{' ' * width} | … {len(body) - EXCERPT_LINES} more lines")
    return out


def _render_result(cfg: Config, rank: int, row, sim: float | None, how: str, cache: dict[str, list[str]]) -> str:
    path, start, end, language, kind, symbol = row[0], row[1], row[2], row[3], row[4], row[5]
    what = f"{kind} `{symbol}`" if symbol else kind
    score = f"{sim:.2f}" if sim is not None else "—"
    head = f"{rank}. `{path}:{start}-{end}` — {what} ({language}) · {score} · {how}"
    ex = _excerpt(cfg, row, cache)
    if not ex:
        return head
    return head + "\n   ```" + _FENCE.get(language, "text") + "\n" + "\n".join("   " + e for e in ex) + "\n   ```"


def _index_line(idx: SemanticIndex, note: str) -> str:
    c = idx.store.counts()
    return f"Index: {c['files']} files, {c['chunks']} chunks ({model_id(idx.cfg)}). {note}"


async def _keyword_only(cfg: Config, query: str, path_glob: str, top_k: int, note: str) -> str:
    terms = query_terms(query)
    out = [f'### 🔎 SEMANTIC SEARCH: "{md.clip(query, 100)}"', note]
    if not terms:
        return "\n".join(out + ["No keywords to fall back on; retry when the index is ready."])
    res = await rg_search(cfg, terms, fixed=True, ignore_case=True, globs=(), max_count=20)
    items = []
    for m in res.matches():
        if path_glob and not matches_glob(m.path, path_glob):
            continue
        items.append(f"- `{m.path}:{m.line}` {md.code_span(m.text)}")
    out.append(f"**Keyword-only results** for {', '.join(f'`{t}`' for t in terms)}:")
    out += md.truncate_list(items, top_k, "keyword hits") if items else ["_No keyword matches._"]
    return "\n".join(out)


async def semantic_search_report(cfg: Config, query: str, path_glob: str = "", language: str = "", kind: str = "",
                                 top_k: int = 10) -> str:
    query = (query or "").strip()
    if not query:
        raise InvalidArgument("`query` is empty.", "Describe the code you are looking for, e.g. 'retry failed connections'.")
    top_k = max(1, min(int(top_k or 10), 30))
    idx = get_semantic_index(cfg)
    note, usable = await idx.ensure_fresh()
    if not usable:
        return await _keyword_only(cfg, query, path_glob, top_k, note)
    embedder = await asyncio.to_thread(get_embedder, cfg, False)
    rows, mat = idx.matrix()
    allowed = _filters(rows, path_glob, language, kind)
    out = [f'### 🔎 SEMANTIC SEARCH: "{md.clip(query, 100)}"', _index_line(idx, note)]
    if not allowed:
        out.append("_No indexed chunks match the filters._")
        return "\n".join(out)
    import numpy as np

    qv = (await asyncio.to_thread(embedder.embed, [query]))[0].astype(np.float64)
    sims = mat[allowed].astype(np.float64) @ qv
    order = sorted(range(len(allowed)), key=lambda k: (-_score(sims[k]), _row_key(rows[allowed[k]])))
    sem = [(allowed[k], _score(sims[k])) for k in order[:SEMANTIC_TOP]]
    sim_of = {allowed[k]: _score(sims[k]) for k in range(len(allowed))}
    lex = await _lexical(cfg, rows, allowed, query_terms(query))
    fused = sorted(_fuse(sem, lex), key=lambda t: (-t[1], _row_key(rows[t[0]])))
    seen: set[tuple] = set()
    picked = []
    for i, _f, how in fused:
        g = _group_key(rows[i])
        if g in seen:
            continue
        seen.add(g)
        picked.append((i, how))
        if len(picked) >= top_k:
            break
    cache: dict[str, list[str]] = {}
    for rank, (i, how) in enumerate(picked, 1):
        out.append(_render_result(cfg, rank, rows[i], sim_of.get(i), how, cache))
    out.append("\n_Scores are cosine similarity from the local embedding model (higher is closer); results are ranked by "
               "fusing semantic and keyword matches. Verify the code before asserting._")
    return "\n".join(out)


async def _region_text(cfg: Config, rel: str, lines: list[str], start: int, end: int) -> tuple[str, int, int, str]:
    """Embedding text for a region: the enclosing chunk when end == 0, else the explicit range."""
    language = language_of(rel)
    if end:
        body = "\n".join(ln[:300] for ln in lines[start - 1 : end])
        return _header(rel, "region", "", "", 0) + "\n" + body, start, end, f"lines {start}-{end}"
    from ..engines.ctags import try_ctags_for_files

    tags = (await try_ctags_for_files(cfg, [rel], generic=True)).get(rel) if is_structural(language) else None
    chunks = chunk_file(rel, lines, language, tags)
    containing = [c for c in chunks if c.start_line <= start <= c.end_line]
    if not containing:
        raise InvalidArgument(f"No indexable code around `{rel}:{start}`.", "Pass an explicit end_line.")
    c = min(containing, key=lambda c: (c.end_line - c.start_line, c.part))
    label = f"{c.kind} `{c.symbol}`" if c.symbol else f"{c.kind} lines {c.start_line}-{c.end_line}"
    return c.text, c.start_line, c.end_line, label


async def similar_code_report(cfg: Config, file_path: str, start_line: int, end_line: int = 0, top_k: int = 8) -> str:
    abs_path, rel = resolve_in_workspace(cfg.workspace_root, file_path)
    lines = split_lines(decode_source(abs_path.read_bytes()))
    if start_line < 1 or start_line > len(lines):
        raise InvalidArgument(f"Line {start_line} is out of range: `{rel}` has {len(lines)} lines.")
    if end_line and (end_line < start_line):
        raise InvalidArgument(f"Invalid range L{start_line}-{end_line}.")
    end_line = min(end_line, len(lines)) if end_line else 0
    top_k = max(1, min(int(top_k or 8), 30))
    idx = get_semantic_index(cfg)
    note, usable = await idx.ensure_fresh()
    title = f"### 🧬 SIMILAR CODE: `{rel}:{start_line}" + (f"-{end_line}`" if end_line else "`")
    if not usable:
        return f"{title}\n{note}"
    text, a, b, label = await _region_text(cfg, rel, lines, start_line, end_line)
    embedder = await asyncio.to_thread(get_embedder, cfg, False)
    import numpy as np

    qv = (await asyncio.to_thread(embedder.embed, [text]))[0].astype(np.float64)
    rows, mat = idx.matrix()
    cand = [i for i, r in enumerate(rows) if not (r[0] == rel and r[1] <= b and a <= r[2])]
    out = [title, f"Source: {label} (L{a}-{b}). " + _index_line(idx, note)]
    if not cand:
        out.append("_Nothing else is indexed yet._")
        return "\n".join(out)
    sims = mat[cand].astype(np.float64) @ qv
    order = sorted(range(len(cand)), key=lambda k: (-_score(sims[k]), _row_key(rows[cand[k]])))
    seen: set[tuple] = set()
    cache: dict[str, list[str]] = {}
    rank = 0
    for k in order:
        r = rows[cand[k]]
        g = _group_key(r)
        if g in seen:
            continue
        seen.add(g)
        rank += 1
        s = _score(sims[k])
        tag = "near-duplicate" if s >= 0.92 else ("very similar" if s >= 0.85 else "similar")
        out.append(_render_result(cfg, rank, r, s, tag, cache))
        if rank >= top_k:
            break
    out.append("\n_near-duplicate ≥ 0.92, very similar ≥ 0.85 (cosine). Check whether a fix in the source also applies "
               "to these places._")
    return "\n".join(out)


async def similar_for_review(cfg: Config, targets: list[tuple[str, int, str]], threshold: float = 0.85,
                             per_target: int = 3) -> list[str]:
    """Near-duplicates of changed functions in OTHER files, for review_changes. Uses the index as is (no refresh);
    returns [] when semantic search is unavailable or not built."""
    idx = get_semantic_index(cfg)
    try:
        if idx.building or not idx.exists() or not idx.compatible():
            return []
        embedder = await asyncio.to_thread(get_embedder, cfg, False)
        rows, mat = idx.matrix()
    except StaticSightError:
        return []
    if not rows:
        return []
    import numpy as np

    out: list[str] = []
    for rel, line, name in targets:
        try:
            lines = split_lines(decode_source((cfg.workspace_root / rel).read_bytes()))
            text, a, b, _label = await _region_text(cfg, rel, lines, line, 0)
        except (StaticSightError, OSError):
            continue
        qv = (await asyncio.to_thread(embedder.embed, [text]))[0].astype(np.float64)
        cand = [i for i, r in enumerate(rows) if r[0] != rel]
        if not cand:
            continue
        sims = mat[cand].astype(np.float64) @ qv
        order = sorted(range(len(cand)), key=lambda k: (-_score(sims[k]), _row_key(rows[cand[k]])))
        hits = []
        seen: set[tuple] = set()
        for k in order:
            s = _score(sims[k])
            if s < threshold or len(hits) >= per_target:
                break
            r = rows[cand[k]]
            if _group_key(r) in seen:
                continue
            seen.add(_group_key(r))
            what = f"`{r[5]}`" if r[5] else r[4]
            hits.append(f"`{r[0]}:{r[1]}-{r[2]}` {what} ({s:.2f})")
        if hits:
            out.append(f"- `{name}` (`{rel}:{line}`) resembles: " + "; ".join(hits))
    return out


async def refresh_report(cfg: Config, full: bool = False) -> str:
    idx = get_semantic_index(cfg)
    title = "### 🧠 SEMANTIC INDEX REFRESH"
    if idx.building:
        return f"{title}\n{idx.progress_note()}"
    exists = idx.exists() and idx.compatible()
    pending = (await idx.drift()).total if exists and not full else None
    if pending is not None and pending <= cfg.semantic_auto_refresh_files:
        summary = await idx.refresh(full=False)
        return f"{title}\n✅ {summary[0].upper() + summary[1:]}. " + _index_line(idx, "").rstrip()
    idx.start_background(full=full or not exists)
    what = "Full rebuild" if (full or not exists) else f"Refresh of {pending} changed files"
    return (f"{title}\n🏗️ {what} started in the background ({idx.progress_note(short=True)}). "
            "Call get_index_status to follow progress; semantic_search keeps working on the current index meanwhile.")


def status_section(cfg: Config) -> list[str]:
    idx = get_semantic_index(cfg)
    out = ["", "### 🧠 SEMANTIC INDEX"]
    try:
        if idx.building:
            out.append(f"- **State:** building. {idx.progress_note()}")
        elif idx.state.status == "failed":
            out.append(f"- **State:** last refresh failed: {idx.state.error}")
        elif not idx.exists():
            out.append("- **State:** not built yet (built automatically on the first semantic_search, or call refresh_semantic_index)")
        elif not idx.compatible():
            out.append("- **State:** needs a rebuild (model or format changed); the next search starts it")
        else:
            meta = idx.store.get_meta()
            age = int(time.time() - float(meta.get("updated_at", "0")))
            out.append(f"- **State:** ready (last refresh {age}s ago{', HEAD ' + meta['head'][:10] if meta.get('head') else ''})")
        if idx.exists():
            c = idx.store.counts()
            out.append(f"- **Content:** {c['files']} files, {c['chunks']} chunks, {c['vectors']} vectors; skipped: "
                       + (", ".join(f"{n} {r}" for r, n in idx.store.skipped_by_reason().items()) or "none"))
            langs = idx.store.languages()[:8]
            if langs:
                out.append("- **Languages:** " + ", ".join(f"{l} ({n})" for l, n in langs))
        out.append(f"- **Model:** {model_id(cfg)}")
        out.append(f"- **Database:** `{idx.db_path}` ({idx.data_dir_reason})")
        if idx.state.last_summary:
            out.append(f"- **Last refresh:** {idx.state.last_summary}")
    except SemanticUnavailable as exc:
        out.append(f"- **State:** unavailable: {exc.message}" + (f" 💡 {exc.hint}" if exc.hint else ""))
    return out
