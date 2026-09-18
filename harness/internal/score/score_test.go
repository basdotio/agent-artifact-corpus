// SPDX-License-Identifier: MIT

package score

import (
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

func tax() *taxonomy.Set {
	return &taxonomy.Set{Techniques: map[string]taxonomy.Technique{
		"exfil-tech": {Dimension: "exfiltration"},
		"fs-tech":    {Dimension: "filesystem"},
	}}
}

// A basis spec that scores the dimension axis only from `read`, matching the real one.
func spec() *taxonomy.BasisSpec {
	return &taxonomy.BasisSpec{Scores: map[string][]string{"dimension": {"read"}}}
}

func mal(id, tech, origin, basisDim string) *label.Label {
	l := &label.Label{ID: id, Class: label.Malicious}
	l.Origin.Type = origin
	l.Truth.Techniques = []string{tech}
	if basisDim != "" {
		l.Basis = &label.Basis{Dimension: basisDim}
	}
	return l
}
func ben(id, origin string) *label.Label {
	l := &label.Label{ID: id, Class: label.Benign}
	l.Origin.Type = origin
	return l
}
func pop(l *label.Label) string { return l.Origin.Type }

func TestCollectedAndConstructedNeverMerge(t *testing.T) {
	labels := []*label.Label{
		mal("m1", "exfil-tech", "derived", ""),
		mal("m2", "exfil-tech", "reconstruction", ""),
	}
	verdicts := []Verdict{
		{Sample: "m1", Verdict: "malicious"},
		{Sample: "m2", Verdict: "benign"},
	}
	rep := Score(labels, verdicts, tax(), spec(), pop)

	var collected, constructed *Group
	for i := range rep.RecallByDimension {
		g := &rep.RecallByDimension[i]
		if g.Key != "exfiltration" {
			t.Fatalf("unexpected dimension %q", g.Key)
		}
		switch g.Evidence {
		case Collected:
			collected = g
		case Constructed:
			constructed = g
		}
	}
	if collected == nil || constructed == nil {
		t.Fatalf("exfiltration must appear once per evidence class; got %+v", rep.RecallByDimension)
	}
	if collected.N != 1 || collected.Hits != 1 {
		t.Errorf("collected: got n=%d hits=%d, want 1/1", collected.N, collected.Hits)
	}
	if constructed.N != 1 || constructed.Hits != 0 {
		t.Errorf("constructed: got n=%d hits=%d, want 1/0", constructed.N, constructed.Hits)
	}
}

func TestSmallGroupIsNotAFigure(t *testing.T) {
	// One caught sample is 100% but the interval is enormous; it must not be dressed as a rate.
	labels := []*label.Label{mal("m1", "fs-tech", "derived", "")}
	rep := Score(labels, []Verdict{{Sample: "m1", Verdict: "malicious"}}, tax(), spec(), pop)
	if len(rep.RecallByDimension) != 1 {
		t.Fatalf("want one group, got %d", len(rep.RecallByDimension))
	}
	if rep.RecallByDimension[0].Figure {
		t.Errorf("n=1 was reported as a figure; half-width should have failed the gate")
	}
}

func TestFalsePositiveByPopulation(t *testing.T) {
	labels := []*label.Label{
		ben("b1", "harvested"), ben("b2", "harvested"),
		ben("b3", "automatelab"),
	}
	verdicts := []Verdict{
		{Sample: "b1", Verdict: "malicious"}, // a false positive
		{Sample: "b2", Verdict: "benign"},
		{Sample: "b3", Verdict: "benign"},
	}
	rep := Score(labels, verdicts, tax(), spec(), pop)
	got := map[string]Group{}
	for _, g := range rep.FPByPopulation {
		got[g.Key] = g
	}
	if got["harvested"].N != 2 || got["harvested"].Hits != 1 {
		t.Errorf("harvested FP: got n=%d flagged=%d, want 2/1", got["harvested"].N, got["harvested"].Hits)
	}
	if got["automatelab"].Hits != 0 {
		t.Errorf("automatelab should have no false positive, got %d", got["automatelab"].Hits)
	}
}

func TestAttributionOnlyScoresReadBasis(t *testing.T) {
	labels := []*label.Label{
		mal("m1", "exfil-tech", "derived", "read"),    // scoreable
		mal("m2", "exfil-tech", "derived", "assumed"), // not scoreable
	}
	verdicts := []Verdict{
		{Sample: "m1", Verdict: "malicious", Dimensions: []string{"exfiltration"}},
		{Sample: "m2", Verdict: "malicious", Dimensions: []string{"filesystem"}}, // wrong, but not scored
	}
	rep := Score(labels, verdicts, tax(), spec(), pop)
	if rep.Attribution.Scoreable != 1 {
		t.Errorf("attribution scoreable = %d, want 1 (only the read-basis sample)", rep.Attribution.Scoreable)
	}
	if rep.Attribution.Correct != 1 {
		t.Errorf("attribution correct = %d, want 1", rep.Attribution.Correct)
	}
}

func TestUncoveredAndUnknownAreTracked(t *testing.T) {
	labels := []*label.Label{mal("m1", "exfil-tech", "derived", ""), ben("b1", "harvested")}
	verdicts := []Verdict{
		{Sample: "m1", Verdict: "malicious"},
		{Sample: "ghost", Verdict: "malicious"}, // names a sample not in the corpus
	}
	rep := Score(labels, verdicts, tax(), spec(), pop)
	if rep.Uncovered != 1 || len(rep.UncoveredIDs) != 1 || rep.UncoveredIDs[0] != "b1" {
		t.Errorf("uncovered tracking wrong: %d %v", rep.Uncovered, rep.UncoveredIDs)
	}
	if len(rep.UnknownVerdicts) != 1 || rep.UnknownVerdicts[0] != "ghost" {
		t.Errorf("unknown verdict tracking wrong: %v", rep.UnknownVerdicts)
	}
}

func TestHardNegativeReportedSeparately(t *testing.T) {
	labels := []*label.Label{
		{ID: "h1", Class: label.HardNegative},
		{ID: "h2", Class: label.HardNegative},
	}
	verdicts := []Verdict{
		{Sample: "h1", Verdict: "malicious"}, // scanner wrongly fired on the near-miss
		{Sample: "h2", Verdict: "benign"},
	}
	rep := Score(labels, verdicts, tax(), spec(), pop)
	if rep.HardNegFlagged.N != 2 || rep.HardNegFlagged.Hits != 1 {
		t.Errorf("hard-neg census wrong: n=%d flagged=%d, want 2/1", rep.HardNegFlagged.N, rep.HardNegFlagged.Hits)
	}
	// Hard negatives must not leak into the benign FP populations.
	if len(rep.FPByPopulation) != 0 {
		t.Errorf("hard negatives leaked into FP populations: %+v", rep.FPByPopulation)
	}
}
