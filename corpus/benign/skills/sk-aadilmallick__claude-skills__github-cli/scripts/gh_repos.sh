#!/bin/bash
# Get GitHub repository information using gh CLI

set -e

# Default values
LIMIT=10
SORT="updated"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --sort)
            SORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--limit N] [--sort {updated|created|pushed|full_name}]"
            exit 1
            ;;
    esac
done

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: gh CLI is not installed. Please install it from https://cli.github.com/"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub. Run 'gh auth login' first."
    exit 1
fi

# Get repositories
echo "=== Top $LIMIT Repositories (sorted by $SORT) ==="
gh repo list --limit "$LIMIT" --json name,description,stargazerCount,forkCount,updatedAt,primaryLanguage,isPrivate \
    --jq ".[] | \"
Repository: \(.name)
Description: \(.description // \"N/A\")
Language: \(.primaryLanguage.name // \"N/A\")
Stars: \(.stargazerCount)
Forks: \(.forkCount)
Private: \(.isPrivate)
Last Updated: \(.updatedAt)
---\""
