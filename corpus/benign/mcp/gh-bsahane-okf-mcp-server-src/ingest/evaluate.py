"""Retrieval evaluation: Hit@k over an agreed question set.

Question file (YAML)::

    questions:
      - question: What is the hotel limit in London?
        expected: [policies/travel-policy]   # concept IDs holding the evidence
      - question: What reward does the model use?
        expected: [papers/r1#2-2-reward-design, papers/r1#3-1-model-based-rewards]
      - question: Who approves exceptions to the parking rule?
        expected: []                          # no answer in the corpus

An expected entry is a concept ID, a source file path as users know it
(`HR/Leave Policy 2024.docx`, mapped through the snapshot manifest), or
`concept#section` to require that exact section (section slugs are listed by `get_knowledge`). Hit@k is the fraction
of answerable questions with at least one expected entry in the top k
results; `all_found` reports whether every entry was retrieved, and `rank` is
the position of the first match (for MRR).
"""

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from okf_mcp_server.src.knowledge.index import SearchIndex
from okf_mcp_server.src.knowledge.snapshot import current_snapshot


def evaluate(data_dir: Path, questions_file: Path, k: int = 5) -> Dict[str, Any]:
    """Run every question against the published snapshot's index."""
    spec = yaml.safe_load(questions_file.read_text(encoding="utf-8")) or {}
    snapshot = current_snapshot(data_dir)
    manifest = snapshot.root / "manifest.json"
    by_path = (
        {
            s["path"]: s["concept_id"]
            for s in json.loads(manifest.read_text(encoding="utf-8"))[
                "sources"
            ].values()
        }
        if manifest.exists()
        else {}
    )
    rows = []
    from okf_mcp_server.src.knowledge.service import search_embedder

    with SearchIndex(snapshot.index, embedder=search_embedder()) as index:
        mode = index.mode
        for q in spec.get("questions") or []:
            expected = [
                by_path.get(str(e).strip("/"), str(e).strip("/").removesuffix(".md"))
                for e in q.get("expected") or []
            ]
            results = index.search(str(q["question"]), limit=k)
            found = [r["concept_id"] for r in results]
            keys = [f"{r['concept_id']}#{r['section']}" for r in results]

            def matched(entry: str) -> bool:
                return entry in keys if "#" in entry else entry in found

            rank = next(
                (
                    i + 1
                    for i, key in enumerate(keys)
                    if any(key == e or key.split("#")[0] == e for e in expected)
                ),
                None,
            )
            rows.append(
                {
                    "question": q["question"],
                    "expected": expected,
                    "retrieved": list(dict.fromkeys(found)),
                    "answerable": bool(expected),
                    "hit": any(matched(e) for e in expected),
                    "rank": rank,
                    "all_found": all(matched(e) for e in expected)
                    if expected
                    else None,
                    "flags": list(
                        dict.fromkeys(
                            f"{r['concept_id']}: {r['status']}"
                            + (" (stale)" if r["stale"] else "")
                            for r in results
                            if r["status"] == "deprecated" or r["stale"]
                        )
                    ),
                }
            )
    answerable = [r for r in rows if r["answerable"]]
    hits = sum(r["hit"] for r in answerable)
    return {
        "snapshot_id": snapshot.id,
        "k": k,
        "search_mode": mode,
        "answerable": len(answerable),
        "unanswerable": len(rows) - len(answerable),
        f"hit_at_{k}": hits / len(answerable) if answerable else None,
        "hit_at_1": sum(r["rank"] == 1 for r in answerable) / len(answerable)
        if answerable
        else None,
        "mrr": sum(1 / r["rank"] for r in answerable if r["rank"]) / len(answerable)
        if answerable
        else None,
        "all_found": sum(bool(r["all_found"]) for r in answerable) / len(answerable)
        if answerable
        else None,
        "questions": rows,
    }
