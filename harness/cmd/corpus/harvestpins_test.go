// SPDX-License-Identifier: MIT

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// treeHashByHand is the pins file's own formula, written out independently of the code under
// test: sha256 over the sorted list of "<relative path>\0<sha256 of content>\n".
func treeHashByHand(files map[string]string) string {
	var lines []string
	for rel, content := range files {
		sum := sha256.Sum256([]byte(content))
		lines = append(lines, rel+"\x00"+hex.EncodeToString(sum[:])+"\n")
	}
	// sorted the same way Python sorts the (path, digest) tuples
	for i := range lines {
		for j := i + 1; j < len(lines); j++ {
			if lines[j] < lines[i] {
				lines[i], lines[j] = lines[j], lines[i]
			}
		}
	}
	sum := sha256.Sum256([]byte(strings.Join(lines, "")))
	return hex.EncodeToString(sum[:])
}

func writeHarvest(t *testing.T, root string, pinHash string, files map[string]string) {
	t.Helper()
	tree := filepath.Join(root, "corpus", "benign", "mcp", "gh-a")
	for rel, content := range files {
		p := filepath.Join(tree, filepath.FromSlash(rel))
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	pins := map[string]any{"pins": []map[string]any{
		{"name": "gh-a", "repo": "owner/a", "surface": "mcp", "tree_sha256": pinHash, "files": len(files)},
	}}
	b, _ := json.Marshal(pins)
	p := filepath.Join(root, filepath.FromSlash(harvestPinsRel))
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, b, 0o644); err != nil {
		t.Fatal(err)
	}
}

var harvestFiles = map[string]string{"server.py": "x", "sub/index.ts": "y", "README.md": "z"}

// The pin's claim and the committed bytes agree: nothing to report.
func TestHarvestTreeMatchingItsPin(t *testing.T) {
	root := t.TempDir()
	writeHarvest(t, root, treeHashByHand(harvestFiles), harvestFiles)
	checked, drift, err := CheckHarvestTrees(root)
	if err != nil || checked != 1 || len(drift) != 0 {
		t.Fatalf("want 1 checked, no drift; got %d, %+v, %v", checked, drift, err)
	}
}

// A tree whose bytes moved away from its pin is exactly what the re-harvest used to delete
// silently. validate must name it.
func TestHarvestTreeDriftedFromItsPin(t *testing.T) {
	root := t.TempDir()
	writeHarvest(t, root, strings.Repeat("0", 64), harvestFiles)
	_, drift, err := CheckHarvestTrees(root)
	if err != nil || len(drift) != 1 || drift[0].Name != "gh-a" || drift[0].State != "drifted" {
		t.Fatalf("want gh-a drifted, got %+v, %v", drift, err)
	}
	if got := reportHarvestTrees(root); len(got) != 1 || !strings.Contains(got[0], "gh-a") {
		t.Fatalf("drift must become a problem naming the tree: %q", got)
	}
}

// A pin whose tree is gone is an orphan — the state #8 had to clean up by hand.
func TestHarvestPinWithoutTree(t *testing.T) {
	root := t.TempDir()
	writeHarvest(t, root, treeHashByHand(harvestFiles), harvestFiles)
	if err := os.RemoveAll(filepath.Join(root, "corpus")); err != nil {
		t.Fatal(err)
	}
	_, drift, _ := CheckHarvestTrees(root)
	if len(drift) != 1 || drift[0].State != "missing" {
		t.Fatalf("want gh-a missing, got %+v", drift)
	}
}

// A checkout without a harvest has nothing to check, which is not a failure.
func TestNoHarvestPinsFile(t *testing.T) {
	checked, drift, err := CheckHarvestTrees(t.TempDir())
	if err != nil || checked != 0 || len(drift) != 0 {
		t.Fatalf("no pins file means nothing checked: %d, %+v, %v", checked, drift, err)
	}
}

// The harvester deliberately writes no benign tree for a pin whose repository a malicious or
// hard-negative label has claimed (promoted_elsewhere), and keeps the pin. That is not an
// orphan, and validate must not fail the build over a state the harvester produces by design.
func TestPromotedPinIsNotMissing(t *testing.T) {
	root := t.TempDir()
	writeHarvest(t, root, treeHashByHand(harvestFiles), harvestFiles)
	if err := os.RemoveAll(filepath.Join(root, "corpus", "benign")); err != nil {
		t.Fatal(err)
	}
	hn := filepath.Join(root, "corpus", "hard-negative", "mcp", "hn-mcp-a.yaml")
	if err := os.MkdirAll(filepath.Dir(hn), 0o755); err != nil {
		t.Fatal(err)
	}
	src := "origin:\n  source: \"https://github.com/owner/a/tree/abc\"\n"
	if err := os.WriteFile(hn, []byte(src), 0o644); err != nil {
		t.Fatal(err)
	}
	checked, drift, err := CheckHarvestTrees(root)
	if err != nil || checked != 1 || len(drift) != 1 || drift[0].State != "promoted" {
		t.Fatalf("want gh-a reported as promoted: checked=%d drift=%+v err=%v", checked, drift, err)
	}
	if got := reportHarvestTrees(root); len(got) != 0 {
		t.Fatalf("a promoted pin must not become a problem: %q", got)
	}
}
