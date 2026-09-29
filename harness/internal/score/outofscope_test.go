// SPDX-License-Identifier: MIT

package score

import (
	"reflect"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// oosLbl builds a malicious label, optionally derived from an upstream entry and carrying evasions.
func oosLbl(id, entry string, evasions ...string) *label.Label {
	l := &label.Label{ID: id, Class: label.Malicious}
	if entry != "" {
		l.Origin.Type = "derived"
		l.Origin.DerivedFrom = &label.DerivedFrom{Entry: entry}
	} else {
		l.Origin.Type = "reconstruction"
	}
	l.Truth.Evasion = evasions
	return l
}

func oosPop(l *label.Label) string {
	if l.Origin.DerivedFrom != nil {
		return l.Origin.DerivedFrom.Entry
	}
	return l.Origin.Type
}

// TestScore_OutOfScope: a tool's declared out_of_scope — by source, by evasion, or on the label
// itself — leaves that tool's recall denominator. The label field promised this in its comment and
// nothing implemented it. Both denominators come back, so a caller cannot print the narrow one alone.
func TestScore_OutOfScope(t *testing.T) {
	perSample := oosLbl("m5", "")
	perSample.Expect = map[string]*label.ToolExpect{"scanner-x": {OutOfScope: "runtime behaviour only"}}
	labels := []*label.Label{
		oosLbl("m1", "server-src"),                     // source → out, flagged
		oosLbl("m2", "server-src"),                     // source → out
		oosLbl("m3", "", "binary-container"),           // evasion → out
		oosLbl("m4", "server-src", "binary-container"), // both → out once, listed under the first
		perSample,                  // label expect → out
		oosLbl("m6", ""),           // in scope, flagged
		oosLbl("m7", ""),           // in scope
		oosLbl("m8", "server-src"), // out, but no verdict: listed, in no denominator
		{ID: "b1", Class: label.Benign, Origin: label.Origin{Type: "derived", DerivedFrom: &label.DerivedFrom{Entry: "server-src"}}},
	}
	verdicts := []Verdict{
		{Sample: "m1", Verdict: "malicious"}, {Sample: "m2", Verdict: "benign"}, {Sample: "m3", Verdict: "benign"},
		{Sample: "m4", Verdict: "benign"}, {Sample: "m5", Verdict: "benign"}, {Sample: "m6", Verdict: "malicious"},
		{Sample: "m7", Verdict: "benign"}, {Sample: "b1", Verdict: "malicious"},
	}
	tool := taxonomy.Tool{OutOfScope: []taxonomy.OutOfScopeSelector{
		{Source: "server-src", Reason: "server source"},
		{Evasion: "binary-container", Reason: "inside a container"},
	}}

	rep := OutOfScope(labels, verdicts, "scanner-x", tool, oosPop)

	if rep.All != 7 || rep.AllHits != 2 {
		t.Errorf("all = %d of %d, want 2 of 7 (covered malicious only; the benign flag is not recall)", rep.AllHits, rep.All)
	}
	if rep.InScope != 2 || rep.InScopeHits != 1 {
		t.Errorf("in scope = %d of %d, want 1 of 2", rep.InScopeHits, rep.InScope)
	}
	if rep.Excluded != 6 {
		t.Errorf("excluded = %d, want 6 (m8 counts as declared even without a verdict; m4 once)", rep.Excluded)
	}
	var ids [][]string
	sum := 0
	for _, g := range rep.Groups {
		ids = append(ids, g.IDs)
		sum += len(g.IDs)
	}
	want := [][]string{{"m1", "m2", "m4", "m8"}, {"m3"}, {"m5"}}
	if !reflect.DeepEqual(ids, want) {
		t.Errorf("groups = %v, want %v (declaration order, then the per-sample group; a sample under its first match)", ids, want)
	}
	if sum != rep.Excluded {
		t.Errorf("group sizes sum to %d, excluded is %d — a reader adding the list up must reach the total", sum, rep.Excluded)
	}
	if rep.Groups[0].Reason != "server source" || rep.Groups[2].Reason != "runtime behaviour only" {
		t.Errorf("reasons not carried: %+v", rep.Groups)
	}
}

// Without a tool nothing is declared, so nothing leaves: the narrow denominator equals the full one.
func TestScore_OutOfScopeWithoutAToolIsEmpty(t *testing.T) {
	labels := []*label.Label{oosLbl("m1", "server-src"), oosLbl("m2", "")}
	verdicts := []Verdict{{Sample: "m1", Verdict: "malicious"}, {Sample: "m2", Verdict: "benign"}}
	rep := OutOfScope(labels, verdicts, "", taxonomy.Tool{}, oosPop)
	if rep.Excluded != 0 || len(rep.Groups) != 0 || rep.InScope != rep.All || rep.InScopeHits != rep.AllHits {
		t.Errorf("no tool must exclude nothing: %+v", rep)
	}
}
