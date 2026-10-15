"""GNU Global powered navigation: callers, definitions and contracts (with ripgrep + ctags fallback)."""

from __future__ import annotations

import re

from ..config import Config, is_cpp_file, is_header, load_config
from ..core import md
from ..core.cpp_text import balanced_parens, extract_leading_comment, strip_code
from ..engines import gnu_global
from ..engines.ctags import DEFINITION_KINDS, FUNCTION_KINDS, TYPE_KINDS, Tag, innermost, try_ctags_for_files
from ..core.paths import matches_glob, read_lines
from ..core.errors import InvalidArgument, StaticSightError
from ..engines.gnu_global import Hit
from ..engines.rg import rg_search
from ..indexer import get_indexer

_IDENT = re.compile(r"^[A-Za-z_~][A-Za-z0-9_]*$")
_GLOBAL_LINE = gnu_global.GLOBAL_LINE
MAX_FILES_FALLBACK = 300

SOURCE_GLOBAL = "GNU Global"
SOURCE_RG = "ripgrep fallback: text match, lower precision"


def normalize_symbol(symbol: str) -> str:
    sym = (symbol or "").strip()
    if sym.endswith("()"):
        sym = sym[:-2]
    short = sym.rsplit("::", 1)[-1]
    if not _IDENT.match(short):
        raise InvalidArgument(
            f"`{symbol}` is not a valid C++ identifier.", "Pass a plain name such as `process_packet` or `Router::process_packet`."
        )
    return short


