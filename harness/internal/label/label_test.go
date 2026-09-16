// SPDX-License-Identifier: MIT

package label

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// testTax is a minimal vocabulary. It deliberately carries two techniques and two tools
// with DIFFERENT severity ladders, because the per-tool ladder is the mechanism that lets
// two scanners annotate the same sample without either adopting the other's scale, and a
// single-tool fixture would not exercise it.
func testTax() *taxonomy.Set {
	return &taxonomy.Set{
		Dimensions: []string{"backdoor", "exfiltration"},
		Techniques: map[string]taxonomy.Technique{
			"reverse-shell":    {ID: "reverse-shell", Title: "Reverse shell", Dimension: "backdoor", What: "x", BenignLookalike: "y"},
			"env-exfiltration": {ID: "env-exfiltration", Title: "Env exfil", Dimension: "exfiltration", What: "x", BenignLookalike: "y"},
		},
		Tools: map[string]taxonomy.Tool{
			"aguard": {ID: "aguard", Name: "AgentGuard", SeverityLadder: []string{"critical", "high", "medium", "low", "none"}},
			"other":  {ID: "other", Name: "Other", SeverityLadder: []string{"error", "warning", "note"}},
		},
	}
}

func goodOrigin() Origin {
	return Origin{
		Type:             "reconstruction",
		Source:           "https://example.invalid",
		License:          "MIT",
		Added:            "2026-09-16",
		LabeledBeforeRun: true,
	}
}

func malicious() *Label {
	return &Label{
		ID: "mal-x", Class: Malicious, Surface: "skills", Kind: "skill", Entry: ".",
		Origin: goodOrigin(),
		Truth:  Truth{Techniques: []string{"reverse-shell"}, Severity: "high"},
		Expect: map[string]*ToolExpect{"aguard": {Rules: []string{"BD-003"}, MinSeverity: "high"}},
	}
}

func hardNegative() *Label {
	return &Label{
		ID: "hn-x", Class: HardNegative, Surface: "skills", Kind: "skill", Entry: ".",
		Origin:    goodOrigin(),
		Truth:     Truth{Resembles: []string{"reverse-shell"}, DiffersBy: "no fd redirection"},
		Expect:    map[string]*ToolExpect{"aguard": {Quiet: []string{"BD-003"}, MaxSeverity: "low"}},
		PairsWith: "mal-x",
	}
}

func errText(errs []error) string {
	var b strings.Builder
	for _, e := range errs {
		b.WriteString(e.Error())
		b.WriteString("\n")
	}
	return b.String()
}

