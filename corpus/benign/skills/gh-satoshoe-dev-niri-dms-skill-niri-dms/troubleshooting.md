# Troubleshooting

Start with read-only checks. Ask before restarting, stopping or resetting
anything.

## First checks

```bash
dms version
niri --version
niri msg version                 # running compositor; differs from niri --version until next login
systemctl --user is-active dms   # "active" when DMS runs as the user unit
dms doctor                       # dependencies, compositor, config files, Quickshell features
dms doctor -v                    # with paths and versions
dms doctor -j                    # JSON
niri validate
```

`dms doctor -C` copies a GitHub-formatted report to the clipboard for a bug
report. Only run it when the user wants to file one.

## Logs

```bash
journalctl --user -u dms -b              # DMS as systemd unit, this boot
journalctl --user -u dms -f              # follow
journalctl --user -u niri -b             # niri as systemd unit (niri-session)
```

If DMS is started by niri with `spawn-at-startup`, its output ends up in
niri's log instead. `DMS_LOG_LEVEL=debug` (in the unit environment) makes the
shell's own logging verbose. Quickshell crash reports land in
`~/.cache/quickshell/crashes/`.

## The bar is gone

1. `systemctl --user is-active dms`
2. Not running: `systemctl --user start dms`. Without the systemd unit:
   `dms run -d`. Both are safe; nothing is running that could be lost.
3. It starts and dies again: read `journalctl --user -u dms -b -n 100`.
   Common causes and fixes:
   - a plugin that just got installed or edited: set its `"enabled"` to
     `false` in `plugin_settings.json` (after a backup), start again
   - invalid settings.json: `jq empty ~/.config/DankMaterialShell/settings.json`
     shows the line; restore the latest `.bak` copy or fix the syntax
   - after a package update: compare `dms version` with the release notes at
     https://github.com/AvengeMedia/DankMaterialShell/releases
4. Running but invisible: the bar may be hidden or auto-hidden
   (`dms ipc call bar status index 0`, then `bar reveal index 0`), disabled in
   `barConfigs`, or on an edge owned by an island.

## The shell hangs or acts strange

- `dms ipc list` fails or times out: the shell is not reachable. Check the
  unit and the log before anything else.
- A toast "Failed to parse settings.json": DMS keeps running with the last
  good settings and will not overwrite the file. Fix the JSON.
- Settings appear to reset: another program or the Settings window wrote the
  file. Compare with the latest backup.
- Last resort, with the user's consent: move settings.json aside
  (`mv settings.json settings.json.bak.$(date +%Y%m%d-%H%M%S)`), restart, and
  DMS starts with defaults. Plugins and themes stay.

## niri problems

- Red "Failed to parse the config file" notice: run `niri validate`, fix, save.
  The previous config stays active until then.
- A rule or bind has no effect: check include order ([niri.md](niri.md)) and
  that the file is included (`dms config resolve-include niri <file>.kdl`).
- Window rule does not match: compare with `niri msg --json windows`; regexes
  match anywhere unless anchored with `^...$`.
- Layer rule does not match: compare with `niri msg layers`.
- Custom shader ignored: compile warnings are in the niri log.

## Keybinding does nothing

1. `dms keybinds show niri` and look for the key; check for a duplicate in a later file.
2. For DMS binds, DMS must be running: `dms ipc list`.
3. Run the bound command in a terminal to see its error, e.g. `dms ipc call spotlight toggle`.
4. `niri validate`; a parse error keeps the old binds active.

## Colors not applied to apps

1. `dms doctor` must find `matugen`.
2. `dms matugen check` lists the apps DMS detects.
3. The template toggle for the app must be on (`matugenTemplate<App>`).
4. The app config must include the generated file ([theming.md](theming.md)).
5. Qt platform theme or other environment changes need a new login.

## After an update

- niri: log out and back in so the running compositor matches the binary.
  New niri versions keep old configs parsing, but check the release notes for
  changed behavior.
- DMS: a restart loads the new shell (ask first). Then:
  - `dms setup <name>` (`binds`, `colors`, `layout`, `outputs`, `cursor`, `windowrules`, `alttab`) creates a missing or empty fragment and leaves existing ones alone; plain `dms setup` is interactive, so leave that to the user
  - `dms config resolve-include niri <file>.kdl` for each `include` DMS expects
  - `dms plugins update --check` and `dms ipc call plugins list` to see plugins that no longer load
- Keep backups (`dms backup create`) before updating so the user can compare.

## Reporting upstream

- DMS: https://github.com/AvengeMedia/DankMaterialShell/issues, include `dms doctor` output
- niri: https://github.com/niri-wm/niri/issues, include `niri --version`, the relevant config and log lines

Before filing, rule out local changes: patched builds, plugins, hand-edited
generated files.
