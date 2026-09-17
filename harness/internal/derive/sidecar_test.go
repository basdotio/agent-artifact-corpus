// SPDX-License-Identifier: MIT

package derive

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// The sidecar mechanism exists because a sampled corpus loses its provenance in the directory
// name: `0x3EF8/moltbook-ai-agent` slugs to `0x3ef8-moltbook-ai-agent-docs`, and no amount of
// parsing gets the repository back out of that. A false-positive rate has to be reported per
// source, so the source has to be recoverable — and it cannot live inside the sample tree,
// because a file in the tree is fed to the scanner as content.
//
// These tests pin the failure modes, not just the happy path. A sidecar that silently resolves
// to the empty string would make every sample report as source-unknown, which is a quiet loss
// of exactly the axis the mechanism was added to provide.

// flatEntry describes a corpus of `extracted/<name>` trees with provenance beside each.
func flatEntry(sourceFrom string) manifest.Entry {
	return manifest.Entry{
		ID: "skillmd-138k",
		Derive: &manifest.Derive{
			Layout:     "extracted/*",
			LabelFile:  strPtr(""),
			Surface:    "skills",
			IDPrefix:   "md",
			ClassFrom:  "constant:benign",
			SourceFrom: sourceFrom,
			Fidelity:   "class is a constant; the judgement is in the sampling",
			BenignNote: "a real public skill",
		},
	}
}

func strPtr(s string) *string { return &s }

// writeFlatSample creates root/extracted/<name>/SKILL.md, and the named sidecar beside the
// tree when body is non-empty.
func writeFlatSample(t *testing.T, root, name, sidecarName, sidecarBody string) {
	t.Helper()
	dir := filepath.Join(root, "extracted", name)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("# a skill\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if sidecarBody == "" {
		return
	}
	if err := os.WriteFile(filepath.Join(root, "extracted", sidecarName), []byte(sidecarBody), 0o600); err != nil {
		t.Fatal(err)
	}
}

func TestSidecarSourceRecoversTheOriginatingRepo(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	// The slug has lost the repository's casing and its slash. Only the sidecar has them.
	writeFlatSample(t, root, "0x3ef8-moltbook-ai-agent-docs", "0x3ef8-moltbook-ai-agent-docs.provenance.json",
		`{"repo": "0x3EF8/moltbook-ai-agent", "path": "docs/SKILL.md"}`)

	res, errs := Derive(flatEntry("sidecar:<name>.provenance.json:repo"), root, testTax())
	if len(errs) != 0 {
		t.Fatalf("unexpected errors: %v", errs)
	}
	if len(res.Coords) != 1 {
		t.Fatalf("got %d coords, want 1", len(res.Coords))
	}
	if got := res.Coords[0].Source; got != "0x3EF8/moltbook-ai-agent" {
		t.Errorf("source = %q, want the repository from the sidecar with its casing intact", got)
	}
	if res.Coords[0].Class != "benign" {
		t.Errorf("class = %q, want benign from constant:", res.Coords[0].Class)
	}
}

func TestSidecarSourceFailuresAreReportedNotSwallowed(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name        string
		sourceFrom  string
		sidecarName string
		sidecarBody string
		wantErr     string
	}{
		{
			name:       "missing sidecar",
			sourceFrom: "sidecar:<name>.provenance.json:repo",
			// No sidecar written at all: the sample is there, its provenance is not.
			wantErr: "is missing",
		},
		{
			name:        "field absent",
			sourceFrom:  "sidecar:<name>.provenance.json:repo",
			sidecarName: "s.provenance.json",
			sidecarBody: `{"path": "docs/SKILL.md"}`,
			wantErr:     `has no field "repo"`,
		},
		{
			name:        "not json",
			sourceFrom:  "sidecar:<name>.provenance.json:repo",
			sidecarName: "s.provenance.json",
			sidecarBody: "repo: o/r\n",
			wantErr:     "is not JSON",
		},
		{
			name:        "malformed spec",
			sourceFrom:  "sidecar:justafile",
			sidecarName: "s.provenance.json",
			sidecarBody: `{"repo": "o/r"}`,
			wantErr:     "must be sidecar:<file>:<field>",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			root := t.TempDir()
			writeFlatSample(t, root, "s", tc.sidecarName, tc.sidecarBody)

			_, errs := Derive(flatEntry(tc.sourceFrom), root, testTax())
			if len(errs) == 0 {
				t.Fatalf("no error reported; an unreadable sidecar would silently drop the source")
			}
			var joined []string
			for _, e := range errs {
				joined = append(joined, e.Error())
			}
			if !strings.Contains(strings.Join(joined, "\n"), tc.wantErr) {
				t.Errorf("errors %v\n  want one containing %q", joined, tc.wantErr)
			}
		})
	}
}

// A benign derivation must not acquire coordinates it has no basis for. The whole credibility
// scheme rests on hand-pinned and derived coordinates being distinguishable, and a benign
// sample from a constant has no tier, dimension or evasion to report.
func TestBenignFromConstantCarriesNoCoordinates(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeFlatSample(t, root, "s", "s.provenance.json", `{"repo": "o/r"}`)

	res, errs := Derive(flatEntry("sidecar:<name>.provenance.json:repo"), root, testTax())
	if len(errs) != 0 {
		t.Fatalf("unexpected errors: %v", errs)
	}
	c := res.Coords[0]
	if c.Tier != "" || len(c.Dimensions) != 0 || len(c.Evasion) != 0 || c.Severity != "" {
		t.Errorf("benign coord carries tier=%q dims=%v evasion=%v severity=%q — all four are "+
			"unearned for a class that came from a constant", c.Tier, c.Dimensions, c.Evasion, c.Severity)
	}
}
