// SPDX-License-Identifier: MIT

// Package fetch materialises layer 2 into a gitignored cache.
//
// Nothing here is ever written into the repository. That is the point of the layer: the
// manifest holds a url and a commit, and a reference is not a redistribution, which is what
// lets layer 2 carry no-license and NonCommercial corpora that layer 1 may never contain.
package fetch

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/basdotio/agent-guard-corpus/harness/internal/manifest"
)

// Get clones the entry at its pinned commit into cacheDir/<id>, or reports that it is
// already there at the right commit. It never updates a checkout in place: a corpus that
// moved under an already-published number is a fact worth an error, not a silent re-pull.
func Get(e manifest.Entry, cacheDir string) (string, error) {
	dst := filepath.Join(cacheDir, e.ID)

	if head, err := headOf(dst); err == nil {
		if e.Commit != "" && !strings.HasPrefix(head, e.Commit) {
			return dst, fmt.Errorf("%s: cached checkout is at %s but the manifest pins %s — "+
				"remove %s and refetch, and check whether numbers published against it need "+
				"revisiting", e.ID, short(head), short(e.Commit), dst)
		}
		return dst, nil
	}

	if err := os.MkdirAll(cacheDir, 0o755); err != nil {
		return "", fmt.Errorf("%s: create cache dir: %w", e.ID, err)
	}
	if err := run("", "git", "clone", "--quiet", e.URL, dst); err != nil {
		return "", fmt.Errorf("%s: clone %s: %w", e.ID, e.URL, err)
	}
	if e.Commit != "" {
		if err := run(dst, "git", "checkout", "--quiet", e.Commit); err != nil {
			return "", fmt.Errorf("%s: checkout %s: %w", e.ID, short(e.Commit), err)
		}
	}
	return dst, nil
}

func headOf(dir string) (string, error) {
	if _, err := os.Stat(filepath.Join(dir, ".git")); err != nil {
		return "", err
	}
	out, err := exec.Command("git", "-C", dir, "rev-parse", "HEAD").Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

func run(dir string, name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Dir = dir
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func short(s string) string {
	if len(s) > 12 {
		return s[:12]
	}
	return s
}
