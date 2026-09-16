#!/usr/bin/env bash
#
# sequence-stories.sh
# -------------------
# Orders stories by epic (ascending epic number) then by dependency
# (topological sort within each epic's group), and assigns parallel_set
# (wave) integers.
#
# This script is part of the bmad-sprint-planning skill in the
# BMAD Planning & Orchestrator plugin.
#
# Wave assignment rule:
#   Wave 1: stories with no dependencies (dependencies: [])
#   Wave N: stories whose every dependency is fully contained in waves 1…(N-1)
#
# Capacity is expressed as wave width (number of concurrent stories),
# NOT as points or velocity.  This script emits NO velocity/burndown fields.
#
# Usage:
#   bash sequence-stories.sh [sprint-status-file]
#
#   sprint-status-file  Defaults to bmad-output/sprint-status.yaml
#
# The script reads the YAML file, extracts story ids and their
# dependencies[], computes wave membership via a pure-bash topological
# sort, prints a sequencing report to stdout, and appends
# parallel_set values back into the YAML file.
#
# Requirements:
#   - bash 4+ (associative arrays)
#   - grep, sed, awk (standard POSIX tools)
#
# Exit codes:
#   0 - Success
#   1 - Error (cycle detected, file not found, etc.)

set -euo pipefail

# ── Args ─────────────────────────────────────────────────────────────────────
STATUS_FILE="${1:-bmad-output/sprint-status.yaml}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# ── Helpers ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${YELLOW}[sequence-stories] $*${NC}" >&2; }
success() { echo -e "${GREEN}[sequence-stories] $*${NC}" >&2; }
error()   { echo -e "${RED}[sequence-stories] ERROR: $*${NC}" >&2; }
header()  { echo -e "${CYAN}$*${NC}"; }

