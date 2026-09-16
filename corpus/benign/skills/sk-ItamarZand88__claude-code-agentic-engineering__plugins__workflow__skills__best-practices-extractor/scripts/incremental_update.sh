#!/bin/bash
# Incremental PR comment update - only fetch new PRs since last update
# Usage: ./incremental_update.sh OWNER REPO_NAME
# Example: ./incremental_update.sh earlyai backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
STATE_FILE="${SKILL_DIR}/.state.json"

# Output to .claude/pr-review-comments/
OUTPUT_DIR=".claude/pr-review-comments"
mkdir -p "$OUTPUT_DIR"

OWNER="${1:?Usage: $0 OWNER REPO_NAME}"
REPO="${2:?Usage: $0 OWNER REPO_NAME}"
REPO_KEY="${OWNER}/${REPO}"

# Find jq
find_jq() {
    local jq_locations=(
        "jq"
        "/usr/bin/jq"
        "/usr/local/bin/jq"
        "/opt/homebrew/bin/jq"
        "/c/Users/ItamarZand/bin/jq.exe"
        "C:/ProgramData/chocolatey/bin/jq.exe"
    )

    for location in "${jq_locations[@]}"; do
        if command -v "$location" &> /dev/null 2>&1; then
            echo "$location"
            return 0
        fi
    done

    echo "Error: jq not found. Please install jq first." >&2
    return 1
}

JQ_CMD=$(find_jq) || exit 1

echo "╔════════════════════════════════════════╗"
echo "║  Incremental PR Comment Update         ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Repository: ${REPO_KEY}"
echo ""

# Get last update timestamp
get_last_update() {
    if [ -f "$STATE_FILE" ]; then
        "$JQ_CMD" -r ".repos[\"$REPO_KEY\"].last_update // \"\"" "$STATE_FILE"
    else
        echo ""
    fi
}

# Save update timestamp
save_update_timestamp() {
    local timestamp="$1"
    local pr_count="$2"
    local comment_count="$3"
    local temp_file=$(mktemp)

    if [ -f "$STATE_FILE" ]; then
        "$JQ_CMD" \
            --arg repo "$REPO_KEY" \
            --arg timestamp "$timestamp" \
            --argjson pr_count "$pr_count" \
            --argjson comment_count "$comment_count" \
            '.repos[$repo] = {
                last_update: $timestamp,
                total_prs_processed: (.repos[$repo].total_prs_processed // 0) + $pr_count,
                total_comments_collected: (.repos[$repo].total_comments_collected // 0) + $comment_count,
                update_count: (.repos[$repo].update_count // 0) + 1
            }' "$STATE_FILE" > "$temp_file"
    else
        "$JQ_CMD" -n \
            --arg repo "$REPO_KEY" \
            --arg timestamp "$timestamp" \
            --argjson pr_count "$pr_count" \
            --argjson comment_count "$comment_count" \
            '{
                version: "1.0.0",
                repos: {
                    ($repo): {
                        last_update: $timestamp,
                        total_prs_processed: $pr_count,
                        total_comments_collected: $comment_count,
                        update_count: 1
                    }
                },
                metadata: {
                    created_at: (now | todate),
                    description: "State tracking for incremental PR comment updates"
                }
            }' > "$temp_file"
    fi

    mv "$temp_file" "$STATE_FILE"
}

LAST_UPDATE=$(get_last_update)
CURRENT_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ -z "$LAST_UPDATE" ]; then
    echo "🆕 No previous update found for this repository"
    echo "   Running FULL extraction..."
    echo ""

    # Run full extraction
    bash "${SCRIPT_DIR}/extract_pr_comments.sh" "$REPO"

    # Count results
    OUTPUT="${OUTPUT_DIR}/${REPO}_inline_comments.ndjson"
    if [ -f "$OUTPUT" ]; then
        TOTAL_COMMENTS=$("$JQ_CMD" -s 'length' "$OUTPUT")
        TOTAL_PRS=$(gh pr list --repo "$REPO_KEY" --state all --limit 1000 --json number | "$JQ_CMD" 'length')
        save_update_timestamp "$CURRENT_TIME" "$TOTAL_PRS" "$TOTAL_COMMENTS"

        echo ""
        echo "✅ State saved. Next run will be incremental."
    fi

    exit 0
