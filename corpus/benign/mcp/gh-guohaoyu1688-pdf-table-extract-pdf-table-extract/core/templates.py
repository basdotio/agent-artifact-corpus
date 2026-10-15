"""SQLite templates and portable template snapshots."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .errors import PDFError
from .extract import extract_tables

OPTIONS = {
    "pages",
    "area",
    "columns",
    "engine",
    "ocr",
    "merge_pages",
    "fill_merged",
    "header_rows",
    "normalize_numbers",
    "trim_top",
    "trim_bottom",
    "exclude_text",
    "compare",
    "camelot_flavor",
}


class Templates:
    def __init__(self, data_dir: str | Path = "data", timezone: str = "Asia/Shanghai"):
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "cache.sqlite"
        self.zone = ZoneInfo(timezone)
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS templates("
                "name TEXT PRIMARY KEY, options_json TEXT NOT NULL)"
            )

    def save(self, name: str, options: dict, *, replace: bool = False) -> dict:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", name):
            raise PDFError(
                "invalid_name", "Template name must be 1..64 letters, numbers, _ or -", 2
            )
        if not isinstance(options, dict) or set(options) - OPTIONS:
            raise PDFError(
                "invalid_template", "Template contains unsupported extraction options", 2
            )
        for key in ("ocr", "merge_pages", "normalize_numbers", "compare"):
            if key in options and type(options[key]) is not bool:
                raise PDFError("invalid_template", f"{key} must be a boolean", 2)
        if "header_rows" in options and (
            type(options["header_rows"]) is not int or not 1 <= options["header_rows"] <= 20
        ):
            raise PDFError("invalid_template", "header_rows must be an integer from 1 to 20", 2)
        for key in ("area", "columns"):
            value = options.get(key)
            if value is not None and (
                not isinstance(value, list)
                or not all(type(x) in {int, float} for x in value)
                or (len(value) != 4 if key == "area" else len(value) < 2)
            ):
                raise PDFError("invalid_template", f"Invalid numeric array: {key}", 2)
        if options.get("pages") is not None and not isinstance(options["pages"], str):
            raise PDFError("invalid_template", "pages must be a range string", 2)
        encoded = json.dumps(options, allow_nan=False)
        with sqlite3.connect(self.path) as db:
            if (
                db.execute("SELECT 1 FROM templates WHERE name=?", (name,)).fetchone()
                and not replace
            ):
                raise PDFError("already_exists", "Template exists; use --yes to replace")
            db.execute("INSERT OR REPLACE INTO templates VALUES(?,?)", (name, encoded))
        return {"name": name, "options": options}

    def list(self) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            return [
                {"name": row[0], "options": json.loads(row[1])}
                for row in db.execute("SELECT * FROM templates ORDER BY name")
            ]

    def get(self, name: str) -> dict:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT options_json FROM templates WHERE name=?", (name,)).fetchone()
        if not row:
            raise PDFError("not_found", f"Template not found: {name}", 3)
        return json.loads(row[0])

    def delete(self, name: str, confirm: bool = False) -> dict:
        if not confirm:
            raise PDFError("confirmation_required", "Deleting a template requires --yes", 2)
        self.get(name)
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM templates WHERE name=?", (name,))
        return {"deleted": name}

    def apply(self, name: str, paths: list[str], out: str, format: str = "csv") -> list[dict]:
        options = self.get(name)
        if len({Path(p).stem for p in paths}) != len(paths):
            raise PDFError("duplicate_output", "Batch PDF basenames must be unique", 2)
        return [
            extract_tables(path, out=Path(out) / Path(path).stem, format=format, **options)
            for path in paths
        ]

    def export(self, path: str | Path, format: str = "json", bom: bool = True) -> dict:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        templates = self.list()
        if format == "json":
            path.write_text(
                json.dumps({"schema_version": 1, "templates": templates}, indent=2) + "\n"
            )
        elif format == "csv":
            with path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["name", "options_json"])
                writer.writerows((t["name"], json.dumps(t["options"])) for t in templates)
        else:
            raise PDFError("invalid_format", "Template export supports json or csv", 2)
        return {"path": str(path.resolve()), "count": len(templates)}

    def import_file(self, path: str | Path) -> dict:
        path = Path(path)
        if path.suffix.lower() == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                records = [
                    {"name": row["name"], "options": json.loads(row["options_json"])}
                    for row in csv.DictReader(stream)
                ]
        else:
            records = json.loads(path.read_text(encoding="utf-8-sig"))["templates"]
        # Validate all records in an isolated store before changing live data.
        with tempfile.TemporaryDirectory() as temporary:
            staged = Templates(temporary)
            for record in records:
                staged.save(record["name"], record["options"])
        count = 0
        with sqlite3.connect(self.path) as db:
            for record in records:
                cursor = db.execute(
                    "INSERT OR IGNORE INTO templates VALUES(?,?)",
                    (record["name"], json.dumps(record["options"])),
                )
                count += cursor.rowcount
        return {"imported": count, "skipped": len(records) - count}

    def backup(self, out: str | Path | None = None) -> dict:
        output = Path(out) if out else self.data_dir / "backups"
        output.mkdir(parents=True, exist_ok=True)
        name = datetime.now(self.zone).strftime("pdf-table-extract_%Y%m%dT%H%M%S_%f.zip")
        destination = output / name
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "cache.sqlite"
            with sqlite3.connect(self.path) as source, sqlite3.connect(snapshot) as target:
                source.backup(target)
            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "cache.sqlite")
        return {"path": str(destination.resolve())}
