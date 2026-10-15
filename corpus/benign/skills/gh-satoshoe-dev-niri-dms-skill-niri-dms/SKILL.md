---
name: niri-dms
description: >
  REQUIRED for end-user customization of a desktop running the niri compositor
  with DankMaterialShell (DMS). Use before editing anything in ~/.config/niri/
  or ~/.config/DankMaterialShell/, before running `dms ipc call`, `dms restart`,
  `dms setup`, `dms plugins` or `niri msg action`, and when the user talks about
  their bar, dock, control center, launcher, notifications, lock screen,
  wallpaper, theme, dark/light mode, dynamic colors, matugen, GTK/Qt/terminal
  colors, keybindings, window rules, layer rules, blur, opacity, rounded corners,
  gaps, animations, monitors, workspaces, the overview, desktop widgets, or DMS
  plugins (installing, enabling, configuring). Also use when the bar is gone or
  the shell misbehaves after an update. Excludes writing new DMS plugins (use
  the official dms-plugin-dev skill) and development of niri or DMS themselves.
---

# niri + DankMaterialShell

Customize an installed niri + DMS desktop. niri is the Wayland compositor
(windows, layout, input, outputs, animations). DMS is the shell on top of it
(bar, dock, launcher, notifications, control center, lock screen, wallpaper,
theming) and runs as a Quickshell process managed by the `dms` binary.

This skill is for end users changing their own setup. It is not for
contributing to niri or DMS, and not for writing DMS plugins.

## When to use

Use this skill for any request that touches:

- files under `~/.config/niri/` (config.kdl, its includes, `dms/*.kdl`)
- files under `~/.config/DankMaterialShell/` (settings.json, plugin_settings.json, themes, plugins)
- `~/.local/state/DankMaterialShell/session.json` (wallpaper, light/dark, night mode)
- `dms` CLI commands and `dms ipc call ...`
- `niri msg ...`, `niri validate`
- app colors that DMS generates through matugen (GTK, Qt, terminals, browsers, editors)

If you are about to edit a file in `~/.config/niri/` or
`~/.config/DankMaterialShell/`, read the matching topic guide first.

## Topic guides

Read the guide that matches the request before you start:

- [niri.md](niri.md): config layout, includes and their order, binds, window and layer rules, blur, animations, outputs, validate and reload
- [dms.md](dms.md): the `dms` CLI, IPC target discovery, settings files, bar and island, control center, dock, desktop widgets, what a restart does
- [theming.md](theming.md): dynamic colors, matugen, custom themes, wallpapers, light/dark, GTK, Qt and terminal colors
- [plugins.md](plugins.md): installing, enabling and configuring DMS plugins, registries, where plugin settings live
- [pitfalls.md](pitfalls.md): known traps with exact symptoms
- [troubleshooting.md](troubleshooting.md): `dms doctor`, logs, the bar is gone, niri config errors, recovery

## Critical safety rules

1. Never edit package-owned files. Reading them is fine and often useful.
   - files the niri package installs, such as `/etc/niri/config.kdl` (a system
     default that is only read when no user config exists), the session files in
     `/usr/share/wayland-sessions/` and the systemd units in `/usr/lib/systemd/user/`
   - the DMS shell UI. Since DMS 1.6.0 it is embedded in the `dms` binary and
     mounted at runtime; older versions installed it to `/usr/share/quickshell/dms/`.
     Changing it means running a separate copy with `dms run -c <dir>`, which is
     shell development and out of scope here.
   - the `dms` and `niri` binaries themselves
2. Do not hand-edit files that DMS generates. Files in `~/.config/niri/dms/`
   that start with `// ! DO NOT EDIT !` or `// ! Auto-generated file` are
   rewritten whenever the matching DMS setting changes. Change the DMS setting
   instead, or override the value in your own niri file placed after the include.
   See [niri.md](niri.md).
3. Back up before editing. Copy the file with a timestamp:
   `cp file file.bak.$(date +%Y%m%d-%H%M%S)`. For the whole DMS config
   directory, `dms backup create` (DMS 1.6.0+) writes a tar.gz.