class _FileCache:
    """Per-request cache of file lines, stripped lines and ctags."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.lines: dict[str, list[str]] = {}
        self.stripped: dict[str, list[str]] = {}
        self.tags: dict[str, list[Tag]] = {}

    def get_lines(self, path: str) -> list[str]:
        if path not in self.lines:
            try:
                self.lines[path] = read_lines(self.cfg.workspace_root / path)
            except (StaticSightError, OSError):
                self.lines[path] = []
        return self.lines[path]

    def get_stripped(self, path: str) -> list[str]:
        if path not in self.stripped:
            self.stripped[path] = strip_code(self.get_lines(path))
        return self.stripped[path]

    async def load_tags(self, paths: list[str]) -> None:
        todo = [p for p in dict.fromkeys(paths) if p not in self.tags]
        if todo:
            got = await try_ctags_for_files(self.cfg, todo)
            for p in todo:
                self.tags[p] = got.get(p, [])


async def global_query(cfg: Config, flag: str, symbol: str) -> list[Hit] | None:
    """Run `global <flag> -- symbol`. Returns None when the index is not usable (caller falls back)."""
    idx = get_indexer(cfg)
    if not await idx.ensure_ready():
        return None
    return await gnu_global.query(cfg, idx.env(), flag, symbol)


async def _candidate_files(cfg: Config, sym: str) -> list[str]:
    res = await rg_search(cfg, sym, word=True, fixed=True, max_count=1)
    return sorted(res.files)[:MAX_FILES_FALLBACK]


async def find_definitions(cfg: Config, sym: str, fc: _FileCache) -> tuple[list[Tag], str]:
    """Definitions of sym as ctags Tags (kind-aware), plus the engine used."""
    hits = await global_query(cfg, "-xd", sym)
    source = SOURCE_GLOBAL
    defs: list[Tag] = []
    if hits:
        await fc.load_tags([h.path for h in hits if is_cpp_file(h.path)])
        for h in hits:
            tag = next(
                (t for t in fc.tags.get(h.path, []) if t.line == h.line and t.short_name == sym and t.kind != "prototype"),
                None,
            )
            defs.append(tag or Tag(name=sym, kind="definition", line=h.line, end=h.line, path=h.path))
    if not defs:
        if hits is None:
            source = SOURCE_RG
        files = await _candidate_files(cfg, sym)
        await fc.load_tags(files)
        for p in files:
            for t in fc.tags.get(p, []):
                if t.short_name == sym and t.kind in DEFINITION_KINDS:
                    defs.append(t)
        if hits is not None and defs:
            source = "ctags (GNU Global had no definition)"
    uniq = {(t.path, t.line, t.kind): t for t in defs}
    return [uniq[k] for k in sorted(uniq)], source


async def find_declarations(cfg: Config, sym: str, fc: _FileCache) -> list[Tag]:
    files = await _candidate_files(cfg, sym)
    await fc.load_tags(files)
    out = [t for p in files for t in fc.tags.get(p, []) if t.short_name == sym and t.kind == "prototype"]
    return sorted(out, key=lambda t: (not is_header(t.path), t.path, t.line))


# --------------------------------------------------------------------------- callers
_CHAIN = re.compile(r"^[\w\.\->\[\]\(\)\*&:\s]*$")


def classify_call(code: str, sym: str) -> str:
    m = re.search(rf"\b{re.escape(sym)}\b", code)
    if not m:
        return ""
    after_sym = code[m.end():].lstrip()
    if not after_sym.startswith("(") and not after_sym.startswith("<"):
        return "referenced (address/callback)"
    bp = balanced_parens(code, m.end())
    after = code[bp[1] + 1 :].strip() if bp else ""
    prefix = code[: m.start()].strip()
    if re.search(r"\(\s*void\s*\)\s*[\w\.\->:]*$", prefix):
        return "result explicitly discarded"
    if after == ";" and _CHAIN.match(prefix) and "(" not in prefix.replace("->", "") and not prefix.startswith("return"):
        return "⚠️ result ignored"
    return "result used"


async def callers_report(cfg: Config, symbol: str, path_glob: str = "") -> str:
    sym = normalize_symbol(symbol)
    fc = _FileCache(cfg)
    hits = await global_query(cfg, "-xr", sym)
    source = SOURCE_GLOBAL
    if hits is None:
        source = SOURCE_RG
        res = await rg_search(cfg, rf"\b{sym}\s*\(|&\s*(?:\w+::)*{sym}\b")
        hits = [Hit(m.path, m.line, m.text) for m in res.matches()]
    hits = [h for h in hits if is_cpp_file(h.path) and matches_glob(h.path, path_glob)]
    await fc.load_tags([h.path for h in hits])
    defs, _ = await find_definitions(cfg, sym, fc)
    ret_types = {t.return_type for t in defs if t.kind in FUNCTION_KINDS | {"prototype"} and t.return_type}
    returns_void = bool(ret_types) and ret_types <= {"void"}
    rows: list[tuple[str, int, str, str, str]] = []
    for h in hits:
        stripped = fc.get_stripped(h.path)
        lines = fc.get_lines(h.path)
        if not (0 < h.line <= len(lines)):
            continue
        code = stripped[h.line - 1]
        if not re.search(rf"\b{re.escape(sym)}\b", code):
            continue  # comment or string literal
        tags = fc.tags.get(h.path, [])
        if any(t.line == h.line and t.short_name == sym and t.kind in ("prototype", "function", "macro") for t in tags):
            continue  # declaration / definition, not a call
        fn = innermost(tags, h.line, FUNCTION_KINDS)
        caller = fn.qualified if fn else "(file scope)"
        usage_kind = classify_call(code, sym)
        if usage_kind == "referenced (address/callback)" and not re.search(
            rf"&\s*(?:\w+::)*{re.escape(sym)}\b|(?:\w+::|\.|->){re.escape(sym)}\b\s*[,)]", code
        ):
            continue  # same-named variable/parameter, not a call or function reference
        usage = "" if returns_void else usage_kind
        rows.append((h.path, h.line, caller, usage, lines[h.line - 1].strip()))
    title = f"### 📞 UPSTREAM CALLERS: `{sym}`"
    if not rows:
        return f"{title}\n✅ No call sites found (source: {source}). The symbol may be unused, called via macro, or only referenced dynamically."
    files = sorted({r[0] for r in rows})
    ignored = sum(1 for r in rows if r[3].startswith("⚠️"))
    head = [title, f"Found {md.plural(len(rows), 'call site')} in {md.plural(len(files), 'file')} (source: {source})."]
    if ret_types:
        rt = ", ".join(f"`{t}`" for t in sorted(ret_types))
        head.append(
            f"Returns {rt}"
            + (f"; ⚠️ {ignored} caller(s) ignore the result — check they tolerate new error values." if ignored else ".")
        )
    items: list[str] = []
    cur = None
    for i, (path, line, caller, usage, text) in enumerate(rows, 1):
        entry = []
        if path != cur:
            entry.append(f"**`{path}`**")
            cur = path
        suffix = f" — {usage}" if usage else ""
        entry.append(f"{i}. L{line} in `{caller}`{suffix}")
        entry.append(f"   {md.code_span(text)}")
        items.append("\n".join(entry))
    shown = md.truncate_list(items, cfg.max_results, "call sites", "Use path_glob to focus on a directory.")
    if len(rows) > cfg.max_results:
        counts: dict[str, int] = {}
        for r in rows:
            counts[r[0]] = counts.get(r[0], 0) + 1
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        shown.append("_Top files: " + ", ".join(f"`{p}` ({n})" for p, n in top) + "._")
    return "\n".join(head + [""] + shown)


async def get_upstream_callers(symbol: str, path_glob: str = "") -> str:
    """Finds every call site of a function/method across the repository (GNU Global reference index; falls back to ripgrep when the index is unavailable). Each hit shows file:line, the enclosing caller function, the call line, and whether the return value is used or ignored. Use after changing a function's signature, return values, error codes, preconditions or side effects to check that callers still hold up."""
    return await callers_report(load_config(), symbol, path_glob)