func TestValidate(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		mutate  func(*Label)
		wantErr string // substring; empty means the label must validate clean
	}{
		{name: "valid malicious", mutate: func(*Label) {}},

		// --- truth is the tool-neutral half and carries the class's real assertion ---
		{
			name:    "malicious without techniques asserts nothing portable",
			mutate:  func(l *Label) { l.Truth.Techniques = nil },
			wantErr: "lists no truth.techniques",
		},
		{
			name:    "malicious without severity cannot be scored by an unlisted tool",
			mutate:  func(l *Label) { l.Truth.Severity = "" },
			wantErr: "must set truth.severity",
		},
		{
			name:    "malicious may not claim it merely resembles",
			mutate:  func(l *Label) { l.Truth.Resembles = []string{"env-exfiltration"} },
			wantErr: "truth.resembles is for benign look-alikes",
		},
		{
			name:    "technique must exist in the vocabulary",
			mutate:  func(l *Label) { l.Truth.Techniques = []string{"not-a-technique"} },
			wantErr: "not in taxonomy/techniques.yaml",
		},
		{
			name:    "severity must be on the neutral ladder",
			mutate:  func(l *Label) { l.Truth.Severity = "error" },
			wantErr: "truth.severity \"error\" is not one of",
		},
		{
			name: "a sample cannot both perform and resemble",
			mutate: func(l *Label) {
				l.Truth.Resembles = []string{"reverse-shell"}
			},
			wantErr: "is in both truth.techniques and truth.resembles",
		},

		// --- expect is per-tool, optional, and checked against that tool's ladder ---
		{
			name:   "truth alone is a complete label",
			mutate: func(l *Label) { l.Expect = nil },
		},
		{
			name: "a second tool with its own ladder is fine",
			mutate: func(l *Label) {
				l.Expect["other"] = &ToolExpect{Rules: []string{"X1"}, MinSeverity: "error"}
			},
		},
		{
			name: "a severity from the wrong tool's ladder is caught",
			mutate: func(l *Label) {
				l.Expect["other"] = &ToolExpect{Rules: []string{"X1"}, MinSeverity: "high"}
			},
			wantErr: "min_severity \"high\" is not on other's ladder",
		},
		{
			name: "an undeclared tool cannot be checked against anything",
			mutate: func(l *Label) {
				l.Expect["snyk"] = &ToolExpect{Rules: []string{"S1"}, MinSeverity: "high"}
			},
			wantErr: "not in taxonomy/tools.yaml",
		},
		{
			name:    "an empty block would read as measured-and-clean",
			mutate:  func(l *Label) { l.Expect["aguard"] = nil },
			wantErr: "is empty — remove the key instead",
		},
		{
			name: "a rule in both lists makes the sample unfalsifiable",
			mutate: func(l *Label) {
				l.Expect["aguard"].Quiet = []string{"BD-003"}
			},
			wantErr: "unfalsifiable",
		},
		{
			name:    "malicious wants min_severity, not max",
			mutate:  func(l *Label) { l.Expect["aguard"].MaxSeverity = "low" },
			wantErr: "sets max_severity; it wants min_severity",
		},
		{
			name: "a block that asserts nothing should be dropped",
			mutate: func(l *Label) {
				l.Expect["aguard"] = &ToolExpect{MinSeverity: "high"}
			},
			wantErr: "lists no rules and is not marked out_of_scope",
		},
		{
			name: "out_of_scope replaces the rule assertion",
			mutate: func(l *Label) {
				l.Expect["aguard"] = &ToolExpect{OutOfScope: "pure runtime behaviour", MinSeverity: "high"}
			},
		},
		{
			name: "known_gap must name a work item",
			mutate: func(l *Label) {
				l.Expect["aguard"].KnownGap = &KnownGap{Observed: "nothing fires"}
			},
			wantErr: "known_gap.item is empty",
		},
		{
			name: "known_gap must record what happens today",
			mutate: func(l *Label) {
				l.Expect["aguard"].KnownGap = &KnownGap{Item: "W-027"}
			},
			wantErr: "known_gap.observed is empty",
		},

		// --- origin and licensing ---
		{
			name:    "labelling after running measures 100 percent every time",
			mutate:  func(l *Label) { l.Origin.LabeledBeforeRun = false },
			wantErr: "must be true",
		},
		{
			name:    "a non-permissive license belongs in layer 2",
			mutate:  func(l *Label) { l.Origin.License = "CC-BY-NC-SA-4.0" },
			wantErr: "may not be vendored into layer 1",
		},
		{
			name:    "surface must be a real surface",
			mutate:  func(l *Label) { l.Surface = "widgets" },
			wantErr: "surface \"widgets\" is not one of",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			l := malicious()
			tt.mutate(l)
			got := errText(l.Validate(testTax()))
			if tt.wantErr == "" {
				if got != "" {
					t.Fatalf("expected a clean label, got:\n%s", got)
				}
				return
			}
			if !strings.Contains(got, tt.wantErr) {
				t.Fatalf("expected an error containing %q, got:\n%s", tt.wantErr, got)
			}
		})
	}
}

