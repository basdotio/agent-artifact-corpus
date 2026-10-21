---
name: scrub-transcripts
model: sonnet
description: Find and redact credentials that ended up in Claude's local transcripts (passwords, API keys, bot tokens, private keys, DB/FTP URLs with passwords), whether the user typed or pasted them into a prompt, or a tool printed them (cat .env, gh auth status, a config file). Scans Claude Code session logs (~/.claude/projects), prompt history (~/.claude/history.jsonl) and the Claude desktop app's session stores (macOS, Windows, Linux), reports findings without ever printing a secret, then rewrites the files in place with [REDACTED:<kind>]. Use whenever the user says they pasted/typed/leaked a password, key or token into Claude, asks to scrub, sanitise, clean or redact transcripts, chat history, session logs or prompt history, wants to check whether any secrets are sitting in Claude's logs, is about to share or back up ~/.claude, or invokes /scrub-transcripts. Trigger even if they only say "I just gave you my password, get rid of it".
---

# Scrub credentials from Claude transcripts

Claude Code keeps every session as plain-text JSONL on disk. Anything typed into a
prompt, pasted in, or printed by a tool stays there indefinitely: in the session log,
in prompt history, and in the desktop app's copies. This skill finds those secrets and
rewrites the files with `[REDACTED:<kind>]` in their place.

The script is `scripts/scrub.py`. It uses only the standard library and needs Python 3.9 or newer.

## The rules that matter

1. **Never ask the user to paste the secret into chat so you can "find it".** The
   message would land in the very transcript you are cleaning. If they want a specific
   value scrubbed and the detectors miss it, use a values file that they create
   themselves (see below). You never read that file.
2. **Never print a secret.** The report shows kind, length, the vendor prefix for
   known formats (`ghp_…`) and a context snippet taken from the *already-redacted*
   text. Don't `grep` or `cat` transcript lines to "check" a finding. That would copy
   the secret into this session. If a finding needs closer inspection, use the
   snippet or re-run with `--path` on that one file.
3. **Dry run first, then `--apply`.** Show the user the summary and the rows before
   writing anything.
4. **Scrubbing doesn't un-leak anything.** The value has already been sent to the
   API, and it may also be in backups (Time Machine, iCloud, a synced dotfiles repo).
   Tell the user to **rotate** anything real that turns up: bot tokens, API keys,
   passwords. This step matters more than the scrub.

## Workflow

### 1. Dry run

```bash
python3 ~/.claude/skills/scrub-transcripts/scripts/scrub.py --format markdown
```

In chat, always pass `--format markdown`. The script prints a ready-made report: a
summary table, one redacted example per kind, and numbered next steps with the exact
`--apply` command. A person running it in a terminal gets the same report as box tables
(the default `--format text`). `--format json` gives raw data if you need to dig.

Scans by default:

| store | path |
|---|---|
| transcripts | `~/.claude/projects/**/*.jsonl` (including subagent logs) |
| prompt-history | `~/.claude/history.jsonl` (the up-arrow history, i.e. what was typed) |
| cowork | `<desktop app dir>/local-agent-mode-sessions/**/*.jsonl` |
| desktop-sessions | `<desktop app dir>/claude-code-sessions/**/*.json` |

The desktop app dir is `~/Library/Application Support/Claude` on macOS, `%APPDATA%\Claude`
on Windows and `~/.config/Claude` on Linux. Stores that don't exist are skipped.

`--all` adds `~/.claude/file-history` (snapshots of files Claude edited, which often
include `.env` files), `shell-snapshots`, `tasks` and `plans`.

A full scan of several GB takes a few minutes across all cores. To narrow it:
- `--since 2` covers files modified in the last 2 days (use this for "I just pasted my password")
- `--path <file-or-dir>` scans one session or project
- `--root <dir>` treats `<dir>` as the home directory, for scanning a backup, a copied
  profile, or a user who says "my Claude data is at X". All the store paths above are resolved under it.
- `--json` gives machine-readable output; `--max-rows N` controls how many rows print

Exit code 1 means findings exist (dry run). 0 means the scan was clean, or `--apply` succeeded.

### 2. Show the report, then stop

