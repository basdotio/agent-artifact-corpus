#!/usr/bin/env python3
"""Discover official links and incrementally collect Berkshire/Wesco originals.

No guessed document URLs. --kind reports follows official annual-report landing
pages. It does not imply that every section is authored by Buffett or Munger.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

from library import HTMLText, Library, clean, decode, download, now

INDEXES = {
    "buffett-letters": "https://www.berkshirehathaway.com/letters/letters.html",
    "wesco-letters": "https://www.berkshirehathaway.com/wesco/WescoHome.html",
    "reports": "https://www.berkshirehathaway.com/reports.html",
}


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.current = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = [dict(attrs).get("href", ""), []]

    def handle_data(self, data):
        if self.current:
            self.current[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            self.links.append((self.current[0], " ".join("".join(self.current[1]).split())))
            self.current = None


def links(raw, base):
    parser = Links()
    parser.feed(decode(raw))
    result = []
    for href, label in parser.links:
        if not href or not href.strip() or href.strip().startswith("#"):
            continue
        url = urljoin(base, href)
        part = urlsplit(url)
        if not part.username and not part.password and part.hostname in {"berkshirehathaway.com", "www.berkshirehathaway.com"}:
            if part.scheme in {"http", "https"}:
                result.append((urlunsplit(("https", part.netloc, part.path, part.query, "")), label))
    return result


def candidates(kind, raw, base):
    if kind not in INDEXES:
        raise ValueError("Unknown source collection: " + kind)
    found = {}
    for url, label in links(raw, base):
        if kind.endswith("letters"):
            match = re.fullmatch(r"(19\d{2}|20\d{2})", label.strip())
            if not match:
                continue
            year = int(match.group(1))
            # Verified Buffett-authored official letter index currently ends 2024.
            # Newer authorship needs a human reading the signature before admission.
            if kind == "buffett-letters" and year > 2024:
                continue
        else:
            match = re.search(r"/(\d{4})ar/linksannual(\d{2})\.html$", urlsplit(url).path, re.I)
            if not match or match.group(1)[-2:] != match.group(2):
                continue
            year = int(match.group(1))
        filename_year = re.match(r"(19\d{2}|20\d{2})(?:ltr|ar)?\.(?:pdf|html?)$", Path(urlsplit(url).path).name, re.I)
        if filename_year and int(filename_year[1]) != year:
            raise ValueError(f"Index label/year conflicts with document URL: {label} / {url}")
        if year in found and found[year]["url"] != url:
            raise ValueError(f"Ambiguous {kind} index: multiple source URLs for {year}")
        found[year] = {"year": year, "url": url, "landing_page": kind == "reports"}
    return sorted(found.values(), key=lambda row: (row["year"], row["url"]))


def read_index(url, archive):
    raw, content_type, resolved = download(url)
    if "html" not in content_type:
        raise ValueError("Index was not HTML: " + url)
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(raw)
    return raw, resolved


def report_pdf(raw, base, expected_year=None):
    if expected_year is None:
        match = re.search(r"/(\d{4})ar/", urlsplit(base).path, re.I)
        expected_year = int(match[1]) if match else None
    values = list(dict.fromkeys((u, t) for u, t in links(raw, base) if urlsplit(u).path.lower().endswith(".pdf")))
    exact = []
    for url, label in values:
        match = re.search(r"/(\d{4})ar\.pdf$", urlsplit(url).path, re.I)
        if match and (expected_year is None or int(match[1]) == expected_year):
            exact.append(url)
    exact = list(dict.fromkeys(exact))
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError("Multiple complete annual-report PDFs on " + base)
    named = []
    for url, label in values:
        year = re.search(r"(19\d{2}|20\d{2})", Path(urlsplit(url).path).name)
        if expected_year is not None and year and int(year[1]) != expected_year:
            continue
        if re.fullmatch(r"(?:\d{4}\s+)?(?:complete\s+)?annual report(?:\s+\(?PDF\)?)?", label, re.I):
            named.append(url)
    named = list(dict.fromkeys(named))
    if len(named) == 1:
        return named[0]
    raise ValueError("No unambiguous complete annual-report PDF on " + base)


def letter_pdf(raw, base, year):
    """Resolve a letter landing page through observed links, never invented filenames."""
    candidates = []
    for url, label in links(raw, base):
        path = urlsplit(url).path
        if not path.lower().endswith(".pdf"):
            continue
        filename_years = re.findall(r"(?:19|20)\d{2}", Path(path).name)
        label_years = re.findall(r"(?:19|20)\d{2}", label)
        if filename_years and str(year) not in filename_years:
            continue
        if label_years and str(year) not in label_years:
            continue
        if str(year) in filename_years + label_years and re.search(r"letter|\bpdf\b", label, re.I):
            candidates.append(url)
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise ValueError("Multiple candidate letter PDFs on " + base)
    parser = HTMLText()
    parser.feed(decode(raw))
    body = clean("".join(parser.parts))
    if len(body) < 1500 or re.search(r"important note.{0,200}chairman.?s letter", body, re.I):
        raise ValueError("Short or unresolved letter landing page; full original not verified: " + base)
    return None


def document_metadata(kind, year, url, index):
    is_wesco = kind == "wesco-letters"
    is_report = kind == "reports"
    name = "Wesco Financial" if is_wesco else "Berkshire Hathaway"
    author = "Berkshire Hathaway Inc." if is_report else "Charlie Munger" if is_wesco else "Warren Buffett"
    meta = {
        "title": f"{name} {year} " + ("Annual Report" if is_report else "Shareholder Letter"),
        "url": url, "date": str(year), "date_precision": "year",
        "publication_date": None, "date_note": "date is report year, not publication or signature date; inspect source for exact publication date",
        "author": author, "speaker": None if is_report else author,
        "source_type": "annual_report" if is_report else "shareholder_letter",
        "series": kind, "primary_status": "primary", "transcript_quality": "official",
        "rights": "Publicly accessible copyrighted original; local research copy, no redistribution licence asserted",
        "discovered_from": index, "accessed_at": now(),
        "attribution_note": "Document-level attribution; verify embedded quotations and other authors before quoting any individual passage",
    }
    if kind == "buffett-letters" and year == 2014:
        meta.update(title="Berkshire Hathaway 2014 Shareholder Letters — Buffett and Munger",
                    author="mixed", speaker="mixed",
                    attribution_note="This PDF contains Buffett and Munger sections; do not inherit Buffett attribution across the document. Page ranges require verified source URL and SHA256.")
        verified_url = "https://www.berkshirehathaway.com/letters/2014ltr.pdf"
        if url == verified_url:
            meta.update(speaker_page_ranges=[{"from": 2, "to": 37, "speaker": "Warren Buffett"},
                                             {"from": 38, "to": 42, "speaker": "Charlie Munger"}],
                        speaker_page_ranges_url=verified_url,
                        speaker_page_ranges_sha256="dd00248b32ad1f67234bb4dba66755bf45a623bd94e40465a2a88707b73cd426",
                        speaker_page_ranges_verified_at="2026-10-04",
                        attribution_note="Verified physical PDF pages on 2026-10-04: Buffett section pages 2–37; Munger's Vice Chairman’s Thoughts – Past and Future pages 38–42; page 1 performance table unassigned. Page 2 includes editorial material. Ranges locate authored sections, not proof that every sentence or embedded quotation was spoken by that author; inspect passage context.")
    return meta


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True)
    parser.add_argument("--kind", choices=list(INDEXES), required=True)
    parser.add_argument("--from-year", type=int, default=1900)
    parser.add_argument("--to-year", type=int, default=2100)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch previously indexed URLs")
    args = parser.parse_args(argv)
    library = Library(args.library)
    archive = library.root / "discovery"
    index = INDEXES[args.kind]
    failures, documents, prefetched = [], [], {}
    try:
        if args.from_year > args.to_year:
            raise ValueError("--from-year must be no later than --to-year")
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be positive")
        raw, resolved = read_index(index, archive / (args.kind + ".html"))
        discovered = candidates(args.kind, raw, resolved)
        if not discovered:
            raise ValueError("No source links discovered; site structure may have changed")
        selected = [d for d in discovered if args.from_year <= d["year"] <= args.to_year]
        if args.limit is not None:
            selected = selected[:args.limit]
        for entry in selected:
            try:
                url = entry["url"]
                landing_url = None
                if entry["landing_page"]:
                    raw_report, landing = read_index(url, archive / f"report-{entry['year']}.html")
                    url = report_pdf(raw_report, landing, expected_year=entry["year"])
                    landing_url = landing
                elif urlsplit(url).path.lower().endswith((".html", ".htm")):
                    cached = library.db.execute("SELECT raw_path FROM documents WHERE url=?", (url,)).fetchone()
                    local = library.root / cached["raw_path"] if cached and not args.refresh else None
                    if local and local.exists():
                        raw_letter, landing = local.read_bytes(), url
                    else:
                        local = archive / f"{args.kind}-{entry['year']}.html"
                        raw_letter, landing = read_index(url, local)
                    pdf = letter_pdf(raw_letter, landing, entry["year"])
                    if pdf:
                        url, landing_url = pdf, landing
                    else:
                        url = landing
                        prefetched[url] = local
                meta = document_metadata(args.kind, entry["year"], url, index)
                if landing_url:
                    meta.update(source_url=url, discovery_landing_url=landing_url)
                documents.append(meta)
            except Exception as error:
                failures.append({"url": entry["url"], "error": str(error)})
                library.log("discovery", entry["url"], False, str(error))
        manifest = {"index": index, "accessed_at": now(), "documents": documents, "discovery_failures": failures}
        archive.mkdir(parents=True, exist_ok=True)
        (archive / (args.kind + "-manifest.json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        succeeded, skipped = [], []
        if not args.dry_run:
            for meta in documents:
                if not args.refresh and library.db.execute("SELECT 1 FROM documents WHERE url=?", (meta["url"],)).fetchone():
                    skipped.append(meta["url"])
                    continue
                try:
                    result = library.ingest(meta, prefetched[meta["url"]], operation="fetch") if meta["url"] in prefetched else library.fetch(meta)
                    succeeded.append(result["document_id"])
                    print(json.dumps({"status": "indexed", "title": meta["title"], "chunks": result["chunks"]}, ensure_ascii=False), flush=True)
                except Exception as error:
                    failures.append({"url": meta["url"], "error": str(error)})
                    print(json.dumps({"status": "failed", **failures[-1]}, ensure_ascii=False), flush=True)
                time.sleep(0.25)
        result = {"kind": args.kind, "discovered": len(discovered), "selected": len(documents), "indexed": len(succeeded), "skipped": len(skipped), "dry_run": args.dry_run, "failures": failures, "manifest": str(archive / (args.kind + "-manifest.json"))}
        (archive / (args.kind + "-last-run.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if failures else 0
    except Exception as error:
        library.log("discovery", index, False, str(error))
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1
    finally:
        library.close()


if __name__ == "__main__":
    sys.exit(main())
