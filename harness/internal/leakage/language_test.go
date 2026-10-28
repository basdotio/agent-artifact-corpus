// SPDX-License-Identifier: MIT

package leakage

import (
	"fmt"
	"testing"
)

// surfaceSamples builds n samples of one class on the given surfaces, the first `with` of
// which carry a file with extension ext. The rest carry only SKILL.md.
func surfaceSamples(prefix, class string, surfaces []string, n, with int, ext string) []Sample {
	var out []Sample
	for i := range n {
		files := []string{"SKILL.md"}
		if i < with {
			files = append(files, "scripts/run"+ext)
		}
		out = append(out, Sample{ID: fmt.Sprintf("%s-%d", prefix, i), Class: class,
			Group: prefix, Surfaces: surfaces, Files: files})
	}
	return out
}

func rowFor(rows []LanguageRow, surface, family string) (LanguageRow, bool) {
	for _, r := range rows {
		if r.Surface == surface && r.Family == family {
			return r, true
		}
	}
	return LanguageRow{}, false
}

// The skew this exists for: on the skills surface the malicious half carries Python several
// times as often as the benign half, so a scanner that reads only Python sees a different
// corpus on each side — and no purity-based check can see it, because `.py` is far from 95%
// pure in either direction.
func TestLanguageSkewReportsAOneSidedLanguage(t *testing.T) {
	t.Parallel()
	ss := append(surfaceSamples("mal", "malicious", []string{"skills"}, 20, 10, ".py"),
		surfaceSamples("ben", "benign", []string{"skills"}, 40, 2, ".py")...)
	r, ok := rowFor(LanguageSkew(ss), "skills", "python")
	if !ok {
		t.Fatalf("50%% of malicious against 5%% of benign must be reported")
	}
	if r.Malicious != 20 || r.MaliciousWith != 10 || r.Benign != 40 || r.BenignWith != 2 {
		t.Fatalf("counts wrong: %+v", r)
	}
	if r.Toward() != "malicious" || r.Ratio() < 9.9 || r.Ratio() > 10.1 {
		t.Fatalf("want 10x toward malicious, got %.2fx toward %s", r.Ratio(), r.Toward())
	}
	if r.BlindSpot() {
		t.Fatalf("both sides carry Python, so it is skew, not a blind spot")
	}
}

// Five malicious samples cannot say anything about a class-wide share; the row would be noise
// that teaches people to skip this section.
func TestLanguageSkewNeedsSupport(t *testing.T) {
	t.Parallel()
	ss := append(surfaceSamples("mal", "malicious", []string{"hooks"}, 5, 5, ".py"),
		surfaceSamples("ben", "benign", []string{"hooks"}, 200, 0, ".py")...)
	if rows := LanguageSkew(ss); len(rows) != 0 {
		t.Fatalf("a surface with fewer than %d samples in a class is not reportable: %+v", MinSupport, rows)
	}
}

// The regression this guards: the mcp surface once had no malicious TypeScript while a fifth
// of its benign servers were TypeScript, so a scanner blind to TypeScript lost nothing on the
// malicious side. That state must fail the build, not scroll past.
func TestLanguageBlindSpot(t *testing.T) {
	t.Parallel()
	ss := append(surfaceSamples("mal", "malicious", []string{"mcp"}, 20, 0, ".ts"),
		surfaceSamples("ben", "benign", []string{"mcp"}, 40, 10, ".ts")...)
	r, ok := rowFor(LanguageSkew(ss), "mcp", "js/ts")
	if !ok || !r.BlindSpot() {
		t.Fatalf("0%% of malicious against 25%% of benign is a blind spot, got %+v (reported=%v)", r, ok)
	}
	if r.Toward() != "benign" {
		t.Fatalf("the language sits on the benign side, got %s", r.Toward())
	}
}

