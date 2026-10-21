#!/usr/bin/env bash
# Every examples/*.before.txt must fail check.py and every *.after.txt must pass,
# plus a few hand-made screens that pin the counting rules.
set -uo pipefail
cd "$(dirname "$0")/.."
pass=0 fail=0
expect() {  # expect <exit code> <label> <screens text>
  local want=$1 label=$2 got
  printf '%b' "$3" | python3 scripts/check.py - >/dev/null; got=$?
  if [ "$got" = "$want" ]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "FAIL $label: exit $got, want $want"; fi
}
expect_out() {  # expect_out <label> <text the output holds> <screens text>
  if printf '%b' "$3" | python3 scripts/check.py - | grep -qF "$2"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "FAIL $1: no \"$2\" in the output"; fi
}
for f in examples/*.before.txt; do expect 1 "$f" "$(cat "$f")"; done
for f in examples/*.after.txt; do expect 0 "$f" "$(cat "$f")"; done
thirteen="One two three four five six.\nseven eight nine ten eleven twelve thirteen"
expect 0 "15 words pass" "picture: a bike\n$thirteen 👇\n[Buy now]\n"
expect 1 "16 words fail" "picture: a bike\n$thirteen fourteen 👇\n[Buy now]\n"
expect 1 "quoted picture text counts" "picture: a bike \"Fast\"\n$thirteen 👇\n[Buy now]\n"
expect 0 "a 6-word headline passes" "☰\npicture: a ring\nA ring that tracks your sleep. 👇\n[Shop now]\n(Log in)\n"
expect 1 "a 7-word headline fails" "picture: a ring\nA ring that tracks your sleep well 👇\n[Shop now]\n"
expect 1 "a two-sentence headline fails" "picture: a ring\nSmart ring. Better sleep. 👇\n[Shop now]\n"
expect 0 "a price or date is not a sentence end" "picture: a ring\nRings from \$299.99, out 10.23 👇\n[Shop now]\n"
expect 0 "circled steps, emoji and ✓ are not words" "① Pick › ② Pay › ③ Ride ✓ 👇\npicture: a bike\n\$24/month\n[Buy now]\n"
expect 1 "two buttons fail" "picture: a bike\nGet a bike 👇\n[Buy now] [Compare plans]\n"
expect 1 "tribe words fail" "picture: a bike\nThe seamless bike platform 👇\n[Buy now]\n"
expect 1 "a later screen failing fails the file" "Hi 👇\n[Go]\n---\n$thirteen fourteen fifteen sixteen\n"
# A text field: {placeholder}, one, right above the button, its words counted.
expect 0 "a field right above its button passes" "picture: the logo\nSearch the web with Google.\n{Search Google}\n👇\n[Google Search]\n"
expect 0 "a field and its button on one line pass" "picture: a letter\nA weekly letter about bikes.\n{Your email} [Subscribe]\n"
expect 1 "two fields fail" "picture: a letter\nA weekly letter about bikes.\n{Your name}\n{Your email}\n👇\n[Subscribe]\n"
expect 1 "a field not right above the button fails" "picture: the logo\n{Search Google}\nSearch the web with Google.\n👇\n[Google Search]\n"
expect 1 "a field under its button fails" "picture: the logo\nSearch the web.\n[Search]\n{Search Google}\n"
expect 1 "a field's placeholder words count" "picture: a bike\n$thirteen\n{Your email here}\n[Buy now]\n"
expect 0 "a field is not the headline" "picture: a sky\n{Type any city to see its weather}\n👇\n[Show weather]\n"
expect_out "a field's button that names no action warns" "does not say what the typing does" "picture: a letter\nA weekly letter about bikes.\n{Your email}\n👇\n[Submit]\n"
# Hype: praise any site could print about itself.
expect 1 "hype fails: world's best" "picture: a shop\nThe world's best commerce store 👇\n[Start a shop]\n"
expect 1 "hype fails: world’s best, curly quote" "picture: a shop\nThe world’s best shop 👇\n[Start a shop]\n"
expect 1 "hype fails: trusted" "picture: a bank card\nA bank trusted by millions 👇\n[Open an account]\n"
expect 1 "hype fails: #1, and #1 is not a heading" "picture: a bike\n#1 bike shop 👇\n[Buy now]\n"
expect 1 "hype fails in quoted picture words" "picture: a box \"All-in-one\"\nA box for your tools 👇\n[Buy now]\n"
expect 1 "hype fails: Leading, any case" "picture: a bike\nLeading bikes for kids 👇\n[Buy now]\n"
expect 0 "hype is whole words only: misleading and #10 pass" "picture: a bike\nNo misleading prices, #10 bike 👇\n[Buy now]\n"
echo "$pass pass, $fail fail"
[ "$fail" = 0 ]
