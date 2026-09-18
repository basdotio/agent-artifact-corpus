// SPDX-License-Identifier: MIT

package score

import (
	"strings"
	"testing"
)

func TestParseVerdictsHappyPath(t *testing.T) {
	in := `{"sample":"mal-a","verdict":"malicious","severity":"high","dimensions":["execution"]}
{"sample":"ben-b","verdict":"benign"}
# a comment line is skipped

`
	vs, err := ParseVerdicts(strings.NewReader(in))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(vs) != 2 {
		t.Fatalf("got %d verdicts, want 2", len(vs))
	}
	if !vs[0].Flagged() || vs[1].Flagged() {
		t.Errorf("Flagged wrong: %v / %v", vs[0].Flagged(), vs[1].Flagged())
	}
	if len(vs[0].Dimensions) != 1 || vs[0].Dimensions[0] != "execution" {
		t.Errorf("dimensions not parsed: %v", vs[0].Dimensions)
	}
}

func TestParseVerdictsRejectsUnknownVerdict(t *testing.T) {
	_, err := ParseVerdicts(strings.NewReader(`{"sample":"x","verdict":"maybe"}`))
	if err == nil || !strings.Contains(err.Error(), "neither") {
		t.Errorf("want a verdict-word error, got %v", err)
	}
}

func TestParseVerdictsRejectsMissingSample(t *testing.T) {
	_, err := ParseVerdicts(strings.NewReader(`{"verdict":"benign"}`))
	if err == nil || !strings.Contains(err.Error(), "sample") {
		t.Errorf("want a missing-sample error, got %v", err)
	}
}

func TestParseVerdictsRejectsDuplicate(t *testing.T) {
	in := `{"sample":"x","verdict":"benign"}
{"sample":"x","verdict":"malicious"}`
	_, err := ParseVerdicts(strings.NewReader(in))
	if err == nil || !strings.Contains(err.Error(), "already had a verdict") {
		t.Errorf("want a duplicate error, got %v", err)
	}
}

func TestParseVerdictsRejectsUnknownField(t *testing.T) {
	// A misspelled key (verdcit) must fail loudly, not silently parse as an empty verdict —
	// that is how a scanner's whole output gets scored as benign without anyone noticing.
	_, err := ParseVerdicts(strings.NewReader(`{"sample":"x","verdcit":"malicious"}`))
	if err == nil {
		t.Errorf("want an unknown-field error, got nil")
	}
}