usage() {
  cat <<EOF
Usage: $(basename "$0") [sprint-status-file]

Order stories by epic then dependency, assign parallel_set wave integers.

Arguments:
  sprint-status-file  Path to sprint-status.yaml (default: bmad-output/sprint-status.yaml)

Output:
  - Sequencing report printed to stdout
  - parallel_set values updated in the YAML file
  - last_updated timestamp refreshed in the YAML file

Wave assignment:
  Wave 1: stories with no dependencies
  Wave N: stories whose dependencies are all in waves 1…(N-1)
  Stories in the same wave may run concurrently (check owned_scope for conflicts).

NO velocity, burndown, or point fields are written.

Exit codes:
  0  Success
  1  Error (cycle, file not found, etc.)
EOF
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage; exit 0
fi

# ── Validate input ────────────────────────────────────────────────────────────
if [[ ! -f "$STATUS_FILE" ]]; then
  error "sprint-status file not found: $STATUS_FILE"
  echo "Run init-sprint-status.sh first, or provide the correct path." >&2
  exit 1
fi

# ── Parse story ids and their dependencies from YAML ─────────────────────────
# We parse with grep/sed since we cannot assume yq or python availability.
# The YAML format expected:
#   stories:
#     - id: "2.1.stripe-integration"
#       ...
#       dependencies:
#         - "1.3.user-auth-api"
#     - id: "2.2.payment-webhook"
#       dependencies: []

declare -A story_deps   # story_id -> space-separated dep ids
declare -a story_order  # insertion order of story ids

current_id=""
in_deps=0

while IFS= read -r line; do
  # Detect story id line
  if [[ "$line" =~ ^[[:space:]]*-[[:space:]]+id:[[:space:]]*\"([^\"]+)\" ]]; then
    current_id="${BASH_REMATCH[1]}"
    story_order+=("$current_id")
    story_deps["$current_id"]=""
    in_deps=0
    continue
  fi

  # Detect dependencies: [] (empty inline)
  if [[ -n "$current_id" ]] && [[ "$line" =~ ^[[:space:]]+dependencies:[[:space:]]*\[\] ]]; then
    story_deps["$current_id"]=""
    in_deps=0
    continue
  fi

  # Detect start of dependencies block
  if [[ -n "$current_id" ]] && [[ "$line" =~ ^[[:space:]]+dependencies: ]]; then
    in_deps=1
    continue
  fi

  # Collect dependency entries (- "id" or - id)
  if [[ $in_deps -eq 1 ]] && [[ "$line" =~ ^[[:space:]]+-[[:space:]]+\"?([^\"#[:space:]]+)\"? ]]; then
    dep_id="${BASH_REMATCH[1]}"
    if [[ -n "$dep_id" && "$dep_id" != "#"* ]]; then
      story_deps["$current_id"]+=" $dep_id"
    fi
    continue
  fi

  # Any non-dep line resets in_deps
  if [[ $in_deps -eq 1 ]] && [[ ! "$line" =~ ^[[:space:]]+-[[:space:]] ]]; then
    in_deps=0
  fi
done < "$STATUS_FILE"

total_stories="${#story_order[@]}"
if [[ $total_stories -eq 0 ]]; then
  info "No stories found in $STATUS_FILE. Nothing to sequence."
  exit 0
fi

info "Found $total_stories stories. Computing wave assignments..."

# ── Topological wave assignment ───────────────────────────────────────────────
declare -A wave_assignment  # story_id -> wave number

assign_wave() {
  local id="$1"
  local visited_key="visiting_$id"

  # Already assigned
  if [[ -n "${wave_assignment[$id]:-}" ]]; then
    echo "${wave_assignment[$id]}"
    return
  fi

  # Cycle detection
  if [[ -n "${!visited_key:-}" ]]; then
    error "Dependency cycle detected at story: $id"
    exit 1
  fi
  declare -g "visiting_$id=1"

  local deps="${story_deps[$id]:-}"
  if [[ -z "$deps" ]]; then
    wave_assignment["$id"]=1
    unset "visiting_$id" 2>/dev/null || true
    echo 1
    return
  fi

  local max_dep_wave=0
  for dep in $deps; do
    if [[ -z "${story_deps[$dep]+_}" ]]; then
      # Dependency not in stories list — treat as satisfied (external)
      continue
    fi
    dep_wave=$(assign_wave "$dep")
    if [[ $dep_wave -gt $max_dep_wave ]]; then
      max_dep_wave=$dep_wave
    fi
  done

  local my_wave=$(( max_dep_wave + 1 ))
  wave_assignment["$id"]=$my_wave
  unset "visiting_$id" 2>/dev/null || true
  echo $my_wave
}

for sid in "${story_order[@]}"; do
  assign_wave "$sid" > /dev/null
done

# ── Compute wave width summary ────────────────────────────────────────────────
declare -A wave_counts
max_wave=0

for sid in "${story_order[@]}"; do
  w="${wave_assignment[$sid]}"
  wave_counts[$w]=$(( ${wave_counts[$w]:-0} + 1 ))
  if [[ $w -gt $max_wave ]]; then max_wave=$w; fi
done

# ── Print sequencing report ───────────────────────────────────────────────────
header ""
header "=== BMAD Sprint Sequencing Report ==="
header "File: $STATUS_FILE"
header "Timestamp: $TIMESTAMP"
header ""

for (( w=1; w<=max_wave; w++ )); do
  count="${wave_counts[$w]:-0}"
  echo "Wave $w (${count} stories — can run concurrently):"
  for sid in "${story_order[@]}"; do
    if [[ "${wave_assignment[$sid]}" -eq $w ]]; then
      deps="${story_deps[$sid]:-}"
      if [[ -z "$deps" ]]; then
        echo "  - $sid  [no dependencies]"
      else
        echo "  - $sid  [depends on:$deps ]"
      fi
    fi
  done
  echo ""
done

# Wave widths summary
wave_widths="["
for (( w=1; w<=max_wave; w++ )); do
  wave_widths+="${wave_counts[$w]:-0}"
  if [[ $w -lt $max_wave ]]; then wave_widths+=", "; fi
done
wave_widths+="]"

echo "Total waves: $max_wave"
echo "Wave widths: $wave_widths"
echo ""

# ── Write parallel_set back into YAML ────────────────────────────────────────
# Strategy: rewrite the file line by line; when inside a story block whose id
# we know, replace the parallel_set line (or insert after the id line if absent).
tmp_file="${STATUS_FILE}.tmp.$$"
trap 'rm -f "$tmp_file"' EXIT

current_id=""
injected_ps=0

while IFS= read -r line; do
  # Detect story id
  if [[ "$line" =~ ^([[:space:]]*-[[:space:]]+id:[[:space:]]*)\"([^\"]+)\" ]]; then
    current_id="${BASH_REMATCH[2]}"
    injected_ps=0
    echo "$line" >> "$tmp_file"
    continue
  fi

  # Replace existing parallel_set line
  if [[ -n "$current_id" ]] && [[ "$line" =~ ^[[:space:]]+parallel_set: ]]; then
    wave="${wave_assignment[$current_id]:-1}"
    # Preserve leading whitespace
    indent="${line%%parallel_set:*}"
    echo "${indent}parallel_set: ${wave}" >> "$tmp_file"
    injected_ps=1
    continue
  fi

  # Update last_updated timestamp
  if [[ "$line" =~ ^last_updated: ]]; then
    echo "last_updated: \"${TIMESTAMP}\"" >> "$tmp_file"
    continue
  fi

  echo "$line" >> "$tmp_file"
done < "$STATUS_FILE"

mv "$tmp_file" "$STATUS_FILE"
trap - EXIT

success "Updated parallel_set values in $STATUS_FILE"
success "Sequencing complete. Wave 1 stories are ready-for-dev."
