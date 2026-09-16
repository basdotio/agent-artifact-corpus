#!/bin/bash
#
# PRD Validation Script (BMAD Planning & Orchestrator)
#
# Validates that a Product Requirements Document contains the required sections,
# well-formed FR/NFR requirements, MoSCoW priorities, acceptance criteria,
# an epics/stories outline, and traceability.
#
# This is a PLANNING validator. It checks document quality only — it never runs
# tests, lints, builds, or touches application code.
#
# Usage:
#   ./validate-prd.sh <prd-file>
#   ./validate-prd.sh --help
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

show_help() {
    cat << EOF
PRD Validation Script (BMAD Planning & Orchestrator)

Usage:
    $0 <prd-file>      e.g. $0 bmad-output/prd.md
    $0 --help

Required Sections:
    Executive Summary, Project Overview, Functional Requirements,
    Non-Functional Requirements, Epics, Success Metrics,
    Assumptions and Dependencies, Out of Scope

Quality Checks:
    - FR-### / NFR-### unique IDs present
    - MoSCoW priorities (MUST/SHOULD/COULD/WON'T)
    - Acceptance criteria present
    - Epics + user stories defined
    - Traceability present
    - Warns on vague terms and on removed practices (story points / velocity / burndown)

Exit Codes:
    0 - all validations passed
    1 - one or more validations failed
    2 - invalid usage or file not found
EOF
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

print_pass() { echo -e "${GREEN}\xE2\x9C\x93${NC} $1"; ((PASS++)) || true; }
print_fail() { echo -e "${RED}\xE2\x9C\x97${NC} $1"; ((FAIL++)) || true; }
print_warn() { echo -e "${YELLOW}\xE2\x9A\xA0${NC} $1"; ((WARN++)) || true; }

check_section() {
    local file=$1 section=$2 pattern=$3
    if grep -qE "$pattern" "$file"; then
        print_pass "Section present: $section"
    else
        print_fail "Section missing: $section"
    fi
}

check_requirements_format() {
    local file=$1 req_type=$2 pattern=$3
    local count
    count=$(grep -cE "$pattern" "$file" || true)
    if [ "$count" -gt 0 ]; then
        print_pass "Found $count $req_type requirements with proper IDs"
    else
        print_fail "No $req_type requirements found with format $pattern"
    fi
}

# --- arg handling ---
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No PRD file specified${NC}\n"
    show_help
    exit 2
fi
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

PRD_FILE=$1
if [ ! -f "$PRD_FILE" ]; then
    echo -e "${RED}Error: File not found: $PRD_FILE${NC}"
    exit 2
fi

print_header "Validating PRD: $PRD_FILE"
echo "File size: $(wc -c < "$PRD_FILE") bytes"
echo "Line count: $(wc -l < "$PRD_FILE") lines"

# --- Required Sections ---
print_header "Required Sections"
check_section "$PRD_FILE" "Executive Summary" "^#{1,3} Executive Summary"
check_section "$PRD_FILE" "Project Overview" "^#{1,3} .*[Pp]roject.*[Oo]verview"
check_section "$PRD_FILE" "Functional Requirements" "^#{1,3} Functional Requirements"
check_section "$PRD_FILE" "Non-Functional Requirements" "^#{1,3} Non-Functional Requirements"
check_section "$PRD_FILE" "Success Metrics" "^#{1,3} Success Metrics"
check_section "$PRD_FILE" "Assumptions" "^#{1,3} Assumptions"
check_section "$PRD_FILE" "Out of Scope" "^#{1,3} Out of Scope"

# --- Requirements Format ---
print_header "Requirements Format"
check_requirements_format "$PRD_FILE" "Functional" "FR-[0-9]"
check_requirements_format "$PRD_FILE" "Non-Functional" "NFR-[0-9]"

# --- Priorities ---
print_header "Priority Assignments (MoSCoW)"
if grep -qiE "(MUST|SHOULD|COULD|WO?N'?T)" "$PRD_FILE"; then
    must=$(grep -ciE "MUST" "$PRD_FILE" || true)
    should=$(grep -ciE "SHOULD" "$PRD_FILE" || true)
    could=$(grep -ciE "COULD" "$PRD_FILE" || true)
    print_pass "Priorities assigned (MUST: $must, SHOULD: $should, COULD: $could)"
    if [ "$must" -gt 0 ] && [ "$should" -eq 0 ] && [ "$could" -eq 0 ]; then
        print_warn "Only MUST priorities found — possible priority inflation. Differentiate Should/Could/Won't."
    fi
else
    print_fail "No priority assignments found (MUST/SHOULD/COULD/WON'T)"
fi

# --- Acceptance Criteria ---
print_header "Acceptance Criteria"
ac=$(grep -ciE "(acceptance criteria|acceptance criterion)" "$PRD_FILE" || true)
if [ "$ac" -gt 0 ]; then
    print_pass "Found $ac acceptance criteria sections"
else
    print_fail "No acceptance criteria found"
fi

# --- Epics & Stories ---
print_header "Epics and User Stories"
if grep -qiE "epic" "$PRD_FILE"; then
    print_pass "Epics found in document"
else
    print_fail "No epics found"
fi
if grep -qiE "(user story|as a .* I want|as an .* I want)" "$PRD_FILE"; then
    print_pass "User stories found"
else
    print_warn "No user stories found (an epics/story outline is recommended)"
fi

# --- Traceability ---
print_header "Traceability"
if grep -qiE "(traceability|requirements matrix|requirements mapping)" "$PRD_FILE"; then
    print_pass "Traceability section found"
else
    print_warn "Traceability matrix not found (recommended)"
fi

# --- Quality Checks ---
print_header "Quality Checks"
vague_terms=("user-friendly" "intuitive" "easy" "simple" "fast" "good" "better" "improved" "robust" "scalable")
vague_found=0
for term in "${vague_terms[@]}"; do
    if grep -qiE "\b$term\b" "$PRD_FILE"; then ((vague_found++)) || true; fi
done
if [ "$vague_found" -gt 5 ]; then
    print_warn "Many vague terms ($vague_found). Replace with specific, measurable criteria."
else
    print_pass "Minimal use of vague terms (good specificity)"
fi

# BMAD removes story points / velocity / burndown — flag if present.
if grep -qiE "(story point|velocity|burndown|fibonacci)" "$PRD_FILE"; then
    print_warn "Found removed estimation practice (story points / velocity / burndown / Fibonacci). BMAD uses count-based delivery; size stories as 'one agent session' instead."
fi

line_count=$(wc -l < "$PRD_FILE")
if [ "$line_count" -lt 40 ]; then
    print_warn "Document is short ($line_count lines). Ensure all sections are complete."
else
    print_pass "Document length is reasonable ($line_count lines)"
fi

# --- Summary ---
print_header "Validation Summary"
total=$((PASS + FAIL + WARN))
echo -e "${GREEN}Passed:${NC}   $PASS/$total"
echo -e "${RED}Failed:${NC}   $FAIL/$total"
echo -e "${YELLOW}Warnings:${NC} $WARN/$total"
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}\xE2\x9C\x93 PRD validation passed!${NC}"
    [ "$WARN" -gt 0 ] && echo -e "${YELLOW}  (with $WARN warnings — review recommended)${NC}"
    exit 0
else
    echo -e "${RED}\xE2\x9C\x97 PRD validation failed with $FAIL errors${NC}"
    exit 1
fi
