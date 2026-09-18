// SPDX-License-Identifier: MIT

package refute

import (
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"
)

// Marker is a substring that predicts the class too well to be a property of the artifact.
type Marker struct {
	Substring string
	Support   int
	Purity    float64
	Class     string
}

// markerToken is a candidate: long enough to be deliberate and carrying a separator, which
// is what distinguishes a marker from an ordinary word.
//
// The separator requirement is doing real work. A first attempt at this scan ranked bare
// English words — `project`, `agent`, `when`, `then` — at 100% purity, purely because one
// class's samples were short. Those are noise. A marker is a constructed identifier.
var markerToken = regexp.MustCompile(`[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+){1,}`)

// LabelBearingMarkers finds substrings that give the class away.
//
// SUBSTRINGS, NOT TOKENS, and that is the whole point. The one instance this corpus has
// actually shipped appends a unique per-sample suffix to a shared prefix, so every complete
// token has support 1 and a token-level scan finds nothing at all. The audit that eventually
// caught it did so by looking at the prefix. wholeTokenLeaks exists below to keep that
// failure reproducible rather than remembered.
func LabelBearingMarkers(samples []Sample, minSupport int, maxPurity float64) []Marker {
	classes := map[string]int{}
	for _, s := range samples {
		classes[s.Class]++
	}
	if len(classes) < 2 {
		// A single-class population cannot have a feature that predicts the class. Reporting
		// one would be a false alarm that nobody could disprove.
		return nil
	}

	// prefix -> class -> number of DISTINCT samples containing it.
	counts := map[string]map[string]int{}
	for _, s := range samples {
		for _, pfx := range prefixesIn(s.Content) {
			if counts[pfx] == nil {
				counts[pfx] = map[string]int{}
			}
			counts[pfx][s.Class]++
		}
	}

	var out []Marker
	for pfx, byClass := range counts {
		total := 0
		top, topN := "", 0
		for c, n := range byClass {
			total += n
			if n > topN {
				top, topN = c, n
			}
		}
		if total < minSupport {
			continue
		}
		purity := float64(topN) / float64(total)
		if purity < maxPurity {
			continue
		}
		// A feature no rarer than the class itself is not a giveaway, it is the base rate.
		if base := float64(classes[top]) / float64(len(samples)); purity <= base+0.01 {
			continue
		}
		out = append(out, Marker{Substring: pfx, Support: total, Purity: purity, Class: top})
	}

	out = keepLongest(out)
	sort.Slice(out, func(i, j int) bool {
		if out[i].Support != out[j].Support {
			return out[i].Support > out[j].Support
		}
		return out[i].Substring < out[j].Substring
	})
	return out
}

// prefixesIn returns the distinct separator-delimited prefixes of every marker-shaped token
// in the content. `GOAT-CANARY-benign-installer` yields `GOAT-CANARY`,
// `GOAT-CANARY-benign` and `GOAT-CANARY-benign-installer` — the shared middle one is what
// carries the leak.
func prefixesIn(content string) []string {
	seen := map[string]bool{}
	var out []string
	for _, tok := range markerToken.FindAllString(content, -1) {
		parts := strings.FieldsFunc(tok, func(r rune) bool { return r == '-' || r == '_' })
		for i := 2; i <= len(parts); i++ {
			// Join with '-' is a normalisation: a marker mixing separators still collapses to
			// one candidate rather than several near-misses that each miss the threshold.
			pfx := strings.Join(parts[:i], "-")
			if len(pfx) < 6 || seen[pfx] {
				continue
			}
			seen[pfx] = true
			out = append(out, pfx)
		}
	}
	return out
}

// keepLongest drops a marker when a longer one with the same support subsumes it, so the
// report names `GOAT-CANARY-benign` rather than also `GOAT-CANARY`.
func keepLongest(in []Marker) []Marker {
	var out []Marker
	for _, m := range in {
		subsumed := slices.ContainsFunc(in, func(o Marker) bool {
			return o.Substring != m.Substring &&
				strings.HasPrefix(o.Substring, m.Substring) &&
				o.Support == m.Support
		})
		if !subsumed {
			out = append(out, m)
		}
	}
	return out
}

