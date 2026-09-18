// SPDX-License-Identifier: MIT

package taxonomy

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The real file is the one that ships, so load it rather than a fixture: a vocabulary test
// that passes against an invented copy tells you nothing about what validate will see.
func realBasis(t *testing.T) *BasisSpec {
	t.Helper()
	b, err := LoadBasis(filepath.Join("..", "..", "..", "taxonomy"))
	if err != nil {
		t.Fatalf("load shipped basis.yaml: %v", err)
	}
	return b
}

func TestShippedBasisIsWellFormed(t *testing.T) {
	b := realBasis(t)

	if b.Version < 1 {
		t.Errorf("version is %d, want >= 1 — a rate measured under one version is not "+
			"comparable to one measured under another, so the version has to be real", b.Version)
	}
	want := []string{"read", "upstream", "derived", "assumed"}
	if len(b.Order) != len(want) {
		t.Fatalf("got %d basis values %v, want %d", len(b.Order), b.Order, len(want))
	}
	for i, id := range want {
		if b.Order[i] != id {
			t.Errorf("basis[%d] = %q, want %q — order is meaningful in reports", i, b.Order[i], id)
		}
	}
	// `what` and `not` are both load-bearing, exactly as for dimensions: `not` is what stops
	// two neighbouring values from being used interchangeably.
	for _, id := range b.Order {
		v := b.Values[id]
		if strings.TrimSpace(v.What) == "" {
			t.Errorf("basis %q has no `what`", id)
		}
		if strings.TrimSpace(v.Not) == "" {
			t.Errorf("basis %q has no `not` — without it the value cannot be told apart "+
				"from its neighbour, which is how `assumed` gets recorded as `derived`", id)
		}
	}
}

func TestShippedBasisRequirementsReferOnlyToKnownValues(t *testing.T) {
	b := realBasis(t)
	if len(b.Requires) == 0 {
		t.Fatal("no `requires` — a basis with no mandatory companion field can be claimed " +
			"without supplying anything that would let a reader check it")
	}
	for id, fields := range b.Requires {
		if _, ok := b.Values[id]; !ok {
			t.Errorf("requires names basis %q, which is not defined", id)
		}
		if len(fields) == 0 {
			t.Errorf("basis %q requires nothing", id)
		}
	}
	for _, id := range b.Order {
		if _, ok := b.Requires[id]; !ok {
			t.Errorf("basis %q has no entry in `requires`", id)
		}
	}
}

// The scoring rule is the whole reason the vocabulary exists, so assert its shape rather
// than trusting the file to keep it.
func TestShippedBasisScoringRules(t *testing.T) {
	b := realBasis(t)

	if got := b.Scores["dimension"]; len(got) != 1 || got[0] != "read" {
		t.Errorf("dimension is scored from %v, want exactly [read] — attribution rests "+
			"entirely on this axis, and every inverted-attribution failure in this corpus "+
			"came from a rule reading a directory name", got)
	}
	if got := b.Scores["class"]; len(got) != 4 {
		t.Errorf("class is scored from %v, want all four bases (reported separately, "+
			"never pooled)", got)
	}
	for axis, allowed := range b.Scores {
		for _, id := range allowed {
			if _, ok := b.Values[id]; !ok {
				t.Errorf("axis %q is scored from %q, which is not a defined basis", axis, id)
			}
		}
	}
}

func TestBasisAllowsAxis(t *testing.T) {
	b := realBasis(t)
	cases := []struct {
		axis, basis string
		want        bool
	}{
		{"dimension", "read", true},
		{"dimension", "derived", false},
		{"dimension", "assumed", false},
		{"class", "assumed", true},
		{"class", "read", true},
		{"nonexistent-axis", "read", false},
	}
	for _, c := range cases {
		if got := b.AllowsAxis(c.axis, c.basis); got != c.want {
			t.Errorf("AllowsAxis(%q, %q) = %v, want %v", c.axis, c.basis, got, c.want)
		}
	}
}

func TestBasisKnown(t *testing.T) {
	b := realBasis(t)
	if !b.Known("assumed") {
		t.Error("`assumed` should be known")
	}
	if b.Known("probably") {
		t.Error("`probably` is not in the vocabulary and must not validate — a basis " +
			"vocabulary that accepts free text is not closed")
	}
}

