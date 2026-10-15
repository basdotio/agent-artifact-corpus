# Known pitfalls

Each entry: what you see, why, what to do. Check this list when something
"should work" but does not.

## DMS settings

### `settings set` fails for lists and objects
`dms ipc call settings set barConfigs '[...]'` returns `SETTINGS_SET_FAILURE`.
The IPC setter only handles booleans, numbers and strings, and Quickshell's
IPC argument handling does not carry JSON lists intact. Edit settings.json
with jq (back up, validate with `jq empty`), see [dms.md](dms.md).

### A key is not in settings.json
DMS writes only values that differ from the default. Read the live value with
`dms ipc call settings get <key>` or `settings dump`, then write the full value.

### Plugin settings "do nothing"
Plugin settings belong in `plugin_settings.json` under the plugin id, not in
settings.json. After a manual edit run `dms ipc call plugins reload <id>`.

### Edits to settings.json get lost
The Settings window was open and saved its own copy. Close it before editing
the file, then check the result with `settings get`.

### Hand edits in ~/.config/niri/dms/ disappear
DMS regenerates `layout.kdl`, `colors.kdl`, `cursor.kdl`, `input.kdl`,
`alttab.kdl` (and `outputs.kdl` when the display page saves). Change the DMS
setting, or override in your own file after the include.

## niri config

### Your binds or layout values are ignored
Includes are positional. If `include "dms/binds.kdl"` comes after your own
`binds {}`, DMS's binds win for the same key; the same goes for `layout`
values. Put your overrides after the DMS includes. `dms keybinds show niri`
shows which bind wins.

### Config "does nothing" after saving
niri kept the old config because the new one failed to parse (red notice on
screen). Run `niri validate`.

### Same output configured twice
An `output "DP-1"` block in config.kdl plus one in `dms/outputs.kdl` can fail
to parse or be ignored. Keep outputs in one place.

### Animation override loses other settings
Each block inside `animations {}` replaces the earlier one completely. Copy
every setting of that animation into your override.

### `spawn` with pipes or `~` does not run
`spawn` does not use a shell. Use `spawn-sh "..."` (niri 25.08+) or
`spawn "sh" "-c" "..."`.

### `niri msg` prints parse errors after an upgrade
The running compositor is older than the `niri` binary. Log out and back in.

## Layers, workspaces, input

### Wallpaper or desktop widgets slide with workspaces
Since niri 25.05, background and bottom layer surfaces belong to each
workspace and move with it. Only `place-within-backdrop true` keeps a surface
still, and it works only for background layer surfaces that ignore exclusive
zones. Surfaces in the backdrop receive no input, so this is not an option
for interactive widgets. DMS desktop widgets are on the bottom layer and will
move; their overlay mode puts them above windows instead.

### A second bar does not appear
A DMS island owns its edge. A regular bar set to the same edge of the same
screen is not drawn. Use another edge or another screen.

### Hover or cursor tracking only works sometimes
Wayland sends pointer motion only to the surface under the pointer. A widget
behind a window, or in the backdrop, gets nothing, and upstream niri has no
IPC request for the global pointer position. Effects that follow the cursor
across the whole screen are not possible from a normal widget.

### Blur shows nothing
The window or layer has to be semitransparent, and `background-effect`
needs niri 26.04. Older niri rejects the config.

## Shell restarts and reloads

### Tray icons missing after `dms restart`
The new shell starts a new StatusNotifierWatcher. Apps that do not register
again keep their icon hidden until the app restarts. Mention this before
offering a restart.

### Two bars, double notifications
DMS runs twice: once from `dms.service` and once from `spawn-at-startup "dms" "run"`.
Keep one.

### New QML file in a plugin: "is not a type" or "File name case mismatch"
Quickshell resolves a folder's QML types when the plugin loads. New files
need a shell restart, and the file name must match the type name exactly,
including case.

### Shell crashes while editing a plugin
Quickshell reloads when a loaded QML file changes. Many writes in a row, or a
half-written file, can crash it. Disable the plugin, edit (or work on a copy),
enable again.

### QML changes do not show up even after a restart
Stop the shell (`dms kill` or `systemctl --user stop dms`), delete
`~/.cache/quickshell/qmlcache`, start it again. Ask first; the bar is gone
while it is stopped.

### `console.log` output is nowhere
In Quickshell `console.log` is debug level and hidden by default. Use
`console.warn` and read `journalctl --user -u dms`.

### Plugin text unreadable after a theme change
Hard-coded colors. `Theme.surfaceText` and `Theme.surfaceVariantText` are
readable on every DMS surface in both modes.

### Control Center tile for a plugin never shows
The tile id must be `plugin_<pluginId>`.

## Theming

### Environment change (Qt platform theme, DMS_*) has no effect
`~/.config/environment.d/*.conf` is read at login. Log out and back in.
Variables in `systemctl --user edit dms` need a restart of dms.

### kitty ignores the DMS colors
kitty may have saved `dark-theme.auto.conf` or `light-theme.auto.conf` in its
config folder, which override includes. Remove them (after a backup).

### Colors you set by hand in a generated file are gone
Files like `dank-colors.css`, `dank-theme.conf` and `dms/colors.kdl` are
rewritten on every color change. Override in the including config instead.
