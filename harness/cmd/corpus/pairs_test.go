// SPDX-License-Identifier: MIT

package main

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/leakage"
)

func pairedLabel(id string, class label.Class, surface, pairsWith string) *label.Label {
	return &label.Label{ID: id, Class: class, Surface: label.Surfaces{surface}, PairsWith: pairsWith}
}

// The pair view holds each hard negative and its twin on the negative's surface, a twin once
// however many negatives point at it, and nothing that is not in a pair.
func TestPairSamples_HoldsEachPairOnce(t *testing.T) {
	labels := []*label.Label{
		pairedLabel("hn-a", label.HardNegative, "skills", "mal-x"),
		pairedLabel("hn-b", label.HardNegative, "skills", "mal-x"),
		pairedLabel("hn-c", label.HardNegative, "instruction", "mal-y"),
		pairedLabel("mal-x", label.Malicious, "skills", ""),
		pairedLabel("mal-y", label.Malicious, "mcp", ""),
		pairedLabel("mal-z", label.Malicious, "skills", ""),
		pairedLabel("ben-q", label.Benign, "skills", ""),
		pairedLabel("hn-dangling", label.HardNegative, "skills", "mal-gone"),
	}
	var samples []leakage.Sample
	for _, l := range labels {
		samples = append(samples, leakage.Sample{ID: l.ID, Class: string(l.Class), Group: "pop"})
	}
	got := pairSamples(labels, samples)
	want := map[string]string{"hn-a": "pairs:skills", "hn-b": "pairs:skills", "mal-x": "pairs:skills",
		"hn-c": "pairs:instruction", "mal-y": "pairs:instruction"}
	if len(got) != len(want) {
		t.Fatalf("got %d samples, want %d: %+v", len(got), len(want), got)
	}
	for _, s := range got {
		if want[s.ID] != s.Group {
			t.Errorf("%s in group %q, want %q", s.ID, s.Group, want[s.ID])
		}
	}
}

// The problem line says what kind of feature gave the class away, because the fix differs.
func TestLeakProblem_NamesTheKindOfFeature(t *testing.T) {
	cases := map[string]string{
		"file:_meta.json":     "structural feature",
		"host:evil.test":      "network literal",
		"word:exfil":          "self-describing word",
		"charset:non-ascii":   "character set",
		"textbytes:<1K":       "length of the text",
		"absent:file:LICENSE": "absence of a feature",
	}
	for name, want := range cases {
		got := leakProblem("among", leakage.Feature{Name: name, Class: "malicious", With: 9, Total: 9, Group: "pairs:skills"})
		if !strings.Contains(got, want) || !strings.HasPrefix(got, "leakage among pairs:skills:") {
			t.Errorf("leakProblem(%q) = %q, want it to say %q", name, got, want)
		}
	}
}
