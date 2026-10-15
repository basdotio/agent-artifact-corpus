# The project profile: runs/PROJECT.md

Everything about the project that the planning process needs, kept in one place, so that the skill stays generic. The planner reads it at the start of every planning session, and copies the facts a task needs into that task. Tasks never read `PROJECT.md` themselves.

## Contents

- [Sections](#sections)
- [Filling it for a new project](#filling-it-for-a-new-project)

## Sections

`templates/PROJECT.md` has these headings. Keep each one short and factual.

| Section                  | What goes in                                                                                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Repositories          | each repo (this one and siblings in `runner.json` `addDirs`), its role, its stack, and which one is the reference for behaviour, if any                              |
| 2. Standing rules        | the "never" rules that hold in every run (files never modified, data never deleted, secrets never written, no push). The planner repeats the relevant ones in tasks |
| 3. Commands              | targeted test form, full suites, linter, build/reload per component, docs build, screenshot capture, dev reset/seed                                                 |
| 4. Environment facts     | tools at full paths, credential files for signing in, ports, services that cannot be exercised locally (payments, mail)                                             |
| 5. Known failing tests   | test id, why, and "do not fix by deleting X"                                                                                                                        |
| 6. Numbering             | the last run's last phase number, and how to find numbered heads (migration head, contract version)                                                                 |
| 7. Documentation         | where the docs live, how they are built, where screenshots come from; or "no docs"                                                                                  |
| 8. Project lessons       | lessons specific to this project (the generic ones are in `lessons.md`)                                                                                             |

## Filling it for a new project

1. Read the README, CI workflow files, package manifests (`pyproject.toml`, `package.json`, ...), the test directory layout, and any existing `runs/`.
2. Fill in what you can prove. Write the rest as `A1`, `A2`, ... in the first plan's assumptions, and update `PROJECT.md` when the owner answers.
3. Ask the owner for the standing rules. They are rarely in the code: "Which files or data must a task never touch?"
4. Commit `PROJECT.md` and `runner.json` together with the first plan.

After each run, update sections 5, 6 and 8 from the ledger and `ADVERSARY.md`: known failures, the last phase number, and the lessons.
