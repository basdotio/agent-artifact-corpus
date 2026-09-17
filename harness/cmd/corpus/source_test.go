// SPDX-License-Identifier: MIT

package main

import (
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
)

func lbl(class label.Class, source string) *label.Label {
	return &label.Label{Class: class, Origin: label.Origin{Source: source}}
}

// The one thing this report must never do is credit the aggregator. Every sampled skill's
// source string names the originating repository AND the entry that redistributed it, and
// reading the entry instead of the origin would report 2,000 independent writers as one
// source — which is the precise error that made a 12.9% figure meaningless and started this
// corpus.
func TestOriginOfNamesTheWriterNotTheRedistributor(t *testing.T) {
	t.Parallel()
	cases := []struct {
		in, want string
	}{
		{"https://github.com/0x3EF8/moltbook-ai-agent (via skillmd-138k @ 0d73048abf2f)", "0x3EF8/moltbook-ai-agent"},
		{"https://github.com/optimuslabs-io/skillsgoat (via skillsgoat @ c03d70d80c32)", "optimuslabs-io/skillsgoat"},
		// An entry that pinned a whole repository has no separate originating repo: the URL
		// IS the source, and it still resolves to one.
		{"https://github.com/DataDog/malicious-software-packages-dataset @ d156188d1e45", "DataDog/malicious-software-packages-dataset"},
		// A purpose-built fixture we wrote. No repository, and it must not be invented.
		{"hand-written for this corpus", ""},
		{"", ""},
		// HuggingFace datasets are not github repos; the field is honest about naming none.
		{"https://huggingface.co/datasets/FayeZC/SkillMD-138K @ 0d73048abf2f", ""},
	}
	for _, tc := range cases {
		if got := originOf(lbl(label.Benign, tc.in)); got != tc.want {
			t.Errorf("originOf(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestConcentrationCountsDistinctSourcesPerClass(t *testing.T) {
	t.Parallel()
	labels := []*label.Label{
		lbl(label.Benign, "https://github.com/agg/feed (via skillmd-138k @ abc)"),
		lbl(label.Benign, "https://github.com/agg/feed (via skillmd-138k @ abc)"),
		lbl(label.Benign, "https://github.com/agg/feed (via skillmd-138k @ abc)"),
		lbl(label.Benign, "https://github.com/solo/one (via skillmd-138k @ abc)"),
		lbl(label.Benign, "hand-written for this corpus"),
		lbl(label.Malicious, "https://github.com/cisco/evals (via cisco @ abc)"),
	}

	c := concentrationOf(labels, label.Benign)
	if c.Samples != 5 {
		t.Errorf("Samples = %d, want 5 (the unattributed one still counts in the denominator)", c.Samples)
	}
	if c.Distinct != 2 {
		t.Errorf("Distinct = %d, want 2", c.Distinct)
	}
	if c.Unattr != 1 {
		t.Errorf("Unattr = %d, want 1 — dropping it would silently shrink the denominator", c.Unattr)
	}
	if c.TopName != "agg/feed" || c.TopCount != 3 {
		t.Errorf("top = %s at %d, want agg/feed at 3", c.TopName, c.TopCount)
	}

	// Classes are never pooled: a malicious census and a benign sample have different
	// denominators, so mixing them into one concentration figure would describe neither.
	if m := concentrationOf(labels, label.Malicious); m.Samples != 1 || m.Distinct != 1 {
		t.Errorf("malicious concentration = %+v, want 1 sample over 1 repo", m)
	}
	if h := concentrationOf(labels, label.HardNegative); h.Samples != 0 {
		t.Errorf("hard-negative concentration = %+v, want empty", h)
	}
}

// Equal counts must not make the report flap between runs, or a diff of two `stats` outputs
// shows a change where the corpus did not change.
func TestConcentrationBreaksTiesDeterministically(t *testing.T) {
	t.Parallel()
	labels := []*label.Label{
		lbl(label.Benign, "https://github.com/zzz/one (via e @ abc)"),
		lbl(label.Benign, "https://github.com/aaa/one (via e @ abc)"),
	}
	for i := 0; i < 20; i++ {
		if got := concentrationOf(labels, label.Benign).TopName; got != "aaa/one" {
			t.Fatalf("top = %q on run %d, want the lexicographically first of the tied sources", got, i)
		}
	}
}
