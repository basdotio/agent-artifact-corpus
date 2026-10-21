#!/usr/bin/env bash
# Verify a live listing links back to your domain, and whether the link is dofollow.
#
# Usage: verify_backlink.sh <listing_url> <your_domain> [expected_substring]
#   listing_url         URL of your directory listing page
#   your_domain         e.g. example.com (no scheme)
#   expected_substring  optional extra match inside the anchor href (defaults to your_domain)
#
# Exit codes:
#   0  dofollow backlink found
#   1  link found but rel=nofollow / noopener-only nofollow variants
#   2  no link to your domain found on the page
#   3  fetch failed
#
# Output (last line): RESULT dofollow|nofollow|not_found|fetch_failed | REL <rel value or ->
#                      | ANCHOR <anchor html, truncated>

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <listing_url> <your_domain> [expected_substring]" >&2
  exit 3
fi

LISTING_URL="$1"
YOUR_DOMAIN="$2"
MATCH="${3:-$2}"

HTML="$(curl -sL --max-time 25 --compressed \
  -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36' \
  -H 'Accept: text/html,application/xhtml+xml' \
  "$LISTING_URL" 2>/dev/null)" || {
  echo "RESULT fetch_failed | REL - | ANCHOR -"
  exit 3
}

if [[ -z "$HTML" ]]; then
  echo "RESULT fetch_failed | REL - | ANCHOR -"
  exit 3
fi

# Extract anchor tags whose href mentions the target domain.
ANCHORS="$(printf '%s' "$HTML" | tr '\n' ' ' | grep -Eio '<a [^>]*href="[^"]*'"$MATCH"'[^"]*"[^>]*>' || true)"

if [[ -z "$ANCHORS" ]]; then
  # Try single-quoted hrefs too.
  ANCHORS="$(printf '%s' "$HTML" | tr '\n' ' ' | grep -Eio "<a [^>]*href='$MATCH[^']*'[^>]*>" || true)"
fi

if [[ -z "$ANCHORS" ]]; then
  echo "RESULT not_found | REL - | ANCHOR -"
  exit 2
fi

# Use the first matching anchor.
FIRST="$(printf '%s\n' "$ANCHORS" | head -n1)"

REL="$(printf '%s' "$FIRST" | grep -Eio 'rel="[^"]*"' | head -n1 | sed 's/^rel="//; s/"$//' || true)"
REL="${REL:-}"

# Strip common safe rel tokens; if anything follow-relevant remains only as
# noopener/noreferrer without nofollow, treat as dofollow.
RESULT="dofollow"
if printf '%s' "$REL" | grep -Eiq '(^| )nofollow( |$)'; then
  RESULT="nofollow"
fi

SHORT_ANCHOR="$(printf '%s' "$FIRST" | cut -c1-300)"
echo "RESULT $RESULT | REL ${REL:-->} | ANCHOR $SHORT_ANCHOR"

case "$RESULT" in
  dofollow) exit 0 ;;
  nofollow) exit 1 ;;
  *) exit 2 ;;
esac
