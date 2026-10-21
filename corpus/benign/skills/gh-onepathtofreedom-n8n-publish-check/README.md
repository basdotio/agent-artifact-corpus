# n8n-publish-check

Check an exported n8n workflow (JSON) for secrets and private data **before** it is committed to GitHub, posted publicly or shared with a client. Works as a Claude skill, as a standalone Python script, or as a git pre-commit hook.

> It is a heuristic scanner plus a manual review, not a guarantee. "No findings" means the known patterns did not match, nothing more.

![Scanner output on the example workflow](docs/img/scan-output.png)

Values are masked in the report (first 3 and last 2 characters), so the report itself is safe to paste into a ticket or a chat.

## What it checks

It knows the structure of an n8n export and looks in the places where data actually leaks:

| Where | Severity |
|---|---|
| `pinData` (real sample data from executions) | high |
| Literal values in `Authorization` / API-key-like fields, secrets in `?api_key=` / `?token=` | high |
| Known token formats (OpenAI/Anthropic, GitHub, Slack, Telegram, AWS, Google, Stripe, JWT, private keys) | high |
| IBANs (checksum-validated) | high |
| Your own deny-list terms (client names, internal domains) | high |
| Emails, phone numbers, IP addresses | medium |
| Resource IDs (`chatId`, `documentId`, ...), `cachedResultName` | medium |
| Webhook `path`, `staticData`, `shared` / `homeProject` | medium |
| Credential id/name, `webhookId`, `meta.instanceId` | low |

Expressions that read `$env`, `$credentials`, `$secrets` or `$vars` are treated as safe.

## Usage

Standard library only, Python 3.8+.

```bash
# scan
python3 scripts/scan.py workflow.json

# write a sanitized copy (the original is never modified), then re-scan it
python3 scripts/scan.py workflow.json --sanitize workflow.public.json
python3 scripts/scan.py workflow.public.json
```

Exit codes: `0` nothing at or above the threshold, `1` findings, `2` invalid JSON. Use `--fail-on low|medium|high` to change the threshold. Raw secret values are never printed in full.

![Before and after sanitizing](docs/img/sanitize-before-after.png)

A sanitized workflow needs its credentials reconnected after import, and the `REPLACE_ME` values filled in.

### Config (optional)

Create `.n8n-publish-check.json` in the folder you run the scan from, or pass `--config path`:

```json
{
  "deny_terms": ["Client GmbH", "internal-domain.example"],
  "allow_values": ["info@my-public-company.example"]
}
```

See `examples/n8n-publish-check.config.example.json`. Do not commit your real config, it contains client names.

### As a Claude skill

Copy this folder to `~/.claude/skills/n8n-publish-check/` (Claude Code) or upload it as a skill. Then ask Claude to "check this n8n workflow before I push it". `SKILL.md` describes the steps Claude follows.

### As a git pre-commit hook

```bash
cp scripts/pre-commit.sh /path/to/repo/.git/hooks/pre-commit
chmod +x /path/to/repo/.git/hooks/pre-commit
export N8N_PUBLISH_CHECK=/path/to/n8n-publish-check/scripts/scan.py   # if not installed as a skill
```

The hook scans the staged content and blocks the commit on findings of `medium` or higher.

## If a real secret was found

Removing it from the file is not enough. Rotate or revoke it. If the file was ever committed or pushed, the secret is in git history and must be treated as leaked.

## Tests

```bash
bash tests/run_tests.sh
```

## Examples

`examples/dirty-workflow.json` contains **fake** secrets on purpose (test fixture). `examples/clean-workflow.json` should produce no findings.

## License

MIT, see [LICENSE](LICENSE).
