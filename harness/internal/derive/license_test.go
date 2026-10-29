// SPDX-License-Identifier: MIT
package derive

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// license_from exists because a compilation's licence is not its contents'. These tests pin
// that the pins file wins over the entry's licence, and that every way the lookup can fail is
// reported rather than quietly falling back to the entry's licence — a fallback would put the
// compilation's CC-BY-4.0 back on a tree whose author published under no licence, which is
// the exact state this mechanism was built to end.

func writePins(t *testing.T, dir, body string) string {
	t.Helper()
	p := filepath.Join(dir, "repo-licenses.json")
	if err := os.WriteFile(p, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
	return p
}

func TestLicenseFromPinsOverridesTheEntryLicence(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeFlatSample(t, root, "0x3ef8-moltbook-ai-agent-docs", "0x3ef8-moltbook-ai-agent-docs.provenance.json",
		`{"repo": "0x3EF8/moltbook-ai-agent"}`)
	pins := writePins(t, root, `{"0x3EF8/moltbook-ai-agent": {"license": "GPL-3.0", "checked": "2026-10-28"}}`)

	e := flatEntry("sidecar:<name>.provenance.json:repo")
	e.License = "CC-BY-4.0"
	e.Derive.LicenseFrom = "pins:" + pins + ":source-repo"
	res, errs := Derive(e, root, testTax())
	if len(errs) != 0 {
		t.Fatalf("unexpected errors: %v", errs)
	}
	if got := res.Coords[0].License; got != "GPL-3.0" {
		t.Errorf("license = %q, want the repository's GPL-3.0 from the pins file, not the compilation's", got)
	}
}

func TestLicenseFromPinsByName(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeFlatSample(t, root, "0xmonaco-mcp-server", "", "")
	pins := writePins(t, root, `{"0xmonaco-mcp-server": {"package": "@0xmonaco/mcp-server", "license": "ISC"}}`)

	e := flatEntry("")
	e.Derive.LicenseFrom = "pins:" + pins + ":name"
	res, errs := Derive(e, root, testTax())
	if len(errs) != 0 {
		t.Fatalf("unexpected errors: %v", errs)
	}
	if got := res.Coords[0].License; got != "ISC" {
		t.Errorf("license = %q, want ISC keyed by the tree's name", got)
	}
}

func TestLicenseFromPinsFailuresAreReportedNotSwallowed(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name       string
		pinsBody   string
		spec       func(pins string) string
		sourceFrom string
		wantErr    string
	}{
		{
			name:       "missing entry",
			pinsBody:   `{"someone/else": {"license": "MIT"}}`,
			spec:       func(p string) string { return "pins:" + p + ":source-repo" },
			sourceFrom: "sidecar:<name>.provenance.json:repo",
			wantErr:    "no entry for",
		},
		{
			name:       "empty licence",
			pinsBody:   `{"0x3EF8/moltbook-ai-agent": {"license": ""}}`,
			spec:       func(p string) string { return "pins:" + p + ":source-repo" },
			sourceFrom: "sidecar:<name>.provenance.json:repo",
			wantErr:    "records no licence",
		},
		{
			name:       "source-repo without a source",
			pinsBody:   `{}`,
			spec:       func(p string) string { return "pins:" + p + ":source-repo" },
			sourceFrom: "",
			wantErr:    "recovered no repository",
		},
		{
			name:       "unknown key",
			pinsBody:   `{}`,
			spec:       func(p string) string { return "pins:" + p + ":stars" },
			sourceFrom: "",
			wantErr:    "neither source-repo nor name",
		},
		{
			name:       "not a pins spec",
			pinsBody:   `{}`,
			spec:       func(p string) string { return "sidecar:x:y" },
			sourceFrom: "",
			wantErr:    "must be pins:",
		},
		{
			name:       "file missing",
			pinsBody:   ``,
			spec:       func(p string) string { return "pins:" + p + ".nope:name" },
			sourceFrom: "",
			wantErr:    "pins file",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			root := t.TempDir()
			writeFlatSample(t, root, "0x3ef8-moltbook-ai-agent-docs", "0x3ef8-moltbook-ai-agent-docs.provenance.json",
				`{"repo": "0x3EF8/moltbook-ai-agent"}`)
			pins := writePins(t, root, tc.pinsBody)
			e := flatEntry(tc.sourceFrom)
			e.Derive.LicenseFrom = tc.spec(pins)
			res, errs := Derive(e, root, testTax())
			if len(errs) == 0 {
				t.Fatalf("want an error containing %q, got none (license=%q)", tc.wantErr, res.Coords[0].License)
			}
			found := false
			for _, err := range errs {
				if strings.Contains(err.Error(), tc.wantErr) {
					found = true
				}
			}
			if !found {
				t.Errorf("errors %v do not mention %q", errs, tc.wantErr)
			}
			if res != nil && len(res.Coords) > 0 && res.Coords[0].License != "" {
				t.Errorf("license = %q after a failed lookup; a failure must not leave a licence behind", res.Coords[0].License)
			}
		})
	}
}