fi

echo "📅 Last update: $LAST_UPDATE"
echo "   Fetching only NEW PRs merged after this date..."
echo ""

# Fetch only new PRs using GitHub search
TEMP_PRS=$(mktemp)
gh pr list \
    --repo "$REPO_KEY" \
    --state merged \
    --search "merged:>=$LAST_UPDATE" \
    --limit 1000 \
    --json number,title,mergedAt \
    > "$TEMP_PRS"

NEW_PR_COUNT=$("$JQ_CMD" 'length' "$TEMP_PRS")

if [ "$NEW_PR_COUNT" -eq 0 ]; then
    echo "✨ No new PRs found since last update"
    echo "   Your best practices are up to date!"
    rm -f "$TEMP_PRS"
    exit 0
fi

echo "📊 Found $NEW_PR_COUNT new merged PRs"
echo ""

# Extract PR numbers
"$JQ_CMD" -r '.[].number' "$TEMP_PRS" > pr_numbers.txt

# Create output file
OUTPUT="${OUTPUT_DIR}/${REPO}_inline_comments_incremental.ndjson"
> "$OUTPUT"

COMMENTS_FOUND=0
COUNT=0

echo "🔍 Extracting comments from new PRs..."
echo ""

while read -r pr; do
    COUNT=$((COUNT + 1))

    # Fetch comments
    TMPFILE=$(mktemp)
    gh api "repos/${OWNER}/${REPO}/pulls/${pr}/comments" > "$TMPFILE" 2>/dev/null || {
        rm -f "$TMPFILE"
        continue
    }

    COMMENT_COUNT=$("$JQ_CMD" 'length' "$TMPFILE")

    if [ "$COMMENT_COUNT" != "0" ]; then
        # Transform to NDJSON
        "$JQ_CMD" -c --arg repo "$REPO" --arg owner "$OWNER" --argjson pr "$pr" '.[] | {
            repo: $repo,
            owner: $owner,
            pr_number: $pr,
            comment_id: .id,
            review_id: .pull_request_review_id,
            in_reply_to_id: .in_reply_to_id,
            file: .path,
            line: .line,
            original_line: .original_line,
            side: .side,
            diff_hunk: .diff_hunk,
            author: .user.login,
            body: .body,
            created_at: .created_at,
            updated_at: .updated_at,
            url: .html_url
        }' "$TMPFILE" >> "$OUTPUT"

        COMMENTS_FOUND=$((COMMENTS_FOUND + COMMENT_COUNT))
        echo "  ✓ PR #${pr}: ${COMMENT_COUNT} comments"
    fi

    rm -f "$TMPFILE"
done < pr_numbers.txt

rm -f "$TEMP_PRS" pr_numbers.txt

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Incremental Update Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📈 Statistics:"
echo "   New PRs processed: $NEW_PR_COUNT"
echo "   Comments extracted: $COMMENTS_FOUND"
echo "   Output file: $OUTPUT"
echo ""

if [ "$COMMENTS_FOUND" -gt 0 ]; then
    echo "📝 Next steps:"
    echo "   1. Sort comments by file tree:"
    echo "      bash scripts/sort_comments_by_filetree.sh $OUTPUT"
    echo ""
    echo "   2. Merge with existing best practices:"
    echo "      (Analyze new comments and update best-practices/ folder)"
    echo ""
fi

# Save state
save_update_timestamp "$CURRENT_TIME" "$NEW_PR_COUNT" "$COMMENTS_FOUND"

echo "💾 State updated. Next run will start from: $CURRENT_TIME"
