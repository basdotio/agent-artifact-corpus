#!/usr/bin/env python3
"""Stage full CNBC Berkshire annual-meeting transcripts; never writes the corpus DB.

Only observed links from the official index and year pages are followed. Ordinary
HTML transcript paragraphs are extracted; videos and embedded application state
are not downloaded. Output contains a merge manifest, original HTML, JSON passages,
metadata, and explicit gaps. Re-running reuses captured HTML unless --refresh.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit

from library import clean, decode, digest, download, now, speaker_name

INDEX = "https://buffett.cnbc.com/annual-meetings/"
VOID = set("area base br col embed hr img input link meta param source track wbr".split())


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return "".join(child.text() if isinstance(child, Node) else child for child in self.children)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def has_class(self, value):
        return value in self.attrs.get("class", "").split()


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root, self.stack = Node(), []
        self.stack.append(self.root)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, value):
        self.stack[-1].children.append(value)


def parse(raw):
    parser = Tree()
    parser.feed(decode(raw))
    return parser.root


def official_url(href, base):
    parts = urlsplit(urljoin(base, href))
    if parts.scheme not in {"http", "https"} or parts.hostname != "buffett.cnbc.com" or parts.username or parts.password:
        return None
    return urlunsplit(("https", parts.netloc.lower(), parts.path, parts.query, ""))


def discover_years(root, base=INDEX):
    years = {}
    for node in root.walk():
        if node.tag != "a":
            continue
        url = official_url(node.attrs.get("href", ""), base)
        match = re.fullmatch(r"/(\d{4})-berkshire-hathaway-annual-meeting/", urlsplit(url).path) if url else None
        if match:
            year = int(match[1])
            if year in years and years[year] != url:
                raise ValueError("Multiple official year pages for " + str(year))
            years[year] = url
    if not years:
        raise ValueError("No annual-meeting year links found; archive layout may have changed")
    return dict(sorted(years.items()))


def discover_sessions(root, year, base):
    by_url = {}
    for node in root.walk():
        if node.tag != "a":
            continue
        url = official_url(node.attrs.get("href", ""), base)
        if url and urlsplit(url).path.startswith("/video/"):
            by_url.setdefault(url, []).append(clean(node.text()))
    sessions = []
    for url, labels in by_url.items():
        if not any("WATCH FULL VIDEO" in label.upper() for label in labels):
            continue
        titles = [label for label in labels if str(year) in label and
                  re.search(r"(?:morning|afternoon) session|annual meeting|part\s*\d+\s*[-–]\s*\d{4}\s+meeting", label, re.I) and
                  not re.search(r"highlight|reel|clip", label, re.I)]
        if not titles:
            continue
        title = max(titles, key=len)
        session = "morning" if re.search("morning", title, re.I) else "afternoon" if re.search("afternoon", title, re.I) else "full"
        part = re.search(r"part\s*(\d+)", title, re.I)
        if part:
            session = "part-" + part[1]
        sessions.append({"year": year, "url": url, "title": title, "session": session, "year_page": base})
    if not sessions:
        raise ValueError(f"No clearly labelled full-session links for {year}; clips are not substitutes")
    return sorted(sessions, key=lambda row: row["url"])


def transcript(root, minimum_paragraphs=20, minimum_characters=4000):
    chapters = [node for node in root.walk() if node.has_class("Chapter-chapter")]
    if not chapters:
        raise ValueError("No ordinary HTML transcript chapters; video-only page or layout change")
    segments, chapter_titles, synthetic_sections = [], [], []
    for chapter in chapters:
        titles = [node for node in chapter.walk() if node.has_class("Chapter-chapterTitle")]
        if len(titles) != 1:
            raise ValueError("Transcript chapter has an ambiguous or missing title")
        section, speaker = clean(titles[0].text()), None
        chapter_titles.append(section)
        synthetic = bool(re.search(r"\bAI\b|AI.generated|synthetic", section, re.I) and re.search(r"Warren|Buffett|voice", section, re.I))
        if synthetic:
            synthetic_sections.append(section)
        for paragraph in (node for node in chapter.walk() if node.tag == "p"):
            text = clean(paragraph.text())
            if not text:
                continue
            label = re.match(r"^([A-Z][A-Z0-9 .,’'()\[\]/&-]{1,75}):\s*", text)
            if label:
                original = label[1]
                speaker = speaker_name(original)
                if original in {"CHARLES MUNGER", "CHARLES T. MUNGER"}:
                    speaker = "Charlie Munger"
                if re.search(r"\bAI\b|AI.GENERATED|SYNTHETIC", original) or (synthetic and speaker == "Warren Buffett"):
                    speaker = "Synthetic or AI-generated voice"
            actual_speaker = None if re.fullmatch(r"[\[(].*[\])]", text) else speaker
            segments.append({"text": text, "speaker": actual_speaker, "section": section})
    if len(segments) < minimum_paragraphs or sum(len(row["text"]) for row in segments) < minimum_characters:
        raise ValueError("Transcript too short to accept as a complete session; review manually")
    if not any(row["speaker"] for row in segments):
        raise ValueError("No explicit speaker labels in transcript")
    return segments, chapter_titles, synthetic_sections


def capture(url, path, refresh=False):
    record = path.with_suffix(".capture.json")
    if path.exists() and not refresh:
        info = json.loads(record.read_text()) if record.exists() else {"requested_url": url, "resolved_url": url, "accessed_at": now()}
        raw = path.read_bytes()
        if info.get("requested_url") != url:
            raise ValueError("Cached HTML URL does not match requested source")
    else:
        raw, mime, final = download(url)
        if "html" not in mime or not official_url(final, url):
            raise ValueError("Expected CNBC HTML, received another content type or host")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        info = {"requested_url": url, "resolved_url": final, "content_type": mime, "accessed_at": now()}
    info["raw_sha256"] = digest(raw)
    record.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
    return raw, info


def stage_session(entry, output, refresh=False):
    document_id = "cnbc-annual-meeting-" + str(entry["year"]) + "-" + entry["session"] + "-" + digest(entry["url"])[:10]
    raw_path = output / (document_id + ".html")
    source_path, metadata_path = output / (document_id + ".json"), output / (document_id + ".metadata.json")
    raw, capture_info = capture(entry["url"], raw_path, refresh)
    root = parse(raw)
    segments, chapters, synthetic = transcript(root)
    props = {node.attrs.get("itemprop") or node.attrs.get("property") or node.attrs.get("name"): node.attrs.get("content") for node in root.walk() if node.tag == "meta"}
    actual_title = props.get("og:title", entry["title"])
    if str(entry["year"]) not in actual_title or re.search("highlight|reel", actual_title, re.I):
        raise ValueError("Session page title does not confirm expected full session/year")
    coverage = {"year": entry["year"], "session": entry["session"], "chapters": len(chapters),
                "paragraphs": len(segments), "characters": sum(len(row["text"]) for row in segments),
                "speakers": dict(Counter(row["speaker"] or "unknown" for row in segments)),
                "timecodes": "not available from extracted paragraphs", "synthetic_voice_sections": synthetic}
    meta = {"id": document_id, "title": "Berkshire Hathaway " + actual_title,
            "url": entry["url"], "resolved_url": capture_info["resolved_url"],
            "date": str(entry["year"]), "date_precision": "year", "publication_date": None,
            "date_note": "Meeting year verified from official archive year page; exact event date not independently verified. URL date is not treated as meeting/publication date.",
            "publisher_record_created_at": props.get("dateCreated"), "publisher_record_modified_at": props.get("dateModified"),
            "source_type": "annual_meeting", "series": "cnbc-annual-meeting-sessions", "speaker": "mixed",
            "author": "CNBC publisher transcript of individually labelled meeting participants",
            "primary_status": "primary", "transcript_quality": "official", "accessed_at": capture_info["accessed_at"],
            "rights": "Publicly accessible copyrighted CNBC transcript; local research copy, no redistribution licence asserted",
            "discovered_from": entry["year_page"], "discovery_index": INDEX, "coverage": coverage,
            "source_html_path": str(raw_path), "source_html_sha256": capture_info["raw_sha256"],
            "capture_method": "Ordinary server-rendered HTML Chapter-chapter paragraphs; no embedded state, media download, or automatic transcription",
            "quality_notes": "Publisher wording preserved apart from whitespace. Chapter titles are editorial headings stored only as locators. Speaker continuation is confined to the same chapter; unlabelled opening paragraphs and standalone stage directions remain unassigned. Verify material quotes against the recording. No timestamps inferred.",
            "locator_notes": "Publisher chapter heading plus original paragraph order; no media timecodes",
            "synthetic_voice_note": "Any AI/synthetic voice section is identified separately and is not an authentic statement by Buffett or Munger." if synthetic else None}
    source_path.write_text(json.dumps({"segments": segments}, ensure_ascii=False, indent=2) + "\n")
    metadata_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return {"document_id": document_id, "url": entry["url"], "metadata_path": str(metadata_path),
            "source_path": str(source_path), "raw_path": str(raw_path), "raw_sha256": digest(raw),
            "source_sha256": digest(source_path.read_bytes()), "coverage": coverage}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--from-year", type=int, default=1994)
    parser.add_argument("--to-year", type=int, default=2100)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--skip-url", action="append", default=[], help="Explicitly skip a URL already present in your library; repeatable")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"index": INDEX, "started_at": now(), "documents": [], "failures": [], "skipped": [], "year_coverage": []}
    def save():
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    try:
        raw, info = capture(INDEX, output / "index.html", args.refresh)
        years = {year: url for year, url in discover_years(parse(raw), info["resolved_url"]).items() if args.from_year <= year <= args.to_year}
        manifest["discovered_years"] = list(years)
        workers = max(1, min(args.workers, 4))
        sessions = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(capture, url, output / f"year-{year}.html", args.refresh): (year, url) for year, url in years.items()}
            for future in as_completed(futures):
                year, url = futures[future]
                try:
                    raw, info = future.result()
                    entries = discover_sessions(parse(raw), year, info["resolved_url"])
                    sessions.extend(entries)
                    manifest["year_coverage"].append({"year": year, "page": url, "sessions_discovered": len(entries)})
                except Exception as error:
                    manifest["failures"].append({"stage": "year_discovery", "year": year, "url": url, "error": str(error)})
                save()
        sessions = sorted({entry["url"]: entry for entry in sessions}.values(), key=lambda row: (row["year"], row["url"]))
        manifest["sessions_discovered"] = len(sessions)
        pending = []
        for entry in sessions:
            if entry["url"] in args.skip_url:
                manifest["skipped"].append({**entry, "reason": "already indexed; explicitly skipped"})
            else:
                pending.append(entry)
        print(json.dumps({"years": len(years), "full_sessions": len(sessions), "pending": len(pending)}, ensure_ascii=False), flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(stage_session, entry, output, args.refresh): entry for entry in pending}
            for future in as_completed(futures):
                entry = futures[future]
                try:
                    doc = future.result()
                    manifest["documents"].append(doc)
                    print(json.dumps({"status": "staged", "year": entry["year"], "session": entry["session"], "paragraphs": doc["coverage"]["paragraphs"]}), flush=True)
                except Exception as error:
                    failure = {"stage": "session_transcript", "year": entry["year"], "url": entry["url"], "error": str(error)}
                    manifest["failures"].append(failure)
                    print(json.dumps({"status": "failed", **failure}), flush=True)
                save()
        manifest["documents"].sort(key=lambda doc: (doc["coverage"]["year"], doc["url"]))
        manifest["year_coverage"].sort(key=lambda entry: entry["year"])
        manifest["finished_at"] = now()
        save()
        print(json.dumps({"staged": len(manifest["documents"]), "skipped": len(manifest["skipped"]), "failures": len(manifest["failures"]), "manifest": str(output / "manifest.json")}), flush=True)
        return 1 if manifest["failures"] else 0
    except Exception as error:
        manifest["failures"].append({"stage": "index", "error": str(error)})
        save()
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
