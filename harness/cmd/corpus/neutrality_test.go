// SPDX-License-Identifier: MIT

package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// Each of these three checks was added after the property it guards had already broken
// quietly, so the test that matters is not that they pass on a clean corpus — it is that they
// FAIL on a dirty one. A neutrality check that cannot fail is worse than none: it prints a
// reassuring line while the coupling it was written for walks straight past.

func taxWithTool() *taxonomy.Set {
	return &taxonomy.Set{
		Dimensions: []string{"backdoor", "exfiltration"},
		Techniques: map[string]taxonomy.Technique{"reverse-shell": {ID: "reverse-shell"}},
		Tools: map[string]taxonomy.Tool{
			"aguard": {ID: "aguard", RulesSource: taxonomy.RulesSource{Env: "AGUARD_RULES_MD"}},
		},
	}
}

func lab(rel string, mutate func(*label.Label)) *label.Label {
	l := &label.Label{
		ID: "mal-x", Class: label.Malicious, Surface: label.Surfaces{"skills"}, Rel: rel,
		Truth: label.Truth{Techniques: []string{"reverse-shell"}, Severity: "high", Tier: "plain"},
	}
	if mutate != nil {
		mutate(l)
	}
	return l
}

func TestToolNamesInNeutralHalf(t *testing.T) {
	t.Parallel()
	tax := taxWithTool()

	cases := []struct {
		name    string
		label   *label.Label
		wantHit bool
	}{
		{"clean", lab("a.yaml", nil), false},
		{
			// The realistic drift: an observation about one scanner written into the shared
			// half, where it reads as helpful context and quietly becomes ground truth.
			name:    "truth.note names a scanner",
			label:   lab("b.yaml", func(l *label.Label) { l.Truth.Note = "aguard's BD-003 misses this" }),
			wantHit: true,
		},
		{
			name:    "truth.differs_by names a scanner",
			label:   lab("c.yaml", func(l *label.Label) { l.Truth.DiffersBy = "AGuard treats this as benign" }),
			wantHit: true,
		},
		{
			// Provenance is a fact about where the artifact came from, not a claim about what
			// it is. A sample rebuilt from a scanner's issue tracker has to cite it.
			name: "origin.source may cite a scanner",
			label: lab("d.yaml", func(l *label.Label) {
				l.Origin.Source = "https://github.com/basdotio/agent-guard W-027"
			}),
			wantHit: false,
		},
		{
			// The designated per-tool slot. Flagging it would make the feature unusable.
			name: "expect block is the slot for it",
			label: lab("e.yaml", func(l *label.Label) {
				l.Expect = map[string]*label.ToolExpect{"aguard": {Rules: []string{"BD-003"}}}
			}),
			wantHit: false,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got := ToolNamesInNeutralHalf([]*label.Label{tc.label}, tax)
			if (len(got) > 0) != tc.wantHit {
				t.Errorf("problems=%v, wantHit=%v", got, tc.wantHit)
			}
		})
	}
}

func TestToolNamesInVocabularyAreCaught(t *testing.T) {
	t.Parallel()
	tax := taxWithTool()
	tax.Dimensions = append(tax.Dimensions, "aguard-permissions")
	tax.Techniques["aguard-bypass"] = taxonomy.Technique{ID: "aguard-bypass"}

	got := ToolNamesInNeutralHalf(nil, tax)
	if len(got) != 2 {
		t.Fatalf("got %d problems, want 2 (one dimension, one technique): %v", len(got), got)
	}
	joined := strings.Join(got, "\n")
	if !strings.Contains(joined, "circular") {
		t.Errorf("the dimension message should say why it matters: %s", joined)
	}
}

func TestNoToolsRegisteredMeansNothingToCheck(t *testing.T) {
	t.Parallel()
	// A consumer who deletes every tool from the registry must not be told off about names
	// that no longer refer to anything.
	empty := taxWithTool()
	empty.Tools = map[string]taxonomy.Tool{}
	dirty := lab("a.yaml", func(l *label.Label) { l.Truth.Note = "aguard misses this" })
	if got := ToolNamesInNeutralHalf([]*label.Label{dirty}, empty); len(got) != 0 {
		t.Errorf("problems with no tools registered: %v", got)
	}
}

func writeGo(t *testing.T, root, rel, body string) {
	t.Helper()
	p := filepath.Join(root, rel)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
}

func TestToolNamesInHarnessCode(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name    string
		file    string
		body    string
		wantHit bool
	}{
		{
			// The exact mistake this check was written for: a CI assertion that pinned the
			// literal "aguard" as the set of scanners whose rules CI could not verify, making
			// one project's name part of the machinery that validates everybody's samples.
			name:    "string literal",
			file:    "internal/x/x.go",
			body:    "package x\n\nvar expected = \"aguard\"\n",
			wantHit: true,
		},
		{
			name:    "identifier",
			file:    "internal/x/y.go",
			body:    "package x\n\nfunc aguardSpecialCase() {}\n",
			wantHit: true,
		},
		{
			// Comments are exempt, and deliberately. The reasoning in this repository lives in
			// its comments, and several rules can only be explained by naming the scanner whose
			// configuration caused them. Explaining a mistake is the opposite of repeating it.
			name:    "comment is exempt",
			file:    "internal/x/z.go",
			body:    "package x\n\n// aguard's path used to escape the repository, hence this rule.\nvar n = 1\n",
			wantHit: false,
		},
		{
			// A test fixture has to put some id in the tools.yaml it builds.
			name:    "test file is exempt",
			file:    "internal/x/x_test.go",
			body:    "package x\n\nvar tools = \"id: aguard\"\n",
			wantHit: false,
		},
		{
			name:    "unrelated code",
			file:    "internal/x/w.go",
			body:    "package x\n\nvar greeting = \"hello\"\n",
			wantHit: false,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			root := t.TempDir()
			writeGo(t, root, filepath.Join("harness", tc.file), tc.body)
			got := ToolNamesInHarnessCode(root, taxWithTool())
			if (len(got) > 0) != tc.wantHit {
				t.Errorf("problems=%v, wantHit=%v", got, tc.wantHit)
			}
		})
	}
}

func TestCIDependsOnAScanner(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name    string
		yaml    string
		wantHit bool
	}{
		{
			// Forbidden through the front door: the rules_source.path rule already stops CI
			// reaching a scanner by relative path, and this is the same asymmetry by env var.
			name:    "env block",
			yaml:    "jobs:\n  x:\n    env:\n      AGUARD_RULES_MD: /tmp/rules.md\n",
			wantHit: true,
		},
		{
			name:    "exported in a run step",
			yaml:    "jobs:\n  x:\n    steps:\n      - run: export AGUARD_RULES_MD=/tmp/rules.md\n",
			wantHit: true,
		},
		{
			// The workflow has to be able to explain why it does not set the variable.
			name:    "comment explaining why it is unset",
			yaml:    "jobs:\n  x:\n    # Setting AGUARD_RULES_MD here would verify one project's rules only.\n    steps: []\n",
			wantHit: false,
		},
		{"clean", "jobs:\n  x:\n    steps:\n      - run: make validate\n", false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			root := t.TempDir()
			dir := filepath.Join(root, ".github", "workflows")
			if err := os.MkdirAll(dir, 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(dir, "v.yml"), []byte(tc.yaml), 0o600); err != nil {
				t.Fatal(err)
			}
			got := CIDependsOnAScanner(root, taxWithTool())
			if (len(got) > 0) != tc.wantHit {
				t.Errorf("problems=%v, wantHit=%v", got, tc.wantHit)
			}
		})
	}
}