# --------------------------------------------------------------------------- definitions
def _loc(t: Tag) -> str:
    return f"{t.path}:{t.line}" if t.end <= t.line else f"{t.path}:{t.line}-{t.end}"


async def definitions_report(cfg: Config, symbol: str) -> str:
    sym = normalize_symbol(symbol)
    fc = _FileCache(cfg)
    defs, source = await find_definitions(cfg, sym, fc)
    title = f"### 📍 DEFINITIONS: `{sym}`"
    if not defs:
        return f"{title}\n❌ No definition found (source: {source}). It may come from a system/third-party header or be generated by a macro."
    items = []
    for i, t in enumerate(defs, 1):
        line = f"{i}. `{_loc(t)}` — {t.kind} `{t.qualified}`"
        if t.kind in ("function", "macro") and t.signature:
            line += f"\n   {md.code_span(t.display_signature)}"
        elif t.kind == "definition":
            text = fc.get_lines(t.path)[t.line - 1].strip() if 0 < t.line <= len(fc.get_lines(t.path)) else ""
            if text:
                line += f"\n   {md.code_span(text)}"
        items.append(line)
    out = [f"{title} ({len(defs)}, source: {source})", *md.truncate_list(items, cfg.max_results, "definitions")]
    return "\n".join(out)


async def get_symbol_definition(symbol: str) -> str:
    """Locates where a C++ symbol (function, method, class, struct, enum, macro, typedef) is defined, including overloads, with kind, signature and file:line (GNU Global; falls back to ripgrep + ctags). Use to jump to the implementation of something referenced in a diff."""
    return await definitions_report(load_config(), symbol)


# --------------------------------------------------------------------------- contract
_QUALIFIERS = [
    ("[[nodiscard]]", re.compile(r"\[\[\s*nodiscard")),
    ("[[deprecated]]", re.compile(r"\[\[\s*deprecated")),
    ("template", re.compile(r"^\s*template\s*<")),
    ("virtual", re.compile(r"\bvirtual\b")),
    ("pure virtual (= 0)", re.compile(r"\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?=\s*0\s*;")),
    ("static", re.compile(r"\bstatic\b")),
    ("inline", re.compile(r"\binline\b")),
    ("constexpr", re.compile(r"\bconstexpr\b")),
    ("explicit", re.compile(r"\bexplicit\b")),
    ("const", re.compile(r"\)\s*const\b")),
    ("noexcept", re.compile(r"\bnoexcept\b")),
    ("override", re.compile(r"\boverride\b")),
    ("final", re.compile(r"\bfinal\b")),
    ("= delete", re.compile(r"=\s*delete\b")),
    ("= default", re.compile(r"=\s*default\b")),
]
_DOXY_TAG = re.compile(r"^[@\\](pre|post|return|returns|retval|throws|throw|exception|warning|note|attention|invariant|param|thread_safety|deprecated)\b")
_OBLIGATION = re.compile(
    r"\b(must|shall|never|always|required?|do not|don't|only|thread[- ]safe|not thread[- ]safe|ownership|owns|caller|callee|"
    r"non-null|not null|nullptr|lock(?:ed)?|mutex|reentrant|blocking|free|release|paired)\b",
    re.IGNORECASE,
)


def _decl_text(stripped: list[str], lines: list[str], t: Tag) -> str:
    start = max(t.line - 2, 0)
    chunk: list[str] = []
    for i in range(start, min(len(lines), t.line + 6)):
        chunk.append(stripped[i])
        if i >= t.line - 1 and ("{" in stripped[i] or ";" in stripped[i]):
            break
    return " ".join(chunk)


