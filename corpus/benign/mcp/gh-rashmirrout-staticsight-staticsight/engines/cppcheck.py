"""cppcheck adapter: builds the command, runs it via the platform layer, parses the XML report."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..core.errors import ToolFailed
from .base import run_engine, to_posix

SEVERITY_ORDER = {"error": 0, "warning": 1, "portability": 2, "performance": 3, "style": 4, "information": 5}
NOISE_IDS = {
    "missingInclude", "missingIncludeSystem", "checkersReport", "normalCheckLevelMaxBranches", "toomanyconfigs",
    "unmatchedSuppression", "noValidConfiguration", "unknownMacro", "syntaxError", "internalAstError", "preprocessorErrorDirective",
}
PARSE_PROBLEM_IDS = {"syntaxError", "unknownMacro", "internalAstError", "preprocessorErrorDirective", "noValidConfiguration"}


@dataclass
class Finding:
    id: str
    severity: str
    msg: str
    cwe: str
    line: int
    locations: list[tuple[str, int, str]] = field(default_factory=list)


def include_dirs(cfg: Config, abs_file: Path) -> list[str]:
    root = cfg.workspace_root
    dirs: list[Path] = []
    cur = abs_file.parent
    while True:
        dirs.append(cur)
        for sub in ("include", "inc"):
            if (cur / sub).is_dir():
                dirs.append(cur / sub)
        if cur == root or root not in cur.parents:
            break
        cur = cur.parent
    for sub in ("include", "src", "inc"):
        if (root / sub).is_dir():
            dirs.append(root / sub)
    uniq = list(dict.fromkeys(dirs))
    return [d.relative_to(root).as_posix() if d != root else "." for d in uniq][:12]


def parse_cppcheck_xml(xml_text: str, rel: str) -> tuple[list[Finding], int, str, bool, list[str]]:
    """Return (findings in rel, findings elsewhere, cppcheck version, parse_problem, unknown macro names)."""
    start = xml_text.find("<?xml")
    if start < 0:
        start = xml_text.find("<results")
    if start < 0:
        raise ToolFailed("cppcheck produced no XML output.")
    try:
        root = ET.fromstring(xml_text[start:])
    except ET.ParseError as exc:
        raise ToolFailed(f"Could not parse cppcheck XML: {exc}") from exc
    ver_el = root.find("cppcheck")
    version = ver_el.get("version", "") if ver_el is not None else ""
    findings: list[Finding] = []
    elsewhere = 0
    parse_problem = False
    macros: list[str] = []
    for err in root.iter("error"):
        eid = err.get("id", "")
        if eid in PARSE_PROBLEM_IDS:
            parse_problem = True
            mm = re.search(r"If (\w+) is a macro", err.get("msg", ""))
            if mm and mm.group(1) not in macros:
                macros.append(mm.group(1))
        if eid in NOISE_IDS:
            continue
        locs = [
            (to_posix(loc.get("file", "")), int(loc.get("line", "0") or 0), loc.get("info", ""))
            for loc in err.findall("location")
        ]
        own = [loc for loc in locs if to_posix(loc[0]) == rel]
        if not own:
            elsewhere += 1
            continue
        findings.append(
            Finding(
                id=eid,
                severity=err.get("severity", "information"),
                msg=err.get("msg", ""),
                cwe=err.get("cwe", ""),
                line=own[0][1],
                locations=own,
            )
        )
    uniq: dict[tuple, Finding] = {}
    for f in findings:
        uniq.setdefault((f.line, f.id, f.msg), f)
    ordered = sorted(uniq.values(), key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.line, f.id))
    return ordered, elsewhere, version, parse_problem, macros



_WIN_INCLUDE = re.compile(
    r'^\s*#\s*include\s*[<"](?:windows|winbase|windef|wtypes|winerror|atlbase|objbase|winsock2|ntddk|wdm|ntifs)\.h[">]',
    re.I | re.M,
)
_SAL = re.compile(r"\b(?:_In_|_Out_|_Inout_|_In_opt_|_Out_opt_|_Inout_opt_|_In_reads_\w*|_Out_writes_\w*|__in|__out|__inout|__in_opt|__out_opt)\b")
_WIN_TYPES = re.compile(r"\b(?:HRESULT|DWORD|HANDLE|LPCWSTR|LPWSTR|LPCSTR|BOOL|WINAPI|__stdcall|HKEY|SC_HANDLE)\b")
MSVC_ARGS = ["--library=windows", "--platform=win64", "-D_WIN32", "-D_MSC_VER=1930"]


def wants_msvc(source_text: str) -> bool:
    """Heuristic: does this file target Windows/MSVC? (STATICSIGHT_CPPCHECK_MSVC=0 disables, =1 forces.)"""
    mode = os.environ.get("STATICSIGHT_CPPCHECK_MSVC", "auto").strip().lower()
    if mode in ("0", "false", "no", "off"):
        return False
    if mode in ("1", "true", "yes", "on"):
        return True
    if _WIN_INCLUDE.search(source_text) or _SAL.search(source_text):
        return True
    return len(set(_WIN_TYPES.findall(source_text))) >= 2


def base_args(rel: str) -> list[str]:
    lang = "c" if rel.lower().endswith(".c") else "c++"
    return [
        "--xml", "--xml-version=2", "--enable=warning,style,performance,portability", "--inline-suppr",
        f"--language={lang}", "--std=c11" if lang == "c" else "--std=c++17", "--quiet", "--max-configs=4",
        "--suppress=missingIncludeSystem", "--suppress=missingInclude", "--suppress=unmatchedSuppression",
        "--suppress=checkersReport",
    ] + os.environ.get("STATICSIGHT_CPPCHECK_ARGS", "").split()


async def run_cppcheck(
    cfg: Config, rel: str, abs_path: Path, include: bool, extra: list[str] | None = None
) -> tuple[list[Finding], int, str, bool, list[str]]:
    args = base_args(rel) + list(extra or [])
    if include:
        args += [f"-I{d}" for d in include_dirs(cfg, abs_path)]
    args.append("./" + rel if rel.startswith("-") else rel)
    res = await run_engine("cppcheck", args, cwd=cfg.workspace_root, timeout=cfg.cppcheck_timeout_s)
    if "<results" not in res.stderr:
        raise ToolFailed(f"cppcheck failed (exit {res.returncode}): {(res.stderr or res.stdout).strip()[:300]}")
    return parse_cppcheck_xml(res.stderr, rel)
