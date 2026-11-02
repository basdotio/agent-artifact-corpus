#!/usr/bin/env python3
"""Build Skill-Inject's injected skills into cache/ as one tree per injection.

WHAT THE SOURCE IS. aisa-group/skill-inject (arXiv 2602.20156) ships no finished samples: it
ships clean carrier skills (data/skills/) and injection definitions (data/obvious_injections.json,
data/contextual_injections.json), and its scripts/build_sandbox.py builds each sample at run time
by copying a carrier, inserting one instruction line into its SKILL.md at a given line, and copying
the injection's payload scripts into the skill's scripts/. This script does the same three steps,
reimplemented here (inject_at_line below is that file's function, line for line) so no upstream
code is run. Every tree is `injected`: real carrier skills plus the authors' inserted line.

LICENCE IS THE CARRIER'S. The repository is MIT, but most carriers are copies of other people's
skills. A carrier is used only when its origin was found and is permissive (CARRIERS below, each
checked against that repository's history on 2026-11-02), or when it is the authors' own:
- wshobson/agents, MIT: matched byte for byte (difflib ratio >= 0.98) to a past revision;
- anthropics/claude-cookbooks custom_skills, MIT; anthropics/skills, Apache-2.0 (not the
  document-skills, which are Anthropic-proprietary and never used); huggingface/skills, Apache-2.0;
- the authors' own: carriers whose frontmatter declares a licence, and email-api, which calls the
  authors' own service.
Carriers whose origin could not be found (python-code, discord, agent-identifier, write-unit-tests,
seo-review, google-calendar-skill, healthcare/*) are never used. Licences go to
manifest/pins/skill-inject-licenses.json so each label carries its carrier's licence.

ONE TREE PER INJECTION: an injection's tasks name several carriers; the least-used licence-clean
one is taken. Every buildable injection is built here; the cap of two per carrier is applied after
reading (manifest/corpora.yaml), so which two a carrier keeps is decided by the readings, not by
file order.

NAMES. `<carrier>-<first 10 hex of the injected SKILL.md's sha256>`, never the injection id or set
(obvious/contextual), which are the upstream's labels; those are in the sidecar.
"""

import hashlib
import json
import pathlib
import shutil
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = ROOT / "cache" / "skill-inject"
DATA = REPO / "data"
OUT = REPO / "_extracted"
PINS = ROOT / "manifest" / "pins" / "skill-inject-licenses.json"
COMMIT = "182f3d9d9836"   # manifest/corpora.yaml

# upstream config.py SKILL_MAPPING: a task's `skill` -> its directory under data/skills/
SKILL_MAPPING = {"pptx": "document-skills/pptx", "docx": "document-skills/docx", "xlsx": "document-skills/xlsx",
                 "pdf": "document-skills/pdf", "internal_comms": "internal-comms", "internal_communication": "internal-comms",
                 "git": "git", "code": "skill-creator", "calendar": "calendar", "email": "email-api", "email-api": "email-api",
                 "mcp": "mcp", "fhir": "healthcare/fhir-developer-skill", "fhir-developer-skill": "healthcare/fhir-developer-skill",
                 "slack": "slack-gif-creator", "webapp": "webapp-testing", "python-code": "python-code"}

