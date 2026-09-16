// SPDX-License-Identifier: MIT

package taxonomy

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func write(t *testing.T, dir, name, body string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, name), []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
}

const goodTechniques = `
dimensions: [backdoor, exfiltration]
tiers:
  - id: plain
    maps_to: "000"
    what: nothing hides it
    calibration: true
  - id: evasive
    maps_to: "200"
    what: the text is transformed
evasion:
  - id: base64-wrapper
    implies_tier: evasive
    what: encoded and decoded at run time
techniques:
  - id: reverse-shell
    title: Reverse shell
    dimension: backdoor
    what: hands an interpreter to a remote peer
    benign_lookalike: any socket client that writes and closes
`

const goodTools = `
tools:
  - id: aguard
    name: AgentGuard
    url: https://example.invalid
    severity_ladder: [critical, high, medium, low, none]
    rule_id_pattern: '\b([A-Z]{2,10}-[A-Z0-9]{3,4})\b'
    section_pattern: '^## (?:[0-9]+ — )?(.+)$'
    rules_source:
      env: TEST_RULES_MD
      path: ../nowhere/rules.md
    native_format: sarif-2.1.0
    dimension_map:
      Backdoor: backdoor
      Obfuscation: ~
`

func loadFrom(t *testing.T, techniques, tools string) (*Set, error) {
	t.Helper()
	dir := t.TempDir()
	write(t, dir, "techniques.yaml", techniques)
	write(t, dir, "tools.yaml", tools)
	return Load(dir)
}

func TestLoadAndValidate(t *testing.T) {
	t.Parallel()
	s, err := loadFrom(t, goodTechniques, goodTools)
	if err != nil {
		t.Fatal(err)
	}
	if errs := s.Validate(); len(errs) != 0 {
		t.Fatalf("expected a clean vocabulary, got %v", errs)
	}
	if s.Dimension("reverse-shell") != "backdoor" {
		t.Fatalf("technique should resolve to its recall axis, got %q", s.Dimension("reverse-shell"))
	}
	if !s.Tools["aguard"].HasSeverity("medium") || s.Tools["aguard"].HasSeverity("warning") {
		t.Fatal("severity ladder membership is wrong")
	}
}

func TestValidateCatchesVocabularyMistakes(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name       string
		techniques string
		tools      string
		wantErr    string
	}{
		{
			name: "a misspelled dimension silently creates a one-member recall axis",
			techniques: `
dimensions: [backdoor]
techniques:
  - id: reverse-shell
    title: Reverse shell
    dimension: backdorr
    what: x
    benign_lookalike: y
`,
			tools:   goodTools,
			wantErr: "which is not in the dimensions list",
		},
		{
			name: "a technique without a definition is not a shared vocabulary",
			techniques: `
dimensions: [backdoor]
techniques:
  - id: reverse-shell
    title: Reverse shell
    dimension: backdoor
    benign_lookalike: y
`,
			tools:   goodTools,
			wantErr: "has no `what`",
		},
		{
			name: "every technique needs its benign lookalike written out",
			techniques: `
dimensions: [backdoor]
techniques:
  - id: reverse-shell
    title: Reverse shell
    dimension: backdoor
    what: x
`,
			tools:   goodTools,
			wantErr: "has no `benign_lookalike`",
		},
		{
			name:       "a tool without a ladder leaves every bound unvalidated",
			techniques: goodTechniques,
			tools: `
tools:
  - id: aguard
    name: AgentGuard
`,
			wantErr: "declares no severity_ladder",
		},
		{
			name:       "a rule pattern that does not compile",
			techniques: goodTechniques,
			tools: `
tools:
  - id: aguard
    name: AgentGuard
    severity_ladder: [high, none]
    rule_id_pattern: '([unclosed'
`,
			wantErr: "does not compile",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			s, err := loadFrom(t, tt.techniques, tt.tools)
			if err != nil {
				t.Fatal(err)
			}
			var b strings.Builder
			for _, e := range s.Validate() {
				b.WriteString(e.Error())
				b.WriteString("\n")
			}
			if !strings.Contains(b.String(), tt.wantErr) {
				t.Fatalf("expected an error containing %q, got:\n%s", tt.wantErr, b.String())
			}
		})
	}
}

// A typo'd field in the vocabulary is a silently ignored definition, which is why the
// decoder runs with KnownFields.
func TestLoadRejectsUnknownFields(t *testing.T) {
	t.Parallel()
	_, err := loadFrom(t, `
dimensions: [backdoor]
techniques:
  - id: reverse-shell
    title: Reverse shell
    dimension: backdoor
    what: x
    benign_lookalike: y
    mapping: ASI-05
`, goodTools)
	if err == nil || !strings.Contains(err.Error(), "mapping") {
		t.Fatalf("expected the unknown field to be rejected, got %v", err)
	}
}

// KnownRules must downgrade to "not checked" rather than pass everything, because this
// repository has to validate with no checkout of any scanner present.
func TestKnownRulesDowngradesWhenUnreachable(t *testing.T) {
	t.Parallel()
	s, err := loadFrom(t, goodTechniques, goodTools)
	if err != nil {
		t.Fatal(err)
	}
	idx := s.Tools["aguard"].ReadRules(t.TempDir())
	if idx != nil {
		t.Fatalf("expected an unreachable reference to yield nothing, got %d ids from %q", idx.Len(), idx.Source)
	}
}

