#!/bin/sh
# Continuous permuter sweep over near-misses: tools/permute_all.sh SCRATCHDIR [secs] [queuefile]
# Processes each address in the queue once (tracked in permuter/done.txt), re-reads the queue
# forever (post_run.py appends new near-misses). Integrates score-0 results and old_agbcc matches.
# PID file: permuter/sweep.pgid (kill with: kill -- -$(cat permuter/sweep.pgid)).
cd "$(dirname "$0")/.."
S=$1; SECS=${2:-300}; Q=${3:-permuter/queue.txt}
mkdir -p permuter; touch permuter/done.txt "$Q"
ps -o pgid= -p $$ | tr -d ' ' > permuter/sweep.pgid
while true; do
  for a in $(grep -vxF -f permuter/done.txt "$Q" | sort -u); do
    echo "$a" >> permuter/done.txt
    grep -q "^$a done$" claims.txt && continue
    [ -f "$S/$a.c" ] || continue
    rm -rf "permuter/$a"
    python3 tools/permute.py "$a" "$S/$a.c" "$SECS" >/dev/null 2>&1
    out=$(ls -d permuter/$a/output-0-* 2>/dev/null | head -1)
    if [ -n "$out" ]; then
      if tools/integrate_one.sh "$a" "$out/source.c" "sub_$a" >/dev/null 2>&1; then echo "$a MATCHED+committed"; else echo "$a matched but integrate failed"; fi
    elif CC1=$PWD/tools/agbcc/bin/old_agbcc python3 tools/check_func.py "$S/$a.c" "$a" >/dev/null 2>&1 &&
         CC1=$PWD/tools/agbcc/bin/old_agbcc tools/integrate_one.sh "$a" "$S/$a.c" "sub_$a" >/dev/null 2>&1; then
      echo "$a MATCHED with old_agbcc+committed"
    else
      echo "$a no match"
    fi
  done
  sleep 300
done