func TestValidateHardNegative(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		mutate  func(*Label)
		wantErr string
	}{
		{name: "valid hard negative", mutate: func(*Label) {}},
		{
			name:    "resembling an attack is the definition of the class",
			mutate:  func(l *Label) { l.Truth.Resembles = nil },
			wantErr: "must list truth.resembles",
		},
		{
			name:    "differs_by is the discrimination test another tool's author needs",
			mutate:  func(l *Label) { l.Truth.DiffersBy = "" },
			wantErr: "must set truth.differs_by",
		},
		{
			name:    "a benign sample performs no technique",
			mutate:  func(l *Label) { l.Truth.Techniques = []string{"reverse-shell"} },
			wantErr: "lists truth.techniques",
		},
		{
			name:    "no finding is not a point on the ladder",
			mutate:  func(l *Label) { l.Truth.Severity = "low" },
			wantErr: "sets truth.severity",
		},
		{
			name:    "a benign sample asserts quiet, not fire",
			mutate:  func(l *Label) { l.Expect["aguard"].Rules = []string{"BD-003"} },
			wantErr: "lists rules",
		},
		{
			name:    "the expectation is a bound, never silence",
			mutate:  func(l *Label) { l.Expect["aguard"].MaxSeverity = "" },
			wantErr: "must set max_severity",
		},
		{
			name:    "out_of_scope is for malicious samples",
			mutate:  func(l *Label) { l.Expect["aguard"].OutOfScope = "runtime" },
			wantErr: "applies to malicious samples only",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			l := hardNegative()
			tt.mutate(l)
			got := errText(l.Validate(testTax()))
			if tt.wantErr == "" {
				if got != "" {
					t.Fatalf("expected a clean label, got:\n%s", got)
				}
				return
			}
			if !strings.Contains(got, tt.wantErr) {
				t.Fatalf("expected an error containing %q, got:\n%s", tt.wantErr, got)
			}
		})
	}
}

// TestPairingRunsThroughTruth is the regression test for the change this file was written
// for. The pairing used to be checked as an overlap between two labels' rule id lists, so a
// pair counted as valid whenever two samples happened to mention the same regex name, and
// the invariant could not be expressed at all for a scanner whose rule ids we do not know.
// It is now checked as "the twin actually performs a technique this sample resembles", which
// is a statement about the artifacts.
func TestPairingRunsThroughTruth(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		build   func() []*Label
		wantErr string
	}{
		{
			name: "twin performs what the hard negative resembles",
			build: func() []*Label {
				return []*Label{malicious(), hardNegative()}
			},
		},
		{
			name: "pairing holds with no rule ids anywhere",
			build: func() []*Label {
				m, h := malicious(), hardNegative()
				m.Expect, h.Expect = nil, nil
				return []*Label{m, h}
			},
		},
		{
			name: "sharing a rule id is not enough if the techniques differ",
			build: func() []*Label {
				m, h := malicious(), hardNegative()
				m.Truth.Techniques = []string{"env-exfiltration"}
				// Both still cite BD-003, which is what the old check looked at.
				return []*Label{m, h}
			},
			wantErr: "they share no technique",
		},
		{
			name: "a hard negative must be paired at all",
			build: func() []*Label {
				h := hardNegative()
				h.PairsWith = ""
				return []*Label{malicious(), h}
			},
			wantErr: "must set pairs_with",
		},
		{
			name: "the twin must exist",
			build: func() []*Label {
				h := hardNegative()
				h.PairsWith = "mal-nonexistent"
				return []*Label{malicious(), h}
			},
			wantErr: "does not exist",
		},
		{
			name: "the twin must be malicious",
			build: func() []*Label {
				h := hardNegative()
				other := hardNegative()
				other.ID = "mal-x" // the name says malicious, the class does not
				return []*Label{other, h}
			},
			wantErr: "not malicious",
		},
		{
			name: "a malicious sample does not pair",
			build: func() []*Label {
				m := malicious()
				m.PairsWith = "mal-x"
				return []*Label{m}
			},
			wantErr: "pairs_with is for benign look-alikes",
		},
		{
			name: "ids are never reused",
			build: func() []*Label {
				a, b := malicious(), malicious()
				return []*Label{a, b}
			},
			wantErr: "ids are never reused",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got := errText(ValidateSet(tt.build(), testTax(), nil))
			if tt.wantErr == "" {
				if got != "" {
					t.Fatalf("expected a clean set, got:\n%s", got)
				}
				return
			}
			if !strings.Contains(got, tt.wantErr) {
				t.Fatalf("expected an error containing %q, got:\n%s", tt.wantErr, got)
			}
		})
	}
}

