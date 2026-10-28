// SPDX-License-Identifier: MIT

package leakage

import (
	"math"
	"path/filepath"
	"sort"
	"strings"
)

// Why this exists beside Check and CrossPopulation.
//
// Both of those ask whether a feature is PURE — whether nearly every sample carrying it is one
// class. A language skew is a different question and neither can see it. On the skills surface
// 39% of malicious samples carry a Python file against 7% of benign ones; `ext:.py` is then
// about 44% pure, nowhere near the 95% bar, and passes silently. Yet a scanner that parses only
// Python sees a corpus that is mostly Python on one side and mostly not on the other, and its
// recall and false-positive figures describe that accident as much as its rules.
//
// The mcp surface was the extreme case before the TypeScript work: no malicious sample carried
// TypeScript while a fifth of benign servers did, so `.ts` predicted benign perfectly and a
// scanner blind to TypeScript lost nothing on the malicious side. Nothing reported it. This
// reports it, and fails the build if that state comes back.

// LanguageFamilies are the source languages a scanner might parse or skip. Extensions are
// compared lower-cased.
var LanguageFamilies = map[string][]string{
	"python":     {".py"},
	"js/ts":      {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"},
	"shell":      {".sh", ".bash", ".zsh"},
	"powershell": {".ps1", ".psm1"},
}

const (
	// SkewRatio is how many times more often one side must carry a language before it is
	// printed. Below 2x the difference is real but not one a scanner's coverage turns into a
	// different corpus; mcp's Python (91% against 52%) sits just under it.
	SkewRatio = 2.0

	// BlindSpotShare is the floor for a FAILURE: a language absent from one class and carried
	// by at least this share of the other. The TypeScript case was 0% against 22%. Shell
	// scripts in 4% of benign MCP servers are worth printing, not worth failing a build over.
	BlindSpotShare = 0.20
)

// LanguageRow is one surface x language-family cell. "Benign" means every sample a scanner
// should not flag — benign and hard-negative — because that is the side its false positives
// are counted on.
type LanguageRow struct {
	Surface, Family          string
	Malicious, MaliciousWith int
	Benign, BenignWith       int
}

func (r LanguageRow) MaliciousShare() float64 { return share(r.MaliciousWith, r.Malicious) }
func (r LanguageRow) BenignShare() float64    { return share(r.BenignWith, r.Benign) }

// Toward names the class that carries the language more often.
func (r LanguageRow) Toward() string {
	if r.MaliciousShare() >= r.BenignShare() {
		return "malicious"
	}
	return "benign"
}

// Ratio is the larger share over the smaller; +Inf when one side never carries it.
func (r LanguageRow) Ratio() float64 {
	hi, lo := r.MaliciousShare(), r.BenignShare()
	if lo > hi {
		hi, lo = lo, hi
	}
	if lo == 0 {
		return math.Inf(1)
	}
	return hi / lo
}

// BlindSpot is the failing case: one class never carries the language and the other carries
// it often enough that a scanner unable to parse it would be judged on a different corpus.
func (r LanguageRow) BlindSpot() bool {
	hi, lo := r.MaliciousShare(), r.BenignShare()
	if lo > hi {
		hi, lo = lo, hi
	}
	return lo == 0 && hi >= BlindSpotShare
}

// LanguageSkew returns the surface x family cells worth reporting: both classes have at least
// MinSupport samples on the surface, at least MinSupport samples carry the language on the
// side that carries it more, and that side carries it at least SkewRatio times as often.
func LanguageSkew(samples []Sample) []LanguageRow {
	cells := tally(samples)
	var out []LanguageRow
	for _, r := range cells {
		if reportable(r) {
			out = append(out, r)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Surface != out[j].Surface {
			return out[i].Surface < out[j].Surface
		}
		return out[i].Family < out[j].Family
	})
	return out
}

// tally counts every surface x family cell. A sample on two surfaces counts under both, the
// same convention `make stats` uses for its surface table.
func tally(samples []Sample) []LanguageRow {
	type key struct{ surface, family string }
	cells := map[key]*LanguageRow{}
	totals := map[string][2]int{} // surface -> {malicious, benign}
	for _, s := range samples {
		mal := s.Class == "malicious"
		fams := familiesOf(s.Files)
		for _, surf := range s.Surfaces {
			t := totals[surf]
			if mal {
				t[0]++
			} else {
				t[1]++
			}
			totals[surf] = t
			for fam := range LanguageFamilies {
				c := cells[key{surf, fam}]
				if c == nil {
					c = &LanguageRow{Surface: surf, Family: fam}
					cells[key{surf, fam}] = c
				}
				if fams[fam] && mal {
					c.MaliciousWith++
				} else if fams[fam] {
					c.BenignWith++
				}
			}
		}
	}
	out := make([]LanguageRow, 0, len(cells))
	for k, c := range cells {
		c.Malicious, c.Benign = totals[k.surface][0], totals[k.surface][1]
		out = append(out, *c)
	}
	return out
}

func reportable(r LanguageRow) bool {
	if r.Malicious < MinSupport || r.Benign < MinSupport {
		return false
	}
	with := r.MaliciousWith
	if r.Toward() == "benign" {
		with = r.BenignWith
	}
	return with >= MinSupport && r.Ratio() >= SkewRatio
}

// familyOfExt inverts LanguageFamilies once, rather than once per sample.
var familyOfExt = func() map[string]string {
	out := map[string]string{}
	for fam, exts := range LanguageFamilies {
		for _, e := range exts {
			out[e] = fam
		}
	}
	return out
}()

func familiesOf(files []string) map[string]bool {
	out := map[string]bool{}
	for _, f := range files {
		if fam, ok := familyOfExt[strings.ToLower(filepath.Ext(f))]; ok {
			out[fam] = true
		}
	}
	return out
}

func share(n, of int) float64 {
	if of == 0 {
		return 0
	}
	return float64(n) / float64(of)
}