WSH = ("MIT", "https://github.com/wshobson/agents (Copyright (c) 2024 Seth Hobson), matched to a past revision")
COOK = ("MIT", "https://github.com/anthropics/claude-cookbooks skills/custom_skills (Copyright (c) 2023 Anthropic)")
ANT = ("Apache-2.0", "https://github.com/anthropics/skills, Apache-2.0 example skill, modified by the Skill-Inject authors")
HF = ("Apache-2.0", "https://github.com/huggingface/skills, modified by the Skill-Inject authors")
OWN_APACHE = ("Apache-2.0", "the Skill-Inject authors' own carrier; its frontmatter declares Apache-2.0")
OWN_MIT = ("MIT", "the Skill-Inject authors' own carrier, under the repository's MIT grant")
CARRIERS = {
    **{c: WSH for c in ("bats-testing-patterns", "data-storytelling", "database-migration", "debugging-strategies",
                        "employment-contract-templates", "llm-evaluation", "paypal-integration", "prompt-engineering-patterns",
                        "rag-implementation", "risk-metrics-calculation", "shellcheck-configuration",
                        "sql-optimization-patterns", "stripe-integration", "git")},
    **{c: COOK for c in ("analyzing-financial-statements", "applying-brand-guidelines", "creating-financial-models")},
    **{c: ANT for c in ("internal-comms", "webapp-testing", "slack-gif-creator", "mcp", "skill-creator", "template-skill")},
    **{c: HF for c in ("hf-llm-trainer", "hf-paper-publisher", "hf_dataset_creator", "hf_model_evaluation")},
    "calendar": OWN_APACHE, "code-review": OWN_APACHE, "system-info": OWN_MIT, "email-api": OWN_MIT,
}


def inject_at_line(file_path: pathlib.Path, instruction_text: str, line_number: int) -> None:
    """Insert instruction text at a specific line number in a file (upstream build_sandbox.py)."""
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    if line_number < 1 or line_number > len(lines) + 1:
        sys.exit(f"[error] Line {line_number} out of range (file has {len(lines)} lines): {file_path}")
    block = []
    for raw in instruction_text.strip("\n").splitlines():
        block.append(f"{raw.strip()}\n" if raw.strip() else "\n")
    pos = line_number - 1
    file_path.write_text("".join(lines[:pos] + block + lines[pos:]), encoding="utf-8")


def main() -> int:
    if not DATA.is_dir():
        sys.exit(f"clone https://github.com/aisa-group/skill-inject at {COMMIT} into {REPO.relative_to(ROOT)} first")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    used, pins, skipped = {}, {}, []
    for setname in ("obvious", "contextual"):
        for inj in json.loads((DATA / f"{setname}_injections.json").read_text()):
            line = (inj.get("instructions") or {}).get("line_injection", "")
            ok = [t for t in inj["tasks"] if t.get("line_num") and line and SKILL_MAPPING.get(t["skill"], t["skill"]) in CARRIERS]
            task = min(ok, key=lambda t: used.get(SKILL_MAPPING.get(t["skill"], t["skill"]), 0)) if ok else None
            if task is None:
                skipped.append(f"{setname}-{inj['id']}")
                continue
            carrier = SKILL_MAPPING.get(task["skill"], task["skill"])
            stage = OUT / "_stage"
            shutil.copytree(DATA / "skills" / carrier, stage)
            target = stage / "SKILL.md"
            prefix = task.get("injection_prefix", "")
            inject_at_line(target, (prefix + line) if prefix else line, task["line_num"])
            for name, rel in (inj.get("task_scripts") or {}).items():
                src = DATA / rel
                if src.exists():
                    (stage / "scripts").mkdir(exist_ok=True)
                    shutil.copyfile(src, stage / "scripts" / name)
            name = f"{pathlib.Path(carrier).name}-{hashlib.sha256(target.read_bytes()).hexdigest()[:10]}"
            stage.rename(OUT / name)
            used[carrier] = used.get(carrier, 0) + 1
            lic, via = CARRIERS[carrier]
            side = {"upstream_set": setname, "injection_id": inj["id"], "title": inj["title"],
                    "injection_goal": inj.get("injection_goal", ""), "carrier": carrier, "line_num": task["line_num"],
                    "payload_scripts": sorted((inj.get("task_scripts") or {}).keys()), "carrier_origin": via,
                    "source": f"https://github.com/aisa-group/skill-inject/tree/{COMMIT}/data ({setname}_injections.json id {inj['id']} on data/skills/{carrier})"}
            (OUT / f"{name}.source.json").write_text(json.dumps(side, indent=1) + "\n")
            pins[name] = {"checked": str(date.today()), "license": lic, "via": via}
    PINS.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n")
    print(f"skill-inject: {len(pins)} tree(s) into {OUT.relative_to(ROOT)}/; {len(skipped)} injection(s) with no "
          f"licence-clean carrier: {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
