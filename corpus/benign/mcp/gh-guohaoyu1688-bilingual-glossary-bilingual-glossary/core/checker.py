"""Longest-span terminology matching, aligned checks and reviewable repairs."""

from __future__ import annotations

import csv
import difflib
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

import polib
from defusedxml.ElementTree import fromstring

from .store import Glossary, GlossError


def pattern(text: str) -> re.Pattern:
    left = r"(?<![A-Za-z0-9_])" if text[0].isascii() and text[0].isalnum() else ""
    right = r"(?![A-Za-z0-9_])" if text[-1].isascii() and text[-1].isalnum() else ""
    return re.compile(left + re.escape(text) + right, re.IGNORECASE)


def occurrences(text: str, terms: list[dict], lang: str | None = None) -> list[dict]:
    if lang not in {None, "en", "zh"}:
        raise GlossError("Language must be en or zh")
    candidates = []
    for term in terms:
        forms = []
        for language in [lang] if lang else ["zh", "en"]:
            forms.append((term[language], language, "canonical"))
            forms += [(v, language, "synonym") for v in term["synonyms_" + language]]
            forms += [
                (v["text"], language, "forbidden")
                for v in term["forbidden"]
                if v["lang"] == language
            ]
        if term["abbr"]:
            forms.append((term["abbr"], lang or "en", "abbreviation"))
        for value, language, kind in forms:
            for match in pattern(value).finditer(text):
                candidates.append(
                    {
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(0),
                        "lang": language,
                        "kind": kind,
                        "term": term,
                    }
                )
    candidates.sort(
        key=lambda m: (
            -(m["end"] - m["start"]),
            m["start"],
            m["kind"] != "canonical",
            m["term"]["id"],
        )
    )
    selected = []
    for match in candidates:
        if not any(
            match["start"] < other["end"] and other["start"] < match["end"] for other in selected
        ):
            selected.append(match)
    return sorted(selected, key=lambda m: m["start"])


class Checker:
    def __init__(self, glossary: Glossary):
        self.glossary = glossary

    def terms(self, domain: str | None = None) -> list[dict]:
        return self.glossary.list(domain, status="approved")

    def check_text(
        self,
        text: str,
        lang: str | None = None,
        domain: str | None = None,
        file: str = "<text>",
        line: int = 1,
    ) -> list[dict]:
        if not isinstance(text, str) or len(text) > 5_000_000:
            raise GlossError("Text must be a string of at most 5 million characters")
        matches = occurrences(text, self.terms(domain), lang)
        issues, used = [], {}
        for match in matches:
            term = match["term"]
            key = (term["id"], match["lang"])
            base = {
                "file": file,
                "line": line + text.count("\n", 0, match["start"]),
                "term_id": term["id"],
                "term": term[match["lang"]],
                "found": match["text"],
                "suggestion": term[match["lang"]],
                "start": match["start"],
                "end": match["end"],
            }
            if match["kind"] == "forbidden":
                issues.append(
                    {
                        **base,
                        "code": "FORBIDDEN_VARIANT",
                        "message": "Replace the deprecated variant with the canonical term.",
                    }
                )
            elif match["kind"] != "abbreviation":
                forms = used.setdefault(key, set())
                folded = match["text"].casefold()
                if forms and folded not in forms:
                    issues.append(
                        {
                            **base,
                            "code": "INCONSISTENT_VARIANT",
                            "message": "Multiple allowed spellings of one concept occur; choose one consistently.",
                        }
                    )
                forms.add(folded)
        return issues

    def check_pair(
        self,
        source: str,
        target: str,
        source_lang: str = "zh",
        target_lang: str = "en",
        domain: str | None = None,
        file: str = "<pair>",
        line: int = 1,
    ) -> list[dict]:
        if {source_lang, target_lang} != {"zh", "en"}:
            raise GlossError("Language pair must be zh,en or en,zh")
        terms = self.terms(domain)
        source_matches = occurrences(source, terms, source_lang)
        target_matches = occurrences(target, terms, target_lang)
        accepted = {
            m["term"]["id"] for m in target_matches if m["kind"] in {"canonical", "abbreviation"}
        }
        seen = set()
        issues = self.check_text(target, target_lang, domain, file, line)
        for match in source_matches:
            term = match["term"]
            if term["id"] in seen:
                continue
            seen.add(term["id"])
            if term["id"] not in accepted:
                issues.append(
                    {
                        "file": file,
                        "line": line,
                        "term_id": term["id"],
                        "term": term[source_lang],
                        "found": None,
                        "suggestion": term[target_lang],
                        "code": "MISSING_TRANSLATION",
                        "message": "Source concept lacks its prescribed canonical target term or abbreviation.",
                    }
                )
        return issues

    def prompt(self, text: str, domain: str | None = None) -> dict:
        selected = {m["term"]["id"]: m["term"] for m in occurrences(text, self.terms(domain))}
        lines = [
            "Use the following canonical terminology when translating. Preserve meaning and report ambiguity.",
            "",
            "| Chinese term | English term | Abbreviation |",
            "| --- | --- | --- |",
        ]
        for row in selected.values():
            lines.append(
                "| "
                + " | ".join(
                    row[k].replace("|", r"\|").replace("\n", " ") for k in ["zh", "en", "abbr"]
                )
                + " |"
            )
        return {"terms": list(selected.values()), "prompt": "\n".join(lines) + "\n"}

    def check_file(
        self,
        path: str | Path,
        pair: str | None = None,
        lang: str | None = None,
        domain: str | None = None,
    ) -> list[dict]:
        path = Path(path)
        if not path.is_file():
            raise GlossError("Document not found", "NOT_FOUND", 3)
        if path.stat().st_size > 20 * 1024 * 1024:
            raise GlossError("Document exceeds 20 MiB")
        text = path.read_text(encoding="utf-8-sig")
        if not pair:
            return self.check_text(text, lang, domain, str(path))
        try:
            source_lang, target_lang = pair.split(",")
        except ValueError as exc:
            raise GlossError("Pair must be zh,en or en,zh") from exc
        issues = []
        for line, source, target in aligned(text, path.suffix, source_lang, target_lang):
            issues += self.check_pair(
                source, target, source_lang, target_lang, domain, str(path), line
            )
        return issues

    def fix(
        self,
        paths: list[str],
        write: bool = False,
        lang: str | None = None,
        domain: str | None = None,
    ) -> dict:
        changes = []
        for name in dict.fromkeys(paths):
            path = Path(name)
            if path.is_symlink() or not path.is_file():
                raise GlossError("Fix requires regular local files")
            if path.suffix.lower() not in {".md", ".txt"}:
                raise GlossError(
                    "Automatic fix supports text and Markdown; review structured files manually"
                )
            before = path.read_text(encoding="utf-8")
            after = before
            for match in reversed(occurrences(before, self.terms(domain), lang)):
                if match["kind"] == "forbidden":
                    after = (
                        after[: match["start"]]
                        + match["term"][match["lang"]]
                        + after[match["end"] :]
                    )
            if after != before:
                diff = "".join(
                    difflib.unified_diff(
                        before.splitlines(keepends=True),
                        after.splitlines(keepends=True),
                        fromfile=str(path),
                        tofile=str(path) + " (proposed)",
                    )
                )
                changes.append({"path": str(path), "before": before, "after": after, "diff": diff})
        backup = None
        written = []
        if write and changes:
            directory = self.glossary.directory / "backups"
            directory.mkdir(exist_ok=True)
            backup = directory / (
                "documents_"
                + datetime.now(self.glossary.zone).strftime("%Y%m%d_%H%M%S_%f")
                + ".zip"
            )
            with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as archive:
                mapping = {}
                for index, item in enumerate(changes):
                    name = f"{index:03d}_{Path(item['path']).name}"
                    archive.writestr(name, item["before"])
                    mapping[name] = item["path"]
                archive.writestr("manifest.json", json.dumps(mapping, indent=2))
            try:
                for item in changes:
                    path = Path(item["path"])
                    if path.read_text(encoding="utf-8") != item["before"]:
                        raise GlossError("Document changed during repair", "CONFLICT")
                    path.write_text(item["after"], encoding="utf-8")
                    written.append(item)
            except Exception:
                for item in written:
                    path = Path(item["path"])
                    if path.read_text(encoding="utf-8") == item["after"]:
                        path.write_text(item["before"], encoding="utf-8")
                raise
        return {
            "written": write,
            "files_changed": len(changes),
            "backup": str(backup) if backup else None,
            "diffs": [{"file": c["path"], "diff": c["diff"]} for c in changes],
        }


