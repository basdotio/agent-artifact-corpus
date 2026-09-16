// SPDX-License-Identifier: MIT

package leakage

import (
	"fmt"
	"strings"
	"testing"
)

func sample(id, class, group string, files ...string) Sample {
	return Sample{ID: id, Class: class, Group: group, Files: files}
}

// A feature that gives the answer away among genuinely comparable samples is the real thing
// this gate exists to catch — malskillbench's _meta.json, present in benign samples and no
// malicious ones, separates its classes at 97% without opening a single skill.
func TestLeakWithinOnePopulation(t *testing.T) {
	t.Parallel()
	var ss []Sample
	for i := range 10 {
		ss = append(ss, sample(string(rune('a'+i)), "benign", "bench", "SKILL.md", "_meta.json"))
		ss = append(ss, sample(string(rune('A'+i)), "malicious", "bench", "SKILL.md"))
	}
	got := Check(ss)
	var found bool
	for _, f := range got {
		if f.Name == "file:_meta.json" && f.Class == "benign" && f.Group == "bench" {
			found = true
		}
	}
	if !found {
		t.Fatalf("a within-population giveaway must be reported, got %+v", got)
	}
}

// Comparing a curated fixture against a real-world repository is a category error: real repos
// ship a LICENSE.txt and purpose-built fixtures do not, so pooling them makes that file look
// like a perfect benign predictor when all it predicts is which corpus a sample came from.
func TestCrossPopulationIsNotALeak(t *testing.T) {
	t.Parallel()
	var ss []Sample
	for i := range 10 {
		// Real public skills, benign only.
		ss = append(ss, sample(string(rune('a'+i)), "benign", "wild", "SKILL.md", "LICENSE.txt"))
		// Curated attack fixtures, malicious only.
		ss = append(ss, sample(string(rune('A'+i)), "malicious", "fixtures", "SKILL.md"))
	}
	if got := Check(ss); len(got) != 0 {
		t.Fatalf("no population here holds both classes, so nothing can be given away: %+v", got)
	}
	cross := CrossPopulation(ss)
	var found bool
	for _, f := range cross {
		if f.Name == "file:LICENSE.txt" {
			found = true
		}
	}
	if !found {
		t.Fatalf("the pooled structure must still be reported, got %+v", cross)
	}
}

// A population holding one class is 100%% pure on every feature by construction, and none of
// that is evidence of anything.
func TestSingleClassPopulationYieldsNothing(t *testing.T) {
	t.Parallel()
	var ss []Sample
	for i := range 12 {
		ss = append(ss, sample(string(rune('a'+i)), "benign", "wild", "SKILL.md", "LICENSE.txt"))
	}
	if got := Check(ss); len(got) != 0 {
		t.Fatalf("expected nothing from a single-class population, got %+v", got)
	}
}

func TestSupportThreshold(t *testing.T) {
	t.Parallel()
	var ss []Sample
	// Only 3 samples carry the giveaway: below MinSupport, so it is an accident not a pattern.
	for i := range 3 {
		ss = append(ss, sample(string(rune('a'+i)), "benign", "g", "SKILL.md", "rare.txt"))
	}
	for i := range 10 {
		ss = append(ss, sample(string(rune('A'+i)), "malicious", "g", "SKILL.md"))
	}
	for _, f := range Check(ss) {
		if f.Name == "file:rare.txt" {
			t.Fatalf("a feature under MinSupport (%d) must not be reported: %+v", MinSupport, f)
		}
	}
}

// A population already more lopsided than the purity threshold cannot demonstrate leakage: a
// feature present in every sample reads as pure while telling you only the class balance.
func TestImbalancedPopulationYieldsNothing(t *testing.T) {
	t.Parallel()
	var ss []Sample
	for i := range 121 {
		ss = append(ss, sample(fmt.Sprintf("m%d", i), "malicious", "cisco", "server.py"))
	}
	for i := range 3 {
		ss = append(ss, sample(fmt.Sprintf("b%d", i), "benign", "cisco", "server.py"))
	}
	// ext:.py is in all 124 and would read as 97.6% pure malicious.
	if got := Check(ss); len(got) != 0 {
		t.Fatalf("a ubiquitous feature in a lopsided population is not evidence: %+v", got)
	}
	im := Imbalanced(ss)
	if len(im) != 1 || !strings.Contains(im[0], "cisco") {
		t.Fatalf("the population the gate cannot judge must be named, got %v", im)
	}
}

// The case the gate exists for still fires: balanced classes, one file present in only one.
func TestBalancedPopulationStillLeaks(t *testing.T) {
	t.Parallel()
	var ss []Sample
	for i := range 10 {
		ss = append(ss, sample(fmt.Sprintf("b%d", i), "benign", "bench", "SKILL.md", "_meta.json"))
		ss = append(ss, sample(fmt.Sprintf("m%d", i), "malicious", "bench", "SKILL.md"))
	}
	var found bool
	for _, f := range Check(ss) {
		if f.Name == "file:_meta.json" {
			found = true
		}
	}
	if !found {
		t.Fatal("a real giveaway in a balanced population must still be reported")
	}
}
