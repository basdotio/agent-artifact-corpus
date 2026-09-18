// SPDX-License-Identifier: MIT

package derive

import (
	"fmt"
	"regexp"
	"unicode/utf8"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// applyTransforms rewrites one file's bytes under an entry's declared transforms and reports
// how many times each one fired.
//
// It is deliberately dumb: a regexp replacement with the empty string, nothing reflowed,
// nothing reformatted. "Vendored unchanged apart from the declared marker" has to be a claim
// a reader can verify by running the same pattern over the upstream, and any cleverness here
// — normalising whitespace, collapsing the blank line left behind — would make the vendored
// bytes something nobody could reproduce from the declaration alone.
func applyTransforms(content []byte, ts []manifest.Transform) ([]byte, map[string]int, error) {
	counts := map[string]int{}
	if len(ts) == 0 {
		return content, counts, nil
	}
	// Binary is left alone. A line-oriented pattern run over a PNG would corrupt it without
	// any error, and this corpus ships binary containers as attacks on purpose.
	if !utf8.Valid(content) {
		return content, counts, nil
	}

	out := content
	for _, t := range ts {
		re, err := regexp.Compile("(?m)" + t.Pattern)
		if err != nil {
			return nil, nil, fmt.Errorf("transform %q: pattern does not compile: %w", t.ID, err)
		}
		n := len(re.FindAll(out, -1))
		if n == 0 {
			continue
		}
		counts[t.ID] += n
		out = re.ReplaceAll(out, nil)
	}
	return out, counts, nil
}

// ValidateTransforms checks the declarations themselves.
func ValidateTransforms(ts []manifest.Transform) []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	seen := map[string]bool{}
	for _, t := range ts {
		switch {
		case t.ID == "":
			bad("a transform has no id")
		case seen[t.ID]:
			bad("transform %q is declared twice", t.ID)
		}
		seen[t.ID] = true

		if t.Pattern == "" {
			bad("transform %q has no pattern", t.ID)
		} else if _, err := regexp.Compile("(?m)" + t.Pattern); err != nil {
			bad("transform %q: pattern does not compile: %v", t.ID, err)
		}
		if t.Reason == "" {
			bad("transform %q has no reason — changing an upstream's bytes without a recorded "+
				"reason is indistinguishable from tampering, whatever the motive", t.ID)
		}
		if t.AppliedTo <= 0 {
			bad("transform %q declares applied_to %d — a transform expected to fire zero "+
				"times should be deleted, not declared", t.ID, t.AppliedTo)
		}
	}
	return errs
}

// checkTransformCounts compares what was declared against what actually happened.
//
// Both directions are errors and for different reasons. Fewer than declared means the
// upstream changed under us, or the pattern stopped matching, and the corpus is now shipping
// bytes the manifest does not describe. More than declared means the transform is reaching
// further than it was reviewed to reach — which, for a rule that deletes content from
// somebody else's artifact, is the one that should worry a reader most.
func checkTransformCounts(entryID string, ts []manifest.Transform, actual map[string]int) []error {
	var errs []error
	for _, t := range ts {
		got := actual[t.ID]
		if got == t.AppliedTo {
			continue
		}
		if got == 0 {
			errs = append(errs, fmt.Errorf(
				"%s: transform %q declares applied_to %d and matched nothing. The corpus is "+
					"carrying a declaration of a change that is not happening — either the "+
					"upstream no longer contains what the pattern targets, or the pattern is "+
					"wrong", entryID, t.ID, t.AppliedTo))
			continue
		}
		errs = append(errs, fmt.Errorf(
			"%s: transform %q declares applied_to %d but fired %d time(s). The vendored bytes "+
				"and the manifest's account of them have diverged; fix whichever is wrong, and "+
				"do not simply update the number without reading why it moved",
			entryID, t.ID, t.AppliedTo, got))
	}
	for id, n := range actual {
		declared := false
		for _, t := range ts {
			if t.ID == id {
				declared = true
				break
			}
		}
		if !declared {
			errs = append(errs, fmt.Errorf(
				"%s: transform %q fired %d time(s) but is not declared", entryID, id, n))
		}
	}
	return errs
}
