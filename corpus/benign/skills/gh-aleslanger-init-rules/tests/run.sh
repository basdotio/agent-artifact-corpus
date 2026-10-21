#!/usr/bin/env bash
# Regression test for /init-rules: runs the skill headless on the `demo` fixture and checks the result.
# Usage: tests/run.sh [--keep]    (needs: claude, git, python3 with PyYAML; takes several minutes)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
[ "${1:-}" = "--keep" ] || trap 'rm -rf "$work"' EXIT

repo="$work/demo"
cp -r "$here/fixtures/demo" "$repo"
mv "$repo/CLAUDE.md.fixture" "$repo/CLAUDE.md"
git -C "$repo" init -q
git -C "$repo" add -A
git -C "$repo" -c user.email=test@example.com -c user.name=test commit -qm fixture

echo "== help mode"
help_out=$(cd "$repo" && claude -p "/init-rules help" --max-turns 2)
if grep -Fq "/init-rules enforce" <<<"$help_out" && grep -Fq "/init-rules help" <<<"$help_out"; then
  echo "PASS help printed"
else
  echo "FAIL help not printed"; exit 1
fi
[ -z "$(git -C "$repo" status --porcelain)" ] && echo "PASS help changed nothing" || { echo "FAIL help changed files"; exit 1; }

echo "== full run (several minutes)"
(cd "$repo" && claude -p "/init-rules" --permission-mode acceptEdits \
  --add-dir "$here/../references" \
  --allowedTools "Read,Write,Edit,Glob,Grep,TodoWrite,Agent,Edit(.claude/rules/**),Edit(CLAUDE.md),Bash(mkdir *),Bash(git *),Bash(ls *),Bash(find *),Bash(cat *),Bash(grep *),Bash(python3 *),Bash(wc *),Bash(head *),Bash(make -n *)" \
  > "$work/report.txt" 2>&1)

[ "${1:-}" = "--keep" ] && echo "kept: $work"
python3 "$here/check.py" "$repo" "$work/report.txt"
