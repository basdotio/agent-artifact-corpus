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
}

// Check returns the features that predict a class too well. A non-empty result fails the
// build.
func Check(samples []Sample) []Feature {
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

	var out []Feature
	for f, total := range support {
		if total < MinSupport {
			continue
		}
		for class, n := range byClass[f] {
			if float64(n)/float64(total) > MaxPurity {
				out = append(out, Feature{Name: f, Class: class, With: n, Total: total})
			}
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
