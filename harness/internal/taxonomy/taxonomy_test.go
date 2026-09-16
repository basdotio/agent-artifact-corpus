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
    rules_source:
      env: TEST_RULES_MD
      path: ../nowhere/rules.md
    native_format: sarif-2.1.0
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
	rules, src := s.Tools["aguard"].KnownRules(t.TempDir())
	if rules != nil || src != "" {
		t.Fatalf("expected an unreachable reference to yield nothing, got %d ids from %q", len(rules), src)
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
	write(t, dir, "rules.md", "| `BD-003` | high | ... |\n| `REP-GOOD` | none | ... |\n")
	t.Setenv("TEST_RULES_MD", ref)

	rules, src := s.Tools["aguard"].KnownRules(dir)
	if src != ref {
		t.Fatalf("expected the env override to win, got %q", src)
	}
	if !rules["BD-003"] || !rules["REP-GOOD"] {
		t.Fatalf("expected both ids, got %v", rules)
	}
}
