# Contributing

Contributions should preserve the read-only behavior and the distinction between heuristic candidates and confirmed findings.

Before opening a pull request, run:

```text
python -m unittest discover -s tests -v
python scripts/validate_package.py
```

Add a regression test for every path, scope, output, or classification change. Keep `SKILL.md` focused on routing and decisions; move detailed background to `references/` and repeatable logic to `scripts/`.
