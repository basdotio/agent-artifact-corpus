# A campaign, as it came out

This is the real output of a campaign, copied here unchanged except for the scrubbing noted below. The
product is a public app — an Android client for [Shiori](https://github.com/go-shiori/shiori), a
self-hosted bookmarks server — so you can read the code, the fixes and the commits it produced.

**2026-09-24, on app code that a previous campaign had already gone through and approved.** Same
commit, nothing new written since. What changed was the skill: the LOG oracle and the online+offline
mix rule did not exist in the earlier run.

| | |
|---|---|
| Found | **1 P0, 2 P1** — all missed by the first campaign, all fixed with a test seen red |
| The P0 | editing a bookmark **deleted the tags** someone had added elsewhere |
| Deferred | 11 P2s, in the queue with a recommendation each |
| **Unproven** | 2 — written down as unproven rather than counted as passes |
| Not covered | minimum-OS pass and the visitor role, by decision, said out loud |
| Suite | 340 tests, one flaky, named as flaky |
| Friction it sent back | 2 tool bugs → [issue #13](https://github.com/DesarrolloAntonio/qa-campaign/issues/13), both fixed the same day (#11, #12) |

## What to read

- [`CAMPAIGN.md`](CAMPAIGN.md) — the plan: scope, devices, accounts, fixtures, oracles, the gates, the
  human queue, the log, and the close-out. This is the file a campaign writes first and finishes last.
- [`00-setup.md`](00-setup.md) — the setup gate of a second campaign, so only what changed: whether
  the app reaches the server, the absence sweeps with their numbers, and whether the release can
  ship. The P1 that put the whole library into the system log is here, with the release dex counted
  before and after.
- [`02-mix.md`](02-mix.md) — the process that found the P0, by making a change offline and another one
  online against the same record before the queue drained.
- [`01-eye.md`](01-eye.md) — the screens that were looked at, one row each, in words.
- [`SKILL-FRICTION.md`](SKILL-FRICTION.md) — where the skill and the harness got it wrong. This is the
  file that improves the tool: both entries were fixed the day they were written.

## Scrubbed

The server's hostname and LAN address, and the serial of a work phone that is on the never-touch list.
Nothing else was edited — including the parts where the campaign says what it could not prove.
