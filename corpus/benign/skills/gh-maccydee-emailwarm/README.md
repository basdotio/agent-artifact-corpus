# emailwarm — email warmup for a new sending domain

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Claude Skill](https://img.shields.io/badge/Claude-skill-8A5CF6.svg)](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)

A Claude skill that does **email warmup** on a new sending domain, hands-on. It audits the domain's
SPF, DKIM and DMARC, helps fix the records where they actually live, sets up the mailboxes,
and then sends and replies on a daily cadence until the domain has a sending history.

Built from a real warm-up that went wrong in most of the ways available, so the traps are
baked in rather than left as an exercise.

## The thing most people get wrong

Perfect SPF, DKIM and DMARC will not put you in the inbox. In the run this is built from,
the first two messages passed all three with full alignment: one landed in Junk, the other
was dropped entirely. Authentication is table stakes, because failing it loses you the
inbox. Reputation is separate, and it is earned from two weeks of small, consistent,
human-looking behaviour.

## What it does

1. **Audits DNS** and tells you what to fix, including where your DNS is actually served
   (a domain is often registered in one place and served from another, and an edit at the
   registrar then changes nothing).
2. **Fixes records** in your own signed-in browser. It never types a password, a one-time
   code, or answers a 2FA prompt.
3. **Seeds mailbox sessions** into a dedicated browser profile, so a scheduled job can run
   later without a human present.
4. **Runs the cadence**: ramp the volume, reply from the other side, rescue anything that
   lands in spam, and record where each message was delivered.
5. **Reports honestly.** Two weeks of engaged sending improves how providers treat a domain.
   It does not guarantee inbox placement, and this says so rather than selling a promise.

## Quick start

On Windows, use `python` or `py -3` in place of `python3` below. Nothing else changes.

```bash
pip install playwright && python3 -m playwright install chromium

python3 scripts/dns_check.py yourdomain.com          # what is wrong, before you touch anything
python3 scripts/seed_login.py seed outlook           # sign in once, in a window it opens
python3 scripts/warmup_log.py next --log warmup.jsonl
python3 scripts/warmup_send.py --provider outlook \
    --to someone@example.com --from-address you@yourdomain.com \
    --subject "quick one" --body "Two ordinary sentences." --dry-run
```

`dns_check.py` on a domain whose SPF does not match where its mail actually comes from:

```
yourdomain.com   (mail: Microsoft 365)   (DNS: Cloudflare)
-----------------------------------------------------
  SPF    v=spf1 include:secureserver.net -all
  DMARC  v=DMARC1; p=quarantine; rua=mailto:...
  DKIM   none found at common selectors
  MX     0 yourdomain-com.mail.protection.outlook.com.

This domain serves a live website, so it is a brand asset.
  Ask what they intend to send from it:
   - normal business mail -> this is the right domain, fix the records below
   - cold outreach -> use a SEPARATE sending domain.

Fix before warming:
  - SPF does not authorise Microsoft 365, which is where the MX records point. Mail sent
    through Microsoft 365 will FAIL SPF.
  - No DKIM key found at the usual selector names.
```

## What is in here

| File | Does |
|---|---|
| `SKILL.md` | The workflow Claude follows |
| `scripts/dns_check.py` | SPF/DKIM/DMARC/MX audit, names the DNS host and the mail provider |
| `scripts/seed_login.py` | Seeds and verifies mailbox sessions for unattended runs |
| `scripts/warmup_send.py` | Sends one message and proves it reached Sent (Gmail, Outlook, AOL/Yahoo) |
| `scripts/warmup_log.py` | Ramp, placement record, stop rule |
| `references/` | Registrar quirks, per-provider placement measurement, failure modes |

## Things it refuses to do

Type passwords, one-time codes or security answers. Accept 2FA prompts. Create accounts.
Email anyone except the warm-up mailboxes you supplied. Each of those stops the run with a
clear message instead of improvising.

## Sending drivers

Gmail, Outlook and AOL are implemented and tested against live mailboxes. Yahoo shares AOL's
client so it uses the same driver, untested. Every driver confirms the message in **Sent**
before reporting success, because the worst outcome available is a log entry claiming
traffic that never existed.

## Built a driver for another provider?

If you point this at a mailbox it does not know and it writes a working driver, a pull
request would be genuinely useful. It saves the next person working out which button is
called "New email" this year, and which field quietly throws the address away.

No obligation at all. You came here to warm a domain, not to maintain my repo.

## Licence

MIT
