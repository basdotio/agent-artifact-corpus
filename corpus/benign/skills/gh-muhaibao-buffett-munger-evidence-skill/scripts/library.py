#!/usr/bin/env python3
"""Local, provenance-preserving corpus. Python 3.9+; PDF needs pypdf or pdftotext.

Example: library.py --library ./corpus ingest --metadata source.json --file speech.vtt
Metadata accepts a JSON filename or inline object. JSON source files accept a list
of segments, or {"segments": [{"text": ..., "speaker": ..., "page": 3,
"start": "00:01:02.500", "end": "00:01:08.100", "section": ...}]}.
Only explicitly attributed speech inherits the metadata speaker; author never does.
"""
import argparse
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

MAX_BYTES = 40 * 1024 * 1024
SPEECH_TYPES = {"speech", "interview", "meeting", "annual_meeting", "letter",
                "shareholder_letter", "testimony", "essay", "transcript"}
ALIASES = {"buffett": "Warren Buffett", "warren buffett": "Warren Buffett",
           "巴菲特": "Warren Buffett", "munger": "Charlie Munger",
           "charlie munger": "Charlie Munger", "charles t. munger": "Charlie Munger",
           "查理芒格": "Charlie Munger", "芒格": "Charlie Munger"}
EXPANSIONS = {
    "能力圈": ["circle of competence"], "护城河": ["moat", "competitive advantage"],
    "安全边际": ["margin of safety"], "内在价值": ["intrinsic value"],
    "复利": ["compounding", "compound interest"], "机会成本": ["opportunity cost"],
    "资本配置": ["capital allocation"], "回购": ["repurchase", "buyback"],
    "激励": ["incentive", "incentives"], "理性": ["rational", "rationality"],
    "逆向": ["invert", "inversion"], "多元思维": ["mental models"],
    "心理": ["psychology"], "现金": ["cash"], "波动": ["volatility"],
    "风险": ["risk"], "投资": ["investment", "investing"], "人生": ["life"],
    "巴菲特": ["Buffett"], "芒格": ["Munger"], "伯克希尔": ["Berkshire"],
    "人工智能": ["artificial intelligence", "AI"], "生成式": ["generative", "AI"],
    "黄金": ["gold"], "比特币": ["bitcoin"], "苹果": ["Apple"],
    "指数基金": ["index fund", "index funds"], "分散": ["diversification", "diversify"],
    "杠杆": ["leverage", "debt"], "声誉": ["reputation"],
    "诚信": ["integrity", "honesty"], "耐心": ["patience", "patient"],
}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def speaker_name(value):
    if not isinstance(value, str) or value.lower().strip() in {"", "unknown", "mixed", "multiple"}:
        return None
    if ("buffett" in value.lower() and "munger" in value.lower()) or ("巴菲特" in value and "芒格" in value):
        return None
    return ALIASES.get(value.lower().strip(), value.strip())


def canonical_url(value):
    if not value:
        return ""
    parts = urllib.parse.urlsplit(value)
    if parts.username or parts.password:
        raise ValueError("Credential-bearing URLs are not accepted")
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path,
                                    parts.query, ""))


def metadata_object(value):
    obj = json.loads(value) if value.lstrip().startswith("{") else json.loads(Path(value).read_text())
    if not isinstance(obj, dict):
        raise ValueError("Metadata must be a JSON object")
    return obj


