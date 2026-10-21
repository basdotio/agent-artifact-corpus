#!/usr/bin/env bash
# Smoke tests: run from anywhere. Exits non-zero on the first failed check.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCAN="$ROOT/scripts/scan.py"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cp "$ROOT/examples/n8n-publish-check.config.example.json" .n8n-publish-check.json
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1 (expected $3, got $2)"; fail=1; fi; }

python3 "$SCAN" "$ROOT/examples/dirty-workflow.json" >/dev/null; check "dirty workflow -> exit 1" "$?" 1
python3 "$SCAN" "$ROOT/examples/clean-workflow.json" >/dev/null; check "clean workflow -> exit 0" "$?" 0

python3 "$SCAN" "$ROOT/examples/dirty-workflow.json" --sanitize "$tmp/d.public.json" >/dev/null
python3 "$SCAN" "$tmp/d.public.json" >/dev/null; check "sanitized copy -> exit 0" "$?" 0

echo '{ not json' > bad.json
python3 "$SCAN" bad.json >/dev/null; check "invalid JSON -> exit 2" "$?" 2

# raw secrets must never appear in the report
out="$(python3 "$SCAN" "$ROOT/examples/dirty-workflow.json")"
if echo "$out" | grep -q -e 'SUPERSECRETKEY12345' -e 'abcdefghijklmnop1234567890' -e 'DE89 3704'; then
  echo "FAIL report leaks raw values"; fail=1
else
  echo "ok   report masks values"
fi
exit "$fail"
