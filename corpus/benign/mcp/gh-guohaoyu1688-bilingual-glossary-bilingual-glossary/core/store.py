"""Transactional terminology records, local search and portable snapshots."""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from defusedxml.ElementTree import fromstring
from pypinyin import Style, lazy_pinyin
from rapidfuzz.fuzz import WRatio, ratio

FIELDS = [
    "id",
    "domain",
    "zh",
    "en",
    "abbr",
    "definition_zh",
    "definition_en",
    "notes",
    "source",
    "status",
    "updated_at",
]
LISTS = ["synonyms_zh", "synonyms_en", "forbidden"]
KB_FIELDS = ["zh", "en", "abbr", "definition_zh", "definition_en"]
NS = "urn:iso:std:iso:30042:ed-2"


class GlossError(Exception):
    def __init__(self, message: str, code: str = "INVALID_INPUT", exit_code: int = 2):
        super().__init__(message)
        self.code, self.exit_code = code, exit_code


def now() -> str:
    return datetime.now(UTC).isoformat()


def normalize(record: dict) -> dict:
    if not isinstance(record, dict):
        raise GlossError("A term must be an object")
    unknown = set(record) - set(FIELDS + LISTS)
    if unknown:
        raise GlossError("Unknown fields: " + ", ".join(sorted(unknown)))
    row = {field: record.get(field, "") for field in FIELDS}
    row["id"] = row["id"] or str(uuid.uuid4())
    row["domain"] = row["domain"] or "general"
    row["status"] = row["status"] or "draft"
    row["updated_at"] = row["updated_at"] or now()
    if any(not isinstance(value, str) for value in row.values()):
        raise GlossError("Term fields must be strings")
    row = {key: value.strip() for key, value in row.items()}
    if not row["zh"] or not row["en"]:
        raise GlossError("Both zh and en are required")
    if row["status"] not in {"draft", "approved"}:
        raise GlossError("Status must be draft or approved")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", row["domain"]):
        raise GlossError("Domain must be a lowercase slug")
    if len(row["id"]) > 100 or any(len(value) > 20000 for value in row.values()):
        raise GlossError("Term fields exceed size limits")
    for field in LISTS:
        values = record.get(field, [])
        if isinstance(values, str):
            try:
                values = json.loads(values) if values else []
            except json.JSONDecodeError as exc:
                raise GlossError(f"{field} must be a JSON array") from exc
        if not isinstance(values, list) or len(values) > 100:
            raise GlossError(f"{field} must be an array of at most 100 items")
        if field != "forbidden":
            if not all(isinstance(v, str) and v.strip() for v in values):
                raise GlossError("Synonyms must be nonempty strings")
            row[field] = list(dict.fromkeys(v.strip() for v in values))
        else:
            output = []
            for value in values:
                if isinstance(value, str):
                    value = {
                        "lang": "zh" if re.search(r"[\u3400-\u9fff]", value) else "en",
                        "text": value,
                    }
                if (
                    not isinstance(value, dict)
                    or set(value) != {"lang", "text"}
                    or value["lang"] not in {"zh", "en"}
                    or not isinstance(value["text"], str)
                    or not value["text"].strip()
                ):
                    raise GlossError("Forbidden variants require lang (zh/en) and nonempty text")
                item = {"lang": value["lang"], "text": value["text"].strip()}
                if item not in output:
                    output.append(item)
            row[field] = output
    for lang in ["zh", "en"]:
        allowed = {
            row[lang].casefold(),
            row["abbr"].casefold(),
            *[v.casefold() for v in row[f"synonyms_{lang}"]],
        }
        if any(v["text"].casefold() in allowed for v in row["forbidden"] if v["lang"] == lang):
            raise GlossError("A variant cannot be both allowed and forbidden")
    return row


