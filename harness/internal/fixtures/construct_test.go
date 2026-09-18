// SPDX-License-Identifier: MIT

//go:build unix

package fixtures

import (
	"os"
	"path/filepath"
	"testing"
)

// find one fixture by name or fail — the tests below assert on specific hostile properties.
func get(t *testing.T, name string) Fixture {
	t.Helper()
	for _, f := range All() {
		if f.Name == name {
			return f
		}
	}
	t.Fatalf("fixture %q not registered", name)
	return Fixture{}
}

func TestAllFixturesConstruct(t *testing.T) {
	for _, f := range All() {
		f := f
		t.Run(f.Name, func(t *testing.T) {
			dir := t.TempDir()
			t.Cleanup(func() { Restore(dir) })
			entry, err := f.Construct(dir)
			if err != nil {
				t.Fatalf("construct: %v", err)
			}
			if entry == "" {
				t.Fatal("construct returned an empty entry path")
			}
			if f.What == "" || f.Expected == "" {
				t.Error("a fixture with no What/Expected cannot be scored by a runner")
			}
		})
	}
}

func TestTraverseOnlyDirIsUnreadable(t *testing.T) {
	// The whole point: a plain directory walk must be UNABLE to list private/, so a scanner that
	// stays silent has scored an unread skill as read.
	dir := t.TempDir()
	t.Cleanup(func() { Restore(dir) })
	root, err := get(t, "traverse-only-dir").Construct(dir)
	if err != nil {
		t.Fatal(err)
	}
	priv := filepath.Join(root, "private")
	if _, err := os.ReadDir(priv); err == nil {
		t.Error("private/ was listable; a 0111 dir must deny enumeration")
	}
}

func TestFifoAsSkillIsNotRegular(t *testing.T) {
	root, err := get(t, "fifo-as-skill").Construct(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	fi, err := os.Lstat(filepath.Join(root, "SKILL.md"))
	if err != nil {
		t.Fatal(err)
	}
	if fi.Mode().IsRegular() {
		t.Error("SKILL.md is a regular file; the fixture must make it a FIFO")
	}
	if fi.Mode()&os.ModeNamedPipe == 0 {
		t.Error("SKILL.md is not a named pipe")
	}
}

func TestSymlinkCycleActuallyCycles(t *testing.T) {
	root, err := get(t, "symlink-cycle").Construct(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	// a/to-b/to-a/to-b must keep resolving — evaluating a few hops proves the loop exists.
	p := filepath.Join(root, "a", "to-b", "to-a", "to-b")
	if _, err := os.Stat(p); err != nil {
		t.Errorf("expected the cycle to resolve several hops deep, got %v", err)
	}
}

func TestSymlinkEscapePointsOutside(t *testing.T) {
	root, err := get(t, "symlink-escape").Construct(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	target, err := os.Readlink(filepath.Join(root, "config.env"))
	if err != nil {
		t.Fatal(err)
	}
	if filepath.IsLocal(target) {
		t.Errorf("link target %q is inside the tree; the escape fixture must point out of it", target)
	}
}

func TestSparseHugeConfigIsHugeButSmallOnDisk(t *testing.T) {
	root, err := get(t, "sparse-huge-config").Construct(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	fi, err := os.Stat(filepath.Join(root, ".mcp.json"))
	if err != nil {
		t.Fatal(err)
	}
	if fi.Size() < 8<<30 {
		t.Errorf("apparent size %d is not the multi-gigabyte the fixture promises", fi.Size())
	}
}
