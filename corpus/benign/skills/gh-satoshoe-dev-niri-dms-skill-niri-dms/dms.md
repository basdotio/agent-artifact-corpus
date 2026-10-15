# DankMaterialShell: CLI, IPC and settings

Read this before changing the bar, dock, control center, launcher,
notifications, lock screen, desktop widgets or any DMS setting.

Upstream: https://danklinux.com/docs/dankmaterialshell/ (source:
https://github.com/AvengeMedia/DankLinux-Docs) and the code at
https://github.com/AvengeMedia/DankMaterialShell. Versions below are DMS
releases; check yours with `dms version`.

## How DMS runs

`dms run` starts the Go backend and the Quickshell UI. Since 1.6.0 the UI is
embedded in the `dms` binary; `dms run -c <dir>` or `DMS_SHELL_DIR` runs a
different copy (development only).

```bash
systemctl --user status dms     # running as a user service?
dms version
dms restart                     # restarts the shell; uses systemd when the unit is active
dms kill                        # stops every dms process
dms run -d                      # start detached when not using systemd
```

Do not run both the systemd unit and `spawn-at-startup "dms" "run"` in niri;
that starts two shells. `systemctl --user add-wants niri.service dms` ties the
unit to niri sessions only.

## What a restart does

Ask before restarting. A restart:

- closes open popouts, modals and the Settings window
- reloads all plugins (their in-memory state is lost; saved settings stay)
- re-reads settings.json, session.json and plugin_settings.json
- drops tray icons of apps that do not register again with the new
  StatusNotifierWatcher; those apps need a restart to show up again
- briefly removes the bar and wallpaper surfaces; niri keeps running and
  windows are not touched

Most settings do not need a restart. Use one when a change only applies at
startup, after adding new QML files to a plugin, or after a DMS update.

## Command discovery

```bash
dms --help                       # top-level commands (auth, backup, blur, brightness, clipboard, color,
                                 # config, dank16, doctor, ipc, keybinds, matugen, notify, plugins,
                                 # registry, restart, run, screenshot, setup, ...)
dms ipc list                     # every IPC target and function of the running shell
dms ipc call <target> <function> [args...]
dms ipc <target> <function> [args...]   # same, "call" may be omitted
```

`dms ipc list` needs a running shell and includes targets registered by
plugins. Function arguments are positional strings. Many functions return a
status string such as `BAR_NOT_FOUND`; read it instead of assuming success.

Frequently used targets (verify with `dms ipc list`):

| Target | Examples |
|--------|----------|
| `theme` | `toggle`, `light`, `dark`, `getMode` |
| `wallpaper` | `get`, `set <path>`, `getFor <output>`, `setFor <output> <path>`, `next`, `prev` |
| `bar` | `toggle index 0`, `hide name "Main Bar"`, `setPosition index 0 left`, `status index 0` |
| `dock` | `toggle`, `status`, `toggleAutoHide` |
| `settings` | `open`, `openWith <tab>`, `tabs`, `get <key>`, `set <key> <value>`, `dump` |
| `control-center` | `toggle`, `open`, `hide` |
| `spotlight` / `launcher` | `toggle`, `openQuery <text>` |
| `notifications` | `toggle`, `toggleDoNotDisturb`, `clearAll` |
| `night` | `enable`, `disable`, `toggle`, `setTargetTemp <K>`, `status` |
| `audio` / `mic` / `brightness` | `increment 5`, `decrement 5`, `mute`, `status` |
| `lock` | `lock`, `isLocked` |
| `desktopWidget` | `list`, `status <instanceId>`, `toggleEnabled <instanceId>`, `toggleClickThrough <instanceId>` |
| `plugins` / `plugin-scan` | see [plugins.md](plugins.md) |

`bar` functions select a bar by `id`, `name` or `index` from `barConfigs`.

## Settings files

| File | Content | Notes |
|------|---------|-------|
| `~/.config/DankMaterialShell/settings.json` | All shell settings: theme, bars, widgets, control center tiles, dock, launcher, lock, power, matugen templates, niri layout overrides | Only non-default values are stored. Watched and reloaded on change. |
| `~/.config/DankMaterialShell/plugin_settings.json` | Settings of every plugin, keyed by plugin id | Not in settings.json. See [plugins.md](plugins.md). |
| `~/.local/state/DankMaterialShell/session.json` | Wallpaper paths (global, per monitor, per light/dark mode), light mode, night mode, do-not-disturb, wallpaper cycling | Machine-specific state. Watched. |
| `~/.config/DankMaterialShell/themes/<id>/` | Themes installed from a registry | |
| `~/.config/DankMaterialShell/plugins/<id>/` | Installed plugins | |
| `~/.config/DankMaterialShell/plugins.lock.json` | Exact revisions of registry plugins | `dms plugins lock` / `restore` |
| `~/.config/DankMaterialShell/registries.json` | Extra plugin/theme registries (1.6.0+) | `dms registry ...` |
| `~/.cache/DankMaterialShell/` | Generated colors and caches | Safe to delete while DMS is stopped |

