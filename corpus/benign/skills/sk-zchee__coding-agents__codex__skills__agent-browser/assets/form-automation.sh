#!/bin/bash
# Starter workflow for form discovery, fill, submit, and evidence capture.
# Update refs and any waits to match the target form before using this on a
# real site.

set -euo pipefail

FORM_URL="${1:?Usage: $0 <form-url> [evidence-dir]}"
EVIDENCE_DIR="${2:-./agent-browser-form-output}"

mkdir -p "$EVIDENCE_DIR"

echo "Opening form: $FORM_URL"
agent-browser open "$FORM_URL"

echo
echo "Form structure:"
agent-browser snapshot -i | tee "$EVIDENCE_DIR/form-structure.txt"

cat <<'EOF'

Next steps:
1. Identify the current refs from form-structure.txt.
2. Replace the example commands below with the real refs and values.
3. Prefer wait --text, wait --url, or wait <ref> over broad network-idle waits.
EOF

# Example submit block. Customize before use.
# agent-browser fill @e1 "Test User"
# agent-browser fill @e2 "test@example.com"
# agent-browser click @e3
#
# agent-browser wait --url "**/success"

echo
echo "Current URL:"
agent-browser get url | tee "$EVIDENCE_DIR/current-url.txt"

agent-browser screenshot "$EVIDENCE_DIR/form-current.png"
echo "Saved screenshot: $EVIDENCE_DIR/form-current.png"

agent-browser close
