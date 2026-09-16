#!/usr/bin/env bash
#
# init-sprint-status.sh
# ---------------------
# Scaffolds bmad-output/sprint-status.yaml from the canonical template
# if the file does not already exist.
#
# This script is part of the bmad-sprint-planning skill in the
# BMAD Planning & Orchestrator plugin.
#
# Usage:
#   bash init-sprint-status.sh [project-name] [output-dir]
#
# Arguments:
#   project-name   Optional. Defaults to dirname of cwd.
#   output-dir     Optional. Defaults to bmad-output/
#
# Exit codes:
#   0 - Success (created or already exists)
#   1 - Error

set -euo pipefail

# ── Args ────────────────────────────────────────────────────────────────────
PROJECT_NAME="${1:-}"
OUTPUT_DIR="${2:-bmad-output}"
STATUS_FILE="${OUTPUT_DIR}/sprint-status.yaml"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# ── Helpers ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${YELLOW}[init-sprint-status] $*${NC}" >&2; }
success() { echo -e "${GREEN}[init-sprint-status] $*${NC}" >&2; }
error()   { echo -e "${RED}[init-sprint-status] ERROR: $*${NC}" >&2; }

usage() {
  cat <<EOF
Usage: $(basename "$0") [project-name] [output-dir]

Scaffold bmad-output/sprint-status.yaml from the canonical template.
If the file already exists, this script exits without modifying it.

Arguments:
  project-name   Project name embedded in the YAML (default: directory name)
  output-dir     Output directory (default: bmad-output/)

Exit codes:
  0  File created or already exists
  1  Error
EOF
}

# ── Parse help flag ──────────────────────────────────────────────────────────
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage; exit 0
fi

# ── Resolve project name ─────────────────────────────────────────────────────
if [[ -z "$PROJECT_NAME" ]]; then
  # Try reading from an existing bmad config
  if [[ -f "bmad-output/project-context.md" ]]; then
    PROJECT_NAME=$(grep -m1 -E "^# Project:" "bmad-output/project-context.md" \
      | sed 's/# Project:[[:space:]]*//' || true)
  fi
  if [[ -z "$PROJECT_NAME" ]]; then
    PROJECT_NAME="$(basename "$(pwd)")"
    info "No project name provided; defaulting to directory name: $PROJECT_NAME"
  fi
fi

# ── Guard: file already exists ───────────────────────────────────────────────
if [[ -f "$STATUS_FILE" ]]; then
  success "sprint-status.yaml already exists at $STATUS_FILE — nothing to do."
  echo "$STATUS_FILE"
  exit 0
fi

# ── Create output directory ──────────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR"

# ── Write scaffold ───────────────────────────────────────────────────────────
cat > "$STATUS_FILE" <<YAML
# BMAD Sprint Status — Sequencing System-of-Record
# Generated: ${TIMESTAMP}
# Project: ${PROJECT_NAME}
#
# STATUS LIFECYCLE (view only — not a metric):
#   backlog → ready-for-dev → in-progress → review → done
#
# CAPACITY MODEL: wave width (stories that can run concurrently), not points.
# NO velocity, burndown, or point fields belong in this file.

project_name: "${PROJECT_NAME}"
track: ""              # Quick Flow | BMad Method | Enterprise
generated_at: "${TIMESTAMP}"
last_updated: "${TIMESTAMP}"

epics: []
  # - id: "epic-1"
  #   title: ""
  #   description: ""
  #   status: backlog
  #   story_ids: []

stories: []
  # - id: "{epic}.{story}.{slug}"
  #   title: ""
  #   epic_id: "epic-1"
  #   status: backlog           # backlog | ready-for-dev | in-progress | review | done
  #   file: "bmad-output/stories/{file}.story.md"
  #   parallel_set: 1           # wave assignment (integer)
  #   dependencies: []          # story ids; empty = no prerequisites
  #   owned_scope: []           # explicit list of paths this story may touch

sequencing_summary:
  total_epics: 0
  total_stories: 0
  total_waves: 0
  wave_widths: []
  ready_for_dev:
    count: 0
    story_ids: []
  handoff_notes: ""
YAML

success "Created $STATUS_FILE"
echo "$STATUS_FILE"
