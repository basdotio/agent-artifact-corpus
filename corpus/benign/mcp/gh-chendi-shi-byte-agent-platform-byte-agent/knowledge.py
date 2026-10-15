"""Versioned local knowledge with lexical retrieval and optional dense fusion."""
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path


def tokens(text):
    # Latin terms plus Chinese bigrams; no claim of semantic tokenization.
    terms = re.findall(r"[a-z0-9_]+", text.lower())
    for span in re.findall(r"[\u4e00-\u9fff]+", text):
        terms.extend(span[i:i + 2] for i in range(max(1, len(span) - 1)))
    return terms


class Knowledge:
    def __init__(self, database):
        self.db = sqlite3.connect(database)
        self.db.execute("CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, source TEXT, text TEXT, vector TEXT, service TEXT)")
        # Existing local indexes can be read and re-ingested without manual migration.
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(chunks)")}
        if "service" not in columns:
            self.db.execute("ALTER TABLE chunks ADD COLUMN service TEXT")
        self.db.commit()

    def ingest(self, root, embed=None):
        root = Path(root).resolve()
        chunks = []
        for path in sorted(root.rglob("*.md")):
            if not path.resolve().is_relative_to(root):
                raise ValueError("knowledge symlink escapes root")
            source = path.relative_to(root).as_posix()
            content = path.read_text(encoding="utf-8")
            header = re.match(r"\A---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            service_match = re.search(r"^service:\s*([a-zA-Z0-9_.-]+)\s*$", header[1], re.MULTILINE) if header else None
            service = service_match[1] if service_match else (path.parent.name if "/" in source else path.stem)
            if header:
                content = content[header.end():]
            # Paragraph-preserving chunks, with a hard bound on large paragraphs.
            for paragraph_index, paragraph in enumerate(re.split(r"\n\s*\n", content)):
                for start in range(0, len(paragraph), 1000):
                    body = paragraph[start:start + 1000].strip()
                    if body:
                        identity = hashlib.sha256((source + "\0" + str(paragraph_index) + "\0" + str(start) + "\0" + body).encode()).hexdigest()[:20]
                        chunks.append((identity, source, body, service))
        vectors = embed([c[2] for c in chunks]) if embed and chunks else [None] * len(chunks)
        if len(vectors) != len(chunks):
            raise ValueError("embedding count mismatch")
        if embed and vectors:
            dims = {len(v) for v in vectors if isinstance(v, list)}
            if len(dims) != 1 or len(vectors) != sum(isinstance(v, list) for v in vectors):
                raise ValueError("invalid embedding dimensions")
            if not next(iter(dims)) or any(not math.isfinite(float(x)) for v in vectors for x in v):
                raise ValueError("invalid embedding values")
        with self.db:
            self.db.execute("DELETE FROM chunks")
            self.db.executemany("INSERT INTO chunks (id,source,text,vector,service) VALUES (?,?,?,?,?)",
                                [(c[0], c[1], c[2], json.dumps(v) if v is not None else None, c[3]) for c, v in zip(chunks, vectors)])
        return len(chunks)

    def search(self, query, limit=5, vector=None, service=None, source=None):
        if not 1 <= limit <= 20:
            raise ValueError("limit must be 1..20")
        if service is not None and (not isinstance(service, str) or not service or len(service) > 200):
            raise ValueError("service filter must be a bounded nonempty string")
        if source is not None and (not isinstance(source, str) or not source or len(source) > 1000):
            raise ValueError("source filter must be a bounded nonempty string")
        # Exact SQL predicates deliberately have no unfiltered fallback.
        clauses, parameters = [], []
        if service is not None:
            clauses.append("service=?")
            parameters.append(service)
        if source is not None:
            clauses.append("source=?")
            parameters.append(source)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.db.execute("SELECT id,source,text,vector FROM chunks" + where + " ORDER BY id", parameters).fetchall()
        if not rows:
            return []
        query_terms = Counter(tokens(query))
        docs = [Counter(tokens(r[2])) for r in rows]
        avg = sum(sum(d.values()) for d in docs) / len(docs) or 1
        df = Counter(t for d in docs for t in d)
        scores = []
        for i, d in enumerate(docs):
            score = 0.0
            for t in query_terms:
                tf = d[t]
                idf = math.log(1 + (len(docs) - df[t] + .5) / (df[t] + .5))
                score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * sum(d.values()) / avg))
            if score:
                scores.append((i, score))
        lexical = sorted(scores, key=lambda item: (-item[1], rows[item[0]][0]))
        fused = {i: 1 / (60 + rank) for rank, (i, _) in enumerate(lexical, 1)}
        if vector is not None:
            norm = math.sqrt(sum(x * x for x in vector))
            if not norm or not math.isfinite(norm):
                raise ValueError("invalid query vector")
            dense = []
            for i, row in enumerate(rows):
                v = json.loads(row[3]) if row[3] else None
                if v is None:
                    raise ValueError("index has no dense vectors; re-ingest with embeddings")
                if len(v) != len(vector):
                    raise ValueError("embedding dimension mismatch")
                denom = math.sqrt(sum(x * x for x in v)) * norm
                cosine = sum(a * b for a, b in zip(v, vector)) / denom if denom else 0
                dense.append((i, cosine))
            for rank, (i, _) in enumerate(sorted(dense, key=lambda item: (-item[1], rows[item[0]][0])), 1):
                fused[i] = fused.get(i, 0) + 1 / (60 + rank)
        return [{"id": rows[i][0], "source": rows[i][1], "text": rows[i][2], "score": score, "trust": "untrusted_evidence"}
                for i, score in sorted(fused.items(), key=lambda item: (-item[1], rows[item[0]][0]))[:limit]]
