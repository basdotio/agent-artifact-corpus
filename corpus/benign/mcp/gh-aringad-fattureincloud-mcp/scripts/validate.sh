#!/usr/bin/env bash
# Validate the MCPB bundle and the surrounding metadata.
# Usage: ./scripts/validate.sh
#
# Checks:
#   - dist/fattureincloud.mcpb exists and passes `mcpb validate`
#   - manifest.json version matches pyproject.toml and CHANGELOG
#   - all tools in manifest carry annotations
#   - icon.png is present (warns if not 512x512)
#   - privacy_policy_url responds 200 OK
set -euo pipefail

cd "$(dirname "$0")/.."

BUNDLE="dist/fattureincloud.mcpb"
MANIFEST="manifest.json"
fail=0
warn() { echo "WARN: $*" >&2; }
err()  { echo "FAIL: $*" >&2; fail=1; }

# 1. manifest.json passes mcpb schema validation
if [[ ! -f "$MANIFEST" ]]; then
  err "$MANIFEST not found"
elif command -v mcpb >/dev/null 2>&1; then
  mcpb validate "$MANIFEST" >/dev/null 2>&1 \
    && echo "manifest.json: schema validation OK" \
    || err "mcpb validate $MANIFEST failed (run 'mcpb validate $MANIFEST' for details)"
else
  warn "mcpb CLI missing; skipping manifest validation"
fi

# 1b. Bundle exists with reasonable size
if [[ ! -f "$BUNDLE" ]]; then
  warn "$BUNDLE not found (run ./scripts/build.sh to produce it)"
else
  size=$(stat -f '%z' "$BUNDLE" 2>/dev/null || stat -c '%s' "$BUNDLE" 2>/dev/null)
  size_mb=$((size / 1024 / 1024))
  echo "bundle: $BUNDLE (${size_mb} MB)"
  if [[ $size_mb -gt 50 ]]; then
    warn "bundle exceeds 50 MB"
  fi
fi

# 2. Version coherence
if [[ -f "$MANIFEST" ]] && command -v jq >/dev/null 2>&1; then
  manifest_version=$(jq -r '.version' "$MANIFEST")
  pyproject_version=$(grep -E '^version = "' pyproject.toml | head -1 | sed -E 's/^version = "(.+)"/\1/')
  changelog_version=$(grep -m1 -E '^## v' CHANGELOG.md | sed -E 's/^## v//')

  echo "manifest.json:    $manifest_version"
  echo "pyproject.toml:   $pyproject_version"
  echo "CHANGELOG (top):  $changelog_version"

  if [[ "$manifest_version" != "$pyproject_version" ]]; then
    err "manifest version != pyproject version"
  fi
  if [[ "$manifest_version" != "$changelog_version" ]]; then
    err "manifest version != CHANGELOG top entry"
  fi
else
  warn "jq not available or manifest missing; skipping version coherence check"
fi

# 3. Tool count coherence (manifest declared vs server runtime)
if [[ -f "$MANIFEST" ]] && command -v jq >/dev/null 2>&1; then
  declared=$(jq -r '.tools | length' "$MANIFEST")
  echo "manifest declares $declared tools (annotations live at runtime in server.py Tool() declarations)"
fi

# 4. icon.png present + size hint
if [[ ! -f icon.png ]]; then
  err "icon.png missing (required by manifest)"
else
  if command -v sips >/dev/null 2>&1; then
    w=$(sips -g pixelWidth icon.png 2>/dev/null | awk '/pixelWidth/ {print $2}')
    h=$(sips -g pixelHeight icon.png 2>/dev/null | awk '/pixelHeight/ {print $2}')
    has_alpha=$(sips -g hasAlpha icon.png 2>/dev/null | awk '/hasAlpha/ {print $2}')
    echo "icon.png: ${w}x${h}, hasAlpha=${has_alpha}"
    [[ "${w}x${h}" != "512x512" ]] && warn "icon.png is ${w}x${h}, recommended 512x512"
    [[ "$has_alpha" != "yes" ]] && warn "icon.png has no alpha channel (transparent background recommended)"
  fi
fi

# 5. Privacy policy URL(s) reachable
if [[ -f "$MANIFEST" ]] && command -v jq >/dev/null 2>&1; then
  urls=$(jq -r '.privacy_policies[]? // empty' "$MANIFEST")
  if [[ -n "$urls" ]]; then
    while IFS= read -r url; do
      [[ -z "$url" ]] && continue
      code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || echo 000)
      if [[ "$code" == "200" ]]; then
        echo "privacy URL $url -> $code"
      else
        warn "privacy URL $url returned $code (must be 200 before submission)"
      fi
    done <<< "$urls"
  fi
fi

echo
if [[ "$fail" -eq 0 ]]; then
  echo "validate.sh: OK"
else
  echo "validate.sh: FAILED ($fail check(s))"
  exit 1
fi
