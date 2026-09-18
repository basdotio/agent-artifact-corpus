// SPDX-License-Identifier: MIT

package derive

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

func canaryTransform() manifest.Transform {
	return manifest.Transform{
		ID:        "strip-goat-canary",
		Pattern:   `^[ \t]*<!--[ \t]*GOAT-CANARY-[^>]*-->[ \t]*\r?\n?`,
		Reason:    "the upstream records its own label inline",
		AppliedTo: 75,
	}
}

func TestApplyTransformsRemovesTheMarker(t *testing.T) {
	in := "# Docs Font Setup\n\nRequires sudo once.\n\n<!-- GOAT-CANARY-benign-admin-installer -->\n"
	out, counts, err := applyTransforms([]byte(in), []manifest.Transform{canaryTransform()})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(out), "GOAT-CANARY") {
		t.Errorf("marker survived: %q", out)
	}
	if counts["strip-goat-canary"] != 1 {
		t.Errorf("count = %d, want 1", counts["strip-goat-canary"])
	}
	// Everything else must be byte-identical. A transform that also reflows the file would
	// make "vendored unchanged apart from the marker" false in a way nobody could audit.
	if !strings.HasPrefix(string(out), "# Docs Font Setup\n\nRequires sudo once.\n") {
		t.Errorf("the transform altered content it was not supposed to touch: %q", out)
	}
}

func TestApplyTransformsLeavesCleanContentByteIdentical(t *testing.T) {
	in := "# Ordinary skill\n\nNothing to strip here.\n"
	out, counts, err := applyTransforms([]byte(in), []manifest.Transform{canaryTransform()})
	if err != nil {
		t.Fatal(err)
	}
	if string(out) != in {
		t.Errorf("clean content changed:\n got %q\nwant %q", out, in)
	}
	if counts["strip-goat-canary"] != 0 {
		t.Errorf("count = %d on clean content, want 0", counts["strip-goat-canary"])
	}
}

// A marker inside a code fence is still a marker: skillsgoat puts one at the end of every
// file and the scan that found them does not care about markdown structure.
func TestApplyTransformsCountsEveryOccurrence(t *testing.T) {
	in := "<!-- GOAT-CANARY-200-a -->\ntext\n<!-- GOAT-CANARY-200-b -->\n"
	out, counts, err := applyTransforms([]byte(in), []manifest.Transform{canaryTransform()})
	if err != nil {
		t.Fatal(err)
	}
	if counts["strip-goat-canary"] != 2 {
		t.Errorf("count = %d, want 2", counts["strip-goat-canary"])
	}
	if string(out) != "text\n" {
		t.Errorf("got %q, want %q", out, "text\n")
	}
}

// Binary content is left alone. Applying a line-oriented regex to a PNG would corrupt it
// silently, and the corpus ships binary containers on purpose.
func TestApplyTransformsSkipsBinary(t *testing.T) {
	in := []byte{0x89, 'P', 'N', 'G', 0x00, 0x1a, 0x0a, 0x00, 0xff}
	out, counts, err := applyTransforms(in, []manifest.Transform{canaryTransform()})
	if err != nil {
		t.Fatal(err)
	}
	if string(out) != string(in) {
		t.Error("binary content was rewritten")
	}
	if counts["strip-goat-canary"] != 0 {
		t.Error("a binary file was counted as transformed")
	}
}

func TestApplyTransformsRejectsBadPattern(t *testing.T) {
	bad := manifest.Transform{ID: "x", Pattern: "([unclosed", Reason: "r", AppliedTo: 1}
	if _, _, err := applyTransforms([]byte("x"), []manifest.Transform{bad}); err == nil {
		t.Fatal("an uncompilable pattern was accepted — it would silently transform nothing")
	}
}

// The declared count and the real count must agree. This is the check that keeps the
// manifest's story about the vendored bytes true: an upstream that adds five samples, or a
// pattern that stops matching, both show up here instead of silently changing what ships.
func TestTransformCountMismatchIsReported(t *testing.T) {
	ts := []manifest.Transform{canaryTransform()} // declares 75
	errs := checkTransformCounts("skillsgoat", ts, map[string]int{"strip-goat-canary": 74})
	if len(errs) == 0 {
		t.Fatal("74 actual against 75 declared validated")
	}
	if !strings.Contains(errs[0].Error(), "74") || !strings.Contains(errs[0].Error(), "75") {
		t.Errorf("error %q does not give both numbers", errs[0])
	}
	if errs := checkTransformCounts("skillsgoat", ts, map[string]int{"strip-goat-canary": 75}); len(errs) != 0 {
		t.Errorf("matching counts produced %v", errs)
	}
}

// A transform that matched nothing at all is worse than a miscount: it means the corpus is
// carrying a declaration of a change that is not happening.
func TestTransformThatMatchesNothingIsReported(t *testing.T) {
	ts := []manifest.Transform{canaryTransform()}
	errs := checkTransformCounts("skillsgoat", ts, map[string]int{})
	if len(errs) == 0 {
		t.Fatal("a transform that never fired validated")
	}
}

func TestValidateTransformRequiresReason(t *testing.T) {
	ts := []manifest.Transform{{ID: "x", Pattern: "a", AppliedTo: 1}}
	errs := ValidateTransforms(ts)
	if len(errs) == 0 {
		t.Fatal("a transform with no reason validated — modifying an upstream's bytes " +
			"without a recorded reason is the thing this field exists to prevent")
	}
}

func TestValidateTransformRequiresCompilablePatternAndID(t *testing.T) {
	cases := map[string][]manifest.Transform{
		"no id":      {{Pattern: "a", Reason: "r", AppliedTo: 1}},
		"no pattern": {{ID: "x", Reason: "r", AppliedTo: 1}},
		"bad regex":  {{ID: "x", Pattern: "([", Reason: "r", AppliedTo: 1}},
		"zero count": {{ID: "x", Pattern: "a", Reason: "r", AppliedTo: 0}},
	}
	for name, ts := range cases {
		t.Run(name, func(t *testing.T) {
			if errs := ValidateTransforms(ts); len(errs) == 0 {
				t.Fatalf("%s validated", name)
			}
		})
	}
}
