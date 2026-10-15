#!/usr/bin/env bash
# kb-lint health scan, checks 1-4. Run, never loaded: the model reads only this output.
# Usage: scan.sh <vault> <stale-days> [today]   (stale-days 0 = stale check off; today = YYYY-MM-DD)
set -eu   # no pipefail: rg exits 1 on zero matches, which a new vault legitimately has
command -v fd >/dev/null || { command -v fdfind >/dev/null && fd() { fdfind "$@"; }; }
for c in fd rg awk; do command -v "$c" >/dev/null || { echo "scan.sh: needs '$c' on PATH (see README Requirements)" >&2; exit 2; }; done
rg --pcre2-version >/dev/null 2>&1 || { echo "scan.sh: ripgrep lacks PCRE2 (-P); install a build with PCRE2" >&2; exit 2; }
V=${1:?vault}; DAYS=${2:?stale-days}; TODAY=${3:-$(date +%F)}
case $DAYS in *[!0-9]*) echo "scan.sh: stale-days must be a non-negative integer, got '$DAYS'" >&2; exit 2;; esac
cd "$V"   # this script's own process: output paths are vault-relative, the caller's cwd is untouched
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

# One frontmatter pass feeds checks 1 and 4: path, type, slug, has-title, has-date, fetched, published.
fd -e md . wiki/ -E _archive -X awk '
  function out() { if (f == "") return; t = ("title" in k); d = ("updated" in k) || ("fetched" in k)
    printf "%s\t%s\t%s\t%d\t%d\t%s\t%s\n", f, k["type"], k["slug"], t, d, k["fetched"], k["published"] }
  FNR == 1 { out(); f = FILENAME; split("", k); fm = ($0 == "---"); next }
  fm && $0 == "---" { fm = 0; next }
  fm && match($0, /^[A-Za-z_]+:/) { v = substr($0, RLENGTH + 1); sub(/^[ \t]+/, "", v); gsub(/["\047]/, "", v); k[substr($0, 1, RLENGTH - 1)] = v }
  END { out() }' | sort > "$T/fm"

echo "## 1 frontmatter ($(( $(wc -l < "$T/fm") )) pages; _archive excluded)"
awk -F'\t' '{ n = $1; sub(/.*\//, "", n); sub(/\.md$/, "", n); m = ""
  if ($2 == "") m = m " type"; if ($3 == "") m = m " slug"; if (!$4) m = m " title"; if (!$5) m = m " updated|fetched"
  if (m != "") print "missing" m ": " $1
  if ($3 != "" && $3 != n) print "slug != stem: " $1 " (slug: " $3 ")" }' "$T/fm"
echo "types: $(cut -f2 "$T/fm" | sort | uniq -c | sort -rn | awk '{printf "%s%s %s", (NR > 1 ? ", " : ""), ($2 == "" ? "(none)" : $2), $1}')"

# Check 2. (?<!`) skips code-span examples like `[[wikilinks]]`; backtick is also out of the class so a
# match cannot run past a closing backtick. lint-[0-9]* reports and log.md are records; _archive pages are
# kept as-is, so their links are not checked (the stems still include _archive, so links into it resolve).
# -g matches the basename, so '!synthesis/lint-*.md' would silently match nothing.
# s/\\$// strips the escaped table pipe in [[slug\|label]].
rg -oIN -P '(?<!`)\[\[[^]|`]+' wiki/ \
   -g '!lint-[0-9]*.md' -g '!log.md' -g '!**/_archive/**' \
  | sed 's/^\[\[//; s/\\$//' | sort -u > "$T/targets"
fd -e md . wiki/ -x basename {} .md | sort -u > "$T/stems"
comm -23 "$T/targets" "$T/stems" > "$T/broken"
echo "## 2 broken links ($(( $(wc -l < "$T/targets") )) unique targets; $(( $(wc -l < "$T/broken") )) broken)"
cat "$T/broken"

# Check 3, one pass (a per-page rg loop is too slow on a large wiki). Exclusions apply on both sides:
# -g filters link sources, fd -E/grep -v the pages checked; '!**/_archive/**' is how -g excludes a dir.
# -H keeps the filename so awk can drop self-links. Wiki-root pages are meta and never orphans.
fd -e md . wiki/ -E _archive -x basename {} .md \
  | grep -vE '^lint-[0-9]' | sort -u > "$T/pages"
rg -oIN --no-heading -H -P '(?<!`)\[\[[^]|`]+' wiki/ \
   -g '!lint-[0-9]*.md' -g '!log.md' -g '!**/_archive/**' \
  | sed 's/\\$//' \
  | awk -F':\\[\\[' '{n=$1; sub(/.*\//,"",n); sub(/\.md$/,"",n); if (n != $2) print $2}' \
  | sort -u > "$T/linked"
fd -e md . wiki/ -d 1 -x basename {} .md | sort -u > "$T/meta"
O=$(comm -13 "$T/linked" "$T/pages" | comm -23 - "$T/meta" | paste -sd' ' -)
echo "## 3 orphans (informational; wiki-root meta excluded): ${O:-none}"

# Check 4 over wiki/sources/. A living doc is published: living-doc or has no published: (stubs from
# docs refreshes carry none); dated sources, published: unknown included, only get a count.
if [ "$DAYS" -eq 0 ]; then echo "## 4 stale: off"; exit 0; fi
CUT=$(date -d "$TODAY - $DAYS days" +%F 2>/dev/null || date -j -v-"$DAYS"d -f %F "$TODAY" +%F)
awk -F'\t' -v cut="$CUT" '$1 ~ /^wiki\/sources\// && $6 < cut {
  n = $1; sub(/.*\//, "", n); sub(/\.md$/, "", n)
  if ($7 == "" || $7 ~ /^living-doc/) print "L\t" n; else print "D\t" n }' "$T/fm" > "$T/stale"
echo "## 4 stale (fetched before $CUT): $(rg -c '^L' "$T/stale" || echo 0) living-doc, $(rg -c '^D' "$T/stale" || echo 0) dated (count only)"
L=$(rg '^L' "$T/stale" | cut -f2 | paste -sd' ' -); [ -z "$L" ] || echo "$L"