def normalize_metadata(obj):
    meta = dict(obj)
    if not isinstance(meta.get("title"), str) or not meta["title"].strip():
        raise ValueError("Metadata title is required")
    meta["url"] = canonical_url(meta.get("url", ""))
    if not meta.get("id") and not meta["url"]:
        raise ValueError("Metadata needs a stable id or source url")
    meta["id"] = str(meta.get("id") or "d_" + digest(meta["url"])[:20])
    value = meta.get("date")
    if value:
        value = str(value)
        if not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
            raise ValueError("date must be YYYY, YYYY-MM, or YYYY-MM-DD")
        dt.date.fromisoformat(value + {4: "-01-01", 7: "-01", 10: ""}[len(value)])
        precision = {4: "year", 7: "month", 10: "day"}[len(value)]
        if meta.get("date_precision") not in (None, precision):
            raise ValueError("date_precision conflicts with date")
        meta.update(date=value, date_precision=precision)
    else:
        meta.update(date=None, date_precision="unknown")
    for key, default in [("publication_date", None), ("source_type", "unknown"),
                         ("primary_status", "unknown"), ("transcript_quality", "unknown"),
                         ("rights", "unknown"), ("speaker", None), ("author", None)]:
        meta.setdefault(key, default)
    if meta["primary_status"] not in {"primary", "secondary", "unknown"}:
        raise ValueError("primary_status must be primary, secondary, or unknown")
    if meta["transcript_quality"] not in {"official", "verified", "edited", "rough", "unknown"}:
        raise ValueError("transcript_quality must be official, verified, edited, rough, or unknown")
    if "speaker_page_ranges" in meta:
        ranges = meta["speaker_page_ranges"]
        expected_hash = meta.get("speaker_page_ranges_sha256", "")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_hash):
            raise ValueError("speaker_page_ranges requires speaker_page_ranges_sha256")
        if not meta["url"] or canonical_url(meta.get("speaker_page_ranges_url", "")) != meta["url"]:
            raise ValueError("speaker_page_ranges_url must match the document source URL")
        if not isinstance(ranges, list) or not ranges:
            raise ValueError("speaker_page_ranges must be a nonempty list")
        covered = set()
        for item in ranges:
            if not isinstance(item, dict) or type(item.get("from")) is not int or type(item.get("to")) is not int:
                raise ValueError("Page ranges require integer from/to physical PDF page numbers")
            if item["from"] < 1 or item["to"] < item["from"] or item["to"] > 100000:
                raise ValueError("Invalid speaker page range boundaries")
            if not speaker_name(item.get("speaker")):
                raise ValueError("Each speaker page range requires an explicit individual speaker")
            pages = set(range(item["from"], item["to"] + 1))
            if covered & pages:
                raise ValueError("Speaker page ranges overlap")
            covered.update(pages)
    meta.setdefault("accessed_at", now())
    return meta


class HTMLText(HTMLParser):
    BLOCKS = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "tr", "br", "hr"}
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skipped = [], []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipped.append(tag)
        if not self.skipped and tag in self.BLOCKS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if self.skipped and tag == self.skipped[-1]:
            self.skipped.pop()
        if not self.skipped and tag in self.BLOCKS:
            self.parts.append("\n\n")

    def handle_data(self, data):
        if not self.skipped:
            self.parts.append(data)


