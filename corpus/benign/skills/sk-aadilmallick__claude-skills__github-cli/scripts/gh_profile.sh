#!/bin/bash
# Get GitHub user profile information using gh CLI

set -e

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

# Get user profile
echo "=== GitHub Profile ==="
gh api user --jq '{
  login: .login,
  name: .name,
  bio: .bio,
  company: .company,
  location: .location,
  email: .email,
  blog: .blog,
  twitter: .twitter_username,
  followers: .followers,
  following: .following,
  public_repos: .public_repos,
  public_gists: .public_gists,
  created_at: .created_at,
  updated_at: .updated_at
}' | jq -r 'to_entries | .[] | "\(.key): \(.value)"'
