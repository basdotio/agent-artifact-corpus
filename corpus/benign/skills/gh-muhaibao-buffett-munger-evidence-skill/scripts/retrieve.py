#!/usr/bin/env python3
"""Local BM25 + multilingual ONNX retrieval; corpus is always opened read-only."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time

import attribution
from library import Library, EXPANSIONS
from setup_retrieval import MODELS, sha256

INDEX_VERSION = 1
STOPWORDS = set("a an the is are was were be been do does did of to in on for and or what how why when would should could can i you he she they it his her their this that with from as at by".split())


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def open_corpus(directory):
    root = Path(directory).expanduser().resolve()
    corpus = Library.__new__(Library)
    corpus.root = root
    corpus.db = sqlite3.connect((root / "corpus.sqlite3").as_uri() + "?mode=ro", uri=True)
    corpus.db.row_factory = sqlite3.Row
    corpus.db.execute("PRAGMA query_only=ON")
    return corpus


def fingerprint(corpus):
    h = hashlib.sha256()
    for row in corpus.db.execute("SELECT id,raw_sha256,metadata FROM documents ORDER BY id"):
        h.update(json.dumps(list(row), ensure_ascii=False).encode())
    for row in corpus.db.execute("SELECT id,document_id,ordinal,text,speaker,locator FROM chunks ORDER BY id"):
        h.update(json.dumps(list(row), ensure_ascii=False).encode())
    return h.hexdigest()


def query_terms(query, exact=False):
    if exact:
        value = query.strip().strip('"“”')
        return [value] if value else []
    phrases = re.findall(r'"([^"\n]+)"|“([^”\n]+)”', query)
    phrases = [a or b for a, b in phrases]
    remainder = re.sub(r'"[^"\n]+"|“[^”\n]+”', ' ', query)
    terms = [w for w in re.findall(r"[^\W_]+", remainder, re.UNICODE)
             if w.lower() not in STOPWORDS]
    for key, values in EXPANSIONS.items():
        if key in query:
            terms.extend(values)
    return list(dict.fromkeys(phrases + terms))[:60]


def attribution_level(include_unassigned=False, attribution_mode=None):
    level = attribution_mode or ("unassigned" if include_unassigned else "strict")
    if level not in attribution.LEVELS:
        raise ValueError("attribution must be one of " + ", ".join(attribution.LEVELS))
    return level


TRANSLATION = "translation"   # Chinese editions and other translations: excluded unless asked for


def filters_sql(speaker=None, year_from=None, year_to=None, primary_status=None,
                source_type=None, include_unassigned=False, attribution_mode=None, exclude_documents=None,
                include_translations=False):
    clauses, values = [], []
    if not include_translations and source_type != TRANSLATION:
        clauses.append("d.source_type IS NOT ?")
        values.append(TRANSLATION)
    if speaker:
        level = attribution_level(include_unassigned, attribution_mode)
        labels = attribution.labels_for(speaker)
        speaker_clause = "c.speaker IN (" + ",".join("?" * len(labels)) + ")" if labels else "0"
        values.extend(labels)
        if level == "unassigned":
            speaker_clause += " OR c.speaker IS NULL"
        elif level == "author":
            documents = list(attribution.author_documents(speaker))
            if documents:
                speaker_clause += " OR (c.speaker IS NULL AND c.document_id IN (" + ",".join("?" * len(documents)) + "))"
                values.extend(documents)
        clauses.append("(" + speaker_clause + ")")
    if exclude_documents:
        clauses.append("c.document_id NOT IN (" + ",".join("?" * len(exclude_documents)) + ")")
        values.extend(exclude_documents)
    for clause, value in [("d.year>=?", year_from), ("d.year<=?", year_to),
                          ("d.primary_status=?", primary_status), ("d.source_type=?", source_type)]:
        if value is not None:
            clauses.append(clause)
            values.append(value)
    return (" AND " + " AND ".join(clauses) if clauses else ""), values


def lexical_search(corpus, query, limit=50, exact=False, **filters):
    terms = query_terms(query, exact)
    if not terms:
        return []
    match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
    where, params = filters_sql(**filters)
    sql = (
        "SELECT c.id,c.text,bm25(chunks_fts) AS score FROM chunks_fts "
        "JOIN chunks c ON c.id=chunks_fts.chunk_id JOIN documents d ON d.id=c.document_id "
        "WHERE chunks_fts MATCH ?" + where + " ORDER BY score,c.id")
    if not exact:
        rows = corpus.db.execute(sql + " LIMIT ?", [match] + params + [limit])
        return [(r["id"], float(r["score"])) for r in rows]
    # FTS tokenization drops punctuation: '90%' must not silently match '90'.
    # Keep scanning ranked candidates until enough literal matches are found.
    needle = " ".join(terms[0].split()).casefold()
    results = []
    for row in corpus.db.execute(sql, [match] + params):
        if needle in " ".join(row["text"].split()).casefold():
            results.append((row["id"], float(row["score"])))
            if len(results) >= limit:
                break
    return results


def rrf(rankings, k=60):
    scores, routes = defaultdict(float), defaultdict(dict)
    for name, ranking in rankings.items():
        seen = set()
        for rank, (key, original_score) in enumerate(ranking, 1):
            if key in seen:
                continue
            seen.add(key)
            scores[key] += 1.0 / (k + rank)
            routes[key][name] = {"rank": rank, "score": original_score}
    return sorted(scores, key=lambda key: (-scores[key], key)), scores, routes


class LocalModel:
    """Only reads pinned ONNX/tokenizer files. No network or remote Python code."""
    def __init__(self, models_dir, kind="embedding", max_tokens=256, threads=4):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        ort.disable_telemetry_events()
        self.np = np
        self.kind = kind
        directory = Path(models_dir) / kind
        spec = MODELS[kind]
        for name, (_, expected) in spec["files"].items():
            path = directory / name
            if not path.exists() or sha256(path) != expected:
                raise ValueError(f"Missing or mismatched {kind}/{name}; run setup_retrieval.py explicitly")
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=max_tokens)
        pad_id = self.tokenizer.token_to_id("<pad>")
        pad_token = "<pad>"
        if pad_id is None:
            pad_id, pad_token = self.tokenizer.token_to_id("[PAD]"), "[PAD]"
        self.tokenizer.enable_padding(pad_id=pad_id if pad_id is not None else 0, pad_token=pad_token)
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(directory / "model.onnx"), sess_options=options,
                                            providers=["CPUExecutionProvider"])
        self.inputs = {x.name for x in self.session.get_inputs()}

    def run(self, texts):
        np = self.np
        tokens = self.tokenizer.encode_batch(texts)
        data = {"input_ids": np.array([t.ids for t in tokens], dtype=np.int64),
                "attention_mask": np.array([t.attention_mask for t in tokens], dtype=np.int64),
                "token_type_ids": np.array([t.type_ids for t in tokens], dtype=np.int64)}
        output = self.session.run(None, {k: v for k, v in data.items() if k in self.inputs})[0]
        return output, data["attention_mask"]

    def embed(self, texts, query=False):
        np = self.np
        prefix = "query: " if query else "passage: "
        hidden, mask = self.run([prefix + text for text in texts])
        mask = mask[..., None]
        pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
        return (pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)).astype(np.float32)

    def rerank(self, query, texts, batch_size=16):
        scores = []
        for start in range(0, len(texts), batch_size):
            logits, _ = self.run([(query, text) for text in texts[start:start + batch_size]])
            scores.extend(float(x) for x in logits.reshape(-1))
        return scores


def source_rows(corpus):
    return corpus.db.execute("SELECT c.*,d.title,d.date,d.year,d.source_type,d.primary_status "
                             "FROM chunks c JOIN documents d ON d.id=c.document_id "
                             "ORDER BY c.document_id,c.ordinal").fetchall()


def indexed_text(row):
    # Only observed metadata; no generated summaries are blended into source text.
    title = row["title"][:180]
    return f"{title} | {row['date'] or 'date unknown'} | {row['speaker'] or 'speaker unassigned'}\n{row['text']}"


def build_index(corpus, index_dir, models_dir, batch_size=32, max_tokens=256, threads=4):
    import fcntl
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    with (index_dir / "build.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another index build is running") from exc
        return _build_index(corpus, index_dir, models_dir, batch_size, max_tokens, threads)


def _build_index(corpus, index_dir, models_dir, batch_size=32, max_tokens=256, threads=4):
    import numpy as np
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    before = fingerprint(corpus)
    rows = source_rows(corpus)
    if not rows:
        raise ValueError("Cannot build an empty corpus")
    config = {"version": INDEX_VERSION, "corpus_fingerprint": before, "chunks": len(rows),
              "model": MODELS["embedding"], "max_tokens": max_tokens}
    key = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:20]
    directory = index_dir / key
    directory.mkdir(exist_ok=True)
    manifest = directory / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()).get("complete"):
        existing = json.loads(manifest.read_text())
        if (sha256(directory / "vectors.npy") != existing["vectors_sha256"]
                or sha256(directory / "rows.json") != existing["rows_sha256"]):
            raise ValueError("Existing completed generation is corrupt; restore it or move that generation aside before rebuilding")
        atomic_json(index_dir / "current.json", {"generation": key})
        return existing
    model = LocalModel(models_dir, max_tokens=max_tokens, threads=threads)
    # Similar-length batches reduce padding; mapping back to corpus rows is explicit.
    order = sorted(range(len(rows)), key=lambda i: (len(rows[i]["text"]), i))
    progress_file = directory / "progress.json"
    completed = json.loads(progress_file.read_text())["completed"] if progress_file.exists() else 0
    vectors_path = directory / "vectors.npy"
    vectors = np.lib.format.open_memmap(vectors_path, mode="r+" if completed else "w+",
                                        dtype=np.float32, shape=(len(rows), 384))
    started = last_log = time.monotonic()
    for start in range(completed, len(rows), batch_size):
        selection = order[start:start + batch_size]
        vectors[selection] = model.embed([indexed_text(rows[i]) for i in selection])
        done = start + len(selection)
        if time.monotonic() - last_log >= 20 or done == len(rows):
            vectors.flush()
            atomic_json(progress_file, {"completed": done})
            print(json.dumps({"indexed": done, "total": len(rows),
                              "elapsed_seconds": round(time.monotonic() - started)}, ensure_ascii=False),
                  file=sys.stderr, flush=True)
            last_log = time.monotonic()
    vectors.flush()
    if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-3):
        raise ValueError("Invalid embeddings; index was not activated")
    if fingerprint(corpus) != before:
        raise ValueError("Corpus changed while indexing; index was not activated")
    records = [{key: r[key] for key in ("id", "document_id", "ordinal", "speaker", "year", "source_type", "primary_status")}
               for r in rows]
    atomic_json(directory / "rows.json", records)
    complete = dict(config, complete=True, built_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    vectors_sha256=sha256(vectors_path), rows_sha256=sha256(directory / "rows.json"))
    atomic_json(manifest, complete)
    atomic_json(index_dir / "current.json", {"generation": key})
    return complete


def index_status(corpus, index_dir):
    pointer = Path(index_dir) / "current.json"
    if not pointer.exists():
        return {"ready": False, "reason": "semantic index not built"}
    try:
        generation = json.loads(pointer.read_text())["generation"]
        if not re.fullmatch(r"[0-9a-f]{20}", generation):
            raise ValueError("invalid index generation")
        directory = pointer.parent / generation
        manifest = json.loads((directory / "manifest.json").read_text())
        if (manifest.get("version") != INDEX_VERSION or not manifest.get("complete")
                or json.dumps(manifest.get("model"), sort_keys=True) != json.dumps(MODELS["embedding"], sort_keys=True)):
            return {"ready": False, "reason": "index configuration mismatch"}
        if manifest["corpus_fingerprint"] != fingerprint(corpus):
            return {"ready": False, "reason": "corpus changed; semantic index is stale"}
        for name, field in [("vectors.npy", "vectors_sha256"), ("rows.json", "rows_sha256")]:
            if sha256(directory / name) != manifest[field]:
                return {"ready": False, "reason": "index checksum mismatch: " + name}
        return {"ready": True, "directory": str(directory), "chunks": manifest["chunks"],
                "max_tokens": manifest["max_tokens"], "built_at": manifest["built_at"]}
    except (OSError, ValueError, KeyError) as exc:
        return {"ready": False, "reason": str(exc)}


def make_matcher(speaker=None, year_from=None, year_to=None, source_type=None,
                 primary_status=None, include_unassigned=False, attribution_mode=None, exclude_documents=None,
                 include_translations=False):
    level = attribution_level(include_unassigned, attribution_mode)
    labels = set(attribution.labels_for(speaker)) if speaker else set()
    documents = set(attribution.author_documents(speaker)) if speaker and level == "author" else set()
    excluded = set(exclude_documents or [])

    def matcher(row):
        if row["document_id"] in excluded:
            return False
        if row["source_type"] == TRANSLATION and not include_translations and source_type != TRANSLATION:
            return False
        if speaker and row["speaker"] not in labels:
            if row["speaker"] is not None or level == "strict":
                return False
            if level == "author" and row["document_id"] not in documents:
                return False
        year = row["year"]
        if year_from is not None and (year is None or year < year_from):
            return False
        if year_to is not None and (year is None or year > year_to):
            return False
        return (source_type is None or row["source_type"] == source_type) and (
            primary_status is None or row["primary_status"] == primary_status)
    return matcher


def matches(row, **filters):
    return make_matcher(**filters)(row)


def semantic_search(status, model, query, limit=50, **filters):
    import numpy as np
    directory = Path(status["directory"])
    rows = json.loads((directory / "rows.json").read_text())
    vectors = np.load(directory / "vectors.npy", mmap_mode="r", allow_pickle=False)
    if vectors.shape != (len(rows), 384):
        raise ValueError("Semantic index dimension mismatch")
    scores = vectors @ model.embed([query], query=True)[0]
    matcher = make_matcher(**filters)
    selected = [i for i, row in enumerate(rows) if matcher(row)]
    selected.sort(key=lambda i: (-float(scores[i]), rows[i]["id"]))
    return [(rows[i]["id"], float(scores[i])) for i in selected[:limit]]


def evidence_group(evidence):
    meta = evidence["provenance"]
    return meta.get("parent_document_id") or meta.get("source_html_sha256") or evidence["raw_sha256"]


def context_passages(corpus, key, window):
    # Neighbors share the target's document provenance; do not repeat large
    # capture manifests, but retain their own speaker, locator and eligibility.
    fields = ("chunk_id", "document_id", "ordinal", "text", "speaker", "locator", "evidence_eligibility")
    return [{name: passage[name] for name in fields}
            for passage in corpus.show(key, context=window)["passages"]]


def search(corpus, query, index_dir, models_dir, mode="auto", lexical_queries=None,
           limit=10, candidates=50, rerank=True, context=2, max_per_document=3,
           exact=False, threads=4, rerank_query=None, **filters):
    warnings, rankings = [], {}
    if not query.strip():
        raise ValueError("Query must not be blank")
    if rerank_query is not None and not rerank_query.strip():
        raise ValueError("Rerank query must not be blank")
    if not 1 <= limit <= 100 or not limit <= candidates <= 500:
        raise ValueError("Require 1 <= limit <= candidates <= 500")
    if not 0 <= context <= 20 or max_per_document < 0 or threads < 1:
        raise ValueError("Require context in 0..20, max-per-document >= 0 and threads >= 1")
    if exact:
        mode, rerank = "lexical", False
    for i, text in enumerate(list(dict.fromkeys([query] + (lexical_queries or [])))):
        rankings[f"bm25_{i}"] = lexical_search(corpus, text, candidates, exact=exact, **filters)
    model, status = None, None
    if mode != "lexical":
        status = index_status(corpus, index_dir)
        if not status["ready"]:
            if mode == "hybrid":
                raise ValueError(status["reason"])
            warnings.append("Lexical-only fallback: " + status["reason"])
        else:
            try:
                model = LocalModel(models_dir, max_tokens=status["max_tokens"], threads=threads)
                rankings["semantic"] = semantic_search(status, model, query, candidates, **filters)
            except (ImportError, OSError, ValueError) as exc:
                if mode == "hybrid":
                    raise
                warnings.append("Lexical-only fallback: " + str(exc))
    keys, scores, routes = rrf(rankings)
    # Keep a bounded union for the cross-encoder; preserve per-route provenance.
    keys = keys[:candidates * 2]
    evidence = []
    for key in keys:
        row = corpus.db.execute("SELECT * FROM chunks WHERE id=?", (key,)).fetchone()
        item = corpus.evidence(row, full=True)
        item["retrieval"] = {"rrf_score": scores[key], "routes": routes[key]}
        item["source_group"] = evidence_group(item)
        evidence.append(item)
    reranked = False
    if rerank and evidence:
        try:
            ranker = LocalModel(models_dir, "reranker", max_tokens=512, threads=threads)
            texts = []
            for item in evidence:
                passages = corpus.show(item["chunk_id"], context=1)["passages"]
                passage_text = "\n".join(f"{p['speaker'] or 'unassigned'}: {p['text']}" for p in passages)
                texts.append(f"{item['provenance']['title']}\nTarget passage: {item['text']}\nContext:\n{passage_text}")
            values = ranker.rerank(rerank_query or query, texts)
            for item, value in zip(evidence, values):
                item["retrieval"]["reranker_logit"] = value
            evidence.sort(key=lambda item: (-item["retrieval"]["reranker_logit"], -item["retrieval"]["rrf_score"]))
            reranked = True
        except (ImportError, OSError, ValueError) as exc:
            warnings.append("Reranker unavailable; retained RRF ordering: " + str(exc))
    speaker = filters.get("speaker")
    level = attribution_level(filters.get("include_unassigned", False), filters.get("attribution_mode"))
    doc_map = attribution.author_documents(speaker) if speaker else {}
    # Near-identical copies are represented once; grouping is not a count of independent sources.
    chosen, seen, document_counts = [], set(), defaultdict(int)
    for item in evidence:
        normalized = " ".join(item["text"].split()).lower()
        duplicate = (item["source_group"], hashlib.sha256(normalized.encode()).hexdigest())
        if duplicate in seen:
            continue
        if max_per_document and document_counts[item["document_id"]] >= max_per_document:
            continue
        seen.add(duplicate)
        document_counts[item["document_id"]] += 1
        item["context"] = context_passages(corpus, item["chunk_id"], context) if context else []
        item["attribution"] = attribution.basis(item["speaker"], item["document_id"], speaker, doc_map)
        chosen.append(item)
        if len(chosen) >= limit:
            break
    return {"query": query, "mode_used": "hybrid" if "semantic" in rankings else "lexical",
            "attribution_level": level if speaker else None,
            "excluded_documents": sorted(filters.get("exclude_documents") or []),
            "rerank_query": (rerank_query or query) if reranked else None,
            "reranked": reranked, "warnings": warnings, "candidate_counts": {k: len(v) for k, v in rankings.items()},
            "results": chosen,
            "note": "Ranks measure relevance, not truth. Context may cross speakers or questions; inspect boundaries. Wiki is synthesis, not independent evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--models-dir", type=Path)
    parser.add_argument("--index-dir", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    build = sub.add_parser("build")
    build.add_argument("--batch-size", type=int, default=32)
    build.add_argument("--max-tokens", type=int, choices=[256, 512], default=512)
    build.add_argument("--threads", type=int, default=4)
    query = sub.add_parser("search")
    query.add_argument("query")
    query.add_argument("--lexical", action="append", default=[])
    query.add_argument("--rerank-query", help="Optional faithful translation of the full question into the source language; original query is preserved")
    query.add_argument("--mode", choices=["auto", "hybrid", "lexical"], default="auto")
    query.add_argument("--speaker")
    query.add_argument("--include-unassigned", action="store_true", help="Same as --attribution unassigned")
    query.add_argument("--attribution", choices=attribution.LEVELS, dest="attribution_mode",
                       help="strict: labelled passages (incl. reviewed label typos); author: also unlabelled passages "
                            "of reviewed single-author documents / Munger meeting notes; unassigned: all unlabelled")
    query.add_argument("--include-translations", action="store_true",
                       help="Also search translated editions (source_type translation, e.g. the Chinese PCA and Snowball); excluded by default")
    query.add_argument("--exclude-document", action="append", default=[], dest="exclude_documents",
                       help="Hold out a document id (repeatable), e.g. for blind evaluation")
    query.add_argument("--year-from", type=int)
    query.add_argument("--year-to", type=int)
    query.add_argument("--primary-status")
    query.add_argument("--source-type")
    query.add_argument("--limit", type=int, default=10)
    query.add_argument("--candidates", type=int, default=50)
    query.add_argument("--context", type=int, choices=range(0, 21), default=2)
    query.add_argument("--max-per-document", type=int, default=3)
    query.add_argument("--no-rerank", action="store_true")
    query.add_argument("--exact", action="store_true")
    query.add_argument("--threads", type=int, default=4)
    query.add_argument("--wiki", action="store_true", help="Also return separately labeled, source-checked Wiki navigation")
    query.add_argument("--output", type=Path)
    args = parser.parse_args()
    corpus = open_corpus(args.library)
    index_dir = args.index_dir or corpus.root / "retrieval" / "index"
    models_dir = args.models_dir or corpus.root / "retrieval" / "models"
    try:
        if args.command == "status":
            result = index_status(corpus, index_dir)
        elif args.command == "build":
            if args.batch_size < 1 or args.threads < 1:
                raise ValueError("batch-size and threads must be positive")
            result = build_index(corpus, index_dir, models_dir, args.batch_size, args.max_tokens, args.threads)
        else:
            kwargs = {key: getattr(args, key) for key in ("speaker", "include_unassigned", "attribution_mode", "exclude_documents", "include_translations",
                                                          "year_from", "year_to", "primary_status", "source_type")}
            result = search(corpus, args.query, index_dir, models_dir, mode=args.mode,
                            lexical_queries=args.lexical, limit=args.limit, candidates=args.candidates,
                            rerank=not args.no_rerank, context=args.context, max_per_document=args.max_per_document,
                            exact=args.exact, threads=args.threads, rerank_query=args.rerank_query, **kwargs)
            if args.wiki:
                from wiki import search_pages
                result["wiki_matches"] = search_pages(corpus, corpus.root / "wiki", args.query, models_dir,
                                                       speaker=args.speaker, limit=3)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                atomic_json(args.output, result)
                result = {"saved": str(args.output.resolve()), "mode_used": result["mode_used"],
                          "reranked": result["reranked"], "results": len(result["results"]), "warnings": result["warnings"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        corpus.close()


if __name__ == "__main__":
    main()