def aligned(
    text: str, suffix: str, source_lang: str, target_lang: str
) -> list[tuple[int, str, str]]:
    if {source_lang, target_lang} != {"zh", "en"}:
        raise GlossError("Language pair must be zh,en or en,zh")
    if suffix.lower() == ".csv":
        reader = csv.DictReader(io.StringIO(text))
        result = []
        if not reader.fieldnames or not {source_lang, target_lang}.issubset(reader.fieldnames):
            raise GlossError("CSV requires columns named for the two languages")
        previous = 1
        for row in reader:
            result.append((previous + 1, row[source_lang] or "", row[target_lang] or ""))
            previous = reader.line_num
        return result
    if suffix.lower() == ".po":
        document = polib.pofile(text)
        if any(entry.msgid_plural for entry in document if not entry.obsolete):
            raise GlossError("Plural PO entries are outside the supported singular subset")
        return [
            (entry.linenum or 1, entry.msgid, entry.msgstr)
            for entry in document
            if not entry.obsolete and entry.msgid and not entry.msgid_plural
        ]
    if suffix.lower() in {".xlf", ".xliff"}:
        root = fromstring(text)
        for element in root.iter():
            element.tag = element.tag.split("}")[-1]
        result = []
        units = list(root.iter("trans-unit")) or list(root.iter("segment"))
        for unit in units:
            source, target = unit.find("source"), unit.find("target")
            if source is None:
                continue
            source_text = "".join(source.itertext())
            target_text = "".join(target.itertext()) if target is not None else ""
            position = text.find(source_text)
            line = text.count("\n", 0, max(position, 0)) + 1
            result.append((line, source_text, target_text))
        return result
    paragraphs = [
        (text.count("\n", 0, m.start()) + 1, m.group(0))
        for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*", text)
    ]
    if len(paragraphs) % 2:
        raise GlossError(
            "Aligned Markdown/text requires alternating source and target paragraphs separated by blank lines"
        )
    return [
        (paragraphs[i][0], paragraphs[i][1], paragraphs[i + 1][1])
        for i in range(0, len(paragraphs), 2)
    ]
