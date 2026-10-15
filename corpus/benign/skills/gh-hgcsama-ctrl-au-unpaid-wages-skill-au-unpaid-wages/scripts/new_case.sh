#!/usr/bin/env bash
# Scaffold an unpaid-wages case folder from the skill templates.
# Usage: scripts/new_case.sh <case-folder>
set -euo pipefail
if [ $# -ne 1 ]; then echo "usage: $0 <case-folder>" >&2; exit 1; fi
dest="$1"
here="$(cd "$(dirname "$0")/.." && pwd)"
tpl="$here/assets/templates"
if [ -e "$dest" ] && [ -n "$(ls -A "$dest" 2>/dev/null)" ]; then
  echo "refusing to scaffold into non-empty folder: $dest" >&2; exit 1
fi
mkdir -p "$dest"/{drafts,evidence/email-exports,evidence/chat,evidence/invoices,evidence/fwo}
cp "$tpl/timeline.md" "$tpl/evidence-index.md" "$tpl/hours.csv" "$tpl/calculations.md" "$tpl/HANDOVER.md" "$dest/"
cp "$tpl/chase-email.md" "$tpl/letter-of-demand.md" "$tpl/final-notice.md" "$tpl/fwo-enquiry-fields.md" "$dest/drafts/"
cat > "$dest/.gitignore" <<'G'
# never commit secrets or raw personal documents
*.pdf
*.heic
evidence/invoices/
G
cat > "$dest/README.md" <<'R'
# Private case file

Do not make this repository public or share its link: it contains personal data and third-party
information. Start every session by reading HANDOVER.md, then timeline.md.
R
echo "scaffolded $dest"
find "$dest" -type f | sort