The full list of keys and defaults is in `quickshell/Common/settings/SettingsSpec.js`
of the DMS source for your version (`SessionSpec.js` for session.json). A key
missing from settings.json is at its default. Read the live value with:

```bash
dms ipc call settings get niriLayoutGapsOverride
dms ipc call settings dump | jq '.barConfigs[0].rightWidgets'
```

Newer DMS (after 1.6.3, on the development branch at the time of writing)
also reads drop-in files from `~/.config/DankMaterialShell/config.d/*.json`.
Do not rely on that on 1.6.x.

### Changing a setting

Scalars (booleans, numbers, strings) can be set over IPC. DMS saves the file:

```bash
dms ipc call settings set niriLayoutRadiusOverride 14
dms ipc call settings set dockAutoHide true
```

The function returns `SETTINGS_SET_SUCCESS`, `SETTINGS_INVALID_KEY` or
`SETTINGS_SET_FAILURE`. Arrays and objects (`barConfigs`,
`controlCenterWidgets`, `desktopWidgetInstances`, ...) are refused over IPC.
For those, edit settings.json directly:

```bash
f=~/.config/DankMaterialShell/settings.json
cp "$f" "$f.bak.$(date +%Y%m%d-%H%M%S)"
jq '.barConfigs[0].rightWidgets += ["clock"]' "$f" > "$f.new" && jq empty "$f.new" && mv "$f.new" "$f"
```

If the key is missing because it is at its default, copy the default from
`dms ipc call settings dump` into the file first. Keep the Settings window
closed while editing the file so the two do not save over each other. If the
change does not show after a few seconds, offer a restart.

## Bar, island and frame

Bars live in `barConfigs` (array). Each entry has `id`, `name`, `enabled`,
`position` (0 top, 1 bottom, 2 left, 3 right), `screenPreferences`, and
`leftWidgets`/`centerWidgets`/`rightWidgets` with widget ids. Plugin bar
widgets use the plugin id (optionally `id:instance`). Change layouts in
Settings, Dank Bar, Widgets (`dms ipc call settings openWith dankbar_widgets`)
when possible.

DMS 1.6 also has the Dank Island bar style and a screen frame mode. An island
claims its screen edge: a normal bar configured on the same edge of the same
screen is not drawn at all. Move one of them to another edge.

## Control Center

Tiles are in `controlCenterWidgets`, an array of `{ "id", "enabled", "width" }`.
Built-in ids include `volumeSlider`, `brightnessSlider`, `wifi`, `bluetooth`,
`audioOutput`, `audioInput`, `nightMode`, `darkMode`. A plugin tile uses the id
`plugin_<pluginId>`; the bare plugin id does not work here.

## Desktop widgets

Built-in and plugin desktop widgets are configured on the Desktop Widgets page
(`dms ipc call settings openWith desktop_widgets`) and stored in
`desktopWidgetInstances`. Positions are kept separately per screen.
`dms ipc call desktopWidget list` shows the instances and their ids. By
default they are layer surfaces on the bottom layer (namespace
`dms:desktop-widget:<id>`), so in niri they move with workspaces and shrink in
the overview; see [niri.md](niri.md). Overlay mode
(`desktopWidget toggleOverlay <instanceId>`) puts an instance on the overlay
layer above windows instead.

## Keybindings, window rules, displays

DMS has pages that write niri config for you:

- Keybinds: `dms keybinds show niri`, `dms keybinds set|remove niri ...`, writes `~/.config/niri/dms/binds.kdl`
- Window rules: `dms config windowrules list|add|update|remove|reorder niri ...`, writes `~/.config/niri/dms/windowrules.kdl`
- Displays: Settings page `display_config`, writes `~/.config/niri/dms/outputs.kdl`
- Compositor layout (gaps, radius, border): Settings page `compositor_layout`, writes `~/.config/niri/dms/layout.kdl`

## Environment variables

DMS reads `DMS_*` variables at startup, for example `DMS_DISABLE_MATUGEN=1`,
`DMS_HIDE_TRAYIDS=a,b`, `DMS_DANKBAR_LAYER=overlay`, `DMS_DISABLE_HOT_RELOAD=1`.
Set them in `~/.config/environment.d/90-dms.conf` (next login), in
`systemctl --user edit dms` under `[Service]` (next restart of dms), or in
niri's `environment {}` block. List:
https://danklinux.com/docs/dankmaterialshell/advanced-configuration

## Backups

```bash
dms backup create      # tar.gz of ~/.config/DankMaterialShell (settings, plugins, themes), DMS 1.6.0+
dms backup restore <archive>   # moves the current config aside first; ask before running
```

session.json and `~/.config/niri/` are not part of it; copy them separately.
