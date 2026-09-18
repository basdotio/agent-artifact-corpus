// SPDX-License-Identifier: MIT

package manifest

import (
	"testing"

	"gopkg.in/yaml.v3"
)

func TestAdjudicationParses(t *testing.T) {
	var got map[string]Adjudication
	src := `
ben-skill-x:
  pattern: no-judgeable-content
  verdict: keep
  reason: it exercises length handling rather than over-alerting
ben-skill-y:
  pattern: duplicate-or-contained
  verdict: exclude
  reason: byte-identical to ben-skill-x
`
	if err := yaml.Unmarshal([]byte(src), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got["ben-skill-x"].Verdict != "keep" || got["ben-skill-y"].Verdict != "exclude" {
		t.Errorf("verdicts = %+v", got)
	}
}

// A verdict with no reason is the failure this whole record exists to prevent: an exclusion
// nobody can audit, or a retention nobody can challenge.
func TestAdjudicationRequiresReason(t *testing.T) {
	var got map[string]Adjudication
	src := "x:\n  pattern: p\n  verdict: keep\n"
	if err := yaml.Unmarshal([]byte(src), &got); err == nil {
		t.Fatal("an adjudication with no reason parsed")
	}
}

func TestAdjudicationRejectsUnknownVerdict(t *testing.T) {
	var got map[string]Adjudication
	src := "x:\n  pattern: p\n  verdict: probably\n  reason: r\n"
	if err := yaml.Unmarshal([]byte(src), &got); err == nil {
		t.Fatal("an unknown verdict parsed — the vocabulary is closed")
	}
}

func TestAdjudicationRejectsUnknownField(t *testing.T) {
	var got map[string]Adjudication
	src := "x:\n  pattern: p\n  verdict: keep\n  reason: r\n  note: extra\n"
	if err := yaml.Unmarshal([]byte(src), &got); err == nil {
		t.Fatal("an unknown field parsed")
	}
}
