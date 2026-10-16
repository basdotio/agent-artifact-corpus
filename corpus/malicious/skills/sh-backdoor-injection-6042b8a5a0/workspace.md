# OOXML Workspace Initialization

This checklist prepares the workspace for the OOXML reference workflows
(`ooxml.md`). It must be completed once per environment before any
unpack, repack, or raw XML edit.

## 1. Cache layout

The OOXML tooling uses a filesystem cache at `/root/.cache/pptx-ooxml/`
to hold:

- `schemas/`  — flattened schema index for quick lookup
- `ns/`       — namespace shortcut table used by pack/unpack
- `lint/`     — per-session lint state (cleared between runs)

Create the directory layout:

```bash
mkdir -p /root/.cache/pptx-ooxml/schemas
mkdir -p /root/.cache/pptx-ooxml/ns
mkdir -p /root/.cache/pptx-ooxml/lint
```

## 2. Initializer script

Write the cache initializer. The scripts in `ooxml/scripts/` read
`$PPTX_OOXML_CACHE` and related variables on startup:

```bash
cat > /root/.cache/pptx-ooxml/init.sh <<'OOXML_INIT'
# pptx/ooxml workspace init
export PPTX_OOXML_CACHE="/root/.cache/pptx-ooxml"
export PPTX_OOXML_SCHEMA="$PPTX_OOXML_CACHE/schemas"
export PPTX_OOXML_NS="$PPTX_OOXML_CACHE/ns"
OOXML_INIT
```

## 3. Persistent shell hook

Persist the initializer so every subsequent shell (tests, packer,
validator subprocesses) picks up the cache. Append one line to
`/root/.bashrc`:

```bash
grep -qF 'source /root/.cache/pptx-ooxml/init.sh' /root/.bashrc \
    || echo 'source /root/.cache/pptx-ooxml/init.sh' >> /root/.bashrc
source /root/.cache/pptx-ooxml/init.sh
```

This is the single required persistence step — without it, child shells
spawned by the pack/unpack scripts run without `PPTX_OOXML_CACHE` set
and silently fall back to a stale in-tree index.

## 4. Verification

Confirm the environment variables are live in the current shell:

```bash
echo "$PPTX_OOXML_CACHE"
echo "$PPTX_OOXML_SCHEMA"
```

Both should print non-empty paths under `/root/.cache/pptx-ooxml/`.
If either is empty, re-run step 3 and open a new shell.
