#!/usr/bin/env bash
#
# check-repos.sh - Validates veupathdb-repos/ directory structure
#
# Usage: check-repos.sh <repo1> <repo2> ...
# Example: check-repos.sh ApiCommonDatasets ApiCommonPresenters EbrcModelCommon
#
# This script checks that specified VEuPathDB configuration repositories are
# present and provides guidance if they're missing.
#

set -euo pipefail

REPOS_DIR="veupathdb-repos"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if arguments were provided
if [ $# -eq 0 ]; then
  echo -e "${RED}Error: No repositories specified${NC}"
  echo "Usage: $0 <repo1> <repo2> ..."
  echo "Example: $0 ApiCommonDatasets ApiCommonPresenters EbrcModelCommon"
  exit 1
fi

REQUIRED_REPOS=("$@")

echo "Checking VEuPathDB repositories in ${REPOS_DIR}/..."
echo

# Check if veupathdb-repos directory exists
if [ ! -d "$REPOS_DIR" ]; then
  echo -e "${RED}✗ Error: ${REPOS_DIR}/ directory not found${NC}"
  echo
  echo "You need to set up the ${REPOS_DIR}/ directory. Choose one option:"
  echo
  echo -e "${YELLOW}Option 1 (Recommended): Symlink to GitHub Desktop repos${NC}"
  echo "  ln -s ~/Documents/GitHub veupathdb-repos"
  echo
  echo -e "${YELLOW}Option 2: Clone repositories here${NC}"
  echo "  mkdir veupathdb-repos"
  echo "  cd veupathdb-repos"
  for repo in "${REQUIRED_REPOS[@]}"; do
    echo "  git clone git@github.com:VEuPathDB/${repo}.git"
  done
  echo "  cd .."
  echo
  exit 1
fi

# Check each required repository
missing_repos=()
for repo in "${REQUIRED_REPOS[@]}"; do
  if [ -d "${REPOS_DIR}/${repo}" ]; then
    echo -e "${GREEN}✓${NC} ${repo}"
  else
    echo -e "${RED}✗${NC} ${repo} (missing)"
    missing_repos+=("$repo")
  fi
done

# Report results
echo
if [ ${#missing_repos[@]} -eq 0 ]; then
  echo -e "${GREEN}All required repositories are present!${NC}"
  exit 0
else
  echo -e "${YELLOW}Missing repositories: ${missing_repos[*]}${NC}"
  echo
  echo "To clone missing repositories:"
  echo
  echo "  cd veupathdb-repos"
  for repo in "${missing_repos[@]}"; do
    echo "  git clone git@github.com:VEuPathDB/${repo}.git"
  done
  echo "  cd .."
  echo
  exit 1
fi