Paste the script's markdown report into your reply **as it is**. Don't paraphrase it
into prose or trim the tables, because the table is what the user reads. Add at most two
sentences of your own above it, such as the one thing that stands out ("3 of these are
Telegram bot tokens, so rotate those today") or a false-positive pattern you noticed in
the examples. Then wait for the go-ahead, unless the request already asked for removal
("get it out of the logs"). That counts as the go-ahead, so go straight to step 3.

How to read it:
- **Confidence.** "certain" means a vendor token format (GitHub, Telegram, Anthropic,
  private key, a password inside a URL…) and it is a real credential. "likely" means a
  value after a label like `password:` or `api_key=`. A few of those may be harmless;
  over-redacting old logs costs nothing, so don't argue a handful of them out. Only a whole
  category of false positives is worth raising.
- **Where it came from.** "you" means typed or pasted by the user, "tool output" means
  printed by a command or API, "Claude" means the model repeated it, and "session data"
  means bookkeeping records that duplicate prompts.

Kinds:

| kind | what it is |
|---|---|
| `anthropic_key`, `openai_key`, `github_token`, `gitlab_token`, `aws_access_key_id`, `google_api_key`, `google_oauth_token`, `google_client_secret`, `slack_token`, `slack_webhook`, `discord_webhook`, `stripe_key`, `stripe_webhook_secret`, `telegram_bot_token`, `huggingface_token`, `npm_token`, `pypi_token`, `sendgrid_key`, `twilio_key`, `digitalocean_token`, `mailgun_key` | vendor token formats, high confidence |
| `private_key` | PEM private key block |
| `jwt` | JSON Web Token (API keys, session tokens, also unsubscribe links) |
| `url_password` | the password part of `scheme://user:PASSWORD@host` |
| `auth_header`, `bearer_token` | `Authorization: Bearer …` values |
| `password` | value after a password-like key: `DB_PASSWORD=…`, `Password: …`, `my password is …`, `--password=…` |
| `secret_assignment` | value after a secret/token/api-key-like key |
| `url_token` | `?token=…` / `&otpToken=…` in URLs (magic-link and unsubscribe tokens) |
| `literal` | an exact value from `--values-file` |
| `high_entropy` | `--aggressive` only: a bare random-looking string in user-typed text |

### 3. Apply, then show the completion report

```bash
python3 ~/.claude/skills/scrub-transcripts/scripts/scrub.py --format markdown --apply
```

Use the same scope flags as the dry run. `--kinds telegram_bot_token,password`
redacts only those kinds, and `--all` also covers the extra stores.

The completion report shows what replaced each secret (`[REDACTED:<kind>]` per kind),
the files changed, how the redacted lines read now, and a re-scan of the changed files
that should say "0 secrets left". Paste it as it is, as in step 2. It is also saved as markdown
under `~/.claude/scrub-reports/` (masked content only, mode 600). Give the user that path.
Finish with the rotate list from its next steps. Rotating is the part that actually protects them.

How the write is kept safe:
- Only lines that contain a finding are rewritten. Every other line stays byte-identical.
- Each rewritten line is re-parsed as JSON, and the line count must match, before the file is replaced.
- The write goes to a temp file **in the same directory**, then an atomic rename.
  The original mtime is restored so session ordering in the app does not change.
- Files modified in the last 10 minutes are **skipped** because a live session may
  be appending to them. That includes the current session. If the leak happened in the
  session you are in, say so and tell the user to re-run after closing it
  (`--since 1`), or use `--include-active` once that session is closed.
- If a file changes between read and write, it is left alone and reported.
- No backup copy is kept. A backup of a secret is just another copy of the secret.


### Scrubbing a specific value the detectors miss

For example, a password typed as a bare word with no "password" nearby. Ask the user
to put the value(s) in a file **themselves**, one per line, and give you only the path:

```bash
# user runs this in their own terminal, not in chat
pbpaste > ~/.scrub-values && chmod 600 ~/.scrub-values
```

Then:

```bash
python3 ~/.claude/skills/scrub-transcripts/scripts/scrub.py --values-file ~/.scrub-values --since 7
python3 ~/.claude/skills/scrub-transcripts/scripts/scrub.py --values-file ~/.scrub-values --since 7 --apply --delete-values-file
```

Values shorter than 4 characters are refused because they would match everywhere.
`--aggressive` also flags bare high-entropy strings in user-typed text only. It is
noisier, so use it for a narrow `--since` window.

## Caveats to state when relevant

- A thinking block that contained a secret will fail its signature check if that
  exact session is resumed and the block is replayed. The transcript still reads fine.
  The trade-off is acceptable: the alternative is keeping the secret.
- Heuristic detectors will miss some things: a password on its own with no label,
  or a token in an unfamiliar format. Point the user at `--values-file` for those.
- This covers Claude's local stores only. It does not touch the user's shell history
  (`~/.zsh_history`), project files, or anything already committed to git.

## Tests

```bash
cd ~/.claude/skills/scrub-transcripts && python3 -m unittest discover -s tests -v
```
