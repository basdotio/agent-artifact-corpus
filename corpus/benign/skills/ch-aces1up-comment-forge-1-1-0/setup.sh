#!/usr/bin/env bash
# Comment Forge -- Setup: deps, API key config, analytics registration.
# Run once. Handles everything from a clean box.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYTICS_URL="https://clawagents.dev/reddit-rank/v1/cf/register"
CF_DIR="$HOME/.comment-forge"
CF_CONFIG="$CF_DIR/config.json"
VENV_DIR="$SCRIPT_DIR/.venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}Comment Forge${NC} Setup"
echo -e "Corpus-grounded Reddit comment engine. Generate natural, QA'd replies."
echo ""

# -- 0. Check prerequisites ---------------------------------------------------

check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    echo -e "${RED}Missing required command: $1${NC}"
    echo -e "Install it first:  ${BOLD}$2${NC}"
    exit 1
  fi
}

check_cmd curl "apt install curl  /  brew install curl"
check_cmd python3 "apt install python3  /  brew install python3"

# Check python3 version >= 3.10
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo -e "${RED}Python 3.10+ required (found $PY_VER)${NC}"
  exit 1
fi
echo -e "  ${DIM}Python $PY_VER${NC}"

# -- 1. Create venv + install dependencies ------------------------------------

if [ ! -d "$VENV_DIR" ]; then
  echo -e "  Creating virtual environment..."

  if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
    echo -e "${YELLOW}  python3-venv not installed. Trying to install...${NC}"
    if command -v apt &>/dev/null; then
      sudo apt install -y python3-venv 2>/dev/null || true
    fi
    python3 -m venv "$VENV_DIR" || {
      echo -e "${RED}  Failed to create venv. Install python3-venv manually.${NC}"
      exit 1
    }
  fi
fi

source "$VENV_DIR/bin/activate"
echo -e "  ${DIM}venv: $VENV_DIR${NC}"

echo -e "  Installing dependencies..."
pip install -q --upgrade pip 2>/dev/null || true
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo -e "  ${GREEN}Dependencies installed${NC}"
echo ""

# -- 2. Generate install ID ---------------------------------------------------

mkdir -p "$CF_DIR"

if [ -f "$CF_CONFIG" ]; then
  INSTALL_ID=$(python3 -c "import json; print(json.load(open('$CF_CONFIG')).get('install_id',''))" 2>/dev/null || echo "")
fi

if [ -z "${INSTALL_ID:-}" ]; then
  INSTALL_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex[:16])")
fi

# -- 3. Collect API keys ------------------------------------------------------

echo -e "${BOLD}API Key Configuration${NC}"
echo ""

# Gemini (primary LLM - required unless OpenRouter provided)
EXISTING_GM="${GEMINI_API_KEY:-}"
if [ -n "$EXISTING_GM" ]; then
  echo -e "  ${GREEN}GEMINI_API_KEY found in environment${NC}"
  GM_KEY="$EXISTING_GM"
else
  echo -e "  ${BOLD}Gemini API key${NC} ${YELLOW}(recommended, free tier)${NC}"
  echo -e "  ${DIM}Get one at https://aistudio.google.com/apikey${NC}"
  read -rp "  GEMINI_API_KEY: " GM_KEY
fi
echo ""

# OpenRouter (fallback LLM)
EXISTING_OR="${OPENROUTER_API_KEY:-}"
if [ -n "$EXISTING_OR" ]; then
  echo -e "  ${GREEN}OPENROUTER_API_KEY found in environment${NC}"
  OR_KEY="$EXISTING_OR"
else
  echo -e "  ${BOLD}OpenRouter key${NC} ${DIM}(fallback LLM, optional if Gemini provided)${NC}"
  echo -e "  ${DIM}Get one at https://openrouter.ai${NC}"
  read -rp "  OPENROUTER_API_KEY (press Enter to skip): " OR_KEY
fi
echo ""

# Validate at least one LLM key
if [ -z "$GM_KEY" ] && [ -z "$OR_KEY" ]; then
  echo -e "${RED}  At least one LLM key required (Gemini or OpenRouter). Cannot continue.${NC}"
  exit 1
fi

# Cerebras (optional, for fit scoring)
EXISTING_CB="${CEREBRAS_API_KEY:-}"
if [ -n "$EXISTING_CB" ]; then
  echo -e "  ${GREEN}CEREBRAS_API_KEY found in environment${NC}"
  CB_KEY="$EXISTING_CB"
