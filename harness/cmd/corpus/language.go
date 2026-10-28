// SPDX-License-Identifier: MIT

package main

import (
	"fmt"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/leakage"
)

// reportLanguageSkew prints the surface x language cells where one class carries a language
// far more often than the other, and returns a problem for each blind spot.
//
// Printed rather than silenced, like the cross-population structure, because it is a property
// of how the two halves were collected rather than a defect in any sample. A blind spot is
// different: one class never carries a language the other carries often, which is the state
// the mcp surface was in before it had malicious TypeScript, and the build fails on it so the
// state cannot come back unnoticed.
func reportLanguageSkew(rows []leakage.LanguageRow) []string {
	if len(rows) == 0 {
		fmt.Printf("\nlanguage skew — none: on every surface with %d+ samples per class, each language "+
			"family is carried at a share within %.0fx between the classes\n", leakage.MinSupport, leakage.SkewRatio)
		return nil
	}
	fmt.Printf("\nlanguage skew — %d cell(s) where one class carries a language far more often. A scanner\n"+
		"that cannot parse it sees a different corpus on each side, and its figures there say so:\n", len(rows))
	var problems []string
	for _, r := range rows {
		fmt.Printf("  %-12s %-11s malicious %4d/%-4d (%5.1f%%)  benign %4d/%-5d (%5.1f%%)  %s\n",
			r.Surface, r.Family, r.MaliciousWith, r.Malicious, r.MaliciousShare()*100,
			r.BenignWith, r.Benign, r.BenignShare()*100, skewNote(r))
		if r.BlindSpot() {
			problems = append(problems, blindSpotProblem(r))
		}
	}
	return problems
}

func skewNote(r leakage.LanguageRow) string {
	switch {
	case r.MaliciousShare() == 0:
		return "absent from malicious" + blindTag(r)
	case r.BenignShare() == 0:
		return "absent from benign" + blindTag(r)
	default:
		return fmt.Sprintf("%.1fx %s", r.Ratio(), r.Toward())
	}
}

func blindTag(r leakage.LanguageRow) string {
	if r.BlindSpot() {
		return " — BLIND SPOT"
	}
	return ""
}

func blindSpotProblem(r leakage.LanguageRow) string {
	has, hasN, hasOf, lacks, lacksOf := "benign", r.BenignWith, r.Benign, "malicious", r.Malicious
	if r.Toward() == "malicious" {
		has, hasN, hasOf, lacks, lacksOf = "malicious", r.MaliciousWith, r.Malicious, "benign", r.Benign
	}
	return fmt.Sprintf("language blind spot on %s: %s appears in %d of %d %s samples (%.0f%%) and in "+
		"none of the %d %s ones — a scanner that cannot parse %s loses nothing on the %s side, so its "+
		"figures on this surface would describe the language mix rather than its rules",
		r.Surface, r.Family, hasN, hasOf, has, float64(hasN)/float64(hasOf)*100,
		lacksOf, lacks, r.Family, lacks)
}
