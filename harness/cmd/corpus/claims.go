// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// An independent audit checked roughly 355 numeric claims in this repository's prose and found
// 47 wrong. They were not 47 separate mistakes. They were four: a count is corrected in
// manifest/corpora.yaml, and the five documents that quote it — each with a Chinese mirror —
// are not. In two cases the manifest carried a hazard string saying the old number was wrong
// while the machine-readable field three lines above still held it.
//
// Fixing the numbers again would fix nothing. It had already been done once, one number at a
// time, and the drift came back because nothing could see it. This is the thing that sees it.
//
// SCOPE, STATED HONESTLY: this matches a number written immediately beside the word
// malicious/benign (or 恶意/良性) on a line that also names a manifest entry. It does not
// understand a bare table cell — `| 142 |` says nothing about which field it is — and it
// cannot check a document that paraphrases. Over the current documents it matches 9 claims.
// That is narrow, and it is the specific shape the drift has actually taken every time.

// How far above a number an entry may be named and still be understood to own it.
const claimWindow = 3

func max0(n int) int {
	if n < 0 {
		return 0
	}
	return n
}

var (
	claimEN = regexp.MustCompile(`(\d[\d,]*)\s+(malicious|benign)\b`)
	claimZH = regexp.MustCompile(`(\d[\d,]*)\s*个?\s*(恶意|良性)`)
)

type prosePlace struct {
	file  string
	line  int
	text  string
	value int
	field string // "malicious" or "benign"
	named []string
}

// ManifestClaimsInProse reports every place a document states a per-entry sample count that
// disagrees with the manifest.
func ManifestClaimsInProse(repoRoot string, classTotals map[string]int) []string {
	entries, err := manifest.Load(filepath.Join(repoRoot, "manifest", "corpora.yaml"))
	if err != nil {
		return []string{fmt.Sprintf("cannot read the manifest to cross-check prose claims: %v", err)}
	}

	// A document names an entry either by its manifest id or by the tail of its url, which is
	// how the catalogue and design tables refer to upstreams.
	declared := map[string]manifest.Entry{}
	alias := map[string]string{}
	for _, e := range entries.Entries {
		declared[e.ID] = e
		alias[e.ID] = e.ID
		if tail := urlTail(e.URL); tail != "" {
			alias[tail] = e.ID
		}
	}

	var problems []string
	for _, f := range proseFiles(repoRoot) {
		b, err := os.ReadFile(f)
		if err != nil {
			continue
		}
		lines := strings.Split(string(b), "\n")
		for i, line := range lines {
			// A window, not a single line. The catalogue names an upstream, then gives its url
			// on the next line, then its counts on the one after — so a line-scoped match sees
			// the number and not the entry it belongs to, which is how three of the four drifted
			// counts survived the first version of this check.
			named := entriesNamedIn(strings.Join(lines[max0(i-claimWindow):i+1], "\n"), alias)
			if len(named) == 0 {
				continue
			}
			for _, p := range claimsIn(line) {
				if matchesAny(p, named, declared) {
					continue
				}
				// "3,241 benign" is a claim about THIS corpus, not about an upstream entry, and
				// prose mentioning both in the same breath is normal. Widening the match to a
				// window made those collide; a value equal to a class total is the corpus's own
				// figure, which `stats` reports and this check has no business second-guessing.
				if classTotals[p.field] == p.value {
					continue
				}
				var want []string
				for _, id := range named {
					want = append(want, fmt.Sprintf("%s declares malicious %d, benign %d",
						id, declared[id].Malicious, declared[id].Benign))
				}
				problems = append(problems, fmt.Sprintf(
					"%s:%d says %d %s, which matches no entry it names (%s). A count corrected "+
						"in the manifest and not in the prose is the drift this check exists "+
						"for — fix the document, or the manifest if the document is right",
					rel(repoRoot, f), i+1, p.value, p.field, strings.Join(want, "; ")))
			}
		}
	}
	sort.Strings(problems)
	return problems
}

// matchesAny is deliberately permissive about WHICH named entry a number belongs to. A line
// naming two upstreams and one count is ambiguous to a regex and unambiguous to a reader; the
// check only fires when the number fits none of them, which is the case that is wrong however
// the ambiguity resolves.
func matchesAny(p prosePlace, named []string, declared map[string]manifest.Entry) bool {
	for _, id := range named {
		e := declared[id]
		if p.field == "malicious" && p.value == e.Malicious {
			return true
		}
		if p.field == "benign" && p.value == e.Benign {
			return true
		}
	}
	return false
}

func claimsIn(line string) []prosePlace {
	var out []prosePlace
	for _, m := range claimEN.FindAllStringSubmatch(line, -1) {
		if v, err := strconv.Atoi(strings.ReplaceAll(m[1], ",", "")); err == nil {
			out = append(out, prosePlace{value: v, field: m[2]})
		}
	}
	for _, m := range claimZH.FindAllStringSubmatch(line, -1) {
		if v, err := strconv.Atoi(strings.ReplaceAll(m[1], ",", "")); err == nil {
			field := "malicious"
			if m[2] == "良性" {
				field = "benign"
			}
			out = append(out, prosePlace{value: v, field: field})
		}
	}
	return out
}

func entriesNamedIn(line string, alias map[string]string) []string {
	seen := map[string]bool{}
	var out []string
	for name, id := range alias {
		if strings.Contains(line, name) && !seen[id] {
			seen[id] = true
			out = append(out, id)
		}
	}
	sort.Strings(out)
	return out
}

func urlTail(u string) string {
	parts := strings.Split(strings.TrimSuffix(u, "/"), "/")
	if len(parts) < 2 {
		return ""
	}
	return strings.Join(parts[len(parts)-2:], "/")
}

func proseFiles(repoRoot string) []string {
	var out []string
	docs, _ := filepath.Glob(filepath.Join(repoRoot, "docs", "*.md"))
	out = append(out, docs...)
	for _, n := range []string{"README.md", "README.zh-CN.md", "NOTICE", "NOTICE.zh-CN.md"} {
		p := filepath.Join(repoRoot, n)
		if _, err := os.Stat(p); err == nil {
			out = append(out, p)
		}
	}
	return out
}
