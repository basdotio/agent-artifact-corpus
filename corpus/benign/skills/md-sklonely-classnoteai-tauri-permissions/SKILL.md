---
name: Tauri v2 Permissions Guide
description: Comprehensive guide for Tauri v2 permissions, capabilities, and macOS-specific requirements
---

# Tauri v2 Permissions Guide

This skill covers the Tauri v2 permissions and capabilities system, including plugin permissions, macOS-specific requirements, and common pitfalls.

## Overview

Tauri v2 uses a **Capabilities** system to control what the frontend (WebView) can access. Each capability grants or denies specific permissions to windows.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tauri v2 Permission Flow                     │
├─────────────────────────────────────────────────────────────────┤
│   Frontend (JS)  ──▶  Tauri IPC  ──▶  Rust Backend              │
│        │                  │                 │                   │
│        └── Capabilities ──┴── Plugins ──────┘                   │
│                                                                 │
│   src-tauri/                                                    │
│   ├── capabilities/       ← Permission definitions              │
│   │   └── default.json                                          │
│   ├── Cargo.toml          ← Plugin dependencies                 │
│   ├── src/lib.rs          ← Plugin registration                 │
│   ├── Info.plist          ← macOS entitlements                  │
│   └── tauri.conf.json     ← App configuration                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Capabilities Configuration

### File Location
Capabilities are defined in `src-tauri/capabilities/default.json` (or additional files).

### Basic Structure

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "plugin-name:default",
    {
      "identifier": "plugin-name:specific-permission",
      "allow": [...],
      "deny": [...]
    }
  ]
}
```

---

## Common Plugin Permissions

### HTTP Plugin (`plugin-http`)

**Cargo.toml:**
```toml
tauri-plugin-http = "2"
```

**package.json:**
```json
"@tauri-apps/plugin-http": "^2.x"
```

**lib.rs registration:**
```rust
.plugin(tauri_plugin_http::init())
```

**Capabilities:**
```json
{
  "permissions": [
    "http:default",
    {
      "identifier": "http:allow-fetch",
      "allow": [
        { "url": "http://**" },
        { "url": "https://**" }
      ]
    }
  ]
}
```

> [!WARNING]
> `http:default` alone does NOT allow arbitrary URLs. You MUST specify `http:allow-fetch` with URL patterns.

**URL Patterns:**
| Pattern | Matches |
|:--|:--|
| `http://**` | All HTTP URLs |
| `https://**` | All HTTPS URLs |
| `http://localhost:*/**` | localhost on any port |
| `http://192.168.*:*/**` | Local network (192.168.x.x) |
| `https://api.example.com/**` | Specific domain |

---

### File System Plugin (`plugin-fs`)

**Capabilities:**
```json
{
  "permissions": [
    "fs:default",
    "fs:allow-appdata-read-recursive",
    {
      "identifier": "fs:allow-read",
      "options": {
        "scope": [
          "$APP_DATA/**",
          "$HOME/Documents/**"
        ]
      }
    },
    {
      "identifier": "fs:allow-write",
      "options": {
        "scope": ["$APP_DATA/**"]
      }
    }
  ]
}
```

**Scope Variables:**
| Variable | Path |
|:--|:--|
| `$APP_DATA` | App data directory |
| `$HOME` | User home directory |
| `$TEMP` | Temp directory |
| `$DOWNLOAD` | Downloads folder |

---

### Updater Plugin (`plugin-updater`)

**Capabilities:**
```json
{
  "permissions": ["updater:default"]
}
```

**tauri.conf.json:**
```json
{
  "plugins": {
    "updater": {
      "pubkey": "YOUR_PUBLIC_KEY",
      "endpoints": [
        "https://github.com/user/repo/releases/latest/download/latest.json"
      ]
    }
  }
}
```

---

### Other Common Plugins

