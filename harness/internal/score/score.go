// SPDX-License-Identifier: MIT

package score

import (
	"sort"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// FigureThresholdPoints is the half-width, in percentage points, past which a proportion is
// reported as a bare count ("caught 4 of 6") rather than a rate. The audit's rule stands: a
// recall from a handful of samples carries about ±24 points, "which is not a figure". 15 is the
// line this corpus already uses when it talks about a reportable per-surface recall.
const FigureThresholdPoints = 15.0

// Evidence is what a group's samples rest on, and the two never merge into one number.
// `collected` samples came from somewhere outside us — harvested configs, an upstream dataset,
// real-world captures — so a rate over them is a claim about the world, wide or narrow by n.
// `constructed` samples are reconstructions of a disclosed shape or synthetic fixtures: a
// scanner's score on them is COVERAGE of the shapes we thought to include, never a rate that
// predicts the wild. Keeping them apart is the whole reason this package exists.
const (
	Collected   = "collected"
	Constructed = "constructed"
)

// Group is one row of a scored table: a dimension, a source, or a population, with the count
// its rate rests on and the interval around it. Figure is false when the interval is too wide
// to call a rate — the caller prints the count alone and says why.
type Group struct {
	Key      string
	Evidence string // Collected | Constructed, empty for FP populations
	N        int
	Hits     int // caught, for recall; flagged, for false positives
	Point    float64
	Lo, Hi   float64
	Figure   bool
}

func newGroup(key, evidence string, n, hits int) Group {
	p, lo, hi := Wilson(hits, n)
	return Group{
		Key: key, Evidence: evidence, N: n, Hits: hits,
		Point: p, Lo: lo, Hi: hi,
		Figure: n > 0 && HalfWidthPoints(p, lo, hi) <= FigureThresholdPoints,
	}
}

// Attribution is the second detection question: of the malicious samples a scanner caught whose
// dimension this corpus may actually score (basis `read`), how often did it name a right one.
// Scored only over those, because a dimension resting on a batch constant cannot grade a
// scanner's guess without grading the constant.
type Attribution struct {
	Scoreable int // caught, read-basis, dimension-bearing
	Correct   int
	Point     float64
	Lo, Hi    float64
}

// Report is the whole readout. Detection and attribution are separate because they rest on
// different evidence; census counts (hard negatives) and estimates (the benign pool) are
// separate because they are different kinds of statement; collected and constructed are
// separate because only one can be a rate.
type Report struct {
	Labels, Malicious, Benign, HardNeg int

	Covered, Uncovered int
	UncoveredIDs       []string // corpus samples the scanner said nothing about
	UnknownVerdicts    []string // verdicts naming a sample not in the corpus

	// BenignReviewed is how many benign samples a person has actually read, and
	// FlagsOnReviewed how many flags landed on those. The pair is the only bridge this corpus
	// offers between a flag rate and a false-positive rate: on an unreviewed sample the benign
	// class rests on `assumed`, so calling a flag an error would assert a harmlessness the
	// label declines to assert. Both start at zero and grow one reading at a time.
	BenignReviewed  int
	FlagsOnReviewed int

	RecallByDimension []Group // split by Evidence; never a pooled total
	RecallBySource    []Group // one source is a rate about that source
	FPByPopulation    []Group
	HardNegFlagged    Group // census over the precision probe, reported alone

	Attribution Attribution
}

// Score computes the report. population is injected rather than recomputed so the scorer groups
// false positives by the exact same batches the leakage gate does — one definition of "source",
// checked in one place.
func Score(labels []*label.Label, verdicts []Verdict, tax *taxonomy.Set,
	spec *taxonomy.BasisSpec, population func(*label.Label) string) Report {

	byID := make(map[string]*label.Label, len(labels))
	for _, l := range labels {
		byID[l.ID] = l
	}
	verdictOf := make(map[string]Verdict, len(verdicts))
	for _, v := range verdicts {
		verdictOf[v.Sample] = v
	}

	var rep Report
	rep.Labels = len(labels)

	// recall[dimension][evidence] = {n, hits}; fp[population] = {n, flagged}
	type tally struct{ n, hits int }
	recall := map[string]map[string]*tally{}
	bySource := map[string]*tally{}
	fp := map[string]*tally{}
	hn := tally{}
	attr := Attribution{}

	for _, l := range labels {
		switch l.Class {
		case label.Malicious:
			rep.Malicious++
		case label.Benign:
			rep.Benign++
		case label.HardNegative:
			rep.HardNeg++
		}

		v, covered := verdictOf[l.ID]
		if !covered {
			rep.Uncovered++
			rep.UncoveredIDs = append(rep.UncoveredIDs, l.ID)
			continue
		}
		rep.Covered++

		switch l.Class {
		case label.Malicious:
			ev := evidenceClass(l)
			hit := 0
			if v.Flagged() {
				hit = 1
			}
			for _, d := range dimensionsOf(l, tax) {
				if recall[d] == nil {
					recall[d] = map[string]*tally{}
				}
				if recall[d][ev] == nil {
					recall[d][ev] = &tally{}
				}
				recall[d][ev].n++
				recall[d][ev].hits += hit
			}
			src := population(l)
			if bySource[src] == nil {
				bySource[src] = &tally{}
			}
			bySource[src].n++
			bySource[src].hits += hit

			// Attribution: only where the dimension may be scored, and only when caught.
			if v.Flagged() && l.Basis != nil && spec.AllowsAxis("dimension", l.Basis.Dimension) {
				truth := dimensionsOf(l, tax)
				if len(truth) > 0 {
					attr.Scoreable++
					if intersects(v.Dimensions, truth) {
						attr.Correct++
					}
				}
			}

		case label.Benign:
			pop := population(l)
			if fp[pop] == nil {
				fp[pop] = &tally{}
			}
			fp[pop].n++
			if v.Flagged() {
				fp[pop].hits++
				// A flag on a sample a person has READ is the only kind this corpus can call a
				// false positive outright. On the rest, the benign class rests on `assumed` and
				// calling the flag an error would assert a harmlessness the label refuses to
				// assert. Counting the reviewed subset separately is the one honest bridge
				// between the flag rate and a false-positive rate.
				if l.Reviewed != nil {
					rep.FlagsOnReviewed++
				}
			}
			if l.Reviewed != nil {
				rep.BenignReviewed++
			}

		case label.HardNegative:
			hn.n++
			if v.Flagged() {
				hn.hits++
			}
		}
	}

	for _, v := range verdicts {
		if _, ok := byID[v.Sample]; !ok {
			rep.UnknownVerdicts = append(rep.UnknownVerdicts, v.Sample)
		}
	}

	for dim, byEv := range recall {
		for ev, t := range byEv {
			rep.RecallByDimension = append(rep.RecallByDimension, newGroup(dim, ev, t.n, t.hits))
		}
	}
	for src, t := range bySource {
		rep.RecallBySource = append(rep.RecallBySource, newGroup(src, "", t.n, t.hits))
	}
	for pop, t := range fp {
		rep.FPByPopulation = append(rep.FPByPopulation, newGroup(pop, "", t.n, t.hits))
	}
	rep.HardNegFlagged = newGroup("hard-negative", "", hn.n, hn.hits)

	attr.Point, attr.Lo, attr.Hi = Wilson(attr.Correct, attr.Scoreable)
	rep.Attribution = attr

	sortGroups(rep.RecallByDimension)
	sortGroups(rep.RecallBySource)
	sortGroups(rep.FPByPopulation)
	sort.Strings(rep.UncoveredIDs)
	sort.Strings(rep.UnknownVerdicts)
	return rep
}

// evidenceClass decides whether a sample can back a rate. A reconstruction's shape came from a
// disclosure but its bytes are ours; a synthetic fixture is ours end to end. Both test coverage
// of shapes we chose, so a scanner's score on them is not a draw from the world.
func evidenceClass(l *label.Label) string {
	switch l.Origin.Type {
	case "reconstruction", "synthetic":
		return Constructed
	default:
		return Collected
	}
}

// dimensionsOf resolves a malicious sample's dimensions: a technique names its dimension in the
// taxonomy, and a derived sample may name a dimension directly. A sample touching two
// dimensions counts in both, because a scanner that misses it misses it on both.
func dimensionsOf(l *label.Label, tax *taxonomy.Set) []string {
	set := map[string]bool{}
	for _, id := range l.Truth.Techniques {
		if t, ok := tax.Techniques[id]; ok && t.Dimension != "" {
			set[t.Dimension] = true
		}
	}
	for _, d := range l.Truth.Dimensions {
		set[d] = true
	}
	out := make([]string, 0, len(set))
	for d := range set {
		out = append(out, d)
	}
	sort.Strings(out)
	return out
}

func intersects(a, b []string) bool {
	m := map[string]bool{}
	for _, x := range a {
		m[x] = true
	}
	for _, y := range b {
		if m[y] {
			return true
		}
	}
	return false
}

func sortGroups(gs []Group) {
	sort.Slice(gs, func(i, j int) bool {
		if gs[i].Key != gs[j].Key {
			return gs[i].Key < gs[j].Key
		}
		return gs[i].Evidence < gs[j].Evidence
	})
}