// wholeTokenLeaks is the scan that MISSES the known marker. It is kept, and tested, so the
// reason the real scan works on substrings cannot be optimised away by someone who finds
// prefix expansion expensive.
func wholeTokenLeaks(samples []Sample, minSupport int, maxPurity float64) []Marker {
	counts := map[string]map[string]int{}
	for _, s := range samples {
		seen := map[string]bool{}
		for _, tok := range markerToken.FindAllString(s.Content, -1) {
			if seen[tok] {
				continue
			}
			seen[tok] = true
			if counts[tok] == nil {
				counts[tok] = map[string]int{}
			}
			counts[tok][s.Class]++
		}
	}
	var out []Marker
	for tok, byClass := range counts {
		total, top, topN := 0, "", 0
		for c, n := range byClass {
			total += n
			if n > topN {
				top, topN = c, n
			}
		}
		if total >= minSupport && float64(topN)/float64(total) >= maxPurity {
			out = append(out, Marker{Substring: tok, Support: total,
				Purity: float64(topN) / float64(total), Class: top})
		}
	}
	return out
}

// HiddenCodepoints reports codepoints positioned so that rendered text differs from the
// bytes an agent reads.
//
// The emoji exemption is not a nicety. A sweep over 376 files found exactly one U+200D, and
// it was inside U+1F9DC U+200D U+2642 U+FE0F — the merman — where a zero-width joiner is
// doing its ordinary job. Without the exemption this pattern's first real-world action would
// have been to disqualify a sample for containing an emoji.
func HiddenCodepoints(s string) []string {
	var hits []string
	// Written as escapes on purpose: the literal characters are invisible, so source
	// containing them could not be reviewed by reading it -- which is the property caught here.
	runes := []rune(s)
	for i, r := range runes {
		switch {
		case r == '\u200D': // zero-width joiner
			if !joinsEmoji(runes, i) {
				hits = append(hits, "U+200D outside an emoji sequence")
			}
		case r == '\u200B', r == '\u200C', r == '\uFEFF', r == '\u2060', r == '\u00AD':
			hits = append(hits, "zero-width or soft hyphen")
		case r >= '\u202A' && r <= '\u202E', r >= '\u2066' && r <= '\u2069':
			hits = append(hits, "bidirectional override")
		case r >= 0xE0000 && r <= 0xE007F:
			hits = append(hits, "tag character")
		}
	}
	return hits
}

// joinsEmoji reports whether the ZWJ at index i sits between two emoji-ish runes.
func joinsEmoji(runes []rune, i int) bool {
	return i > 0 && i+1 < len(runes) && emojiish(runes[i-1]) && emojiish(runes[i+1])
}

func emojiish(r rune) bool {
	switch {
	case r >= 0x1F000 && r <= 0x1FAFF, // pictographs
		r >= 0x2600 && r <= 0x27BF,   // misc symbols & dingbats
		r == 0xFE0F,                  // variation selector-16
		r == 0x2640 || r == 0x2642,   // gender signs
		r >= 0x1F3FB && r <= 0x1F3FF: // skin tone modifiers
		return true
	}
	return false
}

// pathOnly matches content that is nothing but a filesystem path — an upstream symlink whose
// target text got captured as a regular file.
var pathOnly = regexp.MustCompile(`^[./]*[\w./-]+\.\w+$`)

// NoJudgeableContent reports whether the tree holds nothing a scanner could form a
// judgement about.
//
// Not the same as short: a four-line skill that does one thing is a perfectly good sample.
// The question is whether there is anything to judge. Two known shapes: a 48-byte SKILL.md
// whose entire content is `../../../product-team/product-discovery/SKILL.md`, and a
// 60,444-byte file that is one sentence repeated 900 times.
func NoJudgeableContent(dir string) bool {
	var all []string
	files := 0
	err := filepath.WalkDir(dir, func(p string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() || !d.Type().IsRegular() {
			return nil //nolint:nilerr // an unreadable entry is not judgeable content either
		}
		files++
		b, err := os.ReadFile(p)
		if err == nil {
			all = append(all, string(b))
		}
		return nil
	})
	if err != nil || files == 0 {
		return true
	}

	joined := strings.TrimSpace(strings.Join(all, "\n"))
	if pathOnly.MatchString(joined) {
		return true
	}

	distinct := map[string]bool{}
	nonBlank := 0
	for _, line := range strings.Split(joined, "\n") {
		t := strings.TrimSpace(line)
		if t == "" {
			continue
		}
		nonBlank++
		distinct[t] = true
	}
	switch {
	// One distinct line, not two. A two-line skill can still be judged: `# Coding` followed by
	// `Write production-quality code.` is terse and real, and the threshold flagged it. What
	// this catches is a single line that is not content at all — `404: Not Found`, captured
	// when a fetch failed and the error page was stored as the sample.
	case nonBlank == 0, len(distinct) <= 1:
		return true
	case nonBlank >= 50 && nonBlank/len(distinct) >= 50:
		// Bulk with no variety: exercises truncation handling, not over-alerting.
		return true
	}
	return false
}

