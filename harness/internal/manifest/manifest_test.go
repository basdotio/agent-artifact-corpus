// SPDX-License-Identifier: MIT

package manifest

import (
	"strings"
	"testing"
)

func errText(errs []error) string {
	var b strings.Builder
	for _, e := range errs {
		b.WriteString(e.Error())
		b.WriteString("\n")
	}
	return b.String()
}

func goodEntry() Entry {
	return Entry{
		ID:      "skillsgoat",
		URL:     "https://github.com/optimuslabs-io/skillsgoat",
		Commit:  "c03d70d80c32",
		License: "MIT",
		Role:    "recall",
		Hazards: []string{"single author"},
	}
}

func TestValidateEntry(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		mutate  func(*Entry)
		wantErr string
	}{
		{name: "a complete entry", mutate: func(*Entry) {}},
		{
			name:    "url is what makes the reference resolvable",
			mutate:  func(e *Entry) { e.URL = "" },
			wantErr: "url is empty",
		},
		{
			// The licence decides whether a corpus may ever be vendored, so an entry without
			// one cannot be placed in either layer.
			name:    "licence decides the layer",
			mutate:  func(e *Entry) { e.License = "" },
			wantErr: "license is empty",
		},
		{
			name:    "role must be one we report on",
			mutate:  func(e *Entry) { e.Role = "misc" },
			wantErr: "is not one of",
		},
		{
			// An undeclared hazard is how the next person uses a corpus wrong; "none known"
			// has to be written out rather than left implicit.
			name:    "hazards may not be silently empty",
			mutate:  func(e *Entry) { e.Hazards = nil },
			wantErr: "hazards is empty",
		},
		{
			name:    "a moving reference makes published numbers irreproducible",
			mutate:  func(e *Entry) { e.Commit = "" },
			wantErr: "commit is empty",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			e := goodEntry()
			tt.mutate(&e)
			got := errText((&File{Entries: []Entry{e}}).Validate())
			if tt.wantErr == "" {
				if got != "" {
					t.Fatalf("expected a clean entry, got:\n%s", got)
				}
				return
			}
			if !strings.Contains(got, tt.wantErr) {
				t.Fatalf("expected %q, got:\n%s", tt.wantErr, got)
			}
		})
	}
}

// The derive block is format-checked here; the semantic check (do the axis targets exist)
// needs the taxonomy and lives in the derive package.
func TestValidateDeriveBlock(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		derive  *Derive
		wantErr string
	}{
		{
			name: "a complete derive rule",
			derive: &Derive{
				Layout:          "pasture/*/*",
				Fidelity:        "tier mechanical, dimension lossy",
				CategoryAxisMap: map[string]string{"a": "dim:backdoor", "b": "evasion:zero-width", "c": "tier:plain", "d": "ignore"},
			},
		},
		{
			// A derivation with no stated loss is the most dangerous kind, because it reads as
			// exact.
			name:    "fidelity may not be omitted",
			derive:  &Derive{Layout: "x/*"},
			wantErr: "no derive.fidelity",
		},
		{
			name:    "layout says where the samples are",
			derive:  &Derive{Fidelity: "f"},
			wantErr: "derive.layout is empty",
		},
		{
			name: "an axis target must name its axis",
			derive: &Derive{
				Layout: "x/*", Fidelity: "f",
				CategoryAxisMap: map[string]string{"a": "backdoor"},
			},
			wantErr: "must be dim:<x>, evasion:<y>, tier:<z> or ignore",
		},
		{
			name: "an empty value after the prefix is not a target",
			derive: &Derive{
				Layout: "x/*", Fidelity: "f",
				CategoryAxisMap: map[string]string{"a": "dim:"},
			},
			wantErr: "must be dim:<x>",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			e := goodEntry()
			e.Derive = tt.derive
			got := errText((&File{Entries: []Entry{e}}).Validate())
			if tt.wantErr == "" {
				if got != "" {
					t.Fatalf("expected a clean derive block, got:\n%s", got)
				}
				return
			}
			if !strings.Contains(got, tt.wantErr) {
				t.Fatalf("expected %q, got:\n%s", tt.wantErr, got)
			}
		})
	}
}

// Overlapping entries may never be summed: the corpora contain one another, and adding their
// counts inflates a denominator in the flattering direction.
func TestPoolableGroupsKeepsOverlapsTogether(t *testing.T) {
	t.Parallel()
	a, b, c := goodEntry(), goodEntry(), goodEntry()
	a.ID, b.ID, c.ID = "datadog", "trailofbits", "skillmd"
	a.Overlaps = []string{"trailofbits"}

	groups := (&File{Entries: []Entry{a, b, c}}).PoolableGroups()
	var withDatadog []string
	for _, g := range groups {
		for _, id := range g {
			if id == "datadog" {
				withDatadog = g
			}
		}
	}
	if len(withDatadog) != 2 {
		t.Fatalf("datadog and trailofbits overlap and must land in one unpoolable group, got %v", groups)
	}
	if len(groups) != 2 {
		t.Fatalf("skillmd overlaps nothing and should stand alone, got %v", groups)
	}
}

func TestOverlapMustResolve(t *testing.T) {
	t.Parallel()
	e := goodEntry()
	e.Overlaps = []string{"not-an-entry"}
	got := errText((&File{Entries: []Entry{e}}).Validate())
	if !strings.Contains(got, "which is not an entry here") {
		t.Fatalf("an unresolvable overlap must be reported, got:\n%s", got)
	}
}
