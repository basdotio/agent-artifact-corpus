---
name: KOReader Plugin Development
description: This skill should be used when the user asks to "create a koreader plugin", "add a menu item", "create a widget", "save settings", "koreader ui", "lua widget", "koreader api", "dispatcher action", or is working on KOReader e-reader plugin development. Provides comprehensive guidance for KOReader's Lua plugin architecture.
version: 0.1.0
---

# KOReader Plugin Development

Guidance for developing plugins for KOReader, the open-source e-book reader application. KOReader plugins are written in Lua and extend the reader with custom functionality.

## Plugin Structure

Every KOReader plugin requires two files in a `.koplugin` directory:

```
pluginname.koplugin/
├── _meta.lua    # Plugin metadata (required)
└── main.lua     # Plugin entry point (required)
```

### _meta.lua

Define plugin metadata for KOReader's plugin loader:

```lua
local _ = require("gettext")
return {
    name = "pluginname",           -- Internal identifier (lowercase, no spaces)
    fullname = _("Plugin Name"),   -- Display name (translatable)
    description = _([[Brief description of what the plugin does.]]),
}
```

### main.lua

Plugin entry point extending WidgetContainer:

```lua
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local _ = require("gettext")

local MyPlugin = WidgetContainer:extend{
    name = "pluginname",
    is_doc_only = false,  -- true if plugin only works when document is open
}

function MyPlugin:init()
    self.ui.menu:registerToMainMenu(self)
end

function MyPlugin:addToMainMenu(menu_items)
    menu_items.pluginname = {
        text = _("Plugin Name"),
        sorting_hint = "tools",
        sub_item_table = {
            -- Menu items here
        },
    }
end

return MyPlugin
```

## Core Imports

Common imports for KOReader plugins:

```lua
-- UI and widgets
local UIManager = require("ui/uimanager")
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local InfoMessage = require("ui/widget/infomessage")
local InputDialog = require("ui/widget/inputdialog")
local ButtonDialog = require("ui/widget/buttondialog")
local Menu = require("ui/widget/menu")

-- Data and settings
local DataStorage = require("datastorage")
local LuaSettings = require("luasettings")

-- Utilities
local Dispatcher = require("dispatcher")
local _ = require("gettext")
local T = require("ffi/util").template
```

## Settings Persistence

Use LuaSettings to save and load plugin data:

```lua
function MyPlugin:loadSettings()
    self.settings = LuaSettings:open(
        DataStorage:getSettingsDir() .. "/pluginname.lua"
    )
    self.data = self.settings:readSetting("data_key") or {}
end

function MyPlugin:saveSettings()
    self.settings:saveSetting("data_key", self.data)
    self.settings:flush()
end
```

Call `loadSettings()` in `init()` and `saveSettings()` when data changes.

## UI Widgets

### InfoMessage (Simple notification)

```lua
local InfoMessage = require("ui/widget/infomessage")
UIManager:show(InfoMessage:new{
    text = _("Message to display"),
    timeout = 3,  -- Auto-dismiss after 3 seconds (optional)
})
```

### InputDialog (Text input)

```lua
local InputDialog = require("ui/widget/inputdialog")
local input_dialog
input_dialog = InputDialog:new{
    title = _("Enter Value"),
    input = "default text",
    input_hint = _("Placeholder text"),
    buttons = {{
        {
            text = _("Cancel"),
            callback = function()
                UIManager:close(input_dialog)
            end,
        },
        {
            text = _("OK"),
            callback = function()
                local value = input_dialog:getInputText()
                UIManager:close(input_dialog)
                -- Process value
            end,
        },
    }},
}
UIManager:show(input_dialog)
input_dialog:onShowKeyboard()
```

### ButtonDialog (Multiple choice)

```lua
local ButtonDialog = require("ui/widget/buttondialog")
local button_dialog
button_dialog = ButtonDialog:new{
    title = _("Choose Option"),
    buttons = {
        {{
            text = _("Option 1"),
            callback = function()
                UIManager:close(button_dialog)
                -- Handle option 1
            end,
        }},
        {{
            text = _("Option 2"),
            callback = function()
                UIManager:close(button_dialog)
                -- Handle option 2
            end,
        }},
    },
}
UIManager:show(button_dialog)
```

### Menu (List selection)

```lua
local Menu = require("ui/widget/menu")
local menu
menu = Menu:new{
    title = _("Select Item"),
    item_table = {
        { text = "Item 1", callback = function() end },
        { text = "Item 2", callback = function() end },
    },
    close_callback = function()
        UIManager:close(menu)
    end,
}
UIManager:show(menu)
```

## Menu Integration

### Main Menu Structure

```lua
function MyPlugin:addToMainMenu(menu_items)
    menu_items.pluginname = {
        text = _("Plugin Name"),
        sorting_hint = "tools",  -- or "search", "main", "setting"
        sub_item_table = {
            {
                text = _("Action"),
                callback = function()
                    self:doAction()
                end,
            },
            {
                text = _("Toggle Feature"),
                checked_func = function()
                    return self.settings:isTrue("feature_enabled")
                end,
                callback = function()
                    self.settings:toggle("feature_enabled")
                end,
            },
            {
                text = _("Submenu"),
                sub_item_table = {
                    -- Nested items
                },
            },
        },
    }
end
```

### Sorting Hints

- `"main"` - Top-level menu
- `"search"` - Search section
- `"tools"` - Tools section
- `"setting"` - Settings section

## Dispatcher Actions

Register actions for gestures and keyboard shortcuts:

```lua
function MyPlugin:onDispatcherRegisterActions()
    Dispatcher:registerAction("pluginname_action", {
        category = "none",
        event = "PluginAction",
        title = _("Plugin Action"),
        general = true,  -- Available globally (not just in reader)
    })
end

function MyPlugin:onPluginAction()
    -- Handle the action
    return true
end
```

Call `self:onDispatcherRegisterActions()` in `init()`.

## Document Access

When `is_doc_only = true`, access document via `self.ui.document`:

```lua
-- Get current page
local page = self.ui.document:getCurrentPage()

-- Get total pages
local total = self.ui.document:getPageCount()

-- Get document info
local props = self.ui.document:getProps()
local title = props.title
local author = props.authors
```

## Lifecycle Methods

```lua
function MyPlugin:init()
    -- Called when plugin loads
    self:loadSettings()
    self:onDispatcherRegisterActions()
    self.ui.menu:registerToMainMenu(self)
end

function MyPlugin:onFlushSettings()
    -- Called when KOReader saves settings
    self:saveSettings()
end

function MyPlugin:onCloseDocument()
    -- Called when document closes (if is_doc_only)
    self:saveSettings()
end
```

## Event System

KOReader uses an event system for communication:

```lua
-- Send event
UIManager:broadcastEvent(Event:new("CustomEvent", data))

-- Handle event
function MyPlugin:onCustomEvent(data)
    -- Process event
    return true  -- Event handled
end
```

## Additional Resources

### Reference Files

For detailed patterns and advanced techniques:
- **`references/widgets.md`** - Complete widget reference
- **`references/patterns.md`** - Common plugin patterns

### Example Files

Working examples in `examples/`:
- **`examples/minimal-plugin/`** - Minimal plugin template

### External Resources

- KOReader GitHub: https://github.com/koreader/koreader
- Plugin Wiki: https://github.com/koreader/koreader/wiki/Plugin-system
- Lua 5.1 Reference: https://www.lua.org/manual/5.1/