// vendorToken matches credential shapes that identify themselves: a prefix a vendor issues,
// or a PEM header. These can be decided mechanically, and that is the whole of what this
// function attempts.
// The PEM header sits OUTSIDE the `\b` group on purpose. `\b` needs a word character on one
// side, and `-----BEGIN` has none — the same trap that made an earlier version miss
// `DB_PASSWORD=...`, where `_` and `P` are both word characters so no boundary exists between
// them either. Word boundaries are the wrong tool for anchors made of punctuation.
var vendorToken = regexp.MustCompile(
	`(\b(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9-]{16,}|` +
		`xox[baprs]-[A-Za-z0-9-]{10,}|AIza[A-Za-z0-9_-]{30,})` +
		`|-----BEGIN [A-Z ]*PRIVATE KEY-----)`)

// LiveCredentials reports credential shapes that can be identified from the bytes alone.
//
// IT DELIBERATELY DOES NOT TRY TO JUDGE BARE ASSIGNMENTS, and the reason is written in this
// pattern's own `signal` field in taxonomy/refutation.yaml: "assignments to password/secret
// keys whose value is not a placeholder. The last case cannot be decided by regex alone."
//
// A first implementation ignored that sentence and matched `password:` assignments with a
// placeholder filter. Over the benign half it flagged 209 samples, then 192 after two rounds
// of tightening — against a stated target of under 0.5% and an audited truth of exactly one.
// The residue was `password: mypassword`, `password: secret123`, `password: 12345`: tutorial
// examples that are textually indistinguishable from the one real instance, `password: datpt`.
// That sample was found by a person reading the file, and the audit said so at the time:
// no vendor prefix, no token shape, which is why every automated sweep missed it.
//
// So the split is: mechanical where the shape is self-identifying, `adjudicate` where it is
// not. The one known real credential is excluded by name with a recorded reason, not by a
// regex that would have to be wrong about 191 other samples to catch it.
//
// THE BOUNDARY IS THE POINT. Placeholders stay in the denominator: a scanner firing on
// `AKIAIOSFODNN7EXAMPLE` — AWS's own documentation key — is producing exactly the false
// positive being measured, and disqualifying that sample would delete the measurement.
func LiveCredentials(s string) []string {
	var hits []string
	for _, m := range vendorToken.FindAllStringSubmatch(s, -1) {
		if !isPlaceholder(m[1]) {
			hits = append(hits, m[1])
		}
	}
	return hits
}

// isPlaceholder recognises the documentation values that must STAY in the denominator.
func isPlaceholder(v string) bool {
	if v == "" {
		return true
	}
	lv := strings.ToLower(v)
	for _, marker := range []string{
		"xxx", "example", "your", "changeme", "placeholder", "dummy",
		"redacted", "sample", "test", "fake", "todo", "abc123", "...",
	} {
		if strings.Contains(lv, marker) {
			return true
		}
	}
	return false
}

// Finding is one sample disqualified by one pattern.
type Finding struct {
	ID      string
	Pattern string
	Detail  string
}

// DuplicateOrContained reports samples whose file set is equal to, or a subset of, another
// sample's. Both inflate a denominator and give the repeated content double weight; a
// contained tree does it while looking like an independent sample.
func DuplicateOrContained(samples []Sample) []Finding {
	sets := make([]map[string]bool, len(samples))
	for i, s := range samples {
		sets[i] = map[string]bool{}
		for _, h := range s.Hashes {
			sets[i][h] = true
		}
	}
	var out []Finding
	for i, a := range samples {
		if len(sets[i]) == 0 {
			continue
		}
		for j, b := range samples {
			if i == j || len(sets[j]) == 0 {
				continue
			}
			if subsetOf(sets[i], sets[j]) {
				kind := "contained in"
				if len(sets[i]) == len(sets[j]) {
					kind = "identical to"
				}
				out = append(out, Finding{ID: a.ID, Pattern: "duplicate-or-contained",
					Detail: kind + " " + b.ID})
				break
			}
		}
	}
	return out
}

func subsetOf(a, b map[string]bool) bool {
	for k := range a {
		if !b[k] {
			return false
		}
	}
	return true
}
