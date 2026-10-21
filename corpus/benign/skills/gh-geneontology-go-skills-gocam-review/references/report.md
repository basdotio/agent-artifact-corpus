# Deliverables

All files go in `~/reviews/<YYYY-MM-DD>-<id>/` (`<id>` without `gomodel:`).

| File | What |
|---|---|
| `<id>.ttl`, `<id>.gpad` (or `supplied-<stamp>-<name>.ttl`) | the exact version checked |
| `qc.md`, `qc.json` | the script's dump and flags |
| `review.md` | the report; the source of truth |
| `checklist.md` | one row per finding with a status column; the durable tracker across rounds |
| `issues.json` | the findings, machine-readable |
| `uniprot-review.md` | only with `--with-uniprot` |
| `checklist-done.md` | the curator's returned checklist, when they send one |

## review.md

```markdown
# Review of gomodel:<id>: <title>
Noctua: <pathway-editor link from qc.md> (<production|dev>). State: <state>. Taxon: <taxon>.
Contributors: <...>. Curating group: <providedBy>. Round <n>; previous: <date or none>.
Reviewed <date> by Claude on behalf of <reviewer>, read-only. Full text read for <n> of <m> papers.

## Summary
Two to five sentences: what the model represents, the findings that matter most, the verdict.

## Verdict
approve | approve with suggestions | changes requested

## Findings
### critical
- **Q1** (B) <where: fact with handles, evidence line> — <what is wrong>. Fix: <in Noctua>. Comment: "<pasteable>".
### major
### moderate
### minor
### notes

## What is fine
- <things that passed, so the author knows what was looked at>

## What changed since <previous round or parent>
<diff summary, or "first round">

## Evidence notes
| PMID | supports | level | species / protein | read |
|---|---|---|---|---|
| PMID:n | <facts> | biochemical / cellular LOF / genetic / interaction / imaging / clinical | <...> | full text / abstract only |

## What was checked
Scripts and queries run, terms checked (or offline), lookups made, limits reached.
```

## checklist.md

```markdown
# Checklist: gomodel:<id>, round <n>, <date>

| id | severity | group | where | problem | fix | Noctua comment | status | notes |
|---|---|---|---|---|---|---|---|---|
| Q1 | major | C | ... | ... | ... | "..." | open | |
```

`status` is `open`, `done` or `declined`; the curator fills status and notes
and returns the file. On the next round, carry status and notes forward for
the same id; never reuse a withdrawn id.

## issues.json

```json
{
  "model_id": "gomodel:<id>",
  "title": "...",
  "date": "YYYY-MM-DD",
  "round": 1,
  "source": "noctua production download, YYYY-MM-DD",
  "verdict": "changes requested",
  "issues": [
    {"id": "Q1", "severity": "major", "check": "C", "where": "...", "problem": "...",
     "fix": "...", "noctua_comment": "...", "status": "open", "notes": "", "carried_from": null}
  ],
  "fine": ["..."],
  "papers": [{"pmid": "PMID:n", "read": "abstract", "supports": ["..."]}]
}
```
