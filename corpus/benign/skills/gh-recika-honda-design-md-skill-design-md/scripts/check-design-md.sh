#!/usr/bin/env bash
# check-design-md.sh: mechanical checks on a DESIGN.md draft written by the design-md skill.
#
# Usage: check-design-md.sh <DESIGN.md> [picks.txt]
#
# What it proves (the judgment checks stay with the model, see output-template.md):
#   - every leaf token in colors / typography / rounded / spacing / elevation / motion /
#     breakpoints carries a tier comment: chosen, derived, or defaulted
#   - `derived` cites a public rule (sec.1-7 or sec.9), never only the skill defaults (sec.8)
#   - `defaulted` cites sec.8, names an unverified row, or realizes a pick with no literal
#     value on the site (`for pick "<option text>", site N`; with picks.txt, site N exists
#     and the quoted text, trimmed, equals the option text of a `take N` or `said N` line)
#   - `chosen` names `site N` or `user`; with picks.txt, site N exists and the token's full
#     path matches a pattern of a `take N` or `said N` line (an option the user picked or
#     typed). A path that only matches a `decline N` line fails as "offered and not picked";
#     a path that matches both a take and a declined option fails too, unless a said line
#     (the user's own words) also covers it. `chosen: user`
#     needs a `user <group>` line.
#   - no hex value inside `components`
#   - a `rounded` or `spacing` length carries a unit (`0px`, not `0` or "0"): the Google
#     linter silently drops a unitless length; typography values are not checked
#   - a `colors` value whose tier comment contains the word `achromatic` is a pure gray hex
#     (3 or 6 digits, R = G = B)
#   - a defaulted `spacing.page-margin` holding `vw` or `%` is never set beside a chosen
#     `spacing.container`: the fluid margin narrows the width the user picked (key order free)
#   - every numbered item in `## Sources` (one per reference site, running to the next item,
#     a blank line or a heading) says where its values were read: `measured:`
#   - every required body heading appears exactly once, and no `##` heading is duplicated
#
# picks.txt (written during the interview, SKILL.md Step 3), one fact per line:
#   site <N> <url>     pick <N> <structure|component|color-type|mood>
#   take <N> <bundle> <patterns> | <option text>      (a Call B option the user picked)
#   decline <N> <bundle> <patterns> | <option text>   (a Call B option offered, not picked)
#   said <N> <bundle> <patterns> | <the user's words> (a free-text Other answer in Call B)
#   user <group>       reject <N> <text>
# <patterns> is a comma-separated list of token paths (`colors.primary`, `spacing.*`,
# `typography.display-*.fontFamily`), `*` matching any run of characters, or `-` when the
# option covers no token. A typography pattern names a property or ends in `*`. A `said`
# line's patterns are written after the answer, so they may not contain `*`. A take or said
# needs a `pick N <bundle>` line for its bundle; every record's N needs a `site N` line.
# `#` starts a comment at the start of a line, or after a space when a space follows it, so
# a hex such as (#24363f) inside option text is kept. On take / decline / said lines only
# the part before the first `|` can hold a comment: everything after it is option text.
#
# Output: one "FAIL <file>:<line>: <reason>" line per problem, then one summary line:
#   "check: <PASS|FAIL> (<n> failures); chosen <c>, derived <d>, defaulted <f>, open <o>"
# Exit: 0 pass, 1 at least one FAIL, 2 usage or unreadable input.
#
# Portability: bash 3.2+ and POSIX awk (stock macOS awk works).

set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  printf 'usage: check-design-md.sh <DESIGN.md> [picks.txt]\n' >&2
  exit 2
fi

design=$1
picks=${2:-}

if [ ! -r "$design" ]; then
  printf 'check-design-md.sh: cannot read %s\n' "$design" >&2
  exit 2
fi
if [ -n "$picks" ] && [ ! -r "$picks" ]; then
  printf 'check-design-md.sh: cannot read %s\n' "$picks" >&2
  exit 2
fi

