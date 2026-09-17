// SPDX-License-Identifier: MIT

package main

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
)

// The code claimed duplication was "the leakage the corpus rejects elsewhere" while rejecting
// it nowhere: a tree copied verbatim under a new id validated cleanly. These tests exist so
// that claim stays true rather than aspirational.

func tree(t *testing.T, root, name string, files map[string]string) string {
	t.Helper()
	dir := filepath.Join(root, name)
	for n, body := range files {
		p := filepath.Join(dir, n)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(body), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

func TestDuplicateTrees(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	same := map[string]string{"SKILL.md": "# identical\n", "run.sh": "echo hi\n"}

	a := &label.Label{ID: "a", Class: label.Benign, Path: tree(t, root, "a", same)}
	b := &label.Label{ID: "b", Class: label.Benign, Path: tree(t, root, "b", same)}
	c := &label.Label{ID: "c", Class: label.Malicious,
		Path: tree(t, root, "c", map[string]string{"SKILL.md": "# different\n"})}
	// Same bytes, different path inside the tree: NOT a duplicate. Where a file sits is part
	// of what the sample is — a hook in .claude/settings.json is not the same artifact as the
	// same JSON sitting loose.
	d := &label.Label{ID: "d", Class: label.Benign,
		Path: tree(t, root, "d", map[string]string{"nested/SKILL.md": "# identical\n", "run.sh": "echo hi\n"})}

	groups := DuplicateTrees([]*label.Label{a, b, c, d})
	if len(groups) != 1 {
		t.Fatalf("got %d groups, want 1: %+v", len(groups), groups)
	}
	if len(groups[0].IDs) != 2 || groups[0].IDs[0] != "a" || groups[0].IDs[1] != "b" {
		t.Errorf("group = %v, want [a b]", groups[0].IDs)
	}
	if groups[0].CrossClass() {
		t.Errorf("a and b are both benign; CrossClass must be false")
	}
}

// The severe case: one artifact filed under two classes would let a scanner be scored right
// and wrong for the same input.
func TestCrossClassDuplicateIsAnError(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	same := map[string]string{"SKILL.md": "# identical\n"}
	a := &label.Label{ID: "ben-x", Class: label.Benign, Path: tree(t, root, "a", same)}
	b := &label.Label{ID: "mal-x", Class: label.Malicious, Path: tree(t, root, "b", same)}

	groups := DuplicateTrees([]*label.Label{a, b})
	if len(groups) != 1 || !groups[0].CrossClass() {
		t.Fatalf("cross-class duplicate not detected: %+v", groups)
	}
	if problems := reportDuplicates(groups); len(problems) != 1 {
		t.Fatalf("got %d problems, want 1 — a cross-class duplicate must fail, not merely be reported", len(problems))
	}
}

// A same-class duplicate is reported, not failed: five exist today, they are real, and
// deleting them would quietly shrink a published denominator.
func TestSameClassDuplicateIsReportedNotFailed(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	same := map[string]string{"SKILL.md": "# identical\n"}
	a := &label.Label{ID: "ben-a", Class: label.Benign, Path: tree(t, root, "a", same)}
	b := &label.Label{ID: "ben-b", Class: label.Benign, Path: tree(t, root, "b", same)}

	if problems := reportDuplicates(DuplicateTrees([]*label.Label{a, b})); len(problems) != 0 {
		t.Errorf("same-class duplicates must not fail the build: %v", problems)
	}
}

// An empty tree hashes to nothing and must not be grouped with every other empty tree.
func TestEmptyTreesAreNotDuplicatesOfEachOther(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	for _, n := range []string{"a", "b"} {
		if err := os.MkdirAll(filepath.Join(root, n), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	a := &label.Label{ID: "a", Class: label.Benign, Path: filepath.Join(root, "a")}
	b := &label.Label{ID: "b", Class: label.Benign, Path: filepath.Join(root, "b")}
	if groups := DuplicateTrees([]*label.Label{a, b}); len(groups) != 0 {
		t.Errorf("empty trees grouped as duplicates: %+v", groups)
	}
}