def _qualifiers(decl: str) -> list[str]:
    head = decl.split("{", 1)[0]
    return [name for name, rx in _QUALIFIERS if rx.search(head)]


def _obligations(doc: list[str]) -> list[str]:
    out: list[str] = []
    cur: str | None = None
    for line in doc + [""]:
        tm = _DOXY_TAG.match(line)
        if tm or not line.strip():
            if cur:
                out.append(cur)
            cur = None
            if tm and tm.group(1) not in ("param",) or (tm and _OBLIGATION.search(line)):
                cur = line.strip()
            continue
        if cur is not None:
            cur += " " + line.strip()
        elif _OBLIGATION.search(line):
            out.append(line.strip())
    return list(dict.fromkeys(out))


async def contract_report(cfg: Config, symbol: str) -> str:
    sym = normalize_symbol(symbol)
    fc = _FileCache(cfg)
    defs, source = await find_definitions(cfg, sym, fc)
    decls = await find_declarations(cfg, sym, fc)
    title = f"### 🧩 SYMBOL CONTRACT: `{sym}`"
    if not defs and not decls:
        return f"{title}\n❌ No declaration or definition found (source: {source})."
    out = [title, f"_Sources: {source}; declarations via ctags._"]
    entries = [("Declaration", t) for t in decls[:3]] + [("Definition", t) for t in defs[:3]]
    doc_shown = False
    quals: list[str] = []
    for label, t in entries:
        lines = fc.get_lines(t.path)
        stripped = fc.get_stripped(t.path)
        if not (0 < t.line <= len(lines)):
            continue
        sig = t.display_signature if t.kind in FUNCTION_KINDS | {"prototype", "macro"} else f"{t.kind} {t.qualified}"
        out.append(f"- **{label}:** `{_loc(t)}` — {md.code_span(sig)}")
        for q in _qualifiers(_decl_text(stripped, lines, t)):
            if q not in quals:
                quals.append(q)
    if len(decls) + len(defs) > len(entries):
        out.append(f"- _…and {len(decls) + len(defs) - len(entries)} more declarations/definitions (overloads)._")
    if quals:
        out.append("- **Qualifiers:** " + ", ".join(f"`{q}`" for q in quals))
    for label, t in entries:
        lines = fc.get_lines(t.path)
        doc = extract_leading_comment(lines, t.line - 1)
        if not doc:
            continue
        out.append(f"\n**📜 Doc comment** (`{t.path}:{t.line}`):")
        out += [f"> {md.clip(d, 200)}" if d else ">" for d in doc[:25]]
        if len(doc) > 25:
            out.append(f"> _…{len(doc) - 25} more lines_")
        obligations = _obligations(doc)
        if obligations:
            out.append("\n**⚖️ Obligations / preconditions:**")
            out += [f"- {md.clip(o, 240)}" for o in obligations[:10]]
        doc_shown = True
        break
    if not doc_shown:
        out.append("\n_No doc comment found above the declaration/definition. Infer the contract from the body and callers._")
    body_def = next((t for t in defs if t.kind in FUNCTION_KINDS | TYPE_KINDS), None)
    if body_def:
        lines = fc.get_lines(body_def.path)
        span = body_def.end - body_def.line + 1
        limit = 25 if body_def.kind in FUNCTION_KINDS else 40
        if 1 < span <= limit:
            out += [
                f"\n**Body** (`{_loc(body_def)}`):",
                "```cpp",
                *md.numbered_code(lines[body_def.line - 1 : body_def.end], body_def.line),
                "```",
            ]
        elif span > limit:
            out.append(
                f"\n_Body is {span} lines: use `get_branch_skeleton(\"{body_def.path}\", symbol=\"{body_def.qualified}\")`._"
            )
    return "\n".join(out)


async def get_symbol_contract(symbol: str) -> str:
    """Shows the contract of a C++ function or type used by the diff: declaration and definition signatures, qualifiers (const, noexcept, virtual, override, static, [[nodiscard]], ...), the leading doc comment, Doxygen tags (@pre, @post, @return, @throws, @warning, @note) and obligation keywords (MUST, NEVER, thread-safe, ownership, non-null). Use to check that changed code honours the requirements of what it calls (e.g. every allocation must be released, pointer must be non-null, lock must be held)."""
    return await contract_report(load_config(), symbol)
