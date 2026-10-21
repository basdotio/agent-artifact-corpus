# Mechanical enforcement (section 8 and `enforce` mode)

Prose rules are guidance; these mechanisms are hard guardrails. Without the `enforce` argument, only **recommend** them in the report. With `enforce`, install the ones the user confirms.

## Verified formats (Claude Code 2.1.289)

Project settings live in `.claude/settings.json` (shared, committed) or `.claude/settings.local.json` (personal, gitignored). Shape:

```json
{
  "permissions": {
    "deny": ["Edit(frontend/src/client/**)"],
    "ask": ["Bash(docker compose down -v*)"]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-edited-file.sh", "timeout": 60 }
        ]
      }
    ]
  }
}
```

- `permissions` takes `allow`, `deny`, and `ask` lists.
- File rules use `Edit(<glob>)`. These cover every file-editing tool; `Write(<glob>)` is not matched by file permission checks.
- Bash rules use `Bash(<command prefix>*)` or `Bash(<command> *)`.
- Hooks receive JSON on stdin with `tool_name` and `tool_input` (for edits, `tool_input.file_path`). Exit 0 = success. Exit 2 = blocking: stderr is fed back to Claude. Any other code = non-blocking error.
- `$CLAUDE_PROJECT_DIR` is the project root inside hook commands.
- Interactive checks for the user: `/permissions`, `/hooks`.

If any detail above conflicts with the installed version's own docs or behavior, the installed version wins. Report the conflict; don't write config you can't verify.

## Candidates (only those verified in this repo)

| Risk | Mechanism |
|---|---|
| Hand-edited generated files | `deny`: `Edit(<generated glob>)`. The generator runs via Bash, so it's unaffected. |
| Destructive local/prod commands (DB wipe, `down -v`, migrations against non-local DBs, deploy scripts) | `ask`: `Bash(<exact verified command prefix>*)` |
| Secret files | `ask` or `deny` on `Read(<secret file>)` / `Edit(<secret file>)`. Never block files the workflow needs (e.g. `.env.example`). |
| Bypassing hooks | `deny`: `Bash(git commit --no-verify*)`, `Bash(git push --no-verify*)` |
| Late lint/type feedback | the PostToolUse feedback hook below |

## Fast feedback hook (PostToolUse)

Purpose: after each Claude edit, run the repo's **own, verified, fast, non-mutating** checks on **that file only**, so errors surface immediately instead of in CI.

Requirements:
- **Checks:** use only commands already verified in Phase C. Prefer read-only checks: `lint check` and `format --check`, plus a per-file typecheck only if it's fast. Never run auto-fixers that rewrite the file Claude just edited, and never run the full test suite.
- **Scope:** map file extensions or paths to checks. Skip generated paths and files outside the project. Exit 0 for anything unmatched.
- **JSON parsing:** use a tool confirmed present (`command -v jq`, else `python3`, else `node` in JS repos). If none is available, don't install the hook; recommend it instead.
- **Speed:** keep it under the timeout. If a check needs services (a DB, docker), it doesn't belong in this hook.

Template; replace the case arms with this repo's verified commands and working directories:

```bash
#!/usr/bin/env bash
# Fast per-file feedback after Claude edits: runs this repo's own checks on the edited file only.
set -u
file=$(jq -r '.tool_input.file_path // empty')
[ -n "$file" ] && [ -f "$file" ] || exit 0
case "$file" in
  "$CLAUDE_PROJECT_DIR"/<generated-path>/*) exit 0 ;;
  *.py) out=$(cd "$CLAUDE_PROJECT_DIR/<pkg>" && <verified lint check> "$file" 2>&1); rc=$? ;;
  *.ts|*.tsx) out=$(cd "$CLAUDE_PROJECT_DIR" && <verified lint check> "$file" 2>&1); rc=$? ;;
  *) exit 0 ;;
esac
[ "$rc" -eq 0 ] && exit 0
printf 'Checks failed for %s:\n%s\n' "$file" "$out" >&2
exit 2
```

## `enforce` procedure

1. Finish the normal run first (rules written and validated).
2. Build the proposal: for each candidate, give the risk, the exact JSON entry or full hook script, the target file (`settings.json` vs `settings.local.json`), and its side effects.
3. Show the proposal and get explicit confirmation per item (a multi-select question when available). Nothing is written without confirmation. In a headless run, write nothing and put the proposal in the report.
4. **Merge, never overwrite:** read the existing settings JSON and add only the confirmed entries. Keep all existing keys and entries, and add no duplicates. Never touch user/global settings.
5. Write hook scripts to `.claude/hooks/` and make them executable (`chmod +x`).
6. **Validate:**
   - the settings file parses as JSON;
   - each hook gets a sample stdin payload for an existing clean file (expect exit 0) and for an unmatched extension (expect exit 0);
   - a failing case (expect exit 2 with output on stderr) only if it can be produced without modifying the repo, e.g. a temp file the linter accepts outside the repo. Otherwise report it as unverified.
7. Report exactly what was installed, where, how it was tested, and what remains unverified. Tell the user to check `/permissions` and `/hooks` interactively.
