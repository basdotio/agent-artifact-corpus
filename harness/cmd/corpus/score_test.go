// SPDX-License-Identifier: MIT

package main

import (
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// idLbl builds a label whose population is its originating repository, which is the `default`
// arm of populationOf — enough to group by without depending on the other arms' reasoning.
// Named apart from source_test.go's `lbl`, which takes a class rather than an id.
func idLbl(id, repo string) *label.Label {
	return &label.Label{
		ID:     id,
		Class:  label.Benign,
		Origin: label.Origin{Source: "https://github.com/" + repo + "/x"},
	}
}

// TestUncoveredBySourceMarksAWholeSourceOnlyWhenItIsWhole is the claim worth being right about.
// "(the entire source)" tells a reader the denominator lost a source completely — either a
// deliberate de-contamination or a runner dropping a whole shape — and they act differently on
// that than on a handful of stragglers. Printing it wrongly in either direction misleads.
func TestUncoveredBySourceMarksAWholeSourceOnlyWhenItIsWhole(t *testing.T) {
	labels := []*label.Label{
		idLbl("a1", "vendor/one"), idLbl("a2", "vendor/one"), idLbl("a3", "vendor/one"),
		idLbl("b1", "vendor/two"), idLbl("b2", "vendor/two"),
		idLbl("c1", "vendor/three"),
	}

	got := uncoveredBySource(labels, []string{"a1", "a2", "a3", "b1"})
	if len(got) != 2 {
		t.Fatalf("got %d groups, want 2 — a source with nothing missing must not be listed: %+v", len(got), got)
	}
	// Sorted by name, so vendor/one comes before vendor/two.
	if got[0].Source != "vendor/one" || got[0].Missing != 3 || got[0].Total != 3 || !got[0].Whole {
		t.Errorf("vendor/one = %+v, want 3 of 3 marked whole", got[0])
	}
	if got[1].Source != "vendor/two" || got[1].Missing != 1 || got[1].Total != 2 || got[1].Whole {
		t.Errorf("vendor/two = %+v, want 1 of 2 NOT marked whole", got[1])
	}
	for _, g := range got {
		if g.Source == "vendor/three" {
			t.Error("a source with nothing missing was listed")
		}
	}
}

func TestUncoveredBySourceIsEmptyWhenNothingIsMissing(t *testing.T) {
	labels := []*label.Label{idLbl("a1", "vendor/one")}
	if got := uncoveredBySource(labels, nil); len(got) != 0 {
		t.Errorf("groups invented from a fully covered run: %+v", got)
	}
}

// TestUncoveredBySourceIgnoresIDsTheCorpusDoesNotHave — the scorer reports unknown verdicts
// separately, and counting a stranger here would inflate a source's Missing past its Total and
// break the "(the entire source)" test in the confusing direction.
func TestUncoveredBySourceIgnoresIDsTheCorpusDoesNotHave(t *testing.T) {
	labels := []*label.Label{idLbl("a1", "vendor/one")}
	got := uncoveredBySource(labels, []string{"a1", "not-in-the-corpus"})
	if len(got) != 1 {
		t.Fatalf("got %d groups, want 1: %+v", len(got), got)
	}
	if got[0].Missing != 1 || got[0].Total != 1 {
		t.Errorf("got %+v, want 1 of 1 — a stranger id must not be counted", got[0])
	}
}

// TestScoreArgs: `-tool` is optional and comes before the verdicts path; `-` still means stdin.
func TestScoreArgs(t *testing.T) {
	for _, tc := range []struct {
		args       []string
		tool, path string
		ok         bool
	}{
		{[]string{"v.jsonl"}, "", "v.jsonl", true},
		{[]string{"-tool", "scanner-x", "v.jsonl"}, "scanner-x", "v.jsonl", true},
		{[]string{"-tool", "scanner-x", "-"}, "scanner-x", "-", true},
		{[]string{"-"}, "", "-", true},
		{[]string{}, "", "", false},
		{[]string{"-tool", "scanner-x"}, "", "", false},
	} {
		tool, path, err := parseScoreArgs(tc.args)
		if (err == nil) != tc.ok || (tc.ok && (tool != tc.tool || path != tc.path)) {
			t.Errorf("parseScoreArgs(%q) = %q, %q, %v; want %q, %q, ok=%v", tc.args, tool, path, err, tc.tool, tc.path, tc.ok)
		}
	}
}

// TestResolveOutOfScope: an unknown tool, or a source the manifest does not have, stops the run
// rather than printing a narrow denominator nobody can check.
func TestResolveOutOfScope(t *testing.T) {
	tax := &taxonomy.Set{Tools: map[string]taxonomy.Tool{
		"scanner-x": {OutOfScope: []taxonomy.OutOfScopeSelector{{Source: "server-src", Reason: "r"}}},
		"scanner-y": {OutOfScope: []taxonomy.OutOfScopeSelector{{Source: "no-such-entry", Reason: "r"}}},
	}}
	entries := []string{"server-src", "other"}
	if _, err := resolveOutOfScope(tax, entries, "scanner-x"); err != nil {
		t.Errorf("known tool, known source: %v", err)
	}
	if _, err := resolveOutOfScope(tax, entries, "scanner-z"); err == nil {
		t.Error("an unregistered tool must be refused")
	}
	if _, err := resolveOutOfScope(tax, entries, "scanner-y"); err == nil {
		t.Error("a source the manifest does not have must be refused")
	}
}