| Plugin | Permission | Description |
|:--|:--|:--|
| `plugin-dialog` | `dialog:default` | Native dialogs (open/save) |
| `plugin-opener` | `opener:default` | Open URLs/files externally |
| `plugin-process` | `process:default` | Exit/relaunch app |
| `plugin-notification` | `notification:default` | System notifications |
| `plugin-clipboard` | `clipboard:default` | Clipboard access |
| `plugin-shell` | `shell:default` | Execute shell commands |

---

## macOS-Specific Requirements

### Info.plist

Located at `src-tauri/Info.plist`. Tauri merges this with its generated plist.

#### App Transport Security (ATS)

> [!CAUTION]
> macOS blocks HTTP connections by default. You MUST add this to allow non-HTTPS requests.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
        <key>NSAllowsLocalNetworking</key>
        <true/>
    </dict>
</dict>
</plist>
```

#### Common Usage Descriptions

```xml
<dict>
    <!-- Microphone access -->
    <key>NSMicrophoneUsageDescription</key>
    <string>App needs microphone to record audio.</string>
    
    <!-- Camera access -->
    <key>NSCameraUsageDescription</key>
    <string>App needs camera for video calls.</string>
    
    <!-- Location access -->
    <key>NSLocationUsageDescription</key>
    <string>App needs location for local services.</string>
    
    <!-- Contacts access -->
    <key>NSContactsUsageDescription</key>
    <string>App needs contacts for sharing.</string>
    
    <!-- App Transport Security -->
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
```

---

## Rust Backend Configuration

### Plugin Registration (lib.rs)

```rust
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        // ... other plugins
        .invoke_handler(tauri::generate_handler![...])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Enabling DevTools in Release Builds

**Cargo.toml:**
```toml
tauri = { version = "2", features = ["devtools"] }
```

**lib.rs:**
```rust
.setup(|app| {
    use tauri::Manager;
    if let Some(window) = app.get_webview_window("main") {
        window.open_devtools();
    }
    Ok(())
})
```

---

## Troubleshooting Checklist

### "url not allowed on the configured scope"
1. ✅ Check `capabilities/default.json` has `http:allow-fetch` with correct URL pattern
2. ✅ Verify URL pattern uses `**` wildcard correctly
3. ✅ Rebuild the app after changing capabilities

### "App Transport Security policy requires secure connection"
1. ✅ Add `NSAppTransportSecurity` to `Info.plist`
2. ✅ Set `NSAllowsArbitraryLoads` to `true`
3. ✅ Rebuild the app (plist changes require rebuild)

### Plugin not working
1. ✅ Verify plugin in `Cargo.toml` (Rust)
2. ✅ Verify plugin in `package.json` (JS)
3. ✅ Verify `.plugin(...)` call in `lib.rs`
4. ✅ Verify permission in `capabilities/default.json`

### DevTools not opening in release
1. ✅ Add `"devtools"` to Tauri features in `Cargo.toml`
2. ✅ Call `window.open_devtools()` in setup hook
3. ✅ Remove `#[cfg(debug_assertions)]` guard if present

---

## Quick Reference: New Plugin Checklist

When adding a new Tauri plugin:

1. **Cargo.toml** - Add Rust dependency
   ```toml
   tauri-plugin-NAME = "2"
   ```

2. **package.json** - Add JS dependency
   ```json
   "@tauri-apps/plugin-NAME": "^2.x"
   ```

3. **lib.rs** - Register plugin
   ```rust
   .plugin(tauri_plugin_NAME::init())
   ```

4. **capabilities/default.json** - Add permission
   ```json
   "NAME:default"
   ```

5. **Info.plist** (if macOS-specific permissions needed)
   ```xml
   <key>NSXxxUsageDescription</key>
   <string>Reason...</string>
   ```

6. **Rebuild** - `npm run tauri build` or restart dev server

---

## References

- [Tauri v2 Capabilities Documentation](https://v2.tauri.app/develop/capabilities/)
- [Tauri v2 Plugins Reference](https://v2.tauri.app/develop/plugins/)
- [Apple Info.plist Reference](https://developer.apple.com/documentation/bundleresources/information_property_list)
