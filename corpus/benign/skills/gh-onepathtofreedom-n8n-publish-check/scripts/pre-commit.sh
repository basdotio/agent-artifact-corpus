#!/usr/bin/env bash
# Git pre-commit hook: block commits that contain n8n workflow JSON with sensitive data.
# Install:  cp pre-commit.sh /path/to/repo/.git/hooks/pre-commit && chmod +x /path/to/repo/.git/hooks/pre-commit
# Override scanner location with:  export N8N_PUBLISH_CHECK=/path/to/scan.py
# Bypass once (only if you reviewed the report):  git commit --no-verify

SCAN="${N8N_PUBLISH_CHECK:-$HOME/.claude/skills/n8n-publish-check/scripts/scan.py}"
set -o pipefail
[ -f "$SCAN" ] || { echo "n8n-publish-check: scanner not found at $SCAN (set N8N_PUBLISH_CHECK)"; exit 1; }

# Scan the STAGED content, not the working copy.
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
status=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  out="$tmp/$(echo "$f" | tr '/' '_')"
  git show ":$f" > "$out" 2>/dev/null || continue
  if ! python3 "$SCAN" --only-workflows --fail-on medium "$out" | sed "s#$out#$f#"; then
    status=1
  fi
done < <(git diff --cached --name-only --diff-filter=ACM | grep -i '\.json$')

if [ "$status" -ne 0 ]; then
  echo
  echo "Commit blocked: sensitive data in n8n workflow JSON (see above)."
  echo "Fix with:  python3 $SCAN <file> --sanitize <file>.public.json"
fi
exit "$status"