4. Validate after editing.
   - niri: `niri validate` must pass. niri live-reloads on save; if parsing
     fails it keeps the previous config and shows a "Failed to parse the config
     file" notice.
   - DMS JSON files: `jq empty ~/.config/DankMaterialShell/settings.json`.
     DMS ignores (and will not overwrite) a settings.json it cannot parse.
5. Ask before anything that interrupts the session or discards state:
   `dms restart`, `dms kill`, `systemctl --user restart|stop dms`,
   `dms setup headless --force`, `dms backup restore`, `dms plugins restore --prune`,
   deleting or replacing settings.json, `lock`/`powermenu`/logout actions,
   `niri msg action quit`. A restart closes open popouts and can leave tray
   icons missing until those apps restart (see [pitfalls.md](pitfalls.md)).
6. Prefer read-only commands for discovery: `dms ipc list`,
   `dms ipc call settings get <key>`, `dms keybinds show niri`,
   `niri msg --json windows|layers|outputs|workspaces`.
7. Plugins run with full session permissions. Before installing one from a
   registry or a git URL, tell the user and offer to show its source.

## System architecture

| Component | Role | Where it is configured |
|-----------|------|------------------------|
| niri | Compositor: layout, binds, window/layer rules, outputs, animations, blur | `~/.config/niri/config.kdl` and included files |
| DMS fragments | niri config pieces that DMS writes | `~/.config/niri/dms/*.kdl` |
| dms (Go binary) | CLI, backend, launches the shell, matugen runner | `dms --help` |
| DMS shell (Quickshell/QML) | Bar, dock, popouts, modals, lock screen, wallpaper, desktop widgets | `~/.config/DankMaterialShell/settings.json` |
| Session state | Wallpaper, light/dark, night mode, do-not-disturb | `~/.local/state/DankMaterialShell/session.json` |
| Plugins | Extra widgets, daemons, launcher providers | `~/.config/DankMaterialShell/plugins/`, `plugin_settings.json` |
| matugen | Generates colors from the wallpaper or theme for apps | DMS settings, `~/.config/matugen/config.toml` for your own templates |

DMS usually runs as the systemd user unit `dms.service`. Some setups start it
from niri with `spawn-at-startup "dms" "run"` instead. Check which one with
`systemctl --user status dms` before giving restart or log instructions.

## Command discovery

Command surfaces change between versions. Check the installed one instead of
trusting memory:

```bash
dms --help                     # all subcommands
dms <command> --help           # e.g. dms setup --help, dms plugins --help
dms version
dms ipc list                   # IPC targets and functions of the running shell (needs DMS running)
dms ipc call settings tabs     # ids of Settings pages, for `settings openWith <tab>`
niri --version
niri msg --help                # query and control commands
niri msg action --help         # every compositor action
```

IPC targets come from the running shell, including targets that plugins
register, so `dms ipc list` differs between machines. Full upstream reference:
https://danklinux.com/docs/dankmaterialshell/keybinds-ipc

## How changes take effect

| What you changed | How it applies |
|------------------|----------------|
| niri config or any included file | Live reload on save. `niri msg action load-config-file` forces it. |
| `settings.json` | DMS watches the file and reloads it. A few options only apply at startup; restart if a change does not show. |
| `session.json` | Watched like settings.json. Prefer the IPC calls (`wallpaper set`, `theme dark`). |
| Custom theme JSON in use | Applied live when the file changes. |
| Plugin files | `dms ipc call plugin-scan reload <id>` for edits, a shell restart for new QML files. See [plugins.md](plugins.md). |
| `~/.config/environment.d/*.conf` | Next login. |
| `systemctl --user edit dms` drop-ins | Next restart of dms. |

## Safe customization pattern

