"""Compare runs by structure and by selection, not by labels.

Elements are the fixed informant segments created at ingestion, so two runs that quoted
different spans are still compared on the same units (the unitisation problem in intercoder
agreement, Campbell et al. 2013). For each level of the method (Gioia: concept, theme,
dimension) every segment maps to the set of groups it falls in.

- selection: which segments each run coded at all (Jaccard). Intent should change this.
- structure, per level, on segments coded in both: Rand, adjusted Rand, NMI, and pairwise
  co-assignment F1 (do two segments share any group?), which handles overlap.

Comparing runs with the same intent measures reliability; with different intents, sensitivity.
"""

from __future__ import annotations

import math
from collections import Counter
from itertools import combinations

from .graph import Graph
from .method import Method


def _c2(x: int) -> float:
    return x * (x - 1) / 2


def partition_scores(a: dict[str, str], b: dict[str, str]) -> dict:
    keys = sorted(set(a) & set(b))
    n = len(keys)
    if n < 2:
        return {"n": n, "rand": None, "ari": None, "nmi": None}
    nij = Counter((a[k], b[k]) for k in keys)
    ai, bj = Counter(a[k] for k in keys), Counter(b[k] for k in keys)
    tp = sum(_c2(v) for v in nij.values())
    sa, sb, total = sum(_c2(v) for v in ai.values()), sum(_c2(v) for v in bj.values()), _c2(n)
    rand = (total + 2 * tp - sa - sb) / total
    expected, mx = sa * sb / total, (sa + sb) / 2
    ari = 1.0 if mx == expected else (tp - expected) / (mx - expected)

    def h(c: Counter) -> float:
        return -sum(v / n * math.log(v / n) for v in c.values() if v)

    mi = sum(v / n * math.log((v / n) / ((ai[x] / n) * (bj[y] / n))) for (x, y), v in nij.items() if v)
    ha, hb = h(ai), h(bj)
    nmi = 1.0 if ha == 0 and hb == 0 else (2 * mi / (ha + hb) if ha + hb else 0.0)
    return {"n": n, "rand": round(rand, 4), "ari": round(ari, 4), "nmi": round(nmi, 4)}


def pair_f1(a: dict[str, set], b: dict[str, set]) -> float | None:
    keys = sorted(set(a) & set(b))
    pa = {(x, y) for x, y in combinations(keys, 2) if a[x] & a[y]}
    pb = {(x, y) for x, y in combinations(keys, 2) if b[x] & b[y]}
    if not pa and not pb:
        return None
    tp = len(pa & pb)
    return round(2 * tp / (len(pa) + len(pb)), 4) if (pa or pb) else None


def segment_groups(graph: Graph, db: str, m: Method) -> dict[str, dict[str, set]]:
    """level -> segment -> set of group ids at that level."""
    levels = m.levels()
    out: dict[str, dict[str, set]] = {lvl: {} for lvl in levels}
    code_segs: dict[str, set] = {}
    for r in graph.rows(db, f"match $c isa {m.code_type}, has id $cid; evidence (claim: $c, quote: $q); $q has unit $u; select $cid, $u;"):
        code_segs.setdefault(r["cid"], set()).add(r["u"])
    for cid, segs in code_segs.items():
        for s in segs:
            out[m.code_type].setdefault(s, set()).add(cid)
    below = {cid: {cid} for cid in code_segs}  # code -> ids at the current level
    for lvl in levels[1:]:
        g = m.group_of(lvl)
        parent: dict[str, set] = {}
        for r in graph.rows(db, f"match {g.relation} ({g.group_role}: $g, {g.member_role}: $m); $g has id $gid; $m has id $mid; select $gid, $mid;"):
            parent.setdefault(r["mid"], set()).add(r["gid"])
        below = {cid: set().union(*[parent.get(x, set()) for x in xs]) if xs else set() for cid, xs in below.items()}
        for cid, groups in below.items():
            if groups:
                for s in code_segs[cid]:
                    out[lvl].setdefault(s, set()).update(groups)
    return out


def compare_groups(ga: dict[str, dict[str, set]], gb: dict[str, dict[str, set]], levels: list[str]) -> dict:
    sa, sb = set(ga[levels[0]]), set(gb[levels[0]])
    sel = {"segments_a": len(sa), "segments_b": len(sb), "both": len(sa & sb),
           "jaccard": round(len(sa & sb) / len(sa | sb), 4) if sa | sb else None}
    out = {}
    for lvl in levels:
        la = {k: "|".join(sorted(v)) for k, v in ga.get(lvl, {}).items()}
        lb = {k: "|".join(sorted(v)) for k, v in gb.get(lvl, {}).items()}
        sc = partition_scores(la, lb)
        sc.update(pair_f1=pair_f1(ga.get(lvl, {}), gb.get(lvl, {})), segments_a=len(la), segments_b=len(lb),
                  groups_a=len({g for v in ga.get(lvl, {}).values() for g in v}),
                  groups_b=len({g for v in gb.get(lvl, {}).values() for g in v}))
        out[lvl] = sc
    return {"selection": sel, "levels": out}
