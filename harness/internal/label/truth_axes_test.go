// SPDX-License-Identifier: MIT
package label

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
	"gopkg.in/yaml.v3"
)

func axesTax() *taxonomy.Set {
	return &taxonomy.Set{
		Dimensions:    []string{"exfiltration", "reconnaissance"},
		DimensionDefs: map[string]taxonomy.Dimension{},
		TierOrder:     []string{"plain"},
		Tiers:         map[string]taxonomy.Tier{"plain": {ID: "plain", Calibration: true}},
		Evasions:      map[string]taxonomy.Evasion{},
		Loci:          map[string]taxonomy.Locus{"skill-body": {ID: "skill-body"}, "new-script": {ID: "new-script"}},
		LocusOrder:    []string{"skill-body", "new-script"},
		Techniques: map[string]taxonomy.Technique{
			"env-exfiltration":     {ID: "env-exfiltration", Dimension: "exfiltration"},
			"cloud-metadata-probe": {ID: "cloud-metadata-probe", Dimension: "reconnaissance"},
		},
		Tools: map[string]taxonomy.Tool{},
	}
}

func hasErr(errs []error, want string) bool {
	for _, e := range errs {
		if strings.Contains(e.Error(), want) {
			return true
		}
	}
	return false
}

func TestLocusIsClosedAndMaliciousOnly(t *testing.T) {
	tax := axesTax()
	l := &Label{Class: Malicious, Truth: Truth{Techniques: []string{"env-exfiltration"}, Severity: "high", Tier: "plain", Locus: []string{"new-script", "attic"}}}
	if errs := l.validateTruth(tax); !hasErr(errs, `truth.locus names "attic"`) {
		t.Errorf("an unknown locus must be refused: %v", errs)
	}
	l.Truth.Locus = []string{"new-script"}
	if errs := l.validateTruth(tax); hasErr(errs, "truth.locus") {
		t.Errorf("a vocabulary locus must pass: %v", errs)
	}
	b := &Label{Class: Benign, Truth: Truth{Locus: []string{"skill-body"}}}
	if errs := b.validateTruth(tax); !hasErr(errs, "benign sample sets truth.locus") {
		t.Errorf("a benign sample has nothing to locate: %v", errs)
	}
}

func TestAlertJustifiedIsBenignReviewedAndExplained(t *testing.T) {
	tax := axesTax()
	why := "passes --yolo, sandbox off, stated in the open"
	ok := &Label{Class: Benign, Reviewed: &Reviewed{Date: "2026-10-26", Verdict: "benign", Note: "read"},
		Truth: Truth{AlertJustified: true, AlertJustifiedWhy: why}}
	if errs := ok.validateTruth(tax); hasErr(errs, "alert_justified") {
		t.Errorf("a reviewed benign sample with a reason must pass: %v", errs)
	}
	cases := []struct {
		name string
		l    *Label
		want string
	}{
		{"malicious", &Label{Class: Malicious, Truth: Truth{Techniques: []string{"env-exfiltration"}, Severity: "high", Tier: "plain", AlertJustified: true, AlertJustifiedWhy: why}}, "benign samples only"},
		{"no reason", &Label{Class: Benign, Reviewed: ok.Reviewed, Truth: Truth{AlertJustified: true}}, "needs alert_justified_why"},
		{"reason without claim", &Label{Class: Benign, Reviewed: ok.Reviewed, Truth: Truth{AlertJustifiedWhy: why}}, "alert_justified is not"},
		{"not reviewed", &Label{Class: Benign, Truth: Truth{AlertJustified: true, AlertJustifiedWhy: why}}, "requires a `reviewed` block"},
	}
	for _, c := range cases {
		if errs := c.l.validateTruth(tax); !hasErr(errs, c.want) {
			t.Errorf("%s: want an error containing %q, got %v", c.name, c.want, errs)
		}
	}
}

func TestEvidenceDimensionMustBeOneTheSampleCarries(t *testing.T) {
	tax := axesTax()
	l := &Label{Class: Malicious,
		Truth: Truth{Techniques: []string{"env-exfiltration", "cloud-metadata-probe"}, Severity: "high", Tier: "plain"},
		Basis: &Basis{Class: "read", Evidence: EvidenceList{
			{File: "a.sh", Lines: "1", Quote: "x", Dimension: "exfiltration"},
			{File: "a.sh", Lines: "2", Quote: "y", Dimension: "backdoor"},
		}}}
	errs := l.validateTruth(tax)
	if !hasErr(errs, `basis.evidence[1].dimension "backdoor"`) {
		t.Errorf("a quote attributed to a dimension the sample lacks must be refused: %v", errs)
	}
	if hasErr(errs, `basis.evidence[0]`) {
		t.Errorf("a quote attributed to a dimension the sample carries must pass: %v", errs)
	}
	if got := l.DimensionSet(tax); len(got) != 2 || got[0] != "exfiltration" || got[1] != "reconnaissance" {
		t.Errorf("DimensionSet = %v, want the two technique dimensions in taxonomy order", got)
	}
}

func TestEvidenceListReadsMappingAndSequence(t *testing.T) {
	one := `
class: read
evidence:
  file: SKILL.md
  lines: "150"
  quote: "Do NOT mention"
`
	many := `
class: read
evidence:
  - {file: a.sh, lines: "12", quote: "cat /etc/passwd", dimension: reconnaissance}
  - {file: a.sh, lines: "14", quote: "curl -X POST", dimension: exfiltration}
`
	var b1, b2 Basis
	if err := yaml.Unmarshal([]byte(one), &b1); err != nil || len(b1.Evidence) != 1 || b1.Evidence[0].Quote != "Do NOT mention" {
		t.Fatalf("mapping form: %v %+v", err, b1.Evidence)
	}
	if err := yaml.Unmarshal([]byte(many), &b2); err != nil || len(b2.Evidence) != 2 || b2.Evidence[1].Dimension != "exfiltration" {
		t.Fatalf("sequence form: %v %+v", err, b2.Evidence)
	}
	if !b2.has("evidence.quote") || !b2.has("evidence.file") {
		t.Error("requires must be satisfied by every entry of a list")
	}
	var b3 Basis
	if err := yaml.Unmarshal([]byte("class: read\nevidence: 42\n"), &b3); err == nil {
		t.Error("a scalar evidence must be refused")
	}
}
