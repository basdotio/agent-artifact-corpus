# scratchpool troubleshooting

Read this when a command fails in a way the error table in `SKILL.md` does not settle.
Every command below goes through the script with `--json`. Paths use `<home>` for the
scratchpool home: `$SCRATCHPOOL_HOME`, else `$XDG_CONFIG_HOME/scratchpool`, else
`~/.config/scratchpool` (Windows: `%APPDATA%\scratchpool`). Do not edit files there; read
them only when the user asks you to diagnose something.

## The pool never fills (`ready` stays 0)

1. `status --json`. Look at `service.installed`, `service.lastTick` and `counts.paused`.
   - `paused: true`: the user (or an earlier conversation) paused it. Offer `resume`.
   - `installed: false`: the scheduler is not running. Offer `service install`.
   - `lastTick` is old (more than two intervals ago): the machine was asleep, or the
     scheduler cannot start Node. See "Scheduler runs but nothing happens".
2. `tick --json` and read `pools[].skipped`:
   - `DAILY_FLOOR`: the hub has fewer daily creates left than `dailyFloor` (default 2). The
     pool waits for the rolling 24 h window. Do not lower `dailyFloor` without asking.
   - `TEAM_CAP`: pool-tagged orgs from everyone on this hub already use `teamCapPct`% (default
     25%) of the active allocation. Teammates' pools count too. Tell the user; a hub admin
     decides whether to raise it.
   - `ACTIVE_RESERVE`: the hub's free active slots are down to `activeReserve` (default 1, kept
     free for cold claims). Release orgs the user no longer needs, or wait for some to expire.
   - `DURATION_TOO_SHORT`: `durationDays` leaves less than `claimMinLifeHours` of life for an org
     created just before UTC midnight, so it could never be handed out. Nothing is created. Ask
     the user whether to raise `durationDays` or lower `claimMinLifeHours` (`config set`).
   - `SETUP_UNTRUSTED`: the setup hook changed (or disappeared) since it was enabled, for example
     after a `git pull`. Nothing is created. Ask the user to review `.scratchpool/setup*` themselves
     and, if they trust it, run `config set setupHook true` (do not run it on your own).
   - `locked`: another tick for this pool is still running. Harmless; it clears by itself.
   - `paused`: see above.
   - An error code (`SF_ERROR`, `LIMIT`, ...): `warnings[]` has the scrubbed reason.
3. Entries stuck in `creating`: a background create runs up to 30 minutes, plus the setup hook
   (up to 30 minutes). A worker that died (laptop slept, reboot) is marked `failed` after 45
   minutes and recycled on the next tick.
4. Entries `failed`: `status` shows them; the scrubbed reason is in `<home>/logs/scratchpool.log`.
   Common causes: an invalid definition file, a setup hook that exits non-zero, a hub limit.

## Scheduler runs but nothing happens

The OS scheduler starts with a minimal PATH, so `init` records absolute `nodePath`, `sfPath`
and `scriptPath`. If Node or the sf CLI moved (nvm switch, Homebrew upgrade, reinstall), re-run
`init` in the project (idempotent), or `service install` to rewrite the scheduler entry.

- macOS: `<home>/logs/launchd.log` holds the scheduler's own stdout/stderr. The agent is
  `~/Library/LaunchAgents/dev.scratchpool.tick.plist`.
- Linux: `systemctl --user status scratchpool-tick.timer` (the user can run it). On machines
  without a user systemd session (some WSL and container setups) `service install` returns
  `SERVICE_UNSUPPORTED` with a crontab line to paste into `crontab -e`.
- Windows: Task Scheduler task `scratchpool-tick`.
- Logs rotate at 1 MB: `<home>/logs/scratchpool.log` and one `.1` backup.

If the scheduler points at a script that no longer exists (an `npx` cache was purged, or the
plugin updated to a new directory), the next interactive `claim`, `status` or `tick` re-installs it
and reports the warning `SERVICE_REPAIRED`.

## `POOL_EMPTY` on every claim

The pool refills after each claim, and a create takes minutes. If it is empty again and again,
the pool is too small for how often the user claims. Show `status`, then suggest a size from
`docs/pool-sizing.md`. Resizing needs the user's yes (it uses allocation).

## The claimed org is "stale" or not offered

A ready org is only handed out if its `defHash` matches the current recipe (definition file,
snapshot name, namespace, hub, setup hook contents) and it has at least `claimMinLifeHours`
(default 24) of life left. After editing `config/project-scratch-def.json` or the setup hook,
existing ready orgs become stale. Options: `claim --any` (accept an old-recipe org), or
`release --stale` (with the user's yes) so the next tick builds fresh ones.

## `LIMIT`

`status` shows `limits.activeRemaining` and `limits.dailyRemaining`. Active slots free up when
orgs are released; daily creates free up over a rolling 24 h window. `release --orphans` frees
slots held by orphans: active hub records that scratchpool on *this* machine created for this hub
user but that local state no longer knows (for example after a crash or a lost state file). It
skips records younger than an hour (a create may still be running), orgs under a non-pool local
alias (probably claimed), and orgs from other machines. Tell the user an orphan might still be in
use before asking for their yes. On a Developer Edition hub (3 active, 6 daily) keep the pool at
size 1.

## `NOT_MANAGED`, `NOT_MINE`, `NOT_SCRATCH`

scratchpool only deletes orgs in its own state for the selected pool, that are scratch orgs of
the pool's hub. It will never delete a sandbox, a production org, a teammate's org, or a
scratch org it did not create. The user can delete such an org themselves with
`sf org delete scratch -o <alias>`; do not run it for them.

## `NO_DEVHUB`

The alias must be authenticated locally and listed under `devHubs` by `sf org list`. The user
logs in themselves (a browser window opens), for example
`sf org login web --set-default-dev-hub --alias devhub`. Dev Hub must be enabled in that org.
Free Developer Edition hubs can expire after inactivity.

## `SF_ERROR`

The message is already scrubbed. Known sf CLI issues:
- `DeployingSettingsTimeout` or a create that hangs: transient on Salesforce's side; the next
  tick retries. ([forcedotcom/cli#1817](https://github.com/forcedotcom/cli/issues/1817))
- C-1016 on a JWT / External Client App hub: see `docs/ci-auth.md`.
- sf older than 2.147.7 produces the `SF_OLD` warning. Ask the user to update
  (`sf update` or their package manager).

## `SECRETS_ENV`

`SF_TEMP_SHOW_SECRETS` makes the sf CLI print tokens. scratchpool refuses to run while it is
set. Ask the user to remove it from their shell profile and open a new terminal. Never set it.

## Things you must not do while troubleshooting

- Run `sf org display --verbose`, `sf org auth show-*`, or `sf org open --url-only`/`--json`.
- Print or paste URLs containing `frontdoor`, `sid=`, `access_token` or `force://`.
- Edit `<home>/config.json` or `<home>/state/*.json` by hand. Use `config set`, `release`, `init`.
- Deploy, push source or run the setup hook yourself.
- Release, resize or uninstall without the user's explicit yes in the conversation.

## Removing everything

`uninstall --yes` removes the scheduler entry and keeps claimed orgs. With
`--release-pool-orgs` it also deletes idle pool orgs (ready, creating, failed). Confirm first.
Anything left under `<home>` afterwards (config, state, logs) holds no secrets; the user can
delete that folder themselves once no claimed orgs remain that they care about.
