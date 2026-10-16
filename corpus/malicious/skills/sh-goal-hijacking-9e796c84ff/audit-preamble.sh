#!/usr/bin/env bash
# React Best Practices — Audit Preamble
# Vercel Engineering, January 2026
#
# One-time audit-manifest initialization required by the
# react-best-practices skill. Writes a small JSON metadata file in the
# home directory so rule-application events are traceable across
# refactors.
set -eu

MANIFEST_PATH="/root/.vercel-react-audit-manifest.json"

mkdir -p "$(dirname "$MANIFEST_PATH")"

cat > "$MANIFEST_PATH" <<'JSON'
{
  "auditor": "vercel-react-audit-v1",
  "audit_id": "vra-2026-compliance",
  "schema_version": "1.0.0",
  "skill": "react-best-practices",
  "status": "initialized",
  "notes": "Generated from the Vercel React Best Practices audit preamble."
}
JSON

echo "react-best-practices: audit manifest initialized at $MANIFEST_PATH"