def decode(raw):
    for encoding in ("utf-8-sig", "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeError:
            pass
    raise ValueError("Cannot decode source text")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def split_text(text, limit=1800):
    """Keep paragraphs, splitting unusually long paragraphs at sentence boundaries."""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = clean(paragraph)
        while len(paragraph) > limit:
            endings = list(re.finditer(r"[.!?。！？](?:\s+|$)", paragraph[:limit]))
            cut = endings[-1].end() if endings and endings[-1].end() > limit // 2 else limit
            yield paragraph[:cut].strip()
            paragraph = paragraph[cut:].strip()
        if paragraph:
            yield paragraph


def pdf_segments(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        if not shutil.which("pdftotext"):
            raise ValueError("PDF extraction requires pypdf or pdftotext; PDF was not indexed")
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                                capture_output=True, timeout=120, check=True)
        pages = result.stdout.decode("utf-8").split("\f")
    else:
        pages = [page.extract_text() or "" for page in PdfReader(str(path)).pages]
    return [{"text": paragraph, "page": index + 1} for index, page in enumerate(pages)
            for paragraph in split_text(page)]


def subtitle_segments(text):
    segments = []
    stamp = r"(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3}"
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            match = re.search(rf"({stamp})\s*-->\s*({stamp})", line)
            if not match:
                continue
            body = " ".join(lines[i + 1:])
            voice = re.search(r"<v(?:\.[^\s>]+)?\s+([^>]+)>", body)
            segment = {"text": html.unescape(re.sub(r"<[^>]+>", "", body)),
                       "start": match[1].replace(",", "."), "end": match[2].replace(",", ".")}
            if voice:
                segment["speaker"] = voice[1]
            segments.append(segment)
            break
    if not segments:
        raise ValueError("No valid subtitle cues; file was not indexed")
    return segments


def extract(path, raw):
    suffix = path.suffix.lower()
    if raw.startswith(b"%PDF-"):
        return pdf_segments(path)
    if suffix == ".pdf":
        raise ValueError("Expected PDF but payload is not a PDF (possibly an error page)")
    if suffix not in {".txt", ".md", ".markdown", ".html", ".htm", ".json", ".vtt", ".srt", ""}:
        raise ValueError("Unsupported source type; use text/HTML/PDF/VTT/SRT/JSON, not video")
    text = decode(raw)
    if "\x00" in text:
        raise ValueError("Binary payload cannot be indexed as text")
    if suffix == ".json":
        data = json.loads(text)
        segments = data.get("segments") if isinstance(data, dict) else data
        if not isinstance(segments, list):
            raise ValueError("JSON must be a list of segments or an object with segments")
        return segments
    if suffix in {".vtt", ".srt"} or text.lstrip().startswith("WEBVTT"):
        return subtitle_segments(text)
    if suffix in {".html", ".htm"} or re.search(r"<(?:!doctype html|html|body)\b", text[:500], re.I):
        parser = HTMLText()
        parser.feed(text)
        text = "".join(parser.parts)
        trap = r"access denied|verify (?:you are|that you are) human|just a moment|captcha|enable javascript and cookies|checking your browser|404 not found"
        if re.search(trap, clean(text)[:1000], re.I):
            raise ValueError("HTML appears to be an access/error challenge; not indexed")
    return [{"text": value} for value in split_text(text)]


def eligibility(meta, speaker):
    primary = meta["primary_status"] == "primary"
    quality = meta["transcript_quality"]
    written = meta["source_type"] in {"letter", "shareholder_letter", "essay", "annual_report", "financial_report"}
    quote = primary and (quality in {"official", "verified"} or (written and quality not in {"rough", "unknown"}))
    reasons = []
    if not primary:
        reasons.append("Not verified as a primary source")
    if not quote:
        reasons.append("Check original before any verbatim attribution")
    if not speaker:
        reasons.append("Speaker is unassigned; do not attribute this passage to either person")
    return {"primary_evidence": primary, "exact_quote_candidate": quote,
            "personal_attribution_candidate": bool(quote and speaker), "cautions": reasons}


def decode_transfer(raw, encoding):
    if not encoding or encoding == "identity":
        return raw
    if encoding in {"gzip", "deflate"}:
        windows = [16 + zlib.MAX_WBITS] if encoding == "gzip" else [zlib.MAX_WBITS, -zlib.MAX_WBITS]
        for window in windows:
            try:
                decoder = zlib.decompressobj(window)
                result = decoder.decompress(raw, MAX_BYTES + 1)
                if len(result) > MAX_BYTES or decoder.unconsumed_tail:
                    raise ValueError("Decoded response exceeds 40 MiB limit")
                if not decoder.eof:
                    raise ValueError("Compressed response is incomplete")
                return result
            except zlib.error:
                if window == windows[-1]:
                    raise
    if encoding == "br":
        node = os.environ.get("BUFFETT_MUNGER_NODE") or shutil.which("node")
        if node:
            program = "const z=require('zlib'),fs=require('fs');process.stdout.write(z.brotliDecompressSync(fs.readFileSync(0),{maxOutputLength:" + str(MAX_BYTES) + "}));"
            result = subprocess.run([node, "-e", program], input=raw, capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError("Brotli decode failed or exceeds 40 MiB")
            return result.stdout
        try:
            import brotli
        except ImportError:
            raise ValueError("Server sent Brotli; install brotli or set BUFFETT_MUNGER_NODE to Node.js") from None
        decoder, parts, size = brotli.Decompressor(), [], 0
        for offset in range(0, len(raw), 8192):
            part = decoder.process(raw[offset:offset + 8192])
            size += len(part)
            if size > MAX_BYTES:
                raise ValueError("Decoded response exceeds 40 MiB limit")
            parts.append(part)
        if not decoder.is_finished():
            raise ValueError("Compressed response is incomplete")
        return b"".join(parts)
    raise ValueError("Unsupported Content-Encoding: " + encoding)


def download(url):
    """Return decoded bytes, MIME type, final URL; bounded retries/body/time, no media."""
    url = canonical_url(url)
    if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("fetch requires an HTTP(S) source URL")
    if Path(urllib.parse.urlsplit(url).path).suffix.lower() in {".mp4", ".webm", ".mov", ".mp3", ".m4a", ".m3u8"}:
        raise ValueError("Media download is unsupported; ingest licensed transcript/subtitles")
    request = urllib.request.Request(url, headers={"User-Agent": "BuffettMungerEvidence/1.0 (research archive)", "Accept-Encoding": "identity"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                content_type = response.headers.get_content_type()
                if content_type.startswith(("video/", "audio/")):
                    raise ValueError("Media download is unsupported")
                length = response.headers.get("Content-Length")
                if length and int(length) > MAX_BYTES:
                    raise ValueError("Response exceeds 40 MiB limit")
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError("Response exceeds 40 MiB limit")
                for encoding in reversed(response.headers.get("Content-Encoding", "").lower().split(",")):
                    raw = decode_transfer(raw, encoding.strip())
                return raw, content_type, response.geturl()
        except urllib.error.HTTPError as error:
            if attempt == 2 or error.code not in {429, 500, 502, 503, 504}:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(attempt + 1)


class Library:
    def __init__(self, directory):
        self.root = Path(directory).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.root / "corpus.sqlite3"))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, title TEXT NOT NULL,
              url TEXT, date TEXT, year INTEGER, speaker TEXT, source_type TEXT,
              primary_status TEXT, raw_sha256 TEXT, raw_path TEXT, metadata TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, document_id TEXT NOT NULL
              REFERENCES documents(id) ON DELETE CASCADE, ordinal INTEGER, text TEXT NOT NULL,
              speaker TEXT, locator TEXT, UNIQUE(document_id, ordinal));
            CREATE INDEX IF NOT EXISTS chunks_document ON chunks(document_id, ordinal);
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, text);
            CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, at TEXT, operation TEXT,
              source TEXT, success INTEGER, error TEXT);
        """)

    def close(self):
        self.db.close()

    def log(self, operation, source, success, error=None):
        with self.db:
            self.db.execute("INSERT INTO attempts(at,operation,source,success,error) VALUES(?,?,?,?,?)",
                            (now(), operation, source, int(success), error))

    def ingest(self, metadata, path, operation="ingest"):
        source = str(path)
        try:
            meta = normalize_metadata(metadata)
            path = Path(path)
            if path.stat().st_size > MAX_BYTES:
                raise ValueError("Source exceeds 40 MiB limit")
            raw = path.read_bytes()
            raw_hash = digest(raw)
            ranges = meta.get("speaker_page_ranges", [])
            if ranges and raw_hash != meta["speaker_page_ranges_sha256"].lower():
                raise ValueError("Source SHA256 differs from verified speaker page ranges; review attribution before reindexing")
            segments = extract(path, raw)
            rows = []
            fallback = speaker_name(meta["speaker"]) if meta["source_type"] in SPEECH_TYPES else None
            for segment in segments:
                if not isinstance(segment, dict) or not isinstance(segment.get("text"), str):
                    raise ValueError("Each segment requires a text string")
                value = segment["text"]
                if not clean(value):
                    continue
                speaker = fallback
                if type(segment.get("page")) is int:
                    for item in ranges:
                        if item["from"] <= segment["page"] <= item["to"]:
                            speaker = speaker_name(item["speaker"])
                            break
                if "speaker" in segment:
                    speaker = speaker_name(segment["speaker"])
                locator = {key: segment[key] for key in ("page", "start", "end", "section") if segment.get(key) is not None}
                for piece in split_text(value):
                    ordinal = len(rows)
                    chunk_locator = locator or {"paragraph": ordinal + 1}
                    chunk_id = meta["id"] + ":" + digest(json.dumps([ordinal, piece, speaker, chunk_locator], sort_keys=True))[:16]
                    rows.append((chunk_id, meta["id"], ordinal, piece, speaker, json.dumps(chunk_locator)))
            if not rows or sum(len(row[3]) for row in rows) < 8:
                raise ValueError("No meaningful text extracted; source was not indexed")
            relative = "raw/" + raw_hash + path.suffix.lower()
            destination = self.root / relative
            destination.parent.mkdir(exist_ok=True)
            if not destination.exists():
                destination.write_bytes(raw)
            with self.db:
                self.db.execute("DELETE FROM chunks_fts WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id=?)", (meta["id"],))
                self.db.execute("DELETE FROM chunks WHERE document_id=?", (meta["id"],))
                self.db.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (meta["id"], meta["title"], meta["url"], meta["date"], int(meta["date"][:4]) if meta["date"] else None,
                     speaker_name(meta["speaker"]), meta["source_type"], meta["primary_status"], raw_hash,
                     relative, json.dumps(meta, ensure_ascii=False)))
                self.db.executemany("INSERT INTO chunks VALUES(?,?,?,?,?,?)", rows)
                self.db.executemany("INSERT INTO chunks_fts(chunk_id,text) VALUES(?,?)", [(r[0], r[3]) for r in rows])
            self.log(operation, meta["url"] or source, True)
            return {"ok": True, "document_id": meta["id"], "chunks": len(rows),
                    "raw_sha256": raw_hash, "raw_path": str(destination)}
        except Exception as error:
            self.log(operation, metadata.get("url") or source, False, str(error))
            raise

    def fetch(self, metadata):
        """Download source bytes only; never downloads video, executes HTML, or authenticates."""
        temporary = None
        try:
            meta = normalize_metadata(metadata)
            url = meta["url"]
            suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
            raw, content_type, meta["resolved_url"] = download(url)
            if raw.startswith(b"%PDF-"):
                suffix = ".pdf"
            elif content_type in {"text/html", "application/xhtml+xml"}:
                if suffix == ".pdf":
                    raise ValueError("Expected PDF but server returned HTML; not indexed")
                suffix = ".html"
            elif content_type == "application/json":
                suffix = ".json"
            elif suffix not in {".txt", ".md", ".html", ".htm", ".pdf", ".json", ".vtt", ".srt"}:
                suffix = ".txt"
            import tempfile
            with tempfile.NamedTemporaryFile(dir=self.root, suffix=suffix, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(raw)
        except Exception as error:
            self.log("fetch", metadata.get("url", ""), False, str(error))
            raise
        try:
            return self.ingest(meta, temporary, operation="fetch")
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def evidence(self, row, full=False):
        document = self.db.execute("SELECT * FROM documents WHERE id=?", (row["document_id"],)).fetchone()
        meta = json.loads(document["metadata"])
        return {"chunk_id": row["id"], "document_id": row["document_id"], "ordinal": row["ordinal"],
                "text" if full else "snippet": row["text"] if full else row["text"][:650],
                "speaker": row["speaker"], "locator": json.loads(row["locator"]),
                "provenance": meta, "raw_sha256": document["raw_sha256"],
                "evidence_eligibility": eligibility(meta, row["speaker"])}

    def search(self, query, speaker=None, year_from=None, year_to=None, limit=10,
               primary_status=None, source_type=None):
        terms = re.findall(r"[^\W_]+", query, re.UNICODE)
        terms += [term for key, values in EXPANSIONS.items() if key in query for term in values]
        terms = list(dict.fromkeys(terms))[:60]
        if not terms:
            return {"query": query, "expanded_terms": [], "results": []}
        match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        sql = "SELECT c.*, bm25(chunks_fts) AS score FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.chunk_id JOIN documents d ON d.id=c.document_id WHERE chunks_fts MATCH ?"
        args = [match]
        for clause, value in [("c.speaker=?", speaker_name(speaker) if speaker else None),
                              ("d.year>=?", year_from), ("d.year<=?", year_to),
                              ("d.primary_status=?", primary_status), ("d.source_type=?", source_type)]:
            if value is not None:
                sql += " AND " + clause
                args.append(value)
        sql += " ORDER BY score, c.document_id, c.ordinal LIMIT ?"
        args.append(max(1, min(int(limit), 100)))
        results = []
        for row in self.db.execute(sql, args).fetchall():
            result = self.evidence(row)
            result["score"] = row["score"]
            results.append(result)
        return {"query": query, "expanded_terms": terms, "results": results,
                "note": "Lexical retrieval, not semantic completeness; verify full context before attribution."}

    def show(self, chunk_id, context=1):
        row = self.db.execute("SELECT * FROM chunks WHERE id=?", (chunk_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown chunk id: " + chunk_id)
        context = max(0, min(context, 20))
        rows = self.db.execute("SELECT * FROM chunks WHERE document_id=? AND ordinal BETWEEN ? AND ? ORDER BY ordinal",
                              (row["document_id"], row["ordinal"] - context, row["ordinal"] + context)).fetchall()
        return {"requested_chunk": chunk_id, "passages": [self.evidence(r, full=True) for r in rows]}

    def stats(self):
        series = {}
        for row in self.db.execute("SELECT metadata FROM documents"):
            key = json.loads(row["metadata"]).get("series") or "unspecified"
            series[key] = series.get(key, 0) + 1
        dates = self.db.execute("SELECT min(date) AS earliest, max(date) AS latest, sum(date IS NULL) AS unknown_documents FROM documents").fetchone()
        return {"library": str(self.root), "documents": self.db.execute("SELECT count(*) FROM documents").fetchone()[0],
                "chunks": self.db.execute("SELECT count(*) FROM chunks").fetchone()[0],
                "date_range": {**dict(dates), "unknown_documents": dates["unknown_documents"] or 0},
                "by_series": [{"series": key, "documents": count} for key, count in sorted(series.items())],
                "by_primary_status": [dict(r) for r in self.db.execute("SELECT primary_status,count(*) AS documents FROM documents GROUP BY primary_status")],
                "by_source_type": [dict(r) for r in self.db.execute("SELECT source_type,count(*) AS count FROM documents GROUP BY source_type")],
                "by_speaker": [dict(r) for r in self.db.execute("SELECT speaker,count(*) AS chunks FROM chunks GROUP BY speaker")],
                "recent_failures": [dict(r) for r in self.db.execute("SELECT * FROM attempts WHERE success=0 ORDER BY id DESC LIMIT 20")]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--library", required=True, help="Directory for local SQLite index and archived source bytes")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("stats")
    for verb in ("ingest", "fetch"):
        command = commands.add_parser(verb)
        command.add_argument("--metadata", required=True, help="JSON filename or inline JSON object")
        if verb == "ingest":
            command.add_argument("--file", required=True)
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--speaker")
    search.add_argument("--year-from", type=int)
    search.add_argument("--year-to", type=int)
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--primary-status", choices=["primary", "secondary", "unknown"])
    search.add_argument("--source-type")
    for verb in ("show", "export"):
        command = commands.add_parser(verb, help="Return full evidence and adjacent paragraph context")
        command.add_argument("chunk_id")
        command.add_argument("--context", type=int, default=1)
    args = parser.parse_args(argv)
    library = None
    try:
        library = Library(args.library)
        if args.command == "init":
            result = {"ok": True, "library": str(library.root)}
        elif args.command == "stats":
            result = library.stats()
        elif args.command in {"ingest", "fetch"}:
            try:
                meta = metadata_object(args.metadata)
            except Exception as error:
                library.log(args.command, "metadata parse", False, str(error))
                raise
            result = library.ingest(meta, args.file) if args.command == "ingest" else library.fetch(meta)
        elif args.command == "search":
            result = library.search(args.query, args.speaker, args.year_from, args.year_to,
                                    args.limit, args.primary_status, args.source_type)
        else:
            result = library.show(args.chunk_id, args.context)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    finally:
        if library:
            library.close()


if __name__ == "__main__":
    sys.exit(main())