// A malformed vocabulary must fail loudly at load. Silent acceptance of a broken file is
// worse than no file: everything downstream would report against a vocabulary nobody wrote.
func TestLoadBasisRejectsMalformed(t *testing.T) {
	cases := map[string]string{
		"unknown field": `version: 1
values: [{id: read, what: w, not: n}]
requires: {read: [evidence.quote]}
scores: {class: [read]}
surprise: 1
`,
		"duplicate id": `version: 1
values: [{id: read, what: w, not: n}, {id: read, what: w2, not: n2}]
requires: {read: [evidence.quote]}
scores: {class: [read]}
`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			dir := t.TempDir()
			if err := os.WriteFile(filepath.Join(dir, "basis.yaml"), []byte(body), 0o644); err != nil {
				t.Fatal(err)
			}
			if _, err := LoadBasis(dir); err == nil {
				t.Fatalf("malformed basis.yaml (%s) loaded without error", name)
			}
		})
	}
}

func TestLoadBasisMissingFile(t *testing.T) {
	if _, err := LoadBasis(t.TempDir()); err == nil {
		t.Fatal("LoadBasis succeeded with no basis.yaml present")
	}
}

// ValidateBasis guards the vocabulary against itself. Each case below is a way the file
// could be edited into something that still parses and no longer means anything.
func TestValidateBasisCatchesBrokenVocabulary(t *testing.T) {
	cases := map[string]struct {
		spec *BasisSpec
		want string
	}{
		"no version": {
			&BasisSpec{Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", What: "w", Not: "n"}},
				Requires: map[string][]string{"a": {"f"}}}, "version"},
		"missing not": {
			&BasisSpec{Version: 1, Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", What: "w"}},
				Requires: map[string][]string{"a": {"f"}}}, "`not`"},
		"missing what": {
			&BasisSpec{Version: 1, Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", Not: "n"}},
				Requires: map[string][]string{"a": {"f"}}}, "`what`"},
		"requires nothing": {
			&BasisSpec{Version: 1, Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", What: "w", Not: "n"}},
				Requires: map[string][]string{}}, "requires no companion field"},
		"requires unknown basis": {
			&BasisSpec{Version: 1, Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", What: "w", Not: "n"}},
				Requires: map[string][]string{"a": {"f"}, "ghost": {"f"}}}, "not defined"},
		"axis scored from nothing": {
			&BasisSpec{Version: 1, Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", What: "w", Not: "n"}},
				Requires: map[string][]string{"a": {"f"}}, Scores: map[string][]string{"dim": {}}}, "never be scored"},
		"axis scored from unknown": {
			&BasisSpec{Version: 1, Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", What: "w", Not: "n"}},
				Requires: map[string][]string{"a": {"f"}}, Scores: map[string][]string{"dim": {"ghost"}}}, "not a defined basis"},
		"debt without why": {
			&BasisSpec{Version: 1, Order: []string{"a"}, Values: map[string]BasisValue{"a": {ID: "a", What: "w", Not: "n"}},
				Requires: map[string][]string{"a": {"f"}}, Debt: []DebtRule{{Basis: "a", Class: []string{"malicious"}}}}, "`why`"},
	}
	for name, c := range cases {
		t.Run(name, func(t *testing.T) {
			errs := c.spec.ValidateBasis()
			if len(errs) == 0 {
				t.Fatalf("%s validated", name)
			}
			var joined string
			for _, e := range errs {
				joined += e.Error() + "\n"
			}
			if !strings.Contains(joined, c.want) {
				t.Errorf("errors %q do not mention %q", joined, c.want)
			}
		})
	}
}

func TestShippedBasisValidatesItself(t *testing.T) {
	if errs := realBasis(t).ValidateBasis(); len(errs) != 0 {
		t.Errorf("the shipped basis.yaml does not satisfy its own checks: %v", errs)
	}
}

func TestBasisIsDebtAndRequiredFields(t *testing.T) {
	b := realBasis(t)
	if _, ok := b.IsDebt("assumed", "malicious"); !ok {
		t.Error("an assumed malicious sample should be reported as outstanding")
	}
	if _, ok := b.IsDebt("assumed", "benign"); ok {
		t.Error("an assumed benign sample is the expected resting state, not debt")
	}
	if _, ok := b.IsDebt("read", "malicious"); ok {
		t.Error("a read coordinate is not debt")
	}
	if len(b.RequiredFields("read")) == 0 {
		t.Error("`read` should require its evidence fields")
	}
	if len(b.RequiredFields("nonexistent")) != 0 {
		t.Error("an unknown basis should require nothing rather than panicking")
	}
}
