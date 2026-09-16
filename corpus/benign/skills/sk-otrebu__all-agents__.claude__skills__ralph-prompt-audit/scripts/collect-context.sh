#!/usr/bin/env bash

set -euo pipefail

ROOT_INPUT="${1:-$(pwd)}"
ROOT_DIR="$(cd "${ROOT_INPUT}" && pwd)"

if git -C "${ROOT_DIR}" rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT_DIR="$(git -C "${ROOT_DIR}" rev-parse --show-toplevel)"
fi

OUT_DIR="${2:-${ROOT_DIR}/tmp/ralph-prompt-audit}"
mkdir -p "${OUT_DIR}"

if [[ -x "${ROOT_DIR}/bin/aaa" ]]; then
  AAA_BIN="${ROOT_DIR}/bin/aaa"
elif command -v aaa >/dev/null 2>&1; then
  AAA_BIN="$(command -v aaa)"
else
  echo "Error: could not find 'aaa' CLI. Expected ${ROOT_DIR}/bin/aaa or global 'aaa'." >&2
  exit 1
fi

echo "[ralph-prompt-audit] root: ${ROOT_DIR}"
echo "[ralph-prompt-audit] output: ${OUT_DIR}"
echo "[ralph-prompt-audit] using aaa: ${AAA_BIN}"

(
  cd "${ROOT_DIR}"
  "${AAA_BIN}" completion table --format json > "${OUT_DIR}/command-table.json"
)

rg -oN 'context/workflows/ralph/[A-Za-z0-9._/-]+\.md' \
  "${ROOT_DIR}/tools/src/commands/ralph" \
  --glob '*.ts' \
  --no-filename | sed '/^$/d' | sort -u > "${OUT_DIR}/workflow-prompt-files.txt"

: > "${OUT_DIR}/skill-files.txt"
for skill_path in "${ROOT_DIR}"/.claude/skills/ralph-*/SKILL.md; do
  [[ -f "${skill_path}" ]] || continue
  if [[ "${skill_path}" == *"/ralph-prompt-audit/SKILL.md" ]]; then
    continue
  fi
  printf '%s\n' "${skill_path#"${ROOT_DIR}/"}" >> "${OUT_DIR}/skill-files.txt"
done

sort -u "${OUT_DIR}/skill-files.txt" -o "${OUT_DIR}/skill-files.txt"

cat "${OUT_DIR}/workflow-prompt-files.txt" "${OUT_DIR}/skill-files.txt" \
  | sed '/^$/d' | sort -u > "${OUT_DIR}/review-files.txt"

: > "${OUT_DIR}/cli-invocations.txt"
while IFS= read -r relative_path; do
  [[ -z "${relative_path}" ]] && continue
  absolute_path="${ROOT_DIR}/${relative_path}"
  if [[ -f "${absolute_path}" ]]; then
    (
      cd "${ROOT_DIR}"
      rg -nH 'aaa ralph [a-z]' "${relative_path}"
    ) >> "${OUT_DIR}/cli-invocations.txt" || true
  fi
done < "${OUT_DIR}/review-files.txt"

sort -u "${OUT_DIR}/cli-invocations.txt" -o "${OUT_DIR}/cli-invocations.txt"

PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"${PYTHON_BIN}" - "${OUT_DIR}/command-table.json" "${OUT_DIR}/ralph-command-matrix.md" <<'PY'
import json
import sys
from collections import defaultdict

source = sys.argv[1]
target = sys.argv[2]

with open(source, "r", encoding="utf-8") as f:
    rows = json.load(f)

commands = defaultdict(lambda: {
    "description": "",
    "arguments": set(),
    "options": set(),
})

for row in rows:
    command = row.get("command", "")
    if not command.startswith("aaa ralph"):
        continue

    entry = commands[command]

    description = row.get("commandDescription", "")
    if description and description != "-" and not entry["description"]:
        entry["description"] = description

    arguments = row.get("arguments", "")
    if arguments and arguments != "-":
        entry["arguments"].add(arguments)

    option = row.get("option", "")
    if option and option != "-":
        required = "required" if row.get("optionRequired") else "optional"
        option_description = row.get("optionDescription", "").strip()
        if option_description and option_description != "-":
            entry["options"].add(f"{option} ({required}) - {option_description}")
        else:
            entry["options"].add(f"{option} ({required})")

with open(target, "w", encoding="utf-8") as out:
    out.write("# Ralph Command Matrix\n\n")
    out.write("Generated from `aaa completion table --format json`.\n\n")

    for command in sorted(commands):
        entry = commands[command]
        out.write(f"## {command}\n")
        if entry["description"]:
            out.write(f"- Description: {entry['description']}\n")

        if entry["arguments"]:
            args = ", ".join(sorted(entry["arguments"]))
            out.write(f"- Arguments: {args}\n")

        if entry["options"]:
            out.write("- Options:\n")
            for option in sorted(entry["options"]):
                out.write(f"  - {option}\n")
        else:
            out.write("- Options: (none)\n")

        out.write("\n")
PY

workflow_count="$(wc -l < "${OUT_DIR}/workflow-prompt-files.txt" | tr -d ' ')"
skill_count="$(wc -l < "${OUT_DIR}/skill-files.txt" | tr -d ' ')"
file_count="$(wc -l < "${OUT_DIR}/review-files.txt" | tr -d ' ')"
invocation_count="$(wc -l < "${OUT_DIR}/cli-invocations.txt" | tr -d ' ')"

cat > "${OUT_DIR}/README.md" <<EOF
# Ralph Prompt Audit Context

- Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- Root: ${ROOT_DIR}
- Workflow prompts discovered from CLI source: ${workflow_count}
- Ralph skill files included: ${skill_count}
- Total files to review: ${file_count}
- Extracted aaa ralph examples: ${invocation_count}

## Files

- command-table.json
- ralph-command-matrix.md
- workflow-prompt-files.txt
- skill-files.txt
- review-files.txt
- cli-invocations.txt
EOF

echo "[ralph-prompt-audit] context ready"