// A language one class never carries but that is rare on the other side too is worth
// printing and not worth failing over: shell scripts in 4% of benign MCP servers do not make
// a scanner that skips .sh blind to the surface.
func TestNeverOnOneSideBelowTheShareIsReportedNotBlind(t *testing.T) {
	t.Parallel()
	ss := append(surfaceSamples("mal", "malicious", []string{"mcp"}, 30, 0, ".sh"),
		surfaceSamples("ben", "benign", []string{"mcp"}, 100, 9, ".sh")...)
	r, ok := rowFor(LanguageSkew(ss), "mcp", "shell")
	if !ok {
		t.Fatalf("a language absent from one class must still be reported")
	}
	if r.BlindSpot() {
		t.Fatalf("9%% is under the blind-spot share, so this is a warning, not a failure")
	}
}

// Hard negatives are scored on the precision side, so for a scanner's view of the surface
// they belong with the benign samples, not in a third column.
func TestLanguageSkewCountsHardNegativesAsBenignSide(t *testing.T) {
	t.Parallel()
	ss := surfaceSamples("mal", "malicious", []string{"skills"}, 20, 10, ".py")
	ss = append(ss, surfaceSamples("ben", "benign", []string{"skills"}, 30, 1, ".py")...)
	ss = append(ss, surfaceSamples("hn", "hard-negative", []string{"skills"}, 10, 1, ".py")...)
	r, ok := rowFor(LanguageSkew(ss), "skills", "python")
	if !ok || r.Benign != 40 || r.BenignWith != 2 {
		t.Fatalf("hard negatives must count on the benign side: %+v", r)
	}
}

// An artifact on two load paths is read by a scanner pointed at either, so it counts under
// both — the same convention `make stats` uses for its surface table.
func TestLanguageSkewCountsEverySurfaceOfASample(t *testing.T) {
	t.Parallel()
	ss := append(surfaceSamples("mal", "malicious", []string{"skills", "mcp"}, 20, 10, ".py"),
		surfaceSamples("ben", "benign", []string{"skills", "mcp"}, 40, 2, ".py")...)
	rows := LanguageSkew(ss)
	for _, s := range []string{"skills", "mcp"} {
		if _, ok := rowFor(rows, s, "python"); !ok {
			t.Fatalf("sample on two surfaces must be counted under %s: %+v", s, rows)
		}
	}
}

// File systems and upstreams disagree about case; `.TS` is TypeScript.
func TestLanguageSkewExtensionIsCaseInsensitive(t *testing.T) {
	t.Parallel()
	ss := append(surfaceSamples("mal", "malicious", []string{"mcp"}, 20, 0, ".ts"),
		surfaceSamples("ben", "benign", []string{"mcp"}, 40, 10, ".TS")...)
	if _, ok := rowFor(LanguageSkew(ss), "mcp", "js/ts"); !ok {
		t.Fatalf(".TS must count as js/ts")
	}
}

// Equal shares on both sides are the state this check wants; it must say nothing about them.
func TestLanguageSkewIsQuietWhenBalanced(t *testing.T) {
	t.Parallel()
	ss := append(surfaceSamples("mal", "malicious", []string{"mcp"}, 40, 20, ".py"),
		surfaceSamples("ben", "benign", []string{"mcp"}, 80, 40, ".py")...)
	if rows := LanguageSkew(ss); len(rows) != 0 {
		t.Fatalf("50%% against 50%% is balanced, nothing to report: %+v", rows)
	}
}

// Rows come out in a stable order, surface then family, so validate output diffs cleanly.
func TestLanguageSkewOrderIsStable(t *testing.T) {
	t.Parallel()
	var ss []Sample
	for _, surf := range []string{"skills", "mcp"} {
		ss = append(ss, surfaceSamples(surf+"m", "malicious", []string{surf}, 20, 10, ".py")...)
		ss = append(ss, surfaceSamples(surf+"b", "benign", []string{surf}, 40, 2, ".py")...)
	}
	rows := LanguageSkew(ss)
	if len(rows) != 2 || rows[0].Surface != "mcp" || rows[1].Surface != "skills" {
		t.Fatalf("want mcp before skills, got %+v", rows)
	}
}

// An empty side has no share; it must read as 0, not divide by zero.
func TestShareOfNothingIsZero(t *testing.T) {
	t.Parallel()
	if got := (LanguageRow{}).MaliciousShare(); got != 0 {
		t.Fatalf("want 0, got %v", got)
	}
}
