// SPDX-License-Identifier: MIT

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
)

// cmdSamples emits the corpus as a JSONL work list — one object per sample with its id, tree
// path, class and surface — so a runner living beside a scanner can iterate the corpus without
// re-implementing how a label maps to a tree. It is the input side of the scoring loop that
// `corpus score` closes: a runner reads this, points its scanner at each `path`, and emits
// `{"sample": id, "verdict": ...}` back for scoring.
//
// It names no scanner and makes no judgement — it only says what is here. That is why it belongs
// in this repository while the runner that consumes it does not.
//
// # Why it can now filter by source
//
// Some scanners are measured against a corpus that contains their own test fixtures. This one
// holds 127 samples derived from cisco-ai-defense's scanner evals and 6 from NVIDIA's
// SkillSpector fixtures, so a figure for either of those tools is partly that tool graded on its
// own tests. The corpus's own citation rule already covers the reporting side — "any exclusion
// must appear in the conclusion, with both numbers" — but until now there was no way to PRODUCE
// the second number: the work list was all-or-nothing, so "the same figure without its own
// fixtures" could not be computed at all. A footnote cannot fix a number that was never computed.
//
// Two deliberate choices:
//
//   - The default excludes nothing. A denominator that shrinks unless you ask is a denominator
//     that shrinks without anyone noticing.
//   - A name matching no sample is an ERROR, not an empty exclusion. That failure direction
//     matters: a typo in `--exclude-source cisco-mcp-scanner-eval` would otherwise report a
//     de-contaminated figure that is nothing of the kind, and the operator would have the
//     receipt to prove they had checked.
func cmdSamples(root string, args []string) int {
	include, exclude, err := parseSourceFilters(args)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		return 2
	}

	labels, err := loadLabels(root)
	if err != nil {
		fatal(err)
	}

	// populationOf is THE definition of a source in this repository — the same function the
	// scorer is handed so that false positives group by the batches the leakage gate uses.
	// Filtering on anything else here (the originating repository, say) would create a second
	// definition of "source" whose numbers could not be compared with the scorecard's.
	counts := map[string]int{}
	for _, l := range labels {
		counts[populationOf(l)]++
	}
	if err := checkNamesExist(counts, include, exclude); err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		return 2
	}

	kept := make([]*label.Label, 0, len(labels))
	dropped := map[string]int{}
	for _, l := range labels {
		src := populationOf(l)
		switch {
		case len(include) > 0 && !include[src]:
			dropped[src]++
		case exclude[src]:
			dropped[src]++
		default:
			kept = append(kept, l)
		}
	}

	enc := json.NewEncoder(os.Stdout)
	for _, l := range kept {
		rec := struct {
			Sample   string   `json:"sample"`
			Path     string   `json:"path"`
			Class    string   `json:"class"`
			Surface  []string `json:"surface"`
			Severity string   `json:"severity,omitempty"`
		}{
			Sample:   l.ID,
			Path:     l.Rel,
			Class:    string(l.Class),
			Surface:  []string(l.Surface),
			Severity: l.Truth.Severity,
		}
		if err := enc.Encode(rec); err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
			return 1
		}
	}

	reportExclusion(os.Stderr, len(labels), len(kept), dropped)
	return 0
}

// parseSourceFilters reads the two flags. Hand-rolled to match the other subcommands, which take
// `args []string` rather than a FlagSet.
func parseSourceFilters(args []string) (include, exclude map[string]bool, err error) {
	include, exclude = map[string]bool{}, map[string]bool{}
	for i := 0; i < len(args); i++ {
		var target map[string]bool
		switch args[i] {
		case "--source":
			target = include
		case "--exclude-source":
			target = exclude
		default:
			return nil, nil, fmt.Errorf("unknown argument %q\n"+
				"usage: corpus samples [--source a,b] [--exclude-source a,b]", args[i])
		}
		if i+1 >= len(args) {
			return nil, nil, fmt.Errorf("%s needs a comma-separated list of source names", args[i])
		}
		i++
		for _, name := range strings.Split(args[i], ",") {
			if n := strings.TrimSpace(name); n != "" {
				target[n] = true
			}
		}
	}
	if len(include) > 0 && len(exclude) > 0 {
		// Both at once has two readings — subtract from the included set, or intersect — and a
		// reader of the resulting number could not tell which was meant.
		return nil, nil, fmt.Errorf("--source and --exclude-source together are ambiguous; " +
			"use one and say which in the conclusion")
	}
	return include, exclude, nil
}

// checkNamesExist refuses a name no sample carries. See the command comment: the dangerous
// direction is a typo that silently excludes nothing while the operator believes it did.
func checkNamesExist(counts map[string]int, sets ...map[string]bool) error {
	var unknown []string
	for _, set := range sets {
		for name := range set {
			if counts[name] == 0 {
				unknown = append(unknown, name)
			}
		}
	}
	if len(unknown) == 0 {
		return nil
	}
	sort.Strings(unknown)

	known := make([]string, 0, len(counts))
	for name := range counts {
		known = append(known, name)
	}
	sort.Strings(known)
	return fmt.Errorf("no sample comes from %s.\nRefusing rather than filtering nothing: a "+
		"mistyped name would produce a figure that looks de-contaminated and is not.\n"+
		"The sources in this corpus are:\n  %s",
		strings.Join(unknown, ", "), strings.Join(known, "\n  "))
}

// reportExclusion states the cost of a filter on stderr, so it does not contaminate the work
// list on stdout. It prints even when nothing was dropped: "this run excluded nothing" is the
// line that makes the absence of an exclusion notice evidence rather than an assumption.
func reportExclusion(w *os.File, total, kept int, dropped map[string]int) {
	if len(dropped) == 0 {
		fmt.Fprintf(w, "samples: %d of %d, no source excluded\n", kept, total)
		return
	}
	names := make([]string, 0, len(dropped))
	for name := range dropped {
		names = append(names, name)
	}
	sort.Strings(names)

	fmt.Fprintf(w, "samples: %d of %d — %d excluded by source:\n", kept, total, total-kept)
	for _, name := range names {
		fmt.Fprintf(w, "  %5d  %s\n", dropped[name], name)
	}
	fmt.Fprintln(w, "Both numbers belong in any conclusion drawn from this run: the corpus's")
	fmt.Fprintln(w, "citation rule is that an exclusion appears in the conclusion line with the")
	fmt.Fprintln(w, "figure including it and the figure without it.")
}
