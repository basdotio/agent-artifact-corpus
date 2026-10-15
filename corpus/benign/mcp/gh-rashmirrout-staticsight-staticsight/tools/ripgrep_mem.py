"""ripgrep-powered memory-layout risk tracking and #include blast radius."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass

from ..config import CPP_GLOBS, Config, is_header, load_config
from ..core import md
from ..core.cpp_text import strip_code
from ..engines.ctags import FUNCTION_KINDS, TYPE_KINDS, innermost, try_ctags_for_files
from ..core.paths import matches_glob, read_lines
from ..engines.rg import rg_files, rg_search
from ..core.errors import InvalidArgument, StaticSightError
from .graph_gtags import normalize_symbol

CONTEXT_RADIUS = 2


@dataclass(frozen=True)
class RiskRule:
    key: str
    icon: str
    label: str
    explanation: str
    pattern: re.Pattern[str]


def _rules(name: str) -> list[RiskRule]:
    n = re.escape(name)
    return [
        RiskRule("io", "🌐", "raw I/O", "struct bytes sent/received/persisted directly: size, padding or member order changes break the wire/disk format and peers built from older code",
                 re.compile(r"\b(?:send|sendto|sendmsg|recv|recvfrom|recvmsg|write|read|pwrite|pread|writev|readv|fwrite|fread|ioctl|mmap)\s*\(")),
        RiskRule("mem", "🧬", "raw memory op", "memcpy/memmove/memset/memcmp over the object: layout changes shift offsets, and memcmp also compares padding bytes",
                 re.compile(r"\b(?:memcpy|memmove|memset|memcmp|bcopy|bzero|memcpy_s|memmove_s)\s*\(")),
        RiskRule("size", "📏", "size/offset assumption", "sizeof/offsetof/alignof values change with the layout; buffers, protocol lengths and array math sized from them shift silently",
                 re.compile(r"\b(?:sizeof|offsetof|alignof|_Alignof)\s*\(")),
        RiskRule("cast", "🎭", "type punning", "reinterpret_cast / C-style pointer cast / bit_cast reinterprets raw bytes: the layout must match the producer exactly",
                 re.compile(rf"\breinterpret_cast\s*<|\bbit_cast\s*<|\(\s*(?:const\s+)?(?:struct\s+)?{n}\s*(?:const\s*)?\*+\s*\)")),
        RiskRule("pack", "📦", "packing/alignment", "explicit packing or alignment: new members may break alignment assumptions or the ABI",
                 re.compile(r"#\s*pragma\s+pack|__attribute__\s*\(\(\s*(?:packed|aligned)|\balignas\s*\(")),
        RiskRule("assert", "✅", "layout assertion", "static_assert on the layout: it must be updated deliberately (good sign, but check the new value)",
                 re.compile(r"\bstatic_assert\s*\(")),
        RiskRule("union", "🔀", "union aliasing", "aliased through a union: all members must stay layout-compatible",
                 re.compile(r"\bunion\b")),
        RiskRule("endian", "🔁", "byte-order conversion", "per-field endianness conversion: new or resized fields need matching hton/ntoh handling",
                 re.compile(r"\b(?:hton[sl]|ntoh[sl]|htobe\d+|be\d+toh|htole\d+|le\d+toh|bswap\w*|__builtin_bswap\d+)\s*\(")),
        RiskRule("serial", "🗃️", "serialization", "custom (de)serializer: every added/removed member needs matching encode/decode logic and versioning",
                 re.compile(r"\b\w*(?:[Ss]eriali[sz]e|[Mm]arshal|[Ee]ncode|[Dd]ecode)\w*\s*\(")),
    ]


def _risk_keys(code: str, rules: list[RiskRule]) -> list[str]:
    return [r.key for r in rules if r.pattern.search(code)]


async def struct_risks_report(cfg: Config, struct_name: str, path_glob: str = "") -> str:
    name = normalize_symbol(struct_name)
    rules = _rules(name)
    by_key = {r.key: r for r in rules}
    res = await rg_search(cfg, name, word=True, fixed=True, context=CONTEXT_RADIUS)
    title = f"### ⚠️ LOW-LEVEL MEMORY USAGES: `{name}`"
    files = sorted(p for p in res.files if matches_glob(p, path_glob))
    if not files:
        return f"{title}\n✅ `{name}` is not referenced in any C/C++ file" + (f" matching `{path_glob}`." if path_glob else ".")
    tags_by_file = await try_ctags_for_files(cfg, files)
    hits: list[tuple[str, int, list[str], str, str, str]] = []  # path, line, keys, how, func, text
    defs: list[str] = []
    total_refs = 0
    for path in files:
        try:
            lines = read_lines(cfg.workspace_root / path)
        except StaticSightError:
            continue
        stripped = strip_code(lines)
        tags = tags_by_file.get(path, [])
        for t in tags:
            if t.short_name == name and t.kind in TYPE_KINDS:
                defs.append(f"{path}:{t.line}-{t.end}")
        word = re.compile(rf"\b{re.escape(name)}\b")
        match_lines = [m.line for m in res.files[path] if m.is_match and 0 < m.line <= len(lines) and word.search(stripped[m.line - 1])]
        total_refs += len(match_lines)
        direct: dict[int, list[str]] = {}
        for ln in match_lines:
            keys = _risk_keys(stripped[ln - 1], rules)
            if keys:
                direct[ln] = keys
        for ln in match_lines:
            if ln in direct:
                keys, how = direct[ln], "direct"
            else:
                if any(abs(d - ln) <= CONTEXT_RADIUS for d in direct):
                    continue
                keys = []
                for k in range(max(1, ln - CONTEXT_RADIUS), min(len(lines), ln + CONTEXT_RADIUS) + 1):
                    if k != ln:
                        keys += [x for x in _risk_keys(stripped[k - 1], rules) if x not in keys]
                if not keys:
                    continue
                how = "nearby"
            fn = innermost(tags, ln, FUNCTION_KINDS)
            hits.append((path, ln, keys, how, fn.qualified if fn else "", lines[ln - 1].strip()))
    head = [title]
    if defs:
        head.append("Defined at: " + ", ".join(f"`{d}`" for d in defs[:3]) + ".")
    if not hits:
        head.append(f"✅ No layout-sensitive operations found among {md.plural(total_refs, 'reference')}.")
        return "\n".join(head)
    head.append(
        f"Modifying the size, padding or member order of `{name}` may break {md.plural(len(hits), 'site')} "
        f"(out of {md.plural(total_refs, 'reference')}):"
    )
    order = [r.key for r in rules]
    items = []
    for i, (path, ln, keys, how, fn, text) in enumerate(hits, 1):
        keys = sorted(keys, key=order.index)
        labels = ", ".join(f"{by_key[k].icon} {by_key[k].label}" for k in keys)
        where = f" in `{fn}`" if fn else ""
        near = " (operation within ±2 lines)" if how == "nearby" else ""
        items.append(f"{i}. `{path}:{ln}`{where} — {labels}{near}\n   {md.code_span(text)}")
    body = md.truncate_list(items, cfg.max_results, "risk sites", "Use path_glob to focus.")
    used = sorted({k for h in hits for k in h[2]}, key=order.index)
    legend = ["", "**Why it matters:**", *[f"- {by_key[k].icon} **{by_key[k].label}:** {by_key[k].explanation}." for k in used]]
    return "\n".join(head + [""] + body + legend)


async def track_struct_risks(struct_name: str, path_glob: str = "") -> str:
    """Finds low-level memory operations that depend on the exact layout of a struct/class: sizeof/offsetof, memcpy/memmove/memset/memcmp, reinterpret_cast/C-style casts/bit_cast, raw send/recv/read/write/fwrite/mmap, byte-order conversions, packing pragmas, unions and static_asserts. Checks the matching line and the 2 lines around it, ignores comments, and labels each hit with its risk (wire format, on-disk format, padding, ABI). Use whenever a struct/class gains, loses, reorders or resizes a member."""
    return await struct_risks_report(load_config(), struct_name, path_glob)


# --------------------------------------------------------------------------- blast radius
_INCLUDE_RX = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]')


def _normalize_include(p: str) -> str:
    parts = [x for x in p.replace("\\", "/").split("/") if x not in ("", ".")]
    while parts and parts[0] == "..":
        parts.pop(0)
    return "/".join(parts)


def _include_matches(included: str, header_rel: str | None, header_name: str, includer: str) -> bool:
    inc = _normalize_include(included)
    if not inc:
        return False
    if header_rel is None:
        return inc == header_name or inc.endswith("/" + header_name)
    if header_rel == inc or header_rel.endswith("/" + inc):
        return True
    if included.startswith((".", "..")):
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(includer), included))
        return joined == header_rel
    return False


async def _direct_includers(
    cfg: Config, header_rel: str | None, header_name: str, all_basenames: dict[str, list[str]]
) -> list[tuple[str, int, str, bool]]:
    base = header_name.rsplit("/", 1)[-1]
    pattern = rf'^\s*#\s*include\s*["<]([^">]*/)?{re.escape(base)}[">]'
    res = await rg_search(cfg, pattern, globs=CPP_GLOBS)
    out = []
    ambiguous_base = len(all_basenames.get(base, [])) > 1
    for m in res.matches():
        im = _INCLUDE_RX.match(m.text)
        if not im:
            continue
        inc = im.group(1)
        if not _include_matches(inc, header_rel, header_name, m.path):
            continue
        if m.path == header_rel:
            continue
        amb = ambiguous_base and "/" not in _normalize_include(inc)
        out.append((m.path, m.line, m.text.strip(), amb))
    return out


async def blast_radius_report(cfg: Config, header_filename: str, transitive_depth: int = 2) -> str:
    raw = (header_filename or "").strip().replace("\\", "/")
    if not raw or raw.startswith("-") or any(c in raw for c in '"<>\n'):
        raise InvalidArgument(f"`{header_filename}` is not a valid header name.", "Pass e.g. `packet.hpp` or `src/net/packet.hpp`.")
    depth = max(1, min(int(transitive_depth or 1), 3))
    all_files = await rg_files(cfg)
    basenames: dict[str, list[str]] = {}
    for f in all_files:
        basenames.setdefault(f.rsplit("/", 1)[-1], []).append(f)
    norm = _normalize_include(raw)
    header_rel = norm if norm in all_files else None
    if header_rel is None:
        cands = [f for f in all_files if f == norm or f.endswith("/" + norm)]
        if len(cands) == 1:
            header_rel = cands[0]
    title = f"### 💥 BLAST RADIUS: `{header_rel or norm}`"
    direct = await _direct_includers(cfg, header_rel, norm, basenames)
    if not direct:
        note = "" if header_rel else " (header not found in the workspace; matched by name)"
        return f"{title}\n✅ No C/C++ file includes `{norm}`{note}."
    direct_files = sorted({d[0] for d in direct})
    levels: list[list[str]] = [direct_files]
    seen = set(direct_files) | ({header_rel} if header_rel else set())
    frontier = [f for f in direct_files if is_header(f)]
    for _ in range(depth - 1):
        nxt: list[str] = []
        for h in frontier:
            for p, _ln, _inc, _amb in await _direct_includers(cfg, h, h, basenames):
                if p not in seen:
                    seen.add(p)
                    nxt.append(p)
        if not nxt:
            break
        levels.append(sorted(nxt))
        frontier = [f for f in nxt if is_header(f)]
    affected = sorted(set().union(*levels))
    sources = [f for f in affected if not is_header(f)]
    tu_total = sum(1 for f in all_files if not is_header(f))
    share = f"{(100 * len(sources) / tu_total):.0f}%" if tu_total else "n/a"
    out = [
        title,
        f"- **Direct includers:** {md.plural(len(direct_files), 'file')}"
        + (f"; **transitive:** {md.plural(len(affected) - len(direct_files), 'more file')} (depth {len(levels)})" if len(levels) > 1 else ""),
        f"- **Translation units affected:** {len(sources)} of {tu_total} source files ({share}); headers affected: {len(affected) - len(sources)}",
    ]
    groups: dict[str, int] = {}
    for f in affected:
        d = posixpath.dirname(f) or "."
        groups[d] = groups.get(d, 0) + 1
    top = sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))
    out.append("- **By directory:** " + ", ".join(f"`{d}/` ({n})" for d, n in top[:10]) + (" …" if len(top) > 10 else ""))
    if any(d[3] for d in direct):
        out.append(
            f"- ⚠️ Some includes use the bare name `{norm.rsplit('/', 1)[-1]}`, which matches several headers in the repo; those hits are marked (ambiguous)."
        )
    items = []
    for path, ln, inc, amb in sorted(direct):
        items.append(f"- `{path}:{ln}` {md.code_span(inc)}" + (" (ambiguous)" if amb else ""))
    out += ["", "**Direct includers:**", *md.truncate_list(items, cfg.max_results, "includers")]
    if len(levels) > 1:
        trans = [f"- `{p}` (depth {i + 2})" for i, lvl in enumerate(levels[1:]) for p in lvl]
        out += ["", "**Transitive includers:**", *md.truncate_list(trans, cfg.max_results, "transitive includers")]
    if len(sources) >= 20 or (len(sources) >= 5 and tu_total and len(sources) / tu_total >= 0.25):
        out.append("\n_High-fan-out header: macro, inline, template or layout changes here recompile and can alter many modules._")
    return "\n".join(out)


async def get_include_blast_radius(header_filename: str, transitive_depth: int = 2) -> str:
    """Lists every C/C++ file that #includes a header (direct consumers), plus files that include it transitively through other headers, grouped by directory with the share of translation units affected. Use when a header changes (macros, inline functions, struct layout, templates, constants) to see which modules must be re-verified and rebuilt."""
    return await blast_radius_report(load_config(), header_filename, transitive_depth)