class Glossary:
    def __init__(self, data_dir: str | Path = "data", zone: str = "Asia/Shanghai"):
        self.directory = Path(data_dir).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "glossary.db"
        self.zone = ZoneInfo(zone)
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS terms (
                    id TEXT PRIMARY KEY, domain TEXT NOT NULL, zh TEXT NOT NULL, en TEXT NOT NULL,
                    abbr TEXT NOT NULL, definition_zh TEXT NOT NULL, definition_en TEXT NOT NULL,
                    notes TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL,
                    UNIQUE(domain,zh), UNIQUE(domain,en COLLATE NOCASE));
                CREATE TABLE IF NOT EXISTS variants (
                    term_id TEXT NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
                    lang TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL,
                    UNIQUE(term_id,lang,text,kind));
                CREATE VIRTUAL TABLE IF NOT EXISTS terms_fts USING fts5(id UNINDEXED, text);
            """)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        return con

    @staticmethod
    def unpack(con: sqlite3.Connection, row) -> dict:
        result = dict(row)
        result.update({field: [] for field in LISTS})
        for variant in con.execute(
            "SELECT * FROM variants WHERE term_id=? ORDER BY rowid", (row["id"],)
        ):
            if variant["kind"] == "synonym":
                result[f"synonyms_{variant['lang']}"].append(variant["text"])
            else:
                result["forbidden"].append({"lang": variant["lang"], "text": variant["text"]})
        return result

    def list(self, domain: str | None = None, status: str | None = None) -> list[dict]:
        query, args = "SELECT * FROM terms WHERE 1=1", []
        for name, value in [("domain", domain), ("status", status)]:
            if value:
                query += f" AND {name}=?"
                args.append(value)
        with self.connect() as con:
            return [self.unpack(con, r) for r in con.execute(query + " ORDER BY domain,en", args)]

    def get(self, identifier: str) -> dict:
        with self.connect() as con:
            row = con.execute("SELECT * FROM terms WHERE id=?", (identifier,)).fetchone()
            if row is None:
                raise GlossError("Term not found", "NOT_FOUND", 3)
            return self.unpack(con, row)

    @staticmethod
    def write(con: sqlite3.Connection, row: dict) -> None:
        con.execute(
            "INSERT INTO terms VALUES ("
            + ",".join("?" for _ in FIELDS)
            + ") ON CONFLICT(id) DO UPDATE SET "
            + ",".join(f"{f}=excluded.{f}" for f in FIELDS if f != "id"),
            [row[f] for f in FIELDS],
        )
        con.execute("DELETE FROM variants WHERE term_id=?", (row["id"],))
        for lang in ["zh", "en"]:
            for text in row[f"synonyms_{lang}"]:
                con.execute(
                    "INSERT INTO variants VALUES (?,?,?,?)", (row["id"], lang, text, "synonym")
                )
        for variant in row["forbidden"]:
            con.execute(
                "INSERT INTO variants VALUES (?,?,?,?)",
                (row["id"], variant["lang"], variant["text"], "forbidden"),
            )
        con.execute("DELETE FROM terms_fts WHERE id=?", (row["id"],))
        text = " ".join(
            [row["zh"], row["en"], row["abbr"], *row["synonyms_zh"], *row["synonyms_en"]]
        )
        con.execute(
            "INSERT INTO terms_fts VALUES (?,?)",
            (row["id"], text + " " + " ".join(re.findall(r"[\u3400-\u9fff]", text))),
        )

    def add(self, record: dict) -> dict:
        row = normalize(record)
        try:
            with self.connect() as con:
                if con.execute("SELECT 1 FROM terms WHERE id=?", (row["id"],)).fetchone():
                    raise GlossError("Term ID already exists", "CONFLICT")
                self.write(con, row)
        except sqlite3.IntegrityError as exc:
            raise GlossError("A canonical term already exists in this domain", "CONFLICT") from exc
        return row

    def update(
        self, identifier: str, changes: dict, expected_updated_at: str | None = None
    ) -> dict:
        if set(changes) & {"id", "updated_at"}:
            raise GlossError("ID and update timestamp cannot be edited")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            old = con.execute("SELECT * FROM terms WHERE id=?", (identifier,)).fetchone()
            if old is None:
                raise GlossError("Term not found", "NOT_FOUND", 3)
            if expected_updated_at and old["updated_at"] != expected_updated_at:
                raise GlossError("Term changed since it was loaded", "CONFLICT")
            row = normalize({**self.unpack(con, old), **changes, "updated_at": now()})
            try:
                self.write(con, row)
            except sqlite3.IntegrityError as exc:
                raise GlossError("Canonical term collision", "CONFLICT") from exc
        return row

    def delete(self, identifier: str, confirm: bool = False) -> dict:
        if not confirm:
            raise GlossError("Deletion requires --yes / confirm=true", "CONFIRM_REQUIRED")
        self.get(identifier)
        backup = self.backup()
        with self.connect() as con:
            con.execute("DELETE FROM terms WHERE id=?", (identifier,))
            con.execute("DELETE FROM terms_fts WHERE id=?", (identifier,))
        return {"deleted": identifier, "backup": backup["path"]}

    def search(
        self, query: str, domain: str | None = None, lang: str | None = None, limit: int = 10
    ) -> list[dict]:
        if not query.strip() or not 1 <= limit <= 100:
            raise GlossError("Query must be nonempty and limit must be 1..100")
        if lang not in {None, "zh", "en"}:
            raise GlossError("Language must be zh or en")
        needle = query.strip().casefold()
        with self.connect() as con:
            tokens = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]", needle)
            expression = " OR ".join('"' + t + '"' for t in tokens)
            hits = (
                {
                    row["id"]
                    for row in con.execute(
                        "SELECT id FROM terms_fts WHERE terms_fts MATCH ?", (expression,)
                    )
                }
                if tokens
                else set()
            )
        matches = []
        for row in self.list(domain):
            values = [row["abbr"]]
            for language in [lang] if lang else ["zh", "en"]:
                values += [row[language], *row[f"synonyms_{language}"]]
            initials = "".join(lazy_pinyin(row["zh"], style=Style.FIRST_LETTER)).casefold()
            score = max(
                (
                    100
                    if needle == value.casefold()
                    else 96
                    if needle in value.casefold()
                    else (
                        WRatio(needle, value.casefold())
                        if min(len(needle), len(value)) >= 4
                        else ratio(needle, value.casefold())
                    )
                    for value in values
                    if value
                ),
                default=0,
            )
            if lang != "en":
                if needle == initials:
                    score = 100
                elif len(needle) >= 2 and initials.startswith(needle):
                    score = max(score, 95)
            if row["id"] in hits:
                score = max(score, 75)
            if score >= 60:
                matches.append({**row, "score": round(score, 2)})
        return sorted(matches, key=lambda r: (-r["score"], r["domain"], r["en"]))[:limit]

    def import_records(
        self, records: list[dict], replace: bool = False, confirm: bool = False
    ) -> dict:
        if not isinstance(records, list) or len(records) > 100000:
            raise GlossError("Expected a list of at most 100000 terms")
        if replace and not confirm:
            raise GlossError(
                "Replacing existing terms requires --replace --yes", "CONFIRM_REQUIRED"
            )
        prepared = [normalize(row) for row in records]
        seen = set()
        for row in prepared:
            key = (row["domain"], row["zh"])
            if key in seen:
                raise GlossError("Duplicate canonical term within import")
            seen.add(key)
        backup = self.backup() if replace else None
        counts = {"inserted": 0, "updated": 0, "skipped": 0}
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            for row in prepared:
                old = con.execute(
                    "SELECT * FROM terms WHERE id=? OR (domain=? AND (zh=? OR en=? COLLATE NOCASE))",
                    (row["id"], row["domain"], row["zh"], row["en"]),
                ).fetchall()
                if len(old) > 1:
                    raise GlossError("Imported term maps to multiple existing entries", "CONFLICT")
                if old:
                    previous = self.unpack(con, old[0])
                    row["id"] = previous["id"]

                    def comparable(x):
                        return {k: v for k, v in x.items() if k not in {"id", "updated_at"}}

                    if comparable(row) == comparable(previous):
                        counts["skipped"] += 1
                        continue
                    if not replace:
                        raise GlossError(
                            "Different existing term requires --replace --yes", "CONFLICT"
                        )
                    row["updated_at"] = now()
                    counts["updated"] += 1
                else:
                    counts["inserted"] += 1
                try:
                    self.write(con, row)
                except sqlite3.IntegrityError as exc:
                    raise GlossError("Canonical term collision", "CONFLICT") from exc
        return {**counts, "backup": backup["path"] if backup else None}

    def import_file(self, source: str | Path, replace: bool = False, confirm: bool = False) -> dict:
        path = Path(source)
        if not path.is_file():
            raise GlossError("Import file not found", "NOT_FOUND", 3)
        if path.stat().st_size > 50 * 1024 * 1024:
            raise GlossError("Import exceeds 50 MiB")
        return self.import_records(
            read_terms(path.read_text(encoding="utf-8-sig"), path.suffix.lstrip(".")),
            replace,
            confirm,
        )

    def export_text(
        self, format: str = "json", domain: str | None = None, kb: bool = False, bom: bool = True
    ) -> str:
        rows = self.list(domain)
        if format == "json":
            return json.dumps({"schema_version": 1, "terms": rows}, ensure_ascii=False, indent=2)
        if format == "csv":
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(
                buffer, fieldnames=KB_FIELDS if kb else FIELDS + LISTS, extrasaction="ignore"
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {**row, **{k: json.dumps(row[k], ensure_ascii=False) for k in LISTS}}
                )
            return ("\ufeff" if bom else "") + buffer.getvalue()
        if format == "tbx":
            ET.register_namespace("", NS)
            root = ET.Element(
                "{" + NS + "}tbx",
                {
                    "type": "BilingualGlossary",
                    "style": "dca",
                    "{http://www.w3.org/XML/1998/namespace}lang": "en",
                },
            )
            header = ET.SubElement(root, "tbxHeader")
            file_desc = ET.SubElement(header, "fileDesc")
            source = ET.SubElement(file_desc, "sourceDesc")
            ET.SubElement(
                source, "p"
            ).text = "Bilingual Glossary local export; see README for supported subset and metadata extension."
            body = ET.SubElement(ET.SubElement(root, "text"), "body")
            for row in rows:
                entry = ET.SubElement(body, "conceptEntry", {"id": row["id"]})
                ET.SubElement(entry, "descrip", {"type": "subjectField"}).text = row["domain"]
                ET.SubElement(
                    entry, "admin", {"type": "bilingualGlossaryRecord"}
                ).text = json.dumps(row, ensure_ascii=False)
                for lang in ["zh", "en"]:
                    section = ET.SubElement(
                        entry, "langSec", {"{http://www.w3.org/XML/1998/namespace}lang": lang}
                    )
                    if row[f"definition_{lang}"]:
                        ET.SubElement(section, "descrip", {"type": "definition"}).text = row[
                            f"definition_{lang}"
                        ]
                    for text, kind in [
                        (row[lang], "preferredTerm"),
                        *[(v, "admittedTerm") for v in row[f"synonyms_{lang}"]],
                        *[
                            (v["text"], "deprecatedTerm")
                            for v in row["forbidden"]
                            if v["lang"] == lang
                        ],
                    ]:
                        term = ET.SubElement(section, "termSec")
                        ET.SubElement(term, "term").text = text
                        ET.SubElement(
                            term, "termNote", {"type": "administrativeStatus"}
                        ).text = kind
            return ET.tostring(root, encoding="unicode", xml_declaration=True)
        raise GlossError("Format must be json, csv or tbx")

    def export(
        self,
        output: str | Path,
        format: str = "json",
        domain: str | None = None,
        kb: bool = False,
        bom: bool = True,
    ) -> dict:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.export_text(format, domain, kb, bom), encoding="utf-8")
        return {"path": str(path.resolve()), "count": len(self.list(domain))}

    def backup(self) -> dict:
        directory = self.directory / "backups"
        directory.mkdir(exist_ok=True)
        stamp = datetime.now(self.zone).strftime("%Y%m%d_%H%M%S_%f")
        path = directory / f"glossary_{stamp}.zip"
        temp = directory / f"{stamp}.db"
        try:
            with self.connect() as source, sqlite3.connect(temp) as target:
                source.backup(target)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(temp, "glossary.db")
        finally:
            temp.unlink(missing_ok=True)
        return {"path": str(path)}


def read_terms(text: str, format: str) -> list[dict]:
    if format == "json":
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if data.get("schema_version") != 1:
            raise GlossError("Unsupported JSON schema")
        return data["terms"]
    if format == "csv":
        return list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
    if format != "tbx":
        raise GlossError("Import format must be json, csv or tbx")
    root = fromstring(text)
    # Namespace-insensitive for the supported TBX 3 and legacy termEntry subsets.
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]
    if root.tag not in {"tbx", "martif"}:
        raise GlossError("Expected a TBX document")
    result = []
    for entry in list(root.iter("conceptEntry")) + list(root.iter("termEntry")):
        private = next(
            (
                e.text
                for e in entry.findall("admin")
                if e.attrib.get("type") == "bilingualGlossaryRecord"
            ),
            None,
        )
        if private:
            result.append(json.loads(private))
            continue
        row = {"id": entry.get("id", ""), "status": "draft", "domain": "general"}
        for description in entry.findall("descrip"):
            if description.attrib.get("type") == "subjectField":
                row["domain"] = description.text or "general"
        for section in list(entry.findall("langSec")) + list(entry.findall("langSet")):
            lang = section.get("{http://www.w3.org/XML/1998/namespace}lang", "").split("-")[0]
            if lang not in {"zh", "en"}:
                continue
            term_sections = list(section.findall("termSec")) + list(section.findall("tig"))
            preferred, admitted, deprecated = [], [], []
            for term_section in term_sections:
                term_element = term_section.find("term")
                if term_element is None or not term_element.text:
                    continue
                value = term_element.text
                status = next(
                    (
                        e.text
                        for e in term_section.findall("termNote")
                        if e.get("type") == "administrativeStatus"
                    ),
                    "admittedTerm",
                )
                if status == "deprecatedTerm":
                    deprecated.append({"lang": lang, "text": value})
                elif status == "preferredTerm":
                    preferred.append(value)
                else:
                    admitted.append(value)
            values = preferred + admitted
            if values:
                row[lang] = values[0]
                row["synonyms_" + lang] = values[1:]
            row.setdefault("forbidden", []).extend(deprecated)
            definition = next(
                (e.text for e in section.findall("descrip") if e.get("type") == "definition"), ""
            )
            row["definition_" + lang] = definition or ""
        result.append(row)
    return result