func TestValidateSetChecksRuleIDsPerTool(t *testing.T) {
	t.Parallel()
	known := map[string]map[string]bool{"aguard": {"BD-003": true}}

	m := malicious()
	if got := errText(ValidateSet([]*Label{m}, testTax(), known)); got != "" {
		t.Fatalf("BD-003 is emittable, expected clean, got:\n%s", got)
	}

	m2 := malicious()
	m2.Expect["aguard"].Rules = []string{"BD-999"}
	got := errText(ValidateSet([]*Label{m2}, testTax(), known))
	if !strings.Contains(got, "which is not something aguard can emit") {
		t.Fatalf("expected a rule-id error, got:\n%s", got)
	}

	// A tool with no reachable rule reference is skipped, not assumed wrong. This repository
	// has to validate with no checkout of any scanner present.
	m3 := malicious()
	m3.Expect["other"] = &ToolExpect{Rules: []string{"WHATEVER"}, MinSeverity: "error"}
	if got := errText(ValidateSet([]*Label{m3}, testTax(), known)); strings.Contains(got, "WHATEVER") {
		t.Fatalf("an unreachable rule reference must downgrade to unchecked, got:\n%s", got)
	}
}

// TestUnguardedPairs covers the state that passes every structural check while guaranteeing
// nothing: the hard negative silences a rule, the twin is supposed to fire it, and the twin
// is on record failing to. Deleting the rule breaks neither sample. It is legitimate and it
// has to be visible, which is what this reports.
func TestUnguardedPairs(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		build func() []*Label
		want  int
	}{
		{
			name: "twin delivers the shared rule",
			build: func() []*Label {
				return []*Label{malicious(), hardNegative()}
			},
			want: 0,
		},
		{
			name: "twin is on record failing the shared rule",
			build: func() []*Label {
				m, h := malicious(), hardNegative()
				m.Expect["aguard"].KnownGap = &KnownGap{Item: "W-027", Observed: "silent"}
				return []*Label{m, h}
			},
			want: 1,
		},
		{
			name: "a gap on a rule the pair does not share is not this problem",
			build: func() []*Label {
				m, h := malicious(), hardNegative()
				m.Expect["aguard"].Rules = []string{"BD-003", "EXEC-001"}
				m.Expect["aguard"].KnownGap = &KnownGap{Item: "W-999", Observed: "silent"}
				h.Expect["aguard"].Quiet = []string{"EXFIL-001"}
				return []*Label{m, h}
			},
			want: 0,
		},
		{
			name: "a gap for a tool the hard negative does not annotate is not counted",
			build: func() []*Label {
				m, h := malicious(), hardNegative()
				m.Expect["other"] = &ToolExpect{
					Rules:    []string{"BD-003"},
					KnownGap: &KnownGap{Item: "X-1", Observed: "silent"},
				}
				delete(h.Expect, "aguard")
				h.Expect["other"] = &ToolExpect{Quiet: []string{"BD-003"}, MaxSeverity: "note"}
				return []*Label{m, h}
			},
			want: 1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got := UnguardedPairs(tt.build())
			if len(got) != tt.want {
				t.Fatalf("expected %d unguarded pair(s), got %d: %+v", tt.want, len(got), got)
			}
		})
	}
}

func TestUnguardedPairNamesTheEvidence(t *testing.T) {
	t.Parallel()
	m, h := malicious(), hardNegative()
	m.Expect["aguard"].KnownGap = &KnownGap{Item: "W-027", Observed: "88/100, BD-003 silent"}

	got := UnguardedPairs([]*Label{m, h})
	if len(got) != 1 {
		t.Fatalf("expected one unguarded pair, got %d", len(got))
	}
	u := got[0]
	if u.HardNegative != "hn-x" || u.Twin != "mal-x" || u.Tool != "aguard" || u.GapItem != "W-027" {
		t.Fatalf("report does not name the pair, the tool and the work item: %+v", u)
	}
	if len(u.SharedRules) != 1 || u.SharedRules[0] != "BD-003" {
		t.Fatalf("expected the shared rule to be named, got %v", u.SharedRules)
	}
}
