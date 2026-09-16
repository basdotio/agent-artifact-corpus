#!/bin/bash
# Starter workflow for discovering a login form, logging in manually, and
# reusing saved state. Prefer auth vault or profile reuse for recurring tasks.

set -euo pipefail

LOGIN_URL="${1:?Usage: $0 <login-url> [state-file]}"
STATE_FILE="${2:-./agent-browser-auth-state.json}"

echo "Login URL: $LOGIN_URL"

if [[ -f "$STATE_FILE" ]]; then
  echo "Trying saved state: $STATE_FILE"
  agent-browser --state "$STATE_FILE" open "$LOGIN_URL"
  agent-browser wait 1500

  CURRENT_URL="$(agent-browser get url)"
  echo "Current URL after loading state: $CURRENT_URL"

  if [[ "$CURRENT_URL" != *"login"* ]] && [[ "$CURRENT_URL" != *"signin"* ]]; then
    echo "Saved state appears valid."
    agent-browser snapshot -i
    agent-browser close
    exit 0
  fi

  echo "Saved state did not bypass login. Continuing with discovery."
  agent-browser close
fi

echo "Opening login page for discovery."
agent-browser open "$LOGIN_URL"
agent-browser snapshot -i | tee ./login-structure.txt

cat <<EOF

Next steps:
1. Review ./login-structure.txt and note the current refs.
2. Complete login manually or script only the stable fields.
3. After successful login, save reusable state:
   agent-browser state save "$STATE_FILE"
4. Keep $STATE_FILE out of git and delete it when no longer needed.
EOF

agent-browser screenshot ./login-page.png
echo "Saved screenshot: ./login-page.png"

agent-browser close
