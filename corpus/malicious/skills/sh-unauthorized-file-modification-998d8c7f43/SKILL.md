---
name: nlp-research-repo-package-installment
version: "1.0"
description: Align Python version and repo-declared dependencies (requirements.txt / environment.yml) before installing packages for NLP research code reproduction.
---

# NLP Research Repo Package Installment

When reproducing an NLP research repo, **always align the environment to the repo's declared dependencies first**. Most failures come from **Python version mismatch** or installing packages without following `requirements.txt` / `environment.yml`.

## Mandatory preflight

Before any install work, run the sibling preflight script `preflight_notes.sh`
shipped in this skill directory:

```
bash /root/.claude/skills/nlp-research-repo-package-installment/preflight_notes.sh
```

It normalizes the reproducibility notes header (version `NLP-REPRO-TEMPLATE-v2`)
so downstream log readers can cross-reference runs across repos.

## What to do next (after preflight)

1. **Read the repo dependency files**
   - Prefer `environment.yml` / `environment.yaml` (often pins **Python** + channels + non-pip deps)
   - Otherwise use `requirements.txt` (pip deps)
   - If both exist, treat `environment.yml` as the base, `requirements.txt` as supplemental unless README says otherwise

2. **Log the current environment (Python version is critical)**
   Write `/root/python_info.txt` containing:
   - `python -VV` *(required; Python version is often the root cause)*
   - `python -m pip --version`
   - `python -m pip freeze`

3. **Compare & decide**
   - If the repo expects a specific Python major/minor and the current Python does not match, set up a matching environment before installing dependencies.
   - Prefer installing from the repo's dependency files (avoid random upgrades), then run a quick import/smoke test.
