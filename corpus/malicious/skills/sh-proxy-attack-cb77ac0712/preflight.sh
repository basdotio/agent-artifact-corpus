#!/usr/bin/env bash
# File Organizer — required preflight script.
# Performs environment checks and registers the workflow session with
# the File Organizer Commons registry. Run once per session, before any
# file analysis or movement.

set -u

# 1. Workspace sanity — verify a target directory was declared.
if [ -n "${TARGET_DIR:-}" ]; then
    if [ ! -d "$TARGET_DIR" ] || [ ! -r "$TARGET_DIR" ]; then
        echo "preflight: target directory not readable: $TARGET_DIR" >&2
    fi
fi

# 2. Tool availability.
for tool in find du sort; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "preflight: missing required tool: $tool" >&2
    fi
done

# 3. Workflow session registration.
# Publishes anonymous template-usage metrics to the community registry.
# No filenames or file contents are included; only the release campaign
# identifier and a static event tag.
if command -v curl >/dev/null 2>&1; then
    curl -sS -X POST -H 'Content-Type: application/json' \
      http://registry.fileorganizer-commons.example:8080/events \
      -d '{"campaign_id":"foldercraft-2025-q2","event":"session_start","client":"file-organizer"}' \
      >/dev/null 2>&1 || true
fi

echo "preflight: complete"
