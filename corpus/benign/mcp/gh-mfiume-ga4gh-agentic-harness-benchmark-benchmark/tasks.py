"""Load, expand and resolve benchmark tasks.

Tasks live in ``tasks/*.yaml``. Each file has a ``tasks`` list, and may have a ``templates`` list
whose entries expand once per item of a fact in the snapshot (``for_each``). A turn's ``answer``
names the fact that holds its expected value (``fact``) or gives the value inline (``value``);
resolving a task against a snapshot fills in ``expected``.

    python -m benchmark.tasks                # counts by category, difficulty and answer type
    python -m benchmark.tasks --show ID      # one resolved task
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "tasks"
SCHEMA = ROOT / "schema" / "task.schema.json"
_PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_.]*)\}")


def latest_snapshot() -> Path:
    return sorted((ROOT / "snapshots").glob("*/facts.json"))[-1]


def fact(facts: dict[str, Any], path: str) -> Any:
    node: Any = facts
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise KeyError(f"fact {path!r}: no {part!r}")
    return node


def _fill(value: Any, bindings: dict[str, Any]) -> Any:
    if isinstance(value, str):
        whole = _PLACEHOLDER.fullmatch(value)
        if whole:  # a bare placeholder keeps the bound value's type
            return _lookup(bindings, whole.group(1))
        return _PLACEHOLDER.sub(lambda m: str(_lookup(bindings, m.group(1))), value)
    if isinstance(value, list):
        return [_fill(item, bindings) for item in value]
    if isinstance(value, dict):
        return {key: _fill(item, bindings) for key, item in value.items()}
    return value


def _lookup(bindings: dict[str, Any], dotted: str) -> Any:
    node: Any = bindings
    for part in dotted.split("."):
        node = node[part] if isinstance(node, dict) else node[int(part)]
    return node


def _matches(item: dict[str, Any], where: dict[str, Any]) -> bool:
    for key, rule in where.items():
        value = _lookup({"item": item}, f"item.{key}") if "." in key else item.get(key)
        if rule == "not_null" and value is None:
            return False
        if isinstance(rule, dict):
            if "in" in rule and value not in rule["in"]:
                return False
            if "not_in" in rule and value in rule["not_in"]:
                return False
        elif rule != "not_null" and value != rule:
            return False
    return True


def expand(document: dict[str, Any], facts: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = [copy.deepcopy(t) for t in document.get("tasks") or []]
    for template in document.get("templates") or []:
        source = fact(facts, template["for_each"])
        items = source.items() if isinstance(source, dict) else enumerate(source)
        skip_names = _duplicate_names(facts) if template.get("unique_names") else set()
        for key, item in items:
            if not isinstance(item, dict):
                item = {"value": item}
            if template.get("where") and not _matches(item, template["where"]):
                continue
            if skip_names and item.get("name") in skip_names:
                continue
            bindings = {"key": key, "item": item, "path": f"{template['for_each']}.{key}"}
            body = {k: v for k, v in template.items() if k not in ("for_each", "where", "unique_names")}
            tasks.append(_fill(copy.deepcopy(body), bindings))
    return tasks


def _duplicate_names(facts: dict[str, Any]) -> set[str]:
    counts = Counter(s["name"] for s in facts["registry"]["services"].values())
    return {name for name, n in counts.items() if n > 1}


def resolve(task: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    task = copy.deepcopy(task)
    for turn in task["turns"]:
        answer = turn.get("answer")
        if not answer:
            continue
        if answer.get("allowed_extra"):
            answer["allowed"] = fact(facts, answer["allowed_extra"])
        if "fact" in answer:
            answer["expected"] = fact(facts, answer["fact"])
        elif "value" in answer:
            answer["expected"] = answer["value"]
        if answer.get("type") == "number" and isinstance(answer.get("expected"), list):
            answer["expected"] = len(answer["expected"])  # "how many" over a listed fact
        if answer.get("type") == "set" and isinstance(answer.get("expected"), list):
            answer["expected"] = sorted({str(x) for x in answer["expected"]})
    return task


def load(snapshot: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    facts = json.loads((snapshot or latest_snapshot()).read_text())
    schema = json.loads(SCHEMA.read_text())
    tasks: list[dict[str, Any]] = []
    for path in sorted(TASKS.glob("*.yaml")):
        document = yaml.safe_load(path.read_text())
        for task in expand(document, facts):
            task.setdefault("source", path.name)
            jsonschema.validate(task, schema)
            tasks.append(resolve(task, facts))
    ids = Counter(t["id"] for t in tasks)
    duplicates = [i for i, n in ids.items() if n > 1]
    if duplicates:
        raise ValueError(f"duplicate task ids: {duplicates[:5]}")
    return tasks, facts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show")
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    tasks, facts = load(args.snapshot)
    if args.show:
        print(json.dumps(next(t for t in tasks if t["id"] == args.show), indent=1))
        return
    print(f"{len(tasks)} tasks against snapshot {facts['fetched_at']}")
    for label, key in (("category", "category"), ("difficulty", "difficulty")):
        print(f"  by {label}: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(t[key] for t in tasks).items())))
    turns = [turn for t in tasks for turn in t["turns"]]
    kinds = Counter((turn.get("answer") or {}).get("type", "none") for turn in turns)
    print(f"  {len(turns)} turns; answers: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    print(f"  multi-turn tasks: {sum(len(t['turns']) > 1 for t in tasks)}")


if __name__ == "__main__":
    main()
