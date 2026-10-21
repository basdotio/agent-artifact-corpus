#!/usr/bin/env python3
"""Stage official Berkshire annual/interim reports discovered from report-table cells.

No database writes. Original HTML/PDF and provenance stay in --stage. A manifest
distinguishes staged reports, previously indexed reports, and failures.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urljoin, urlsplit

from library import download, decode, digest, extract, now
from collect import links, report_pdf

INDEX = "https://www.berkshirehathaway.com/reports.html"


class ReportTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {"text": [], "links": []}
        elif tag == "a" and self.cell is not None:
            self.cell["links"].append(dict(attrs).get("href", ""))

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def discover(raw):
    parser = ReportTable()
    parser.feed(decode(raw))
    records = {}
    for row in parser.rows:
        if len(row) != 5:
            continue
        text = "".join(row[0]["text"]).strip()
        if not re.fullmatch(r"(?:19|20)\d{2}", text):
            continue
        year = int(text)
        for column, cell in enumerate(row[1:], 1):
            urls = list(dict.fromkeys(urljoin(INDEX, h) for h in cell["links"] if h))
            urls = [u for u in urls if urlsplit(u).hostname == "www.berkshirehathaway.com"]
            if not urls:
                continue
            if len(urls) != 1:
                raise ValueError(f"Ambiguous report table cell: {year}/{column}")
            period = "annual" if column == 4 else f"Q{column}"
            records[(year, period)] = {"year": year, "period": period, "url": urls[0]}
    if not records:
        raise ValueError("No report rows discovered; index structure may have changed")
    return sorted(records.values(), key=lambda r: (r["year"], r["period"]))


def save_download(url, folder, label):
    raw, content_type, resolved = download(url)
    suffix = ".pdf" if raw.startswith(b"%PDF-") else ".html" if "html" in content_type else ".txt"
    path = folder / (label + suffix)
    path.write_bytes(raw)
    return raw, resolved, path


def choose_child(raw, base, item):
    values = links(raw, base)
    if item["period"] == "annual":
        try:
            return report_pdf(raw, base, expected_year=item["year"])
        except ValueError:
            return None
    quarter = item["period"][-1]
    year = str(item["year"])[-2:]
    pdfs = list(dict.fromkeys(u for u, label in values
                            if re.search(rf"/{quarter}(?:st|nd|rd)qtr{year}[a-z]?\.pdf$", u, re.I)))
    if len(pdfs) == 1:
        return pdfs[0]
    if len(pdfs) > 1:
        raise ValueError("Ambiguous quarterly PDF links")
    same_period = list(dict.fromkeys(u for u, label in values
                                  if re.search(rf"/{quarter}(?:st|nd|rd)qtr{year}\.html?$", u, re.I)
                                  and u != base))
    if len(same_period) == 1:
        return same_period[0]
    return None


def stage_one(item, stage, existing):
    # A retry may receive a failed-manifest record; do not retain stale status/errors.
    item = {key: item[key] for key in ("year", "period", "url")}
    folder = stage / f"{item['year']}-{item['period']}"
    folder.mkdir(parents=True, exist_ok=True)
    saved_meta = folder / "metadata.json"
    saved_ready = folder / "ready.json"
    if saved_meta.exists() and saved_ready.exists():
        ready = json.loads(saved_ready.read_text())
        source = Path(ready["source_path"])
        if source.exists() and digest(source.read_bytes()) == ready.get("source_sha256"):
            return ready
    url = item["url"]
    raw_sources = []
    if url in existing:
        return {"status": "already_indexed", **item}
    raw, resolved, path = save_download(url, folder, "landing")
    raw_sources.append({"url": resolved, "path": str(path), "sha256": digest(raw)})
    for depth in range(2):
        if path.suffix == ".pdf":
            break
        child = choose_child(raw, resolved, item)
        if not child:
            break
        if child in existing:
            return {"status": "already_indexed", **item, "source_url": child}
        raw, resolved, path = save_download(child, folder, f"body-{depth}")
        raw_sources.append({"url": resolved, "path": str(path), "sha256": digest(raw)})
    title = f"Berkshire Hathaway {item['year']} " + ("Annual Report" if item["period"] == "annual" else f"{item['period']} Interim Report")
    metadata = {
        "title": title, "url": resolved, "author": "Berkshire Hathaway Inc.", "speaker": None,
        "date": str(item["year"]), "date_precision": "year", "publication_date": None,
        "report_period": item["period"], "report_year": item["year"],
        "date_note": "Report year/quarter comes from the official reports table; not a claim about publication date",
        "source_type": "annual_report" if item["period"] == "annual" else "financial_report",
        "series": "reports" if item["period"] == "annual" else "berkshire-quarterly-reports",
        "primary_status": "primary", "transcript_quality": "official", "discovered_from": INDEX,
        "discovery_landing_url": item["url"], "accessed_at": now(),
        "rights": "Publicly accessible copyrighted corporate disclosure; local research copy, no redistribution licence asserted",
        "attribution_note": "Company filing, no blanket personal attribution; letter, management discussion and auditor sections have different authors",
        "raw_sources": raw_sources,
    }
    # The 1996/1997 reports are official multi-file HTML publications.
    parts = []
    if item["period"] == "annual" and path.suffix == ".html":
        directory = urlsplit(resolved).path.rsplit("/", 1)[0] + "/"
        parts = [(u, label) for u, label in links(raw, resolved)
                 if urlsplit(u).path.startswith(directory) and u != resolved
                 and urlsplit(u).path.endswith((".html", ".htm"))]
        parts = list(dict.fromkeys(parts))
    if parts and len(parts) >= 5:
        segments = []
        for ordinal, (part_url, label) in enumerate(parts):
            part_raw, part_resolved, part_path = save_download(part_url, folder, f"section-{ordinal:02d}")
            metadata["raw_sources"].append({"url": part_resolved, "path": str(part_path), "sha256": digest(part_raw)})
            content = extract(part_path, part_raw)
            if sum(len(s["text"]) for s in content) < 50:
                raise ValueError("Empty annual report section: " + part_url)
            for segment in content:
                segment.update(speaker=None, section=label + " | " + part_resolved)
                segments.append(segment)
        path = folder / "segments.json"
        path.write_text(json.dumps({"segments": segments}, ensure_ascii=False))
        metadata["coverage"] = f"All {len(parts)} substantive HTML report sections linked by the official annual report contents page; section URL in locator"
    else:
        segments = extract(path, raw)
        metadata["coverage"] = "Full official report file; tables require checking original formatting before numerical quotation"
    if sum(len(s["text"]) for s in segments) < 3000:
        raise ValueError("Report body too short; may be a landing page or empty scan")
    saved_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    ready = {"status": "staged", **item, "source_url": metadata["url"], "metadata_path": str(saved_meta),
             "source_path": str(path), "source_sha256": digest(path.read_bytes()), "segments": len(segments),
             "characters": sum(len(s["text"]) for s in segments)}
    saved_ready.write_text(json.dumps(ready, ensure_ascii=False, indent=2))
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--library", help="Read-only duplicate check")
    parser.add_argument("--from-year", type=int, default=1995)
    parser.add_argument("--to-year", type=int, default=2100)
    parser.add_argument("--kind", choices=["all", "annual", "quarterly"], default="all")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    stage = Path(args.stage).resolve()
    stage.mkdir(parents=True, exist_ok=True)
    raw, content_type, resolved = download(INDEX)
    (stage / "index.html").write_bytes(raw)
    items = [item for item in discover(raw) if args.from_year <= item["year"] <= args.to_year
             and (args.kind == "all" or (item["period"] == "annual") == (args.kind == "annual"))]
    existing = set()
    if args.library:
        database = Path(args.library).resolve() / "corpus.sqlite3"
        if database.exists():
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as conn:
                existing = {r[0] for r in conn.execute("SELECT url FROM documents")}
    completed, failed = [], []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4))) as pool:
        futures = {pool.submit(stage_one, item, stage, existing): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                completed.append(result)
                print(json.dumps({"year": item["year"], "period": item["period"], "status": result["status"], "segments": result.get("segments")}), flush=True)
            except Exception as error:
                failed.append({**item, "error": str(error)})
                print(json.dumps({"status": "failed", **failed[-1]}), flush=True)
    manifest = {"index_url": INDEX, "accessed_at": now(), "discovered": len(items),
                "documents": sorted(completed, key=lambda r: (r["year"], r["period"])), "failures": failed}
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({"discovered": len(items), "staged": sum(r["status"] == "staged" for r in completed), "already_indexed": sum(r["status"] == "already_indexed" for r in completed), "failed": len(failed), "manifest": str(stage / "manifest.json")}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
