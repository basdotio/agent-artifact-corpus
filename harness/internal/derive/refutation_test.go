// SPDX-License-Identifier: MIT

package derive

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeTree(t *testing.T, files map[string]string) string {
	t.Helper()
	dir := t.TempDir()
	for name, body := range files {
		p := filepath.Join(dir, name)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

func TestRefutationBlockCleanSample(t *testing.T) {
	dir := writeTree(t, map[string]string{
		"SKILL.md": "---\nname: x\n---\n\n# X\n\nRun `npm test` before pushing.\n",
	})
	got := RefutationBlock(dir, 1)

	for _, want := range []string{"refutation_search:", "ruleset_version: 1", "matched: []"} {
		if !strings.Contains(got, want) {
			t.Errorf("got %q, missing %q", got, want)
		}
	}
	// The byte count is what separates a clean tree from an empty one; both match nothing.
	if strings.Contains(got, "scanned_bytes: 0") {
		t.Errorf("got %q — a non-empty tree must not report zero bytes scanned", got)
	}
}

func TestRefutationBlockRecordsMatches(t *testing.T) {
	dir := writeTree(t, map[string]string{
		"SKILL.md": "token: ghp_abcdefghijklmnopqrstuvwxyz0123\n",
	})
	if got := RefutationBlock(dir, 1); !strings.Contains(got, "live-credential") {
		t.Errorf("got %q, want the match recorded", got)
	}
}

// An empty tree and a clean tree both match nothing. Only the byte count tells them apart,
// which is why refutation.yaml makes it mandatory.
func TestRefutationBlockEmptyTreeIsDistinguishable(t *testing.T) {
	got := RefutationBlock(t.TempDir(), 1)
	if !strings.Contains(got, "scanned_bytes: 0") {
		t.Errorf("got %q, want zero bytes reported", got)
	}
	if !strings.Contains(got, "no-judgeable-content") {
		t.Errorf("got %q — an empty tree has nothing to judge and should say so", got)
	}
}

func TestRefutationBlockReadsSymlinkTargetNotTarget(t *testing.T) {
	dir := t.TempDir()
	if err := os.Symlink("../../fixtures/escape-target.yaml", filepath.Join(dir, "config.yaml")); err != nil {
		t.Skip("symlinks unavailable")
	}
	got := RefutationBlock(dir, 1)
	// The link text is 33 bytes; following it would error and read nothing.
	if strings.Contains(got, "scanned_bytes: 0") {
		t.Errorf("got %q — the link target path is the content worth scanning", got)
	}
}
