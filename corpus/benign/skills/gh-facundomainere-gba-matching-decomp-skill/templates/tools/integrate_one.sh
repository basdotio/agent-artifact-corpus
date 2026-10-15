#!/bin/sh
# Integrate one matched function: tools/integrate_one.sh ADDR file.c name
# Serialized by .decomp.lock. Re-checks the match, adds it to src/, requires make compare,
# records progress, commits and pushes. Exit 0 only if committed.
set -e
cd "$(dirname "$0")/.."
ADDR=$1; FILE=$2; NAME=${3:-sub_$1}  # env END=XXXXXXXX: span several functions
exec 9>.decomp.lock
flock 9
python3 - "$ADDR" "$FILE" "$NAME" > .one.json <<'PY'
import json, sys
import os
r = {"addr": sys.argv[1], "matched": True, "c_code": open(sys.argv[2]).read(), "name": sys.argv[3]}
if os.environ.get("END"):
    r["end"] = os.environ["END"]  # one C file spanning several functions
print(json.dumps([r]))
PY
python3 tools/add_funcs.py .one.json
rm -f .one.json
P=$(python3 tools/progress.py --record)
sed -i -E "s/^$ADDR (claimed|retry[0-9]+)$/$ADDR done/" claims.txt
echo "- $(date +%F): $NAME ($ADDR). $P" >> PROGRESS.md
git add -A src splits.txt asm ld_script.ld objects.mk progress_history.csv PROGRESS.md claims.txt
git commit -qm "Decompile $NAME ($ADDR)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q || echo "push failed (commit kept locally)"
echo "$P"