# Without picks.txt the provenance of `chosen` cannot be proven; say so loudly instead of
# passing silently. An empty file stands in so awk always gets two inputs.
picks_input=$picks
if [ -z "$picks" ]; then
  printf 'WARN: no picks.txt given; chosen tokens are checked for form only, not provenance\n'
  picks_input=/dev/null
fi

# awk reads an operand containing "=" as a variable assignment; a ./ prefix keeps it a file.
case $design in /*) design_arg=$design ;; *) design_arg=./$design ;; esac
case $picks_input in /*) picks_arg=$picks_input ;; *) picks_arg=./$picks_input ;; esac

awk -v design_name="$design" -v picks_name="${picks:-picks.txt}" -v have_picks="${picks:+1}" '
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
function fail(file, line, msg) { printf "FAIL %s:%d: %s\n", file, line, msg; failures++ }

# Blank out quoted strings (same length) so a "#hex" value is not read as a comment start,
# while the comment itself can still be cut from the original line at the same position.
function mask_quotes(s,   out, i, c, q) {
  out = ""; q = ""
  for (i = 1; i <= length(s); i++) {
    c = substr(s, i, 1)
    if (q == "" && (c == "\"" || c == "\047")) { q = c; out = out c; continue }
    if (q != "" && c == q) { q = ""; out = out c; continue }
    out = out (q == "" ? c : "x")
  }
  return out
}

# Token-path glob -> anchored regex: `*` is any run of characters, `.` is literal.
# Built char by char so no backslash escaping is involved (BSD and GNU awk differ there).
function glob_re(p,   i, c, out) {
  out = "^"
  for (i = 1; i <= length(p); i++) {
    c = substr(p, i, 1)
    if (c == "*") out = out ".*"
    else if (c == ".") out = out "[.]"
    else out = out c
  }
  return out "$"
}

# Record number of the first option on site s whose patterns match path, or 0. side is
# "picked" (take and said lines) or "declined" (decline lines).
function option_for(side, s, path,   j, r) {
  for (j = 1; j <= n_pat; j++) {
    r = pat_rec[j]
    if (rec_side[r] == side && rec_site[r] == s && path ~ pat_re[j]) return r
  }
  return 0
}

# Record number of the first said line on site s whose patterns match path, or 0.
function said_for(s, path,   j, r) {
  for (j = 1; j <= n_pat; j++) {
    r = pat_rec[j]
    if (rec_kind[r] == "said" && rec_site[r] == s && path ~ pat_re[j]) return r
  }
  return 0
}

# Remember that a record names site s, so END can fail it when no `site s` line exists
# (checked there so the order of lines in picks.txt is free).
function needs_site(kind, s) { n_ref++; ref_kind[n_ref] = kind; ref_site[n_ref] = s; ref_line[n_ref] = FNR }

# 1 when v (quotes allowed) is a 3- or 6-digit hex with R = G = B, else 0.
function is_pure_gray(v,   h) {
  h = tolower(v); gsub(/["\047]/, "", h)
  if (h ~ /^#[0-9a-f][0-9a-f][0-9a-f]$/)
    return substr(h, 2, 1) == substr(h, 3, 1) && substr(h, 3, 1) == substr(h, 4, 1)
  if (h ~ /^#[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]$/)
    return substr(h, 2, 2) == substr(h, 4, 2) && substr(h, 4, 2) == substr(h, 6, 2)
  return 0
}

# End the open `## Sources` item, failing it when none of its lines said `measured:`.
function close_source_item() {
  if (src_item != "" && !src_measured)
    fail(design_name, src_line, "Sources item " src_item ": no \"measured:\"; say where this site\047s values were read (measured: rendered page at 1440px | static CSS (facts.txt))")
  src_item = ""; src_measured = 0
}

BEGIN {
  failures = 0; n_chosen = 0; n_derived = 0; n_defaulted = 0; n_open = 0
  n_rec = 0; n_pat = 0; n_ref = 0
  split("colors typography rounded spacing elevation motion breakpoints", g, " ")
  for (i in g) token_group[g[i]] = 1
  split("structure component color-type mood", g, " ")
  for (i in g) bundle_name[g[i]] = 1
  required_list = "Agent Guide|Hard Baseline|Layout Heuristics|Overview|Colors|Typography|Layout|Elevation & Depth|Shapes|Components|Interaction States|Motion|Responsive Behavior|Imagery & Iconography|Voice & Content|Accessibility|Do'"'"'s and Don'"'"'ts|Intent|Sources|Iteration Guide|Known Gaps|Brief (Japanese)"
  n_required = split(required_list, required, "|")
}

{ sub(/\r$/, "") }   # tolerate CRLF files

# ---- pass 1: picks.txt (phase is set to 2 on the command line before DESIGN.md) ----
phase != 2 {
  line = $0
  if (line ~ /^[ \t]*#/) next
  # take / decline / said lines: everything after the first | is option text, kept verbatim
  # (a " # " inside it is text), so only the part before the bar can hold a comment.
  word = trim(line); sub(/[ \t].*/, "", word)
  has_text = 0; text = ""
  if ((word == "take" || word == "decline" || word == "said") && index(line, "|")) {
    bar = index(line, "|")
    has_text = 1; text = trim(substr(line, bar + 1))
    line = substr(line, 1, bar - 1)
  }
  if (match(line " ", /[ \t]#[ \t]/)) line = substr(line, 1, RSTART - 1)
  line = trim(line)
  if (line == "") next
  n = split(line, f, /[ \t]+/)
  if (f[1] == "site") {
    if (f[2] !~ /^[1-9][0-9]*$/) { fail(picks_name, FNR, "site needs a number: " line); next }
    site[f[2]] = 1
  } else if (f[1] == "pick") {
    if (f[2] !~ /^[1-9][0-9]*$/ || n < 3) { fail(picks_name, FNR, "pick needs <N> <bundle>: " line); next }
    if (!(f[3] in bundle_name)) { fail(picks_name, FNR, "unknown bundle \"" f[3] "\" (structure|component|color-type|mood)"); next }
    picked[f[2], f[3]] = 1
    needs_site("pick", f[2])
  } else if (f[1] == "take" || f[1] == "decline" || f[1] == "said") {
    kind = f[1]
    usage = kind " needs <N> <bundle> <patterns> | <option text>: " trim($0)
    if (!has_text || n != 4 || f[2] !~ /^[1-9][0-9]*$/ || text == "") { fail(picks_name, FNR, usage); next }
    if (!(f[3] in bundle_name)) { fail(picks_name, FNR, "unknown bundle \"" f[3] "\" (structure|component|color-type|mood)"); next }
    # Patterns: `-` alone (covers no token), or <group>.<key>[.<prop>] globs whose group is a
    # literal token group, so one option can never cover every group at once. A typography
    # token is <role>.<prop>, so a two-part typography pattern without `*` covers nothing.
    np = split(f[4], p, ",")
    bad_found = 0; bad = ""; hint = ""
    if (f[4] != "-") {
      for (i = 1; i <= np; i++) {
        grp = p[i]; sub(/[.].*/, "", grp)
        if (p[i] == "") { bad_found = 1; bad = p[i]; hint = "an empty element; remove the stray comma"; break }
        if (p[i] !~ /^[a-z]+[.][A-Za-z0-9_*-]+([.][A-Za-z0-9_*-]+)*$/ || !(grp in token_group)) {
          bad_found = 1; bad = p[i]; hint = "use <group>.<key> or <group>.<role>.<prop>, * as wildcard, or - for none"; break
        }
        if (grp == "typography" && p[i] ~ /^typography[.][^.]+$/ && index(p[i], "*") == 0) {
          bad_found = 1; bad = p[i]; hint = "covers no property; write " p[i] ".* or name the property, e.g. " p[i] ".fontFamily"; break
        }
      }
    }
    if (bad_found) { fail(picks_name, FNR, kind ": bad token pattern \"" bad "\" (" hint ")"); next }
    # A said line is written after the user answered, so it may not reach wider than the
    # attribute they named: no wildcards.
    if (kind == "said" && index(f[4], "*")) { fail(picks_name, FNR, "said: pattern \"" f[4] "\" has a *; a free-text answer names only the tokens for the attribute the user named, one by one"); next }
    n_rec++
    rec_kind[n_rec] = kind; rec_site[n_rec] = f[2]; rec_bundle[n_rec] = f[3]
    rec_side[n_rec] = (kind == "decline" ? "declined" : "picked")
    rec_text[n_rec] = text; rec_line[n_rec] = FNR
    option_text[rec_side[n_rec], f[2], text] = n_rec
    needs_site(kind, f[2])
    if (f[4] != "-") for (i = 1; i <= np; i++) { n_pat++; pat_rec[n_pat] = n_rec; pat_re[n_pat] = glob_re(p[i]) }
  } else if (f[1] == "user") {
    if (!(f[2] in token_group)) { fail(picks_name, FNR, "user needs a token group: " line); next }
    user_group[f[2]] = 1
  } else if (f[1] == "note") {
    fail(picks_name, FNR, "\"note\" is no longer a record; write each picked option as \"take <N> <bundle> <patterns> | <option text>\" and each offered, unpicked one as \"decline\"")
  } else if (f[1] == "reject") {
    if (f[2] ~ /^[1-9][0-9]*$/) needs_site("reject", f[2])
  } else {
    fail(picks_name, FNR, "unknown record \"" f[1] "\" (site|pick|take|decline|said|user|reject)")
  }
  next
}

# ---- pass 2: DESIGN.md ----
FNR == 1 {
  if ($0 != "---") { fail(design_name, 1, "front matter must start with --- on line 1"); in_fm = 0; fm_done = 1 }
  else { in_fm = 1 }
  next
}

in_fm && $0 == "---" { in_fm = 0; fm_done = 1; next }

in_fm {
  raw = $0
  # Comment-only lines: count open tokens, nothing else to check.
  if (raw ~ /^[ \t]*#/) {
    if (raw ~ /^[ \t]*#[ \t]*[A-Za-z0-9_.-]+:[ \t]*open/) n_open++
    next
  }
  if (raw ~ /^[A-Za-z]/) {           # top-level key starts a group
    top = raw; sub(/:.*/, "", top); parent = ""; next
  }
  bare = mask_quotes(raw)
  comment = ""
  if (match(bare, /[ \t]#/)) { comment = trim(substr(raw, RSTART + 2)); bare = substr(bare, 1, RSTART - 1) }

  if (top == "components") {
    if (raw ~ /["\047]#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]/) fail(design_name, FNR, "hex value inside components; reference a token instead")
    next
  }
  if (!(top in token_group)) next

  # A leaf has a value after the colon; a key with nothing after it opens a nested map
  # (a typography role), remembered so failures name the full path.
  key = trim(bare); sub(/:.*/, "", key)
  if (bare !~ /:[ \t]*[^ \t]/) { parent = key; next }
  if (bare ~ /^  [^ ]/) parent = ""
  if (parent != "") key = parent "." key

  if (bare ~ /:[ \t]*[{[]/) { fail(design_name, FNR, top "." key ": flow map or list; write it in block form, one property per line, each with its own tier"); next }
  # The value as written (quotes kept), cut where bare was cut so the comment is not in it.
  ci = index(bare, ":"); val = trim(substr(raw, ci + 1, length(bare) - ci))
  # The Google linter silently drops a unitless length (rounded.none: 0), and every
  # {rounded.none} reference then breaks. Typography (lineHeight, letterSpacing) is not a length.
  if ((top == "rounded" || top == "spacing") && val ~ /^["\047]?-?([0-9]+|[0-9]*[.][0-9]+)["\047]?$/)
    fail(design_name, FNR, top "." key ": length without a unit (" val "); write it with a unit, e.g. 0px")
  if (comment == "") { fail(design_name, FNR, top "." key ": no tier comment (chosen | derived | defaulted)"); next }

  # Remembered for END: a defaulted fluid page margin beside a chosen container, in either order.
  tier = comment; sub(/:.*/, "", tier)
  if (top "." key == "spacing.container") container_tier = tier
  if (top "." key == "spacing.page-margin") { margin_tier = tier; margin_value = val; margin_line = FNR }
  # A comment that says achromatic promises a gray with no hue (sec.8 neutral palette seed).
  if (top == "colors" && tolower(comment) ~ /(^|[^a-z])achromatic([^a-z]|$)/ && !is_pure_gray(val))
    fail(design_name, FNR, top "." key ": the tier comment says achromatic, but " val " is not a pure gray hex (R = G = B); seed the neutral palette at chroma 0 or drop the word")

  if (comment ~ /^chosen:/) {
    n_chosen++
    if (comment ~ /^chosen:[ \t]*skill default/) { fail(design_name, FNR, top "." key ": a skill default labeled chosen; use defaulted: <row>, sec.8"); next }
    if (comment ~ /^chosen:[ \t]*site[ \t]+[0-9]/) {
      s = comment; sub(/^chosen:[ \t]*site[ \t]+/, "", s); sub(/[^0-9].*/, "", s)
      if (have_picks) {
        if (!(s in site)) { fail(design_name, FNR, top "." key ": chosen from site " s ", which picks.txt does not list"); next }
        r = option_for("picked", s, top "." key)
        d = option_for("declined", s, top "." key)
        # Words the user typed outrank an option they left unticked: a said line
        # that covers the path settles it, whatever was declined.
        if (r && rec_kind[r] != "said") r_said = said_for(s, top "." key); else r_said = r
        if (r_said) d = 0
        if (r && d) fail(design_name, FNR, top "." key ": chosen from site " s ", but it is covered by a picked option (\"" rec_text[r] "\") and a declined option (\"" rec_text[d] "\"); where the two overlap the truthful tier is derived or defaulted, unless the two options'"'"' patterns were in fact disjoint")
        else if (d) fail(design_name, FNR, top "." key ": chosen from site " s ", but the user was offered this there and did not pick it (declined: \"" rec_text[d] "\"); use derived or defaulted")
        else if (!r) fail(design_name, FNR, top "." key ": chosen from site " s ", but no picked option on site " s " covers it (no take or said " s " line with a matching pattern)")
      }
    } else if (comment ~ /^chosen:[ \t]*user([ \t(;,]|$)/) {
      if (have_picks && !(top in user_group)) fail(design_name, FNR, top "." key ": chosen: user, but picks.txt has no \"user " top "\" line")
    } else {
      fail(design_name, FNR, top "." key ": chosen must name \"site N\" or \"user\"")
    }
  } else if (comment ~ /^derived:/) {
    n_derived++
    # Public-rule sections are 1-7 and 9; sec.8 holds the skill defaults.
    cited = comment " "
    if (cited !~ /sec\.[0-9]/) { fail(design_name, FNR, top "." key ": derived without a rule citation (sec.N)"); next }
    if (cited !~ /sec\.[1-79][^0-9]/) fail(design_name, FNR, top "." key ": derived cites no public rule (sec.1-7 or sec.9); sec.8 values are defaulted")
  } else if (comment ~ /^defaulted:/) {
    n_defaulted++
    # A value the skill supplies to realize a pick with no literal value on the site
    # ("device fonts" -> system-ui) is defaulted and names the pick instead of a sec.8 row.
    for_pick = (comment ~ /for pick "/)
    if (for_pick) {
      if (!match(comment, /for pick "[^"]+",[ \t]*site[ \t]+[0-9]+/)) { fail(design_name, FNR, top "." key ": write the pick as for pick \"<option text>\", site N"); next }
      s = substr(comment, RSTART, RLENGTH); sub(/.*site[ \t]+/, "", s)
      q = substr(comment, RSTART, RLENGTH); sub(/^for pick "/, "", q); sub(/".*/, "", q); q = trim(q)
      if (have_picks && !(s in site)) { fail(design_name, FNR, top "." key ": defaulted for a pick on site " s ", which picks.txt does not list"); next }
      # The quote is what exempts this value from citing sec.8, so it must be a real pick:
      # the option text of a take or said line on that site, not a declined or invented one.
      if (have_picks && !(("picked", s, q) in option_text)) {
        if (("declined", s, q) in option_text) fail(design_name, FNR, top "." key ": defaulted for pick \"" q "\", site " s ", but that option was offered there and not picked (a decline line); cite a sec.8 row or use derived")
        else fail(design_name, FNR, top "." key ": defaulted for pick \"" q "\", site " s ", but no picked option on site " s " has that text (copy it exactly from a take or said " s " line)")
        next
      }
    }
    if (!for_pick && (comment " ") !~ /sec\.8[^0-9]/ && comment !~ /unverified/) fail(design_name, FNR, top "." key ": defaulted must cite sec.8, an unverified row, or for pick \"<option text>\", site N")
  } else {
    fail(design_name, FNR, top "." key ": comment does not start with chosen:, derived:, or defaulted:")
  }
  next
}

# Body: headings outside fenced code blocks.
/^```/ { in_fence = !in_fence; next }
!in_fence && /^## / {
  h = substr($0, 4); h = trim(h)
  if (h in seen) fail(design_name, FNR, "duplicate heading \"## " h "\"")
  seen[h]++
  close_source_item(); in_sources = (h == "Sources")
  next
}

# Sources: a numbered item runs to the next numbered item, a blank line, or a heading.
!in_fence && in_sources {
  if ($0 ~ /^[0-9]+[.] /) { close_source_item(); src_item = $0; sub(/[.].*/, "", src_item); src_line = FNR }
  else if ($0 ~ /^#/ || trim($0) == "") { close_source_item(); next }
  if (src_item != "" && index($0, "measured:")) src_measured = 1
}

END {
  # Checked here, not while reading picks.txt, so the order of pick and take lines is free.
  for (i = 1; i <= n_ref; i++)
    if (!(ref_site[i] in site))
      fail(picks_name, ref_line[i], ref_kind[i] " " ref_site[i] ": no \"site " ref_site[i] " <url>\" line; every record names a site listed in picks.txt")
  for (r = 1; r <= n_rec; r++)
    if (rec_side[r] == "picked" && !((rec_site[r], rec_bundle[r]) in picked))
      fail(picks_name, rec_line[r], rec_kind[r] " " rec_site[r] " " rec_bundle[r] ": no \"pick " rec_site[r] " " rec_bundle[r] "\" line; an option belongs to a bundle the user ticked in Call A")
  if (!fm_done || in_fm) fail(design_name, NR, "front matter is not closed with ---")
  close_source_item()
  # The sec.8 clamp is tuned to the default 1120 container; beside a chosen container its
  # vw step cuts into the width the user picked.
  if (container_tier == "chosen" && margin_tier == "defaulted" && margin_value ~ /vw|%/)
    fail(design_name, margin_line, "spacing.page-margin: a defaulted fluid margin (" margin_value ") beside a chosen spacing.container narrows the width the user picked; use the fixed 24px (sec.8, page margin beside a chosen container) or the site\047s measured side padding")
  for (i = 1; i <= n_required; i++) if (!(required[i] in seen)) fail(design_name, 0, "missing required heading \"## " required[i] "\"")
  printf "check: %s (%d failures); chosen %d, derived %d, defaulted %d, open %d\n", (failures ? "FAIL" : "PASS"), failures, n_chosen, n_derived, n_defaulted, n_open
  exit (failures ? 1 : 0)
}
' "$picks_arg" phase=2 "$design_arg"
