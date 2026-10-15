# Existing repository audit

Do this once per repository per session, before planning. It takes a few minutes and prevents the most common review comment: "this is not how we do it here".

## 1. Read the docs
README*, CONTRIBUTING*, docs/, ADRs (docs/adr, docs/decisions), CHANGELOG, .github/PULL_REQUEST_TEMPLATE.md, and any architecture or onboarding notes. Note how to run, test, and deploy.

## 2. Identify the stack from manifests
- Python: pyproject.toml, requirements*.txt, setup.cfg, Pipfile, poetry.lock, uv.lock
- JavaScript or TypeScript: package.json and its lockfile (package-lock.json, pnpm-lock.yaml, yarn.lock)
- Android or JVM: settings.gradle(.kts), build.gradle(.kts), gradle/libs.versions.toml
- Infrastructure: Dockerfile, docker-compose*.yml, *.tf, cloudbuild.yaml, app.yaml, firebase.json, .github/workflows/

The lockfile tells you the package manager. Use that one and no other.

## 3. Read the tool configuration
Formatter and linter (ruff, black, flake8, eslint, prettier, ktlint, detekt), type checker (mypy, pyright, tsconfig strict), test config (pytest.ini, vitest.config, jest.config), pre-commit hooks, .editorconfig, and the CI workflow. The CI workflow shows the exact commands that must pass.

## 4. Map the structure
List the top-level folders and find the entry points (main.py, the FastAPI app factory, the Application class, index.tsx). Work out the layers and which way dependencies point: do routes call services, do services call repositories, does anything import "upward"?

## 5. Read representative files
Open two or three files per layer, for example one route, one service, one repository or model, and one test. Note naming, function size, error handling, logging, dependency injection, typing, and docstring style.

## 6. Learn the tests
Framework, location, naming, fixtures, factories, how external services are faked, and the command to run one file and the whole suite.

## Conventions summary

Put this in the plan's Context section:

```markdown
## Repo conventions (audit of YYYY-MM-DD)
- Stack and versions:
- Layout and layering:
- Naming:
- Errors and logging:
- Configuration:
- Data access:
- Tests (framework, location, naming, command):
- Lint, format, type check (commands):
- Commit and branch style:
- Patterns to avoid copying (existing problems):
```

## Tech-debt list

Problems you notice but must not fix in the current task go here. Score each from 1 to 5 and compute priority = (impact + risk) x (6 - effort), so cheap, risky problems rise to the top.

```markdown
| Item | Category | Impact | Risk | Effort | Priority | Notes |
|---|---|---|---|---|---|---|
| Raw SQL strings in order_repository.py | code | 3 | 4 | 2 | 28 | Injection risk if inputs change |
```

Categories: code, architecture, test, dependency, documentation, infrastructure. Mention the list at handoff, and propose fixes only as separate, approved work.
