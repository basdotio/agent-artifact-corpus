// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"runtime"
	"sort"
	"strings"
	"sync"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/leakage"
)

// pairSamples is the second comparison unit the leakage gate runs over: every hard negative
// together with the malicious twin it pairs with, grouped by surface.
//
// The population grouping cannot reach these. A hard negative we write is `synthetic`, and so
// is its twin, and populationOf splits synthetic samples by class on purpose — a controlled
// family shares its payload by design, so pooling it with an unrelated sample of the other
// class manufactures a leak. That leaves the one comparison that matters for an authored
// batch unmade: a look-alike was written to resemble its twin, so the two ARE comparable, and
// whatever still separates them — the host the twin calls, the word its payload uses, how long
// each is — is what a scanner could learn instead of reading. With a few pairs the gate has no
// support and says nothing; with a batch of them it is the check that the batch was built
// without a tell.
//
// A twin pointed at by several negatives is included once. Samples outside a pair are not
// here at all: this is a view over the pairs, beside the population view, not a replacement.
func pairSamples(labels []*label.Label, samples []leakage.Sample) []leakage.Sample {
	bySample := map[string]leakage.Sample{}
	for _, s := range samples {
		bySample[s.ID] = s
	}
	surfaceOf := map[string]string{}
	for _, l := range labels {
		surfaceOf[l.ID] = l.Surface.Primary()
	}
	in := map[string]bool{}
	var out []leakage.Sample
	add := func(id, surface string) {
		s, ok := bySample[id]
		if !ok || in[id] {
			return
		}
		in[id] = true
		s.Group = "pairs:" + surface
		out = append(out, s)
	}
	for _, l := range labels {
		if l.Class != label.HardNegative || l.PairsWith == "" {
			continue
		}
		if _, ok := bySample[l.PairsWith]; !ok {
			continue // a dangling pairs_with is ValidateSet's finding, not this one's
		}
		// The pair sits on the negative's surface: that is where a scanner meets both.
		add(l.ID, surfaceOf[l.ID])
		add(l.PairsWith, surfaceOf[l.ID])
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

// reportPairs prints the pair view's reach the way the population view's is printed: how
// many samples it holds, and which surfaces have too few pairs for any feature to clear
// MinSupport — said out loud, so an unjudged view cannot read as a clean one.
func reportPairs(pairs []leakage.Sample) {
	if len(pairs) == 0 {
		fmt.Printf("  pairs          none — no hard negative pairs with a twin\n")
		return
	}
	bySurface := map[string]int{}
	for _, s := range pairs {
		bySurface[strings.TrimPrefix(s.Group, "pairs:")]++
	}
	var parts, thin []string
	for _, surf := range sortedKeys(bySurface) {
		parts = append(parts, fmt.Sprintf("%s %d", surf, bySurface[surf]))
		if bySurface[surf] < leakage.MinSupport {
			thin = append(thin, surf)
		}
	}
	fmt.Printf("  pairs          %d hard negative(s) and twin(s) compared as pairs, by surface: %s\n",
		len(pairs), strings.Join(parts, ", "))
	if len(thin) > 0 {
		fmt.Printf("                 under %d samples on %s, so no feature there can reach support\n",
			leakage.MinSupport, strings.Join(thin, ", "))
	}
}

// leakProblem words a leak for the problem list. "in" is the population view, "among" the
// pair view; the wording says which kind of feature gave the class away, because the fix
// differs — a file is renamed or stripped, a literal is varied or the sample rewritten.
func leakProblem(rel string, f leakage.Feature) string {
	how := "by a structural feature"
	switch leakage.ContentFeatureKind(f.Name) {
	case "host", "hostclass", "ip", "ipclass", "email":
		how = "by a network literal in the text"
	case "word":
		how = "by a self-describing word in the text"
	case "charset":
		how = "by the character set of the text"
	case "entrysize", "textbytes":
		how = "by the length of the text"
	}
	if strings.HasPrefix(f.Name, "absent:") {
		how = "by the absence of a feature"
	}
	return fmt.Sprintf(
		"leakage %s %s: %q appears in %d of its samples and %d of them are %s (%.0f%% pure) "+
			"— a classifier can separate the classes %s, without reading the sample the way a "+
			"scanner must", rel, f.Group, f.Name, f.Total, f.With, f.Class, f.Purity()*100, how)
}

type contentResult struct {
	features []string
	err      error
}

// contentFeaturesOf reads every sample tree for its content features, in parallel. The pass
// is a second read of the whole corpus beside the refutation scan's, and serially it took
// longer than the rest of validate together; the result is indexed like labels.
func contentFeaturesOf(labels []*label.Label) []contentResult {
	out := make([]contentResult, len(labels))
	var wg sync.WaitGroup
	sem := make(chan struct{}, runtime.NumCPU())
	for i, l := range labels {
		wg.Add(1)
		sem <- struct{}{}
		go func(i int, l *label.Label) {
			defer wg.Done()
			defer func() { <-sem }()
			files, err := treeFiles(l.Path)
			if err != nil {
				out[i].err = err
				return
			}
			out[i].features, out[i].err = leakage.ContentFeatures(l.Path, l.Entry, files)
		}(i, l)
	}
	wg.Wait()
	return out
}
