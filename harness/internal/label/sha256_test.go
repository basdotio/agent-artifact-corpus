// SPDX-License-Identifier: MIT

package label

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func hashOf(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

// writeTree creates a sample tree holding the named files and returns its path.
func writeTree(t *testing.T, files map[string]string) string {
	t.Helper()
	dir := filepath.Join(t.TempDir(), "sample")
	for name, body := range files {
		p := filepath.Join(dir, name)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(body), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

func TestVerifySha256(t *testing.T) {
	t.Parallel()
	const body = `{"hooks": {}}`

	cases := []struct {
		name    string
		hash    string
		files   map[string]string
		wantErr string
	}{
		{
			// The common case across the corpus: upstream published no hash, so there is
			// nothing to check and inventing one from our own copy would only prove we can
			// hash a file.
			name:  "no hash is not a failure",
			hash:  "",
			files: map[string]string{".claude/settings.json": body},
		},
		{
			name:  "matching hash passes",
			hash:  hashOf(body),
			files: map[string]string{".claude/settings.json": body},
		},
		{
			// The reason the field exists. The vendored bytes are not the ones collected, so
			// every number published against this sample is suspect.
			name:    "mismatch is caught",
			hash:    hashOf("something else"),
			files:   map[string]string{".claude/settings.json": body},
			wantErr: "is not the one that was collected",
		},
		{
			name:    "several files have no single artifact",
			hash:    hashOf(body),
			files:   map[string]string{".claude/settings.json": body, ".mcp.json": "{}"},
			wantErr: "holds 2 files",
		},
		{
			name:    "malformed digest",
			hash:    "not-a-hash",
			files:   map[string]string{".claude/settings.json": body},
			wantErr: "not a 64-character lowercase hex digest",
		},
		{
			// Uppercase hex is the same value but not the same string, and accepting it would
			// make two labels that disagree textually both pass.
			name:    "uppercase digest rejected",
			hash:    strings.ToUpper(hashOf(body)),
			files:   map[string]string{".claude/settings.json": body},
			wantErr: "not a 64-character lowercase hex digest",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			l := &Label{Path: writeTree(t, tc.files)}
			l.Origin.Sha256 = tc.hash

			errs := l.VerifySha256()
			if tc.wantErr == "" {
				if len(errs) != 0 {
					t.Fatalf("unexpected errors: %v", errs)
				}
				return
			}
			if len(errs) == 0 {
				t.Fatalf("no error; an unverified hash reads like integrity while providing none")
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

// An empty tree with a hash set is a mispin, not a pass: the label claims to have collected
// bytes that are not here.
func TestVerifySha256EmptyTree(t *testing.T) {
	t.Parallel()
	l := &Label{Path: writeTree(t, map[string]string{})}
	l.Origin.Sha256 = hashOf("anything")
	if errs := l.VerifySha256(); len(errs) == 0 {
		t.Fatal("an empty tree with a hash set must be reported")
	}
}
