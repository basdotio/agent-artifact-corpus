# DMS plugins: install, enable, configure

Read this before installing, enabling, configuring or removing a DMS plugin,
or when a plugin widget does not show up.

For writing a new plugin or changing plugin code beyond a small tweak, use
the official `dms-plugin-dev` skill:
https://github.com/AvengeMedia/DankMaterialShell/tree/master/.agents/skills/dms-plugin-dev
(`npx skills add AvengeMedia/DankMaterialShell --skill dms-plugin-dev`).

Upstream docs: https://danklinux.com/docs/dankmaterialshell/plugins-overview

## What a plugin is

A folder with a `plugin.json` manifest and QML files. The manifest `type`
says where it shows up: `widget` (bar or dock pill, optional Control Center
tile), `daemon` (no UI), `launcher` (items in the launcher, filtered by a
trigger string), `desktop` (desktop widget), `dash`/`dashCard` (DankDash tab or
card), `composite` (several of these, DMS 1.5.0+).

Plugins run with the full permissions of the user session. Before installing
from a registry or a git URL, say so and offer to show the source.

## Where things are

| Path | Content |
|------|---------|
| `~/.config/DankMaterialShell/plugins/<dir>/` | User plugins (registry installs and manual clones) |
| `/etc/xdg/quickshell/dms-plugins/` | System plugins from packages. Do not edit. |
| `~/.config/DankMaterialShell/plugin_settings.json` | Settings of all plugins, keyed by plugin id, including `"enabled": true/false` |
| `~/.local/state/DankMaterialShell/plugins/<id>_state.json` | Runtime state some plugins keep |
| `~/.config/DankMaterialShell/plugins.lock.json` | Exact git revisions of registry installs |

Plugin settings are never in settings.json. Placement is: bar widgets in
`barConfigs[].leftWidgets/centerWidgets/rightWidgets` (plugin id), Control
Center tiles in `controlCenterWidgets` (`plugin_<id>`), desktop widgets in
`desktopWidgetInstances`.

## Install and update

```bash
dms plugins browse                  # registry listing
dms plugins install <id>
dms plugins list                    # installed plugins
dms plugins update --check          # read-only: show available updates
dms plugins update <id>             # or: dms plugins update --all
dms plugins uninstall <id>
```

Registry: https://plugins.danklinux.com. Extra registries (DMS 1.6.0+):

```bash
dms registry list
dms registry add <name> <git-url>   # only registries the user trusts
dms registry remove <name>
```

Manual install from git:

```bash
git clone <url> ~/.config/DankMaterialShell/plugins/<Name>
dms ipc call plugin-scan scan
```

Reproduce a set of registry plugins on another machine:

```bash
dms plugins lock --output ~/plugins.lock.json
dms plugins restore ~/plugins.lock.json          # --prune also removes unlisted ones; ask first
```

## Enable and place

```bash
dms ipc call plugin-scan scan          # pick up new plugin folders
dms ipc call plugins list              # "<id> [loaded|disabled]"
dms ipc call plugins enable <id>
dms ipc call plugins status <id>
dms ipc call plugin-scan status <id>   # loaded, type, load error
```

Enabling loads the plugin; it still has to be placed:

- bar widget: Settings, Dank Bar, Widgets (`dms ipc call settings openWith dankbar_widgets`), or add the id to a widget list in `barConfigs`
- Control Center tile: edit mode of the Control Center, or add `{ "id": "plugin_<id>", "enabled": true, "width": 50 }` to `controlCenterWidgets`
- desktop widget: Desktop Widgets page (`settings openWith desktop_widgets`)
- launcher plugin: type its trigger in the launcher
- dash tab: appears on its own; dash cards are added in the dash edit mode

Bar layouts and tile lists are arrays, so `settings set` cannot change them;
see "Changing a setting" in [dms.md](dms.md).

## Configure

Use the plugin's own settings page (Settings, Plugins, click the plugin).
That writes `plugin_settings.json`. For a manual edit:

```bash
f=~/.config/DankMaterialShell/plugin_settings.json
cp "$f" "$f.bak.$(date +%Y%m%d-%H%M%S)"
jq '.["<id>"].refreshInterval = 30' "$f" > "$f.new" && jq empty "$f.new" && mv "$f.new" "$f"
dms ipc call plugins reload <id>
```

Setting names come from the plugin's settings QML (`settingKey: "..."`) or
its README.

## Small changes to plugin code

Registry plugins are git checkouts that `dms plugins update` manages, so
local edits can be lost or block the next update. Tell the user, or copy the
plugin to a new folder with a new `id` in `plugin.json` and change the copy.

- Edits to existing QML files: `dms ipc call plugin-scan reload <id>`.
- New QML files in a plugin folder are not found until the shell restarts
  ("X is not a type"). Ask before `dms restart`.
- Quickshell reloads when a loaded QML file changes. Many writes in a row to a
  loaded plugin can crash the shell. Disable the plugin first
  (`dms ipc call plugins disable <id>`), edit, then enable it.
- `console.log` is debug level in Quickshell and does not reach the journal
  by default. Use `console.warn` when you need output in
  `journalctl --user -u dms`.
- Use theme colors (`Theme.surfaceText`, `Theme.surfaceVariantText`,
  `Theme.primary`), not hex values, so the plugin follows the theme.

Anything larger: switch to the `dms-plugin-dev` skill.

## When a plugin does not work

- Not listed: `jq . ~/.config/DankMaterialShell/plugins/<dir>/plugin.json`, then `dms ipc call plugin-scan scan`.
- Listed but not loaded: `dms ipc call plugin-scan status <id>` shows the load error.
  A `requires_dms` higher than `dms version` keeps it from loading.
- Missing tools: the manifest's `dependencies` list commands it needs; check them with `command -v`.
- Loaded but invisible: it is not placed yet (see above), or it sits on a bar
  edge that an island owns ([pitfalls.md](pitfalls.md)).
- Tile missing in the Control Center: the id lacks the `plugin_` prefix.
- Logs: `journalctl --user -u dms -b | grep -i <id>`.
