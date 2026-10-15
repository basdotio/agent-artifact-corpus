# secretary

A chief-of-staff skill for Claude Code. It keeps a small plain-text store (goal, deadlines,
money, one main project, a daily log) and answers from it, so you stop holding the whole
picture in your head.

## Modes

| Say | It does |
|---|---|
| "set up my secretary" | Interviews you once, creates the store. Unknowns become `TBC`. |
| "secretary" / "brief me" | Under 25 lines: days to goal, next deadlines, project status, the one thing to do today. |
| "log this" / "I submitted X" | Updates the right file and appends to the log. One-line confirmation. |
| "plan my week" | Works backwards from due dates, flags pinch weeks. |
| "check my email" | Optional. Searches your webmail in the browser for deadline changes. Read-only. |

## Install

```bash
git clone https://github.com/ashtonhwoi/claude-skills.git
cp -R claude-skills/skills/secretary ~/.claude/skills/
mkdir -p ~/Secretary && cp claude-skills/skills/secretary/templates/* ~/Secretary/
```

Then tell Claude Code "set up my secretary".

## Make it yours

- **Store location:** change `store_path` in `goal.md` and the default in `SKILL.md`.
- **No money tracking?** Delete `investing.csv`. The brief drops that block.
- **No courses?** Use `area` in `deadlines.csv` for clients, projects or job tasks.
- **Mail:** list the senders and keywords in `mail.md`. It never sends, deletes or moves mail
  and never types a password.
- **Tone:** the standing rules at the bottom of `SKILL.md` set the bluntness. Edit them.

## Privacy

The store holds personal data (goal numbers, deadlines, balances). Keep `~/Secretary/`
out of any public repo.
