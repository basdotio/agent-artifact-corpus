#!/usr/bin/env sh
# Keep the GitNexus index at HEAD without touching tracked files.
#
# Called from the repo's post-commit / post-merge / post-checkout / post-rewrite
# git hooks (husky, lefthook, pre-commit or plain core.hooksPath), so the index
# never reports "N commits behind" after ordinary git work.
#  - `--index-only`: never rewrites CLAUDE.md, AGENTS.md or .claude/skills,
#    so a re-index can't manufacture a commit.
#  - Detached background run: git returns immediately. gitnexus serialises
#    overlapping runs on its own lock, so back-to-back hooks are safe.
#  - No-op when gitnexus isn't installed or this clone was never indexed.
# Output: .gitnexus/refresh.log (the directory is self-ignored).
# Set GITNEXUS_HOOK=0 to skip.
[ "${GITNEXUS_HOOK:-1}" = "0" ] && exit 0
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
META="$ROOT/.gitnexus/gitnexus.json"
[ -f "$META" ] || exit 0
command -v gitnexus >/dev/null 2>&1 || exit 0

HEAD=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null) || exit 0
LAST=$(sed -n 's/.*"lastCommit": *"\([0-9a-f]*\)".*/\1/p' "$META" | head -n 1)
[ "$HEAD" = "$LAST" ] && exit 0

(
  cd "$ROOT" || exit 0
  nohup gitnexus analyze --index-only > "$ROOT/.gitnexus/refresh.log" 2>&1 &
) > /dev/null 2>&1 < /dev/null
exit 0
