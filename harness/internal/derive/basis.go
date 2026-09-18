// SPDX-License-Identifier: MIT

package derive

import (
	"fmt"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// basisBlock renders a derived label's `basis:` block from the rules that produced it.
//
// It is generated rather than hand-written for the same reason the coordinates are: the
// manifest already knows how each axis was established, and transcribing that by hand into
// 3,402 labels would go wrong in exactly the way this field exists to expose.
//
// What it will NOT do is upgrade a claim. Where the rules do not support a basis, no basis is
// written and the axis is reported as unscoreable — which is true — rather than given a value
// that reads better than the evidence behind it.
func basisBlock(e manifest.Entry, c Coord) string {
	d := e.Derive
	if d == nil {
		return ""
	}

	classBasis, classField, classValue := fromSpec(d.ClassFrom, c.Class)
	if classBasis == "" {
		// class_from is neither `constant:` nor `field:`. Guessing would stamp a fabricated
		// provenance onto every sample of the entry.
		return ""
	}

	var lines []string
	add := func(f string, a ...any) { lines = append(lines, fmt.Sprintf("  "+f, a...)) }

	add("class: %s", classBasis)

	// Companion fields are emitted once and shared across the axes that need them, because a
	// basis is claimed per axis while the evidence for it is about the entry. Where two axes
	// rest on the same kind of thing — cisco's class and severity are both constants — one
	// assumption sentence covers both and says so.
	var assumption, sourceField, sourceValue string
	if classBasis == "assumed" {
		assumption = fmt.Sprintf(
			"every sample collected from %s is treated as %s; nothing about this particular "+
				"sample was examined", e.ID, c.Class)
	}
	if classBasis == "upstream" {
		sourceField, sourceValue = classField, classValue
	}

	sevBasis, sevField, sevValue := "", "", ""
	if c.Severity != "" {
		sevBasis, sevField, sevValue = fromSpec(d.SeverityFrom, c.Severity)
	}

	dimBasis := dimensionBasis(d, c)

	// Assemble the companion fields the chosen bases require.
	if sevBasis == "assumed" && assumption == "" {
		assumption = fmt.Sprintf("severity for every sample from %s is the constant %q; "+
			"it carries no information about this sample", e.ID, c.Severity)
	} else if sevBasis == "assumed" {
		assumption += fmt.Sprintf(". Severity is likewise the constant %q for the whole batch",
			c.Severity)
	}
	if sevBasis == "upstream" && sourceField == "" {
		sourceField, sourceValue = sevField, sevValue
	}

	if assumption != "" {
		add("assumption: %q", assumption)
	}
	if sourceField != "" {
		add("source_field: %s", sourceField)
		add("source_value: %s", sourceValue)
	}
	if dimBasis != "" {
		add("dimension: %s", dimBasis)
		add("rule: category_axis_map")
	}
	if sevBasis != "" {
		add("severity: %s", sevBasis)
	}

	return "basis:\n" + strings.Join(lines, "\n") + "\n"
}

// fromSpec reads a `constant:x` / `field:y` spec and returns the basis it implies.
//
// The mapping is the whole argument of taxonomy/basis.yaml in two lines: a constant is a
// statement about the batch (`assumed`), and reading the upstream's own field is adopting
// their claim unchanged (`upstream`).
func fromSpec(spec, value string) (basis, field, val string) {
	switch {
	case strings.HasPrefix(spec, "constant:"):
		return "assumed", "", ""
	case strings.HasPrefix(spec, "field:"):
		return "upstream", strings.TrimPrefix(spec, "field:"), value
	default:
		return "", "", ""
	}
}

// dimensionBasis decides what, if anything, may be claimed for the attribution axis.
//
// A hand-read dimension gets NOTHING, and that is the deliberate part. Those judgements are
// real — a person opened the sample — but their evidence lives in a YAML comment beside the
// override, which no machine can check and VerifyEvidence would find nothing to confirm.
// `read` is the only basis allowed to score attribution, so claiming it here would hand the
// axis's strongest guarantee to the one case that cannot honour it.
//
// Leaving it empty makes the axis unscoreable for those samples. That is the accurate state
// of affairs, and it is recoverable: moving each comment into an `evidence` block promotes
// the sample to `read` with a quote that validate can locate.
func dimensionBasis(d *manifest.Derive, c Coord) string {
	if len(c.Dimensions) == 0 || c.HandReadDimension {
		return ""
	}
	if len(d.CategoryAxisMap) == 0 {
		return ""
	}
	return "derived"
}
