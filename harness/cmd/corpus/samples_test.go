// SPDX-License-Identifier: MIT

package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestParseSourceFilters(t *testing.T) {
	tests := []struct {
		name        string
		args        []string
		wantInclude []string
		wantExclude []string
		wantErr     string
	}{
		{name: "no arguments filters nothing"},
		{
			name:        "a comma-separated exclusion",
			args:        []string{"--exclude-source", "cisco-mcp-scanner-evals,harvested"},
			wantExclude: []string{"cisco-mcp-scanner-evals", "harvested"},
		},
		{
			name:        "whitespace around a name is trimmed",
			args:        []string{"--exclude-source", " harvested , hand-written "},
			wantExclude: []string{"hand-written", "harvested"},
		},
		{
			name:        "an inclusion",
			args:        []string{"--source", "skillmd-138k"},
			wantInclude: []string{"skillmd-138k"},
		},
		{
			// Two readings — subtract from the included set, or intersect — and a reader of the
			// resulting number could not tell which was meant.
			name:    "both at once is ambiguous",
			args:    []string{"--source", "a", "--exclude-source", "b"},
			wantErr: "ambiguous",
		},
		{
			name:    "a flag with no value",
			args:    []string{"--exclude-source"},
			wantErr: "needs a comma-separated list",
		},
		{
			name:    "an unknown argument",
			args:    []string{"--exclude", "a"},
			wantErr: "unknown argument",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			inc, exc, err := parseSourceFilters(tt.args)
			if tt.wantErr != "" {
				if err == nil {
					t.Fatalf("parseSourceFilters accepted %v", tt.args)
				}
				if !strings.Contains(err.Error(), tt.wantErr) {
					t.Errorf("error does not mention %q: %v", tt.wantErr, err)
				}
				return
			}
			if err != nil {
				t.Fatalf("parseSourceFilters: %v", err)
			}
			assertSet(t, "include", inc, tt.wantInclude)
			assertSet(t, "exclude", exc, tt.wantExclude)
		})
	}
}

func assertSet(t *testing.T, what string, got map[string]bool, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Errorf("%s has %d names, want %d: %v", what, len(got), len(want), got)
		return
	}
	for _, name := range want {
		if !got[name] {
			t.Errorf("%s is missing %q: %v", what, name, got)
		}
	}
}

// TestAMistypedSourceIsRefused pins the failure direction that matters. Filtering nothing is the
// dangerous outcome: the operator would publish a figure believing it excluded a tool's own
// fixtures, with a command in their shell history to prove they had asked.
func TestAMistypedSourceIsRefused(t *testing.T) {
	counts := map[string]int{"cisco-mcp-scanner-evals": 127, "harvested": 391}

	err := checkNamesExist(counts, map[string]bool{"cisco-mcp-scanner-eval": true}, nil)
	if err == nil {
		t.Fatal("checkNamesExist accepted a name no sample carries")
	}
	for _, want := range []string{
		"cisco-mcp-scanner-eval",  // the name that was wrong
		"looks de-contaminated",   // why refusing beats filtering nothing
		"cisco-mcp-scanner-evals", // the list, so the fix is in the error
	} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error does not contain %q:\n%v", want, err)
		}
	}

	if err := checkNamesExist(counts, map[string]bool{"harvested": true}, nil); err != nil {
		t.Errorf("checkNamesExist rejected a name that exists: %v", err)
	}
}

// TestReportExclusionAlwaysSaysSomething — the no-exclusion line is not noise. It is what makes
// the ABSENCE of an exclusion notice into evidence: a reader who sees nothing cannot tell whether
// nothing was excluded or the report was not printed.
func TestReportExclusionAlwaysSaysSomething(t *testing.T) {
	t.Run("nothing dropped", func(t *testing.T) {
		got := captureStderr(t, func(w *os.File) {
			reportExclusion(w, 3539, 3539, nil)
		})
		if !strings.Contains(got, "no source excluded") {
			t.Errorf("silent on a run that excluded nothing: %q", got)
		}
	})

	t.Run("a source dropped", func(t *testing.T) {
		got := captureStderr(t, func(w *os.File) {
			reportExclusion(w, 3539, 3412, map[string]int{"cisco-mcp-scanner-evals": 127})
		})
		for _, want := range []string{"3412 of 3539", "127 excluded", "cisco-mcp-scanner-evals",
			"citation rule"} {
			if !strings.Contains(got, want) {
				t.Errorf("report does not mention %q:\n%s", want, got)
			}
		}
	})
}

// captureStderr runs fn against a temporary file and returns what was written. A real *os.File
// rather than a buffer because reportExclusion takes one — it writes to stderr so the work list
// on stdout stays parseable, and that distinction is the point of the signature.
func captureStderr(t *testing.T, fn func(*os.File)) string {
	t.Helper()
	p := filepath.Join(t.TempDir(), "err")
	f, err := os.Create(p)
	if err != nil {
		t.Fatal(err)
	}
	fn(f)
	if err := f.Close(); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}