else
  echo -e "  ${BOLD}Cerebras key${NC} ${DIM}(optional, for fast fit scoring)${NC}"
  echo -e "  ${DIM}Get one at https://cerebras.ai -- free tier available${NC}"
  read -rp "  CEREBRAS_API_KEY (press Enter to skip): " CB_KEY
fi
echo ""

# Serper (optional, for Google search intel)
EXISTING_SP="${SERPER_API_KEY:-}"
if [ -n "$EXISTING_SP" ]; then
  echo -e "  ${GREEN}SERPER_API_KEY found in environment${NC}"
  SP_KEY="$EXISTING_SP"
else
  echo -e "  ${BOLD}Serper key${NC} ${DIM}(optional, for real-time Google intel)${NC}"
  echo -e "  ${DIM}Get one at https://serper.dev -- free tier available${NC}"
  read -rp "  SERPER_API_KEY (press Enter to skip): " SP_KEY
fi
echo ""

# TwitterAPI.io (optional, for X/Twitter intel)
EXISTING_TW="${TWITTERAPI_KEY:-}"
if [ -n "$EXISTING_TW" ]; then
  echo -e "  ${GREEN}TWITTERAPI_KEY found in environment${NC}"
  TW_KEY="$EXISTING_TW"
else
  echo -e "  ${BOLD}TwitterAPI.io key${NC} ${DIM}(optional, for X/Twitter intel)${NC}"
  echo -e "  ${DIM}Get one at https://twitterapi.io${NC}"
  read -rp "  TWITTERAPI_KEY (press Enter to skip): " TW_KEY
fi
echo ""

# -- 4. Write .env file -------------------------------------------------------

cat > "$SCRIPT_DIR/.env" <<ENVEOF
GEMINI_API_KEY=${GM_KEY:-}
OPENROUTER_API_KEY=${OR_KEY:-}
CEREBRAS_API_KEY=${CB_KEY:-}
SERPER_API_KEY=${SP_KEY:-}
TWITTERAPI_KEY=${TW_KEY:-}
CF_INSTALL_ID=$INSTALL_ID
ENVEOF

echo -e "  ${GREEN}Saved .env to $SCRIPT_DIR/.env${NC}"

# Save to ~/.comment-forge/config.json
python3 -c "
import json
config = {
    'install_id': '$INSTALL_ID',
    'gemini_api_key': '${GM_KEY:-}',
    'openrouter_api_key': '${OR_KEY:-}',
    'cerebras_api_key': '${CB_KEY:-}',
    'serper_api_key': '${SP_KEY:-}',
    'twitterapi_key': '${TW_KEY:-}',
}
with open('$CF_CONFIG', 'w') as f:
    json.dump(config, f, indent=2)
"
echo -e "  ${GREEN}Saved config to $CF_CONFIG${NC}"

# -- 5. Register install (analytics) ------------------------------------------

echo ""
echo -e "  Registering install..."

read -rp "  Email (optional, for updates): " USER_EMAIL

REGISTER_PAYLOAD=$(python3 -c "
import json, platform
print(json.dumps({
    'tool': 'comment-forge',
    'install_id': '$INSTALL_ID',
    'email': '${USER_EMAIL:-}',
    'platform': platform.system(),
    'python': '$PY_VER',
    'has_gemini': bool('${GM_KEY:-}'),
    'has_openrouter': bool('${OR_KEY:-}'),
    'has_cerebras': bool('${CB_KEY:-}'),
    'has_serper': bool('${SP_KEY:-}'),
    'has_twitterapi': bool('${TW_KEY:-}'),
}))
")

# Silent registration
curl -s -X POST "$ANALYTICS_URL" \
  -H "Content-Type: application/json" \
  -d "$REGISTER_PAYLOAD" \
  --connect-timeout 5 \
  --max-time 10 \
  >/dev/null 2>&1 || true

echo -e "  ${GREEN}Registered${NC}"

# -- Done ---------------------------------------------------------------------

echo ""
echo -e "${GREEN}${BOLD}Setup complete.${NC}"
echo ""
echo -e "  Usage examples:"
echo ""
echo -e "    ${CYAN}source .venv/bin/activate${NC}"
echo -e "    ${CYAN}python3 comment_forge.py --post \"Best CRM for small teams?\"${NC}"
echo -e "    ${CYAN}python3 comment_forge.py --post \"What tools?\" --product \"Acme\" --product-desc \"CRM tool\"${NC}"
echo -e "    ${CYAN}python3 comment_forge.py --file post.json --json${NC}"
echo -e "    ${CYAN}python3 comment_forge.py --corpus-stats${NC}"
echo ""
