#!/usr/bin/env bash
#
# check-delivery-dirs.sh - Ensures delivery directory structure exists
#
# Usage: check-delivery-dirs.sh <dataset-type> [identifier]
# Example: check-delivery-dirs.sh bulk-rnaseq PRJNA1018599
#
# This script creates the delivery directory structure for non-git-managed outputs.
#

set -euo pipefail

DELIVERY_DIR="delivery"

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if arguments were provided
if [ $# -eq 0 ]; then
  echo "Error: No dataset type specified"
  echo "Usage: $0 <dataset-type> [identifier]"
  echo "Example: $0 bulk-rnaseq PRJNA1018599"
  exit 1
fi

DATASET_TYPE="$1"
IDENTIFIER="${2:-}"

# Create delivery directory if needed
if [ ! -d "$DELIVERY_DIR" ]; then
  mkdir -p "$DELIVERY_DIR"
  echo -e "${GREEN}Created${NC} ${DELIVERY_DIR}/"
fi

# Create dataset type subdirectory
TYPE_DIR="${DELIVERY_DIR}/${DATASET_TYPE}"
if [ ! -d "$TYPE_DIR" ]; then
  mkdir -p "$TYPE_DIR"
  echo -e "${GREEN}Created${NC} ${TYPE_DIR}/"
fi

# Create identifier subdirectory if provided
if [ -n "$IDENTIFIER" ]; then
  ID_DIR="${TYPE_DIR}/${IDENTIFIER}"
  if [ ! -d "$ID_DIR" ]; then
    mkdir -p "$ID_DIR"
    echo -e "${GREEN}Created${NC} ${ID_DIR}/"
  fi
  echo "$ID_DIR"
else
  echo "$TYPE_DIR"
fi
