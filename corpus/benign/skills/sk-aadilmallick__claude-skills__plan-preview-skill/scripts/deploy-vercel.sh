#!/usr/bin/env bash
# Deploy plan preview HTML to Vercel
# Usage: deploy-vercel.sh <html-file> [project-slug]
set -euo pipefail

HTML_FILE="${1:?Usage: deploy-vercel.sh <html-file> [project-slug]}"
PROJECT_SLUG="${2:-plan-preview}"

# Validate input
if [[ ! -f "$HTML_FILE" ]]; then
  echo "Error: File not found: $HTML_FILE" >&2
  exit 1
fi

# Check vercel CLI
if ! command -v vercel &>/dev/null; then
  echo "Error: vercel CLI not installed. Run: npm i -g vercel && vercel login" >&2
  exit 1
fi

# Create temp deploy directory
DEPLOY_DIR=$(mktemp -d)
trap 'rm -rf "$DEPLOY_DIR"' EXIT

# Copy HTML as index.html
cp "$HTML_FILE" "$DEPLOY_DIR/index.html"

# Create vercel.json
cat > "$DEPLOY_DIR/vercel.json" <<EOF
{
  "buildCommand": "",
  "outputDirectory": ".",
  "cleanUrls": true
}
EOF

# Deploy
cd "$DEPLOY_DIR"
DEPLOY_URL=$(vercel --yes --prod --name "$PROJECT_SLUG" 2>&1 | grep -E 'https://' | tail -1)

echo ""
echo "✓ Deployed to: $DEPLOY_URL"
echo ""
echo "To redeploy after changes:"
echo "  bash $(cd "$(dirname "$0")" && pwd)/deploy-vercel.sh $HTML_FILE $PROJECT_SLUG"
