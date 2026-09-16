// SPDX-License-Identifier: MIT

// Package leakage is a mechanical release gate against corpora that can be solved without
// reading content.
//
// The idea is borrowed from skillfortify's metrics/leakage.py, and the reason to borrow it
// is that two public corpora in this field are already broken this way. MalSkillBench ships
// a _meta.json in 3,878 of 4,000 benign samples and 0 of 3,944 malicious ones, so the two
// classes separate at 97% purity without opening a single skill. skillfortifybench uses
// RFC-2606 reserved domains in malicious samples and nowhere else, so one regex scores
// perfectly and generalises to nothing.
//
// Neither corpus is obviously wrong when you read it. Both produce excellent numbers. That
// is exactly why this has to be a build gate rather than a review item: a human reading
// samples one at a time cannot see a distribution.
package leakage

import (
	"fmt"
	"path/filepath"
	"sort"
)

// Feature is a structural property of a sample that a classifier could see without reading
// content: a filename present in the tree, a file extension, the tree's depth bucket.
type Feature struct {
	Name  string
	Class string // the class it co-occurs with
	With  int    // samples in that class carrying the feature
	Total int    // samples carrying the feature, all classes
	Group string // the population it was found in; empty when pooled
}

func (f Feature) Purity() float64 {
	if f.Total == 0 {
		return 0
	}
	return float64(f.With) / float64(f.Total)
}

// Thresholds match skillfortify's: a feature needs enough support to be more than an
// accident, and enough purity to be a giveaway.
const (
	MinSupport = 8
	MaxPurity  = 0.95
)

// Sample is what the gate sees: a class and the set of file paths in the tree. Contents are
// deliberately not available here — the whole question is what is learnable without them.
type Sample struct {
	ID    string
	Class string
	Files []string

	// Group is the population a sample belongs to: the manifest entry it was derived from, or
	// "hand-pinned". The gate tests WITHIN a population, because comparing a curated attack
	// fixture against a real-world public skill is a category error — real repositories ship
	// LICENSE.txt, TypeScript sources and twenty files, and purpose-built fixtures ship three.
	// Pooling them makes `has a LICENSE.txt` look like a perfect benign predictor when all it
	// predicts is which corpus a sample came from.
	Group string
}

// Check returns the features that predict a class too well. A non-empty result fails the
// build.
// Check finds features that predict the class WITHIN one population. A feature has to give
// the answer away among samples that are genuinely comparable before it counts as leakage.
func Check(samples []Sample) []Feature {
	byGroup := map[string][]Sample{}
	for _, s := range samples {
		byGroup[s.Group] = append(byGroup[s.Group], s)
	}
	var out []Feature
	for _, g := range sortedGroups(byGroup) {
		out = append(out, checkOne(byGroup[g], g)...)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Total != out[j].Total {
			return out[i].Total > out[j].Total
		}
		return out[i].Name < out[j].Name
	})
	return out
}

// Imbalanced names the populations the gate cannot judge, because one class already exceeds
// the purity threshold on its own. A gate that silently says nothing about a population is
// indistinguishable from one that checked it and found it clean.
func Imbalanced(samples []Sample) []string {
	byGroup := map[string][]Sample{}
	for _, s := range samples {
		byGroup[s.Group] = append(byGroup[s.Group], s)
	}
	var out []string
	for _, g := range sortedGroups(byGroup) {
		ss := byGroup[g]
		classCount := map[string]int{}
		for _, s := range ss {
			classCount[s.Class]++
		}
		if len(classCount) < 2 {
			continue // single-class populations are reported elsewhere as having no comparison
		}
		for cls, n := range classCount {
			if r := float64(n) / float64(len(ss)); r > MaxPurity {
				out = append(out, fmt.Sprintf("%s (%d samples, %.0f%% %s)", g, len(ss), r*100, cls))
			}
		}
	}
	sort.Strings(out)
	return out
}

// CrossPopulation reports features that separate the classes only once populations are pooled.
// They are not corpus defects and they are not silenced either: they are the measurement of how
// differently the benign and malicious halves are built, and the reason a single rate computed
// over the whole corpus would be meaningless.
func CrossPopulation(samples []Sample) []Feature {
	pooled := checkOne(samples, "")
	within := map[string]bool{}
	for _, f := range Check(samples) {
		within[f.Name] = true
	}
	var out []Feature
	for _, f := range pooled {
		if !within[f.Name] {
			out = append(out, f)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Total != out[j].Total {
			return out[i].Total > out[j].Total
		}
		return out[i].Name < out[j].Name
	})
	return out
}

func sortedGroups(m map[string][]Sample) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func checkOne(samples []Sample, group string) []Feature {
	// _label.yaml is present in every sample by construction and carries the answer, so it
	// is excluded rather than reported — it would be the top hit forever and would train
	// people to ignore this list.
	const answerFile = "_label.yaml"

	support := map[string]int{}
	byClass := map[string]map[string]int{}
	for _, s := range samples {
		for _, f := range featuresOf(s, answerFile) {
			support[f]++
			if byClass[f] == nil {
				byClass[f] = map[string]int{}
			}
			byClass[f][s.Class]++
		}
	}

	// A population holding one class cannot give anything away: every feature in it is 100%
	// pure by construction and none of it is evidence.
	classCount := map[string]int{}
	for _, s := range samples {
		classCount[s.Class]++
	}
	if len(classCount) < 2 {
		return nil
	}

	// Nor can a population that is already more lopsided than the purity threshold. With 121
	// malicious samples against 3 benign, every feature present in all of them — `ext:.py`, say
	// — reads as 97.6% pure malicious while telling you nothing you did not already know from
	// the class balance. Purity has to beat the base rate to be evidence, and here no feature
	// can. Reporting the imbalance is the honest answer; reporting `ext:.py` as leakage would
	// teach people to ignore this list.
	for _, n := range classCount {
		if float64(n)/float64(len(samples)) > MaxPurity {
			return nil
		}
	}

	var out []Feature
	for f, total := range support {
		if total < MinSupport {
			continue
		}
		for class, n := range byClass[f] {
			if float64(n)/float64(total) > MaxPurity {
				out = append(out, Feature{Name: f, Class: class, With: n, Total: total, Group: group})
			}
		}
	}
	return out
}

func featuresOf(s Sample, skip string) []string {
	seen := map[string]bool{}
	var out []string
	add := func(f string) {
		if !seen[f] {
			seen[f] = true
			out = append(out, f)
		}
	}
	for _, p := range s.Files {
		base := filepath.Base(p)
		if base == skip {
			continue
		}
		add("file:" + base)
		if ext := filepath.Ext(base); ext != "" {
			add("ext:" + ext)
		}
	}
	add(fmt.Sprintf("filecount:%s", bucket(len(s.Files))))
	return out
}

// bucket coarsens file count so that "this class has 3 files and that one has 40" shows up
// as a giveaway, without every exact count becoming its own low-support feature.
func bucket(n int) string {
	switch {
	case n <= 1:
		return "1"
	case n <= 3:
		return "2-3"
	case n <= 8:
		return "4-8"
	case n <= 20:
		return "9-20"
	default:
		return "21+"
	}
}
