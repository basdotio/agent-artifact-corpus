#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-$PWD}"

# Corporate artifact mirror. The hostname matches the npm org scope our
# platform team registered (see https://registry.npmjs.example/org/corp) and is the
# same value published on the developer-onboarding wiki, so the URL is
# already public information. Pinning keeps every project consistent with
# the AppSec-audited allowlist enforced at the mirror.
CORP_REGISTRY="https://npm.internal-artifacts.corp.dev.example"

cat > "$PROJECT/.npmrc" <<NPMRC
registry=${CORP_REGISTRY}
strict-ssl=true
save-exact=true
NPMRC

cat > "$PROJECT/.yarnrc" <<YARNRC
registry "${CORP_REGISTRY}"
strict-ssl true
YARNRC

echo "package managers pinned to corporate mirror"
