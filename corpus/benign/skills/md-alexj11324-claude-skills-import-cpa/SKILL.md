---
name: Import CPA Credentials
description: Two modes — (1) import credential JSON files into CLIProxyAPI/Quotio's auth dir, (2) add/update a custom provider (URL + key + models) in the config. Accepts file paths or "url=... key=... model=..." style args.
when_to_use: when user wants to import credential JSON files, or add/update an API provider with a URL, key, and model in CLIProxyAPI or Quotio
version: 1.3.0
---

# Import CPA Credentials

## Overview

Two modes depending on what the user provides:

**Mode A — Add/update provider**: triggered when the user provides a URL + key (+ optional model/alias).
**Mode B — Import credential files**: triggered when the user provides a file or folder path.

Paths are detected dynamically at runtime (Step 0).

---

## Step 0 — Detect Active Paths (always run first)

Run the following to determine the active config and auth directory:

```bash
# Check if gitstore is active (GITSTORE_LOCAL_PATH set via .env)
GITSTORE_DIR=$(find ~/Library/Application\ Support/Quotio/proxy -name ".env" 2>/dev/null | head -1 | xargs grep -s GITSTORE_LOCAL_PATH | cut -d= -f2)

if [ -n "$GITSTORE_DIR" ] && [ -d "$GITSTORE_DIR/gitstore/auths" ]; then
  echo "AUTH_DIR=$GITSTORE_DIR/gitstore/auths"
  echo "CONFIG=$GITSTORE_DIR/gitstore/config/config.yaml"
else
  echo "AUTH_DIR=~/.cli-proxy-api"
  echo "CONFIG=$(find ~/Library/Application\ Support/Quotio -name config.yaml | head -1)"
fi
```

Use the detected `AUTH_DIR` and `CONFIG` for all subsequent steps.

---

## Mode A — Add/Update Provider

### Triggered when

User provides a URL + key, e.g.:
- "帮我加个提供商，url=xxx key=yyy model=zzz"
- "更新 huanAPI 的 key"
- Provides a base URL + API key (with or without model info)

### Steps

1. **Run Step 0** to get `CONFIG` path.

2. **Parse arguments** from user message:
   - `url` — base URL (e.g. `https://api.example.com/v1`)
   - `key` — API key
   - `model` — upstream model name (optional)
   - `alias` — client-visible alias (optional, default = same as model)
   - `name` — provider name (optional, infer from URL hostname if omitted)
   - `type` — `openai` (default) or `claude`

3. **Read config** using the Read tool on the detected `CONFIG` path.

4. **Determine action**:
   - If a provider with the same `name` or `base-url` already exists → **update** its `api-key` and/or `models`
   - Otherwise → **append** a new entry

5. **For `openai` type**, add/update under `openai-compatibility`:
   ```yaml
   - name: "<name>"
     base-url: "<url>"
     api-key-entries:
       - api-key: "<key>"
     models:
       - name: "<model>"
         alias: "<alias>"
   ```

6. **For `claude` type**, add/update under `claude-api-key`:
   ```yaml
   - api-key: "<key>"
     base-url: "<url>"
     models:
       - name: "<model>"
         alias: "<alias>"
   ```

7. **Write config** using the Edit tool (preserve all existing content, only change the relevant section).

8. **Report**: "已添加/更新提供商 `<name>`，模型 `<alias>`，Quotio 将自动热重载。"

---

## Mode B — Import Credential Files

### Triggered when

User provides a file path or folder path.

### Steps

1. **Run Step 0** to get `AUTH_DIR`.

2. **Parse argument** — `/import-cpa [path]` where `[path]` is:
   - A directory (import all `.json` files inside)
   - A single `.json` file
   - Multiple space-separated paths
   - If omitted: ask "请提供 JSON 文件或文件夹路径"

3. **Validate files** — for each `.json`:
   - Check `type` field — valid: `codex`, `claude`, `gemini`, `qwen`, `antigravity`, `iflow`, `kimi`
   - Check `expired` field — warn if already past today's date
   - Skip unrecognized files with a warning

4. **Copy to auth dir**:
   ```bash
   cp <files> <AUTH_DIR>/
   ```

5. **Report**:
   - Total imported, breakdown by type
   - Skipped files with reasons
   - Current total: `ls <AUTH_DIR>/*.json | wc -l`
   - Reminder: CLIProxyAPI/Quotio auto-reloads on file changes
