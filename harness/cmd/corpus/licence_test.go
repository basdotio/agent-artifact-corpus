// SPDX-License-Identifier: MIT
package main

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// A deferral folds licence failures into one line for the entries that recorded one, and only
// those. The two properties worth pinning: a non-deferred entry's failures survive untouched,
// and a deferred entry's OTHER failures (anything that is not the permissive-set check) survive
// too — a deferral is about one obligation, not a blanket exemption.
func TestDeferLicenceFailuresIsNarrow(t *testing.T) {
	labels := []*label.Label{
		{Rel: "corpus/benign/skills/md-a.yaml", Origin: label.Origin{DerivedFrom: &label.DerivedFrom{Entry: "skillmd-138k"}}},
		{Rel: "corpus/benign/skills/sk-b.yaml", Origin: label.Origin{DerivedFrom: &label.DerivedFrom{Entry: "skillet-wild"}}},
		{Rel: "corpus/benign/skills/gh-c.yaml", Origin: label.Origin{Type: "harvested"}},
	}
	entries := []manifest.Entry{
		{ID: "skillmd-138k", LicenseReview: "deferred", LicenseReviewNote: "owner's call, 2026-10-28"},
		{ID: "skillet-wild"}, // not deferred
	}
	problems := []string{
		`corpus/benign/skills/md-a.yaml: origin.license "NONE" may not be vendored into layer 1 — reference it from manifest/ instead (docs/licensing.md)`,
		`corpus/benign/skills/md-a.yaml: origin.added is empty`,
		`corpus/benign/skills/sk-b.yaml: origin.license "GPL-3.0" may not be vendored into layer 1 — reference it from manifest/ instead (docs/licensing.md)`,
		`corpus/benign/skills/gh-c.yaml: origin.license "NONE" may not be vendored into layer 1 — reference it from manifest/ instead (docs/licensing.md)`,
	}
	got := deferLicenceFailures(problems, labels, entries)
	if len(got) != 3 {
		t.Fatalf("kept %d problem(s), want 3: %v", len(got), got)
	}
	for _, p := range got {
		if strings.HasPrefix(p, "corpus/benign/skills/md-a.yaml: origin.license") {
			t.Errorf("the deferred entry's licence failure was kept: %s", p)
		}
	}
	if !strings.Contains(strings.Join(got, "\n"), "md-a.yaml: origin.added is empty") {
		t.Errorf("a deferral removed a failure that is not about licence")
	}
}

func TestDeferLicenceFailuresWithNoDeferralIsIdentity(t *testing.T) {
	problems := []string{"x: origin.license \"NONE\" may not be vendored into layer 1"}
	got := deferLicenceFailures(problems, nil, []manifest.Entry{{ID: "a"}})
	if len(got) != 1 {
		t.Fatalf("got %v, want the input unchanged", got)
	}
}
