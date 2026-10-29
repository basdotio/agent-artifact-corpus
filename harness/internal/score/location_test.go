// SPDX-License-Identifier: MIT
package score

import (
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
)

// A location hit is "the scanner named the file the quote came from", compared as paths on a
// slash boundary in either direction. The cases that matter: a relative prefix the scanner
// added, a basename-only report, and a different file that merely shares a suffix of its name.
func TestLocationHit(t *testing.T) {
	ev := []label.Evidence{{File: "scripts/collect.sh", Quote: "cat /etc/passwd"}}
	cases := []struct {
		named []string
		want  bool
	}{
		{[]string{"scripts/collect.sh"}, true},
		{[]string{"./scripts/collect.sh"}, true},
		{[]string{"collect.sh"}, true},
		{[]string{"tree/scripts/collect.sh"}, true},
		{[]string{"SKILL.md", "scripts/collect.sh"}, true},
		{[]string{"SKILL.md"}, false},
		{[]string{"notcollect.sh"}, false}, // shares a suffix, not a path component
		{[]string{""}, false},
		{nil, false},
	}
	for _, c := range cases {
		if got := locationHit(c.named, ev); got != c.want {
			t.Errorf("locationHit(%v) = %v, want %v", c.named, got, c.want)
		}
	}
	if locationHit([]string{"scripts/collect.sh"}, []label.Evidence{{Quote: "x"}}) {
		t.Error("evidence with no file must not match anything")
	}
}

func TestEvidenceClassHarvestedIsWild(t *testing.T) {
	prov := map[string]string{"skillharm": Synthetic, "cisco-mcp-scanner-evals": Fixture}
	cases := []struct {
		l    label.Label
		want string
	}{
		{label.Label{Origin: label.Origin{Type: "harvested"}}, Wild},
		{label.Label{Class: label.HardNegative, Origin: label.Origin{Type: "harvested"}}, Wild},
		{label.Label{Origin: label.Origin{Type: "reconstruction"}}, Constructed},
		{label.Label{Origin: label.Origin{Type: "derived", DerivedFrom: &label.DerivedFrom{Entry: "skillharm"}}}, Synthetic},
		{label.Label{Origin: label.Origin{Type: "derived", DerivedFrom: &label.DerivedFrom{Entry: "cisco-mcp-scanner-evals"}}}, Fixture},
		{label.Label{Origin: label.Origin{Type: "real-world", Provenance: "wild"}}, Wild},
		{label.Label{Origin: label.Origin{Type: "real-world"}}, Unclassified},
	}
	for _, c := range cases {
		l := c.l
		if got := EvidenceClass(&l, prov); got != c.want {
			t.Errorf("EvidenceClass(%s/%s) = %q, want %q", l.Origin.Type, l.Origin.Provenance, got, c.want)
		}
	}
}
