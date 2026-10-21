"""A method is a folder of three files, and optionally stages, guides and task prompts:

    schema.tql     the nouns: types and the rules the database enforces (on top of core.tql)
    actions.yaml   the verbs: which objects agents create, their fields, how groups are formed,
                   which checks to run (soft expectations, as TypeQL)
    method.md      how to think: the open-ended guide the agent reads and interprets
    stages.yaml    optional: the method's stages, in order, and what each lets an agent write
    guides/*.md    optional: short how-tos for single tasks, served by guide(name)
    stages/*.md    optional: the task prompt for each kind of agent session

All of them are part of the method's hash, so every run records exactly which prompts it used.

The server generates its method tools from actions.yaml, so a new method needs no server code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml

from .util import QlsError, sha256_text

CORE_PREFIXES = {"quote": "Q", "memo": "M", "codebook-entry": "CB"}


@dataclass
class Field:
    param: str
    attr: str
    required: bool = False
    doc: str = ""


@dataclass
class Group:
    type: str              # the group type (theme)
    relation: str          # theme-membership
    group_role: str        # theme
    member_role: str       # concept
    member_type: str       # concept
    min: int = 1
    exclusive: bool = True


@dataclass
class Action:
    name: str
    kind: str              # create_code | create_group
    type: str
    doc: str = ""
    members_param: str | None = None
    answers: str = "no"    # no | optional | required
    into: str | None = None          # create_code only: the group type the new code is placed in, in the same call
    into_param: str | None = None    # the parameter holding [{"id", "reason"}] for those groups
    into_min: int = 1                # how many groups the new code must be placed in


@dataclass
class Method:
    name: str
    title: str
    version: int
    root: Path | None
    schema: str
    guide: str
    raw: dict
    prefixes: dict[str, str]
    fields: dict[str, list[Field]]
    groups: list[Group]
    actions: dict[str, Action]
    checks: list[dict] = field(default_factory=list)
    stages: list[dict] = field(default_factory=list)
    guides: dict[str, str] = field(default_factory=dict)
    tasks: dict[str, str] = field(default_factory=dict)
    hash: str = ""

    def stage(self, sid: str | None) -> dict | None:
        return next((s for s in self.stages if s["id"] == sid), None)

    @property
    def code_type(self) -> str:
        return self.raw["code_type"]

    def levels(self) -> list[str]:
        """Bottom-up: code type, then each group type that groups the level below."""
        out = [self.code_type]
        while True:
            g = next((g for g in self.groups if g.member_type == out[-1]), None)
            if g is None:
                return out
            out.append(g.type)

    def group_of(self, group_type: str) -> Group | None:
        return next((g for g in self.groups if g.type == group_type), None)

    def group_for_member(self, member_type: str) -> Group | None:
        return next((g for g in self.groups if g.member_type == member_type), None)

    def prefix(self, typ: str) -> str:
        return self.prefixes.get(typ) or CORE_PREFIXES[typ]

    def type_of_id(self, oid: str) -> str | None:
        p = oid.rsplit("-", 1)[0]
        return next((t for t, pre in {**CORE_PREFIXES, **self.prefixes}.items() if pre == p), None)

    def memo_budget(self, level: str) -> int:
        return int((self.raw.get("memo") or {}).get("budgets", {}).get(level, 4000))

    def summary(self) -> dict:
        return {
            "method": self.name, "title": self.title, "version": self.version,
            "levels_bottom_up": self.levels(),
            "types": {t: {"fields": {f.param: {"required": f.required, "doc": f.doc} for f in fs}} for t, fs in self.fields.items()},
            "groups": [{"group": g.type, "members": g.member_type, "min": g.min, "exclusive": g.exclusive} for g in self.groups],
            "actions": {a.name: a.doc for a in self.actions.values()},
            "checks": [{"id": c["id"], "text": c["text"]} for c in self.checks],
            "stages": [s["id"] for s in self.stages],
            "guides": sorted(self.guides),
        }


def core_schema() -> str:
    return resources.files("qls.schema").joinpath("core.tql").read_text(encoding="utf-8")


def builtin_methods() -> list[str]:
    root = resources.files("qls.methods")
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.joinpath("actions.yaml").is_file())


def _md_files(d, sub: str) -> dict[str, str]:
    sd = d.joinpath(sub)
    if not sd.is_dir():
        return {}
    return {f.name[:-3]: f.read_text(encoding="utf-8") for f in sorted(sd.iterdir(), key=lambda f: f.name) if f.name.endswith(".md")}


def load_method(name_or_path: str) -> Method:
    p = Path(name_or_path)
    if p.is_dir():
        d, root = p, p.resolve()
    else:
        d, root = resources.files("qls.methods").joinpath(name_or_path), None
        if not d.joinpath("actions.yaml").is_file():
            raise QlsError(f"Unknown method {name_or_path!r}. Built in: {', '.join(builtin_methods())}; or give a folder.")
    files = {f: d.joinpath(f).read_text(encoding="utf-8") for f in ("schema.tql", "actions.yaml", "method.md")}
    if d.joinpath("stages.yaml").is_file():
        files["stages.yaml"] = d.joinpath("stages.yaml").read_text(encoding="utf-8")
    guides, tasks = _md_files(d, "guides"), _md_files(d, "stages")
    raw = yaml.safe_load(files["actions.yaml"])
    fields = {t: [Field(param=k, attr=v.get("attr", k), required=bool(v.get("required")), doc=v.get("doc", ""))
                  for k, v in (spec or {}).items()] for t, spec in (raw.get("fields") or {}).items()}
    groups = [Group(**g) for g in raw.get("groups") or []]
    actions = {k: Action(name=k, kind=v["kind"], type=v["type"], doc=" ".join(str(v.get("doc", "")).split()),
                         members_param=v.get("members_param"), answers=v.get("answers", "no"),
                         into=v.get("into"), into_param=v.get("into_param"), into_min=int(v.get("into_min", 1)))
               for k, v in (raw.get("actions") or {}).items()}
    for a in actions.values():
        if a.kind not in ("create_code", "create_group"):
            raise QlsError(f"action {a.name}: unknown kind {a.kind!r}")
        if a.kind == "create_group" and (not a.members_param or not any(g.type == a.type for g in groups)):
            raise QlsError(f"action {a.name}: a group action needs members_param and a groups entry for {a.type}")
        if a.into and (not a.into_param or not any(g.type == a.into and g.member_type == a.type for g in groups)):
            raise QlsError(f"action {a.name}: 'into' needs into_param and a groups entry grouping {a.type} into {a.into}")
    stages = (yaml.safe_load(files.get("stages.yaml", "")) or {}).get("stages") or []
    for s in stages:
        s.setdefault("create", [])
        s.setdefault("edit", [])
        unknown = set(s["create"]) - set(actions)
        if unknown:
            raise QlsError(f"stage {s['id']}: unknown actions {', '.join(sorted(unknown))}")
    m = Method(name=raw["name"], title=raw.get("title", raw["name"]), version=int(raw.get("version", 1)), root=root,
               schema=files["schema.tql"], guide=files["method.md"], raw=raw, prefixes=raw.get("prefixes") or {},
               fields=fields, groups=groups, actions=actions, checks=raw.get("checks") or [], stages=stages,
               guides=guides, tasks=tasks)
    parts = [files[f] for f in ("schema.tql", "actions.yaml", "method.md")]
    parts += [files["stages.yaml"]] if "stages.yaml" in files else []
    parts += [f"guides/{k}\n{v}" for k, v in guides.items()] + [f"stages/{k}\n{v}" for k, v in tasks.items()]
    m.hash = sha256_text(core_schema() + "\n" + "\n".join(parts))
    return m
