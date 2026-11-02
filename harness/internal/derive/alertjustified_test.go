// SPDX-License-Identifier: MIT

package derive

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// An alert_justified override moves one candidate of a malicious-constant entry to the benign
// side. These tests pin the three things that make it safe: the class really flips and takes no
// malicious coordinates with it, the reading behind it must be whole and located, and it cannot
// be combined with another decision about the same sample.

func candidateEntry(aj map[string]manifest.AlertJustifiedOverride, exclude map[string]string) manifest.Entry {
	return manifest.Entry{
		ID: "clawhub-live",
		Derive: &manifest.Derive{
			Layout:         "extracted/*",
			LabelFile:      strPtr(""),
			Surface:        "skills",
			IDPrefix:       "ch",
			ClassFrom:      "constant:malicious",
			TierFrom:       "constant:plain",
			SeverityFrom:   "constant:high",
			ExcludeSamples: exclude,
			AlertJustified: aj,
		},
	}
}

func goodAJ() manifest.AlertJustifiedOverride {
	return manifest.AlertJustifiedOverride{
		Boundary: "data-to-fixed-party",
		Why:      "sends the user's report to the author's hardcoded chat id",
		ReadBy:   "two models (gpt-6.1-sol, gpt-5.5)",
		Date:     "2026-11-02",
		Evidence: &manifest.Evidence{File: "SKILL.md", Lines: "1", Quote: "a skill"},
	}
}

func TestAlertJustifiedFilesTheSampleBenign(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeFlatSample(t, root, "a", "", "")
	writeFlatSample(t, root, "b", "", "")
	e := candidateEntry(map[string]manifest.AlertJustifiedOverride{"a": goodAJ()}, map[string]string{"b": "not malicious"})

	res, errs := Derive(e, root, testTax())
	if len(errs) != 0 {
		t.Fatalf("unexpected errors: %v", errs)
	}
	if len(res.Coords) != 1 || res.AlertJustified != 1 {
		t.Fatalf("want one alert_justified coord, got %d coords, %d alert_justified", len(res.Coords), res.AlertJustified)
	}
	c := res.Coords[0]
	if c.Class != "benign" || c.AlertJustified == nil {
		t.Fatalf("class %q, override %v — the sample should be benign and carry its reading", c.Class, c.AlertJustified)
	}
	if c.Tier != "" || c.Severity != "" || len(c.Dimensions) != 0 || len(c.Evasion) != 0 {
		t.Errorf("benign coord kept malicious axes: tier=%q severity=%q dims=%v evasion=%v", c.Tier, c.Severity, c.Dimensions, c.Evasion)
	}

	plans, perrs := PlanMaterialize(e, res)
	if len(perrs) != 0 || len(plans) != 1 {
		t.Fatalf("plan: %v (%d plans)", perrs, len(plans))
	}
	if plans[0].LocalID != "ben-skill-ch-a" || !strings.HasPrefix(plans[0].Dir, "corpus/benign/") {
		t.Errorf("planned %q at %q — an alert_justified sample belongs under corpus/benign", plans[0].LocalID, plans[0].Dir)
	}
	label := renderLabel(e, plans[0], "", "2026-11-02")
	for _, want := range []string{
		"class: benign", "  class: assumed", "verdict: would-fire",
		"alert_justified: true", "data-to-fixed-party: sends the user's report",
	} {
		if !strings.Contains(label, want) {
			t.Errorf("label lacks %q:\n%s", want, label)
		}
	}
	if strings.Contains(label, "dimensions:") || strings.Contains(label, "is treated as benign") {
		t.Errorf("label carries a malicious axis or the batch-constant sentence:\n%s", label)
	}
}

func TestAlertJustifiedRefusesAQuoteNotOnTheLine(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeFlatSample(t, root, "a", "", "")
	aj := goodAJ()
	aj.Evidence = &manifest.Evidence{File: "SKILL.md", Lines: "1", Quote: "not in the file"}
	_, errs := Derive(candidateEntry(map[string]manifest.AlertJustifiedOverride{"a": aj}, nil), root, testTax())
	if !containsErr(errs, "quote is not on line 1") {
		t.Fatalf("an unlocated quote must be refused, got %v", errs)
	}
}

func TestAlertJustifiedRefusesAnIncompleteReading(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeFlatSample(t, root, "a", "", "")
	aj := goodAJ()
	aj.Boundary, aj.ReadBy, aj.Date = "looks-odd", "", "yesterday"
	_, errs := Derive(candidateEntry(map[string]manifest.AlertJustifiedOverride{"a": aj}, nil), root, testTax())
	for _, want := range []string{"boundary \"looks-odd\"", "has no read_by", "not YYYY-MM-DD"} {
		if !containsErr(errs, want) {
			t.Errorf("missing refusal %q in %v", want, errs)
		}
	}
}

func TestAlertJustifiedIsOneDecisionPerSample(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeFlatSample(t, root, "a", "", "")
	e := candidateEntry(map[string]manifest.AlertJustifiedOverride{"a": goodAJ()}, map[string]string{"a": "not malicious"})
	_, errs := Derive(e, root, testTax())
	if !containsErr(errs, "one decision per sample") {
		t.Fatalf("alert_justified and exclude_samples on one sample must be refused, got %v", errs)
	}
}
