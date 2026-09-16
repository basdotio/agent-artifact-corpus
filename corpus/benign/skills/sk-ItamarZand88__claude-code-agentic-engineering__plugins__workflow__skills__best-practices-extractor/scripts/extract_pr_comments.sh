#!/bin/bash
# Extract inline PR comments from a GitHub repo to NDJSON format
# Usage: ./extract_pr_comments.sh REPO_NAME
# Example: ./extract_pr_comments.sh backend

set -e

OWNER="earlyai"
REPO="${1:?Usage: $0 REPO_NAME (e.g., backend, vscode-extension)}"

# Output to .claude/pr-review-comments/
OUTPUT_DIR=".claude/pr-review-comments"
mkdir -p "$OUTPUT_DIR"
OUTPUT="${OUTPUT_DIR}/${REPO}_inline_comments.ndjson"

# Find jq
JQ_CMD="jq"
if [ -f "/c/Users/ItamarZand/bin/jq.exe" ]; then
    JQ_CMD="/c/Users/ItamarZand/bin/jq.exe"
elif ! command -v jq &> /dev/null; then
    echo "Error: jq not found. Install it first."
    exit 1
fi

echo "Fetching PRs from ${OWNER}/${REPO}..."

# Get all PR numbers (strip Windows line endings)
PR_NUMBERS=$(gh api "repos/${OWNER}/${REPO}/pulls?state=all&per_page=100" --paginate -q '.[].number' | tr -d '\r')

TOTAL_PRS=$(echo "$PR_NUMBERS" | wc -l | tr -d ' ')
echo "Found ${TOTAL_PRS} PRs"

# Clear output file
> "$OUTPUT"

COUNT=0
COMMENTS_FOUND=0
TMPFILE=$(mktemp)

for pr in $PR_NUMBERS; do
    COUNT=$((COUNT + 1))

    # Fetch comments to temp file
    gh api "repos/${OWNER}/${REPO}/pulls/${pr}/comments" > "$TMPFILE" 2>/dev/null || continue

    # Check if there are comments
    COMMENT_COUNT=$($JQ_CMD 'length' "$TMPFILE")

    if [ "$COMMENT_COUNT" != "0" ]; then
        # Transform to NDJSON with all fields
        $JQ_CMD -c --arg repo "$REPO" --arg owner "$OWNER" --argjson pr "$pr" '.[] | {
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
        echo "PR #${pr}: ${COMMENT_COUNT} comments (${COUNT}/${TOTAL_PRS})"
    else
        # Progress indicator every 50 PRs
        if [ $((COUNT % 50)) -eq 0 ]; then
            echo "Progress: ${COUNT}/${TOTAL_PRS} PRs processed..."
        fi
    fi
done

rm -f "$TMPFILE"

echo ""
echo "Done! Extracted ${COMMENTS_FOUND} comments from ${TOTAL_PRS} PRs"
echo "Output: ${OUTPUT}"
