// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// An auditor spot-checking this corpus's pins ran, for each cached upstream:
//
//	git -C cache/<id> rev-parse HEAD
//
// and got a plausible commit sha back for every one of them. Two of those caches are not git
// checkouts at all — they are HuggingFace parquet drops — and for those, git walked UP out of
// the cache directory and answered with THIS repository's own HEAD. The check did not fail.
// It returned a real sha, of the wrong repository, silently.
//
// That is the shape of defect this repository keeps finding in its own instrumentation: not a
// check that breaks, a check that answers confidently about something it never looked at. So
// the pin check lives here, states which entries it could verify, and names the ones it could
// not rather than letting a shell one-liner appear to have done it.

// PinStatus is one entry's pin, as far as the local cache can attest to it.
type PinStatus struct {
	ID       string
	Declared string
	Actual   string
	State    string // "verified", "drifted", "not-a-checkout", "not-fetched", "no-pin"
}

// CheckPins reports the state of every manifest entry that has something in cache/.
func CheckPins(repoRoot string, entries []manifest.Entry) []PinStatus {
	var out []PinStatus
	for _, e := range entries {
		dir := filepath.Join(repoRoot, "cache", e.ID)
		if _, err := os.Stat(dir); err != nil {
			continue // not fetched; nothing local to attest to, and that is not a defect
		}
		st := PinStatus{ID: e.ID, Declared: e.Commit}
		switch {
		case e.Commit == "":
			st.State = "no-pin"
		case !isGitCheckout(dir):
			// The decisive test. Without it, `git -C` finds an ancestor repository and answers
			// for that one instead — which is how a data drop passed as a verified pin.
			st.State = "not-a-checkout"
		default:
			head, err := headOf(dir)
			if err != nil {
				st.State = "not-a-checkout"
			} else {
				st.Actual = head
				if strings.HasPrefix(head, e.Commit) || strings.HasPrefix(e.Commit, head) {
					st.State = "verified"
				} else {
					st.State = "drifted"
				}
			}
		}
		out = append(out, st)
	}
	return out
}

// isGitCheckout reports whether dir is itself a repository, rather than merely sitting inside
// one. `.git` is a directory in a normal clone and a file in a worktree; both count.
func isGitCheckout(dir string) bool {
	_, err := os.Stat(filepath.Join(dir, ".git"))
	return err == nil
}

func headOf(dir string) (string, error) {
	out, err := exec.Command("git", "-C", dir, "rev-parse", "HEAD").Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

// reportPins prints the verification, and returns the drifted ones as problems.
//
// A drifted checkout is an error because every figure already published against that entry was
// measured on different bytes. A cache that is not a git checkout is NOT an error — several
// upstreams ship a parquet file and there is nothing to rev-parse — but it must be named, or
// "no pin problems" reads as "all pins verified".
func reportPins(statuses []PinStatus) []string {
	if len(statuses) == 0 {
		return nil
	}
	verified, unverifiable := 0, []string{}
	var problems []string
	for _, s := range statuses {
		switch s.State {
		case "verified":
			verified++
		case "drifted":
			problems = append(problems, fmt.Sprintf(
				"%s: the cached checkout is at %s but the manifest pins %s. Every number "+
					"published against this entry was measured on different bytes",
				s.ID, short12(s.Actual), short12(s.Declared)))
		case "not-a-checkout":
			unverifiable = append(unverifiable, s.ID+" (not a git checkout — a data drop; "+
				"`git -C` here answers for an ancestor repository, so a shell spot-check LOOKS "+
				"like it verified and did not)")
		case "not-fetched":
			unverifiable = append(unverifiable, s.ID+" (not fetched)")
		case "no-pin":
			unverifiable = append(unverifiable, s.ID+" (entry declares no commit)")
		}
	}
	fmt.Printf("pins        %d of %d cached entr(ies) verified against the manifest\n",
		verified, len(statuses))
	for _, u := range unverifiable {
		fmt.Printf("  unverifiable  %s\n", u)
	}
	return problems
}

func short12(s string) string {
	if len(s) > 12 {
		return s[:12]
	}
	return s
}
