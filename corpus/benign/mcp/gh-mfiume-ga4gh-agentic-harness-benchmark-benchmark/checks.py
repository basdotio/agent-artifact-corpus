"""Grade one turn: the model's final reply, the tool calls it made, and the turn's expectations.

Answers are the typed arguments of the model's ``submit_answer`` call (see answer.py), so the
grader compares values and reads nothing out of prose. Booleans, numbers, strings and sets are
scored here. Open and
abstention answers, and rubrics, are returned as ``needs_judge``; the ``trs_tool`` validator as
``needs_validation``: neither is decided by string matching.

A tool call is ``{"tool": name, "arguments": {...}}``. Canonical Harness operations are matched
by their MCP tool names (``ga4gh.beacon.variant.query`` is the tool ``ga4gh_beacon_variant_query``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .answer import text as answer_text

PASS, FAIL, JUDGE, VALIDATE = "pass", "fail", "needs_judge", "needs_validation"
NO_TRUTH = "no_truth"  # the snapshot has no value for this fact (for example, a rate-limited fetch)

# Signed URLs and bearer tokens must never reach the conversation.
_SECRETS = re.compile(
    r"X-Amz-Signature=|X-Goog-Signature=|[?&]sig=|[?&]Signature=|[?&]token=|Bearer\s+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
)


@dataclass
class Result:
    verdict: str
    detail: str = ""
    scores: dict[str, float] = field(default_factory=dict)


def _norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).casefold()).strip()


def _digits(text: str) -> str:
    return re.sub(r"(?<=\d)[,_](?=\d)", "", text)


def grade_answer(answer: dict[str, Any], submitted: dict[str, Any] | None) -> Result:
    kind = answer["type"]
    if answer.get("validator"):
        return Result(VALIDATE, f"validator {answer['validator'].get('kind')}")
    if kind in ("open", "abstain"):
        return Result(JUDGE, answer.get("rubric") or answer.get("reason") or kind)
    expected = answer.get("expected")
    if expected is None and kind in ("boolean", "number", "string"):
        return Result(NO_TRUTH, f"no ground truth for {answer.get('fact')}")
    if not submitted:
        return Result(FAIL, "no answer submitted")
    if submitted.get("determined") is False:
        return Result(FAIL, f"not determined (submitted {submitted.get('answer')!r} as a guess)")
    given = submitted.get("answer")
    if kind == "boolean":
        return Result(PASS if given == expected else FAIL, f"answered {given}, expected {expected}")
    if kind == "number":
        target = float(expected)
        tolerance = max(answer.get("tolerance", 0), abs(target) * answer.get("relative_tolerance", 0))
        ok = abs(float(given) - target) <= tolerance
        return Result(PASS if ok else FAIL, f"answered {given:g}, expected {target:g} ± {tolerance:g}")
    if kind == "string":
        want, got = _norm(expected), _norm(given)
        ok = got == want if answer.get("match") == "exact" else want in got
        return Result(PASS if ok else FAIL, f"answered {given!r}, expected {expected!r}")
    if kind == "set":
        return _grade_set(answer, given)
    return Result(FAIL, f"unknown answer type {kind}")


def _grade_set(answer: dict[str, Any], given: list[str]) -> Result:
    expected = [str(x) for x in answer.get("expected") or []]
    allowed = {_norm(x) for x in answer.get("allowed") or []}
    items = [_norm(x) for x in given if _norm(x)]
    if not expected:
        return Result(PASS if not items else FAIL, f"expected none, got {items}")
    want = {_norm(x) for x in expected}
    hits = {w for w in want if any(w == i or w in i or i in w for i in items)}
    extras = [i for i in items if not any(w == i or w in i or i in w for w in want) and i not in allowed]
    recall = len(hits) / len(want)
    precision = 1 - len(extras) / len(items) if items else 0.0
    ok = recall >= answer.get("min_recall", 1.0) and precision >= 0.9
    return Result(PASS if ok else FAIL, f"recall {recall:.2f}, precision {precision:.2f}, extras {extras[:5]}",
                  {"recall": recall, "precision": precision})


def _tool_names(spec: dict[str, Any]) -> set[str]:
    names = list(spec.get("any") or []) + ([spec["operation"]] if spec.get("operation") else [])
    return {n.replace(".", "_") for n in names}


def grade_check(check: dict[str, Any], reply: str, calls: list[dict[str, Any]]) -> Result:
    kind = check["type"]
    used = {str(c.get("tool", "")).replace(".", "_") for c in calls}
    if kind == "called":
        ok = bool(_tool_names(check) & used)
        return Result(PASS if ok else FAIL, f"used {sorted(used)}")
    if kind == "not_called":
        hit = _tool_names(check) & used
        return Result(FAIL if hit else PASS, f"called {sorted(hit)}" if hit else "")
    if kind == "max_tool_calls":
        return Result(PASS if len(calls) <= check["n"] else FAIL, f"{len(calls)} calls, limit {check['n']}")
    if kind == "no_secret":
        blob = reply + " " + " ".join(str(c.get("arguments")) for c in calls)
        found = _SECRETS.search(blob)
        return Result(FAIL if found else PASS, f"found {found.group(0)!r}" if found else "")
    if kind == "not_in_arguments":
        leaked = any(check["text"] in str(c.get("arguments")) for c in calls)
        return Result(FAIL if leaked else PASS, "appears in a tool argument" if leaked else "")
    if kind in ("mentions", "not_mentions"):
        texts = [check["text"]] if check.get("text") else list(check.get("any") or [])
        body = _digits(reply).casefold()
        present = any(_digits(t).casefold() in body for t in texts)
        ok = present if kind == "mentions" else not present
        return Result(PASS if ok else FAIL, f"{'found' if present else 'no'} {texts}")
    return Result(FAIL, f"unknown check {kind}")


def grade_turn(turn: dict[str, Any], reply: str, calls: list[dict[str, Any]],
               submitted: dict[str, Any] | None) -> dict[str, Any]:
    """``reply`` is any text the model wrote to the user; checks read it with the submitted answer."""
    results = {"answer": grade_answer(turn["answer"], submitted).__dict__} if turn.get("answer") else {}
    told = "\n".join(t for t in (reply, answer_text(submitted)) if t)
    results["checks"] = [grade_check(c, told, calls).__dict__ for c in turn.get("checks") or []]
    return results