```bash
# 1. Read the current state
cat ~/.config/niri/config.kdl
dms ipc call settings get barConfigs

# 2. Back up
cp ~/.config/niri/config.kdl ~/.config/niri/config.kdl.bak.$(date +%Y%m%d-%H%M%S)

# 3. Edit with the Edit tool (smallest change that does the job)

# 4. Validate
niri validate
jq empty ~/.config/DankMaterialShell/settings.json

# 5. Verify the result with a read-only query and tell the user what changed
niri msg --json windows | jq '.[] | {app_id, title}'
```

When the user did the change through the DMS Settings window, do not also
write the same value into the file. The UI saves on its own.

## Decision framework

1. Is there a DMS setting for it (Settings window, `settings.json` key)? Use
   that. Gaps, corner radius, border size, cursor, keyboard repeat, outputs and
   the floating rule for DMS windows are all DMS settings that end up in
   `~/.config/niri/dms/*.kdl`.
2. Is it a one-shot action (wallpaper, dark mode, open a panel, volume)? Use
   `dms ipc call <target> <function>`. Find it with `dms ipc list`.
3. Is it compositor behavior DMS does not cover (window rules, layer rules,
   blur, animations, workspaces, extra binds)? Edit your own niri file
   (`config.kdl` or a file you include), following [niri.md](niri.md).
4. Is it a keybinding? Check what is bound first with
   `dms keybinds show niri`, then use `dms keybinds set niri ...` or a `binds {}`
   block in your own file placed after the DMS include.
5. Is it app colors? Follow [theming.md](theming.md).
6. Is it a plugin? Follow [plugins.md](plugins.md). For writing or changing
   plugin code, switch to the official dms-plugin-dev skill.
7. Not sure a command exists? Run its `--help` or `dms ipc list` before using it.

## Example requests

- "Switch to dark mode" -> `dms ipc call theme dark`
- "Set this image as wallpaper" -> `dms ipc call wallpaper set /absolute/path.jpg` (per monitor: `wallpaper setFor <output> <path>`)
- "Make the gaps smaller" -> `dms ipc call settings set niriLayoutGapsOverride 8` (or open the page with `dms ipc call settings openWith compositor_layout`); do not edit `dms/layout.kdl`
- "Round the window corners more" -> `dms ipc call settings set niriLayoutRadiusOverride 16`
- "Bind Mod+E to my file manager" -> `dms keybinds show niri` to see what Mod+E does now, tell the user, then `dms keybinds set niri "Mod+E" "spawn nautilus" --desc "Files"`
- "Open Firefox on workspace 2" -> window rule with `open-on-workspace` in your niri file ([niri.md](niri.md))
- "Blur my terminal" -> make the terminal semitransparent, then a `background-effect { blur true }` window rule (niri 26.04+)
- "Keep the wallpaper still when switching workspaces" -> check the `place-within-backdrop` layer rule and `background-color "transparent"` ([niri.md](niri.md))
- "Move the bar to the left" -> `dms ipc call bar setPosition index 0 left` (bars are selected by `id`, `name` or `index`)
- "Hide the bar" -> `dms ipc call bar toggle index 0`
- "Turn on night light" -> `dms ipc call night enable`
- "Add a clock/weather/system widget" -> DMS Settings, Widgets or Desktop Widgets page; plugins from the registry with `dms plugins browse`
- "Install plugin X" -> `dms plugins install <id>`, then enable it (see [plugins.md](plugins.md))
- "My GTK/Qt apps ignore the colors" -> [theming.md](theming.md), then `dms doctor`
- "The bar disappeared" -> [troubleshooting.md](troubleshooting.md); usually `systemctl --user start dms`
- "Configure my second monitor" -> `niri msg --json outputs`, then the DMS display page (`dms ipc call settings openWith display_config`), or an `output` block if `dms/outputs.kdl` is not included

## Out of scope

- Writing or debugging DMS plugin code: use the official `dms-plugin-dev`
  skill from https://github.com/AvengeMedia/DankMaterialShell/tree/master/.agents/skills/dms-plugin-dev
- Changing the DMS shell source, running dev builds, building niri
- Installing DMS or niri from scratch (see https://danklinux.com/docs and the niri wiki)
- Display manager / greeter setup beyond pointing to `dms-greeter`
