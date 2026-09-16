#!/usr/bin/env bash
# Kyverno version lookup from Artifact Hub
# Filters to stable releases only (no rc/beta/alpha)

set -euo pipefail

API_URL="https://artifacthub.io/api/v1/packages/helm/kyverno/kyverno"
LIMIT=""
JSON_OUTPUT=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Query Kyverno Helm chart versions from Artifact Hub.
Shows only stable releases (major.minor.patch), excludes RCs.

Options:
    --json          Output raw JSON instead of table
    --limit N       Show only the latest N releases
    --help          Show this help message

Examples:
    $(basename "$0")              # Show all stable releases
    $(basename "$0") --limit 10   # Show latest 10 releases
    $(basename "$0") --json       # Output as JSON
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            ;;
    esac
done

# Fetch and filter data
DATA=$(curl -sf "$API_URL")

if [[ -z "$DATA" ]]; then
    echo "Error: Failed to fetch data from Artifact Hub" >&2
    exit 1
fi

# Build jq filter for stable versions only (no rc/beta/alpha)
JQ_FILTER='[.available_versions[] | select(.version | test("^[0-9]+\\.[0-9]+\\.[0-9]+$"))] | sort_by(.ts) | reverse'

if [[ -n "$LIMIT" ]]; then
    JQ_FILTER="$JQ_FILTER | .[0:$LIMIT]"
fi

FILTERED=$(echo "$DATA" | jq "$JQ_FILTER")

if [[ "$JSON_OUTPUT" == "true" ]]; then
    echo "$FILTERED" | jq .
else
    # Table output
    echo "CHART_VERSION  APP_VERSION  RELEASE_DATE"
    echo "-------------  -----------  ------------"
    echo "$FILTERED" | jq -r '.[] | [.version, .app_version, (.ts | strftime("%Y-%m-%d"))] | @tsv' | \
        column -t -s $'\t'
fi
