// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"regexp"
	"sort"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
)

// A false-positive rate is a claim about sources, not about files. If one repository supplies
// a third of the denominator then the headline number describes that repository's house style,
// which is the specific failure this corpus was built to stop repeating. So the concentration
// is printed beside the sample count, every run, whether or not it looks good.
//
// It cannot be computed from the manifest — an aggregator's 138,133 files come from 20,556
// repositories and the entry can only say so in prose. It has to be read back off the labels
// that were actually written.

// originRepo pulls the ORIGINATING repository out of a label's source, not the collection that
// redistributed it. `https://github.com/o/r (via skillmd-138k @ abc)` is one source, r; the
// same string read as "skillmd-138k" would report 2,000 samples as one.
var originRepo = regexp.MustCompile(`github\.com/([^/\s]+/[^/\s)]+)`)

func originOf(l *label.Label) string {
	if m := originRepo.FindStringSubmatch(l.Origin.Source); m != nil {
		return m[1]
	}
	return ""
}

type concentration struct {
	Samples  int
	Distinct int
	Unattr   int // samples whose source names no originating repository
	TopName  string
	TopCount int
}

// concentrationOf counts distinct originating repositories within one class.
func concentrationOf(labels []*label.Label, class label.Class) concentration {
	c := concentration{}
	counts := map[string]int{}
	for _, l := range labels {
		if l.Class != class {
			continue
		}
		c.Samples++
		repo := originOf(l)
		if repo == "" {
			c.Unattr++
			continue
		}
		counts[repo]++
	}
	c.Distinct = len(counts)

	// Ties broken by name so the report does not change between runs on equal counts.
	names := make([]string, 0, len(counts))
	for n := range counts {
		names = append(names, n)
	}
	sort.Strings(names)
	for _, n := range names {
		if counts[n] > c.TopCount {
			c.TopName, c.TopCount = n, counts[n]
		}
	}
	return c
}

// reportSources prints, per class, how many real sources the samples came from and how much of
// the class the largest one holds.
func reportSources(labels []*label.Label) {
	fmt.Println("  by originating repository — a rate over few sources is a rate about those sources.")
	fmt.Println("    A repository is not always one writer: an aggregator is counted once here and")
	fmt.Println("    its hazards in manifest/corpora.yaml say how many authors are actually inside it.")
	for _, class := range []label.Class{label.Benign, label.Malicious, label.HardNegative} {
		c := concentrationOf(labels, class)
		if c.Samples == 0 {
			continue
		}
		if c.Distinct == 0 {
			fmt.Printf("    %-14s %d sample(s), none naming an originating repository — "+
				"no per-source rate can be computed for these\n", string(class), c.Samples)
			continue
		}
		fmt.Printf("    %-14s %d repos over %d sample(s); largest %s at %d (%.1f%%)\n",
			string(class), c.Distinct, c.Samples, c.TopName, c.TopCount,
			float64(c.TopCount)/float64(c.Samples)*100)
		if c.Unattr > 0 {
			// Named and counted rather than dropped: a denominator that silently excluded them
			// would be reporting a different population than the one it claims.
			fmt.Printf("    %-14s %d of those name no originating repository (purpose-built "+
				"fixtures, or an upstream that did not record one)\n", "", c.Unattr)
		}
	}
}