// Not parallel: t.Setenv and t.Parallel are mutually exclusive.
func TestKnownRulesReadsTheReference(t *testing.T) {
	s, err := loadFrom(t, goodTechniques, goodTools)
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	ref := filepath.Join(dir, "rules.md")
	// REP-GOOD is the case a digits-only pattern gets wrong: it is a real rule id whose
	// suffix is not numeric, and a validator that misses it rejects any label citing it.
	write(t, dir, "rules.md",
		"## 7 — Backdoor\n| `BD-003` | high | ... |\n"+
			"## 6 — Obfuscation\n| `OBF-001` | medium | ... |\n"+
			"## Scan notes (dimension 0)\n| `REP-GOOD` | none | ... |\n")
	t.Setenv("TEST_RULES_MD", ref)

	idx := s.Tools["aguard"].ReadRules(dir)
	if idx == nil {
		t.Fatal("expected the reference to be read")
	}
	if idx.Source != ref {
		t.Fatalf("expected the env override to win, got %q", idx.Source)
	}
	if !idx.Has("BD-003") || !idx.Has("REP-GOOD") {
		t.Fatalf("expected both ids, got %v", idx.Dimension)
	}
}

// A rule's dimension is read from the tool's own generated reference, so it cannot drift
// from the tool. Keying on rule id prefix would be wrong: in AgentGuard `PERM-*` rules sit
// under three different dimensions.
func TestReadRulesAttributesDimensionPerSection(t *testing.T) {
	s, err := loadFrom(t, goodTechniques, goodTools)
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	write(t, dir, "rules.md",
		"## 7 — Backdoor\n| `BD-003` | high | ... |\n"+
			"## 6 — Obfuscation\n| `OBF-001` | medium | ... |\n")
	t.Setenv("TEST_RULES_MD", filepath.Join(dir, "rules.md"))

	idx := s.Tools["aguard"].ReadRules(dir)
	if idx == nil {
		t.Fatal("expected the reference to be read")
	}
	if d := idx.Dimension["BD-003"]; d == nil || *d != "backdoor" {
		t.Fatalf("BD-003 should attribute to backdoor, got %v", d)
	}
	// Measurement part 2 in one assertion: the tool found something and named no kind of
	// attack. That is a pass on part 1 and a failure on part 2, and it has to be
	// representable rather than collapsed into "caught it".
	if d, ok := idx.Dimension["OBF-001"]; !ok || d != nil {
		t.Fatalf("OBF-001 should be present and map to no dimension, got %v present=%v", d, ok)
	}
}

// A section carrying rules but missing from dimension_map is an oversight; a section mapped
// to null is a decision. They must not look alike.
func TestUnmappedSectionsAreReported(t *testing.T) {
	s, err := loadFrom(t, goodTechniques, goodTools)
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	write(t, dir, "rules.md",
		"## 7 — Backdoor\n| `BD-003` | high | ... |\n"+
			"## 4 — Code execution\n| `EXEC-001` | high | ... |\n")
	t.Setenv("TEST_RULES_MD", filepath.Join(dir, "rules.md"))

	idx := s.Tools["aguard"].ReadRules(dir)
	if idx == nil {
		t.Fatal("expected the reference to be read")
	}
	if len(idx.Unmapped) != 1 || idx.Unmapped[0] != "Code execution" {
		t.Fatalf("expected Code execution to be reported as unmapped, got %v", idx.Unmapped)
	}
}

// A section that only MENTIONS rules defined elsewhere is not a category. AgentGuard's
// reference ends with exactly such a section, and counting mentions made the check cry wolf
// about its own document's prose.
func TestMentionsDoNotCreateSections(t *testing.T) {
	s, err := loadFrom(t, goodTechniques, goodTools)
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	write(t, dir, "rules.md",
		"## 7 — Backdoor\n| `BD-003` | high | ... |\n"+
			"## Not covered by any rule\n- see `BD-003` for the adjacent case\n")
	t.Setenv("TEST_RULES_MD", filepath.Join(dir, "rules.md"))

	idx := s.Tools["aguard"].ReadRules(dir)
	if len(idx.Unmapped) != 0 {
		t.Fatalf("a prose mention must not register as a category, got %v", idx.Unmapped)
	}
	if d := idx.Dimension["BD-003"]; d == nil || *d != "backdoor" {
		t.Fatalf("the defining section must win, got %v", d)
	}
}

func TestTierOrdering(t *testing.T) {
	t.Parallel()
	s, err := loadFrom(t, goodTechniques, goodTools)
	if err != nil {
		t.Fatal(err)
	}
	if !s.TierAtLeast("evasive", "plain") {
		t.Fatal("evasive must rank at or above plain")
	}
	if s.TierAtLeast("plain", "evasive") {
		t.Fatal("plain must not rank at or above evasive")
	}
	// An unknown tier is not comparable, so a typo fails the bound rather than passing it.
	if s.TierAtLeast("typo", "plain") || s.TierAtLeast("plain", "typo") {
		t.Fatal("an unknown tier must never satisfy a bound")
	}
}
