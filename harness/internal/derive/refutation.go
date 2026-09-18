// SPDX-License-Identifier: MIT

package derive

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/refute"
)

// RefutationBlock records what was searched for in a benign sample, and what matched.
//
// A benign sample cannot be proven harmless — that is a universal negative — so the honest
// alternative is to state what WAS looked for. Without this, `class: benign` means "collected
// from a batch we treat as benign and nobody opened it", and there is nothing in the label to
// say otherwise. With it, the label carries the ruleset version, the patterns that fired, and
// the volume read, so "searched and found nothing" stops looking like "never searched".
//
// It is the corpus's third red line applied to the corpus itself: "no scanner complained" is
// not evidence of benignity, and neither is our own silence.
//
// The byte count is not decoration. An empty tree and a clean tree both produce `matched: []`,
// and the only thing separating them is how much was read.
func RefutationBlock(treeDir string, version int) string {
	var matched []string
	var scanned int64

	if refute.NoJudgeableContent(treeDir) {
		matched = append(matched, "no-judgeable-content")
	}
	seen := map[string]bool{}
	_ = filepath.WalkDir(treeDir, func(p string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil //nolint:nilerr // an unreadable entry contributes nothing, and the
			// byte count below is what makes that visible rather than silent
		}
		b, rerr := readSampleBytes(p)
		if rerr != nil {
			return nil
		}
		scanned += int64(len(b))
		body := string(b)
		if len(refute.LiveCredentials(body)) > 0 && !seen["live-credential"] {
			seen["live-credential"] = true
			matched = append(matched, "live-credential")
		}
		if len(refute.HiddenCodepoints(body)) > 0 && !seen["hidden-codepoint"] {
			seen["hidden-codepoint"] = true
			matched = append(matched, "hidden-codepoint")
		}
		return nil
	})

	var b strings.Builder
	fmt.Fprintf(&b, "refutation_search:\n")
	fmt.Fprintf(&b, "  ruleset_version: %d\n", version)
	if len(matched) == 0 {
		fmt.Fprintf(&b, "  matched: []\n")
	} else {
		fmt.Fprintf(&b, "  matched: [%s]\n", strings.Join(matched, ", "))
	}
	fmt.Fprintf(&b, "  scanned_bytes: %d\n", scanned)
	return b.String()
}

// readSampleBytes returns a symlink's TARGET PATH rather than following it, for the same
// reason the scan in cmd/corpus does: a dangling link escaping its directory is the payload,
// and resolving it would read somebody else's file while the payload went unexamined.
func readSampleBytes(path string) ([]byte, error) {
	fi, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if fi.Mode()&os.ModeSymlink != 0 {
		t, err := os.Readlink(path)
		return []byte(t), err
	}
	return os.ReadFile(path)
}

// refutationRulesetVersion must track taxonomy/refutation.yaml's `version`. A rate measured
// under one version is not comparable to one measured under another, so the number is written
// into every benign label rather than assumed.
const refutationRulesetVersion = 1
