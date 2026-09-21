// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/score"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// cmdScore reads a scanner's verdicts and prints what they measure. It grades the scanner
// against `truth`, never the reverse: nothing here decides whether the scanner passed, only
// what its numbers are and what each one is allowed to mean. The exit code is 0 whenever the
// verdicts were readable and scored — a low recall is a finding, not a tool error.
func cmdScore(root string, args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "usage: corpus score <verdicts.jsonl>   (use - for stdin)")
		return 2
	}

	var raw *os.File
	if args[0] == "-" {
		raw = os.Stdin
	} else {
		f, err := os.Open(args[0])
		if err != nil {
			fmt.Fprintf(os.Stderr, "cannot read verdicts: %v\n", err)
			return 2
		}
		defer f.Close()
		raw = f
	}
	verdicts, err := score.ParseVerdicts(raw)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		return 2
	}

	tax, err := taxonomy.Load(filepath.Join(root, "taxonomy"))
	if err != nil {
		fatal(err)
	}
	basisSpec, err := taxonomy.LoadBasis(filepath.Join(root, "taxonomy"))
	if err != nil {
		fatal(err)
	}
	labels, err := loadLabels(root)
	if err != nil {
		fatal(err)
	}

	rep := score.Score(labels, verdicts, tax, basisSpec, populationOf)
	printReport(rep, labels)
	return 0
}

func printReport(rep score.Report, labels []*label.Label) {
	fmt.Printf("corpus     %d labels — %d malicious, %d benign, %d hard-negative\n",
		rep.Labels, rep.Malicious, rep.Benign, rep.HardNeg)
	fmt.Printf("coverage   %d of %d scored; %d had no verdict",
		rep.Covered, rep.Labels, rep.Uncovered)
	if len(rep.UnknownVerdicts) > 0 {
		fmt.Printf("; %d verdict(s) named a sample not in the corpus", len(rep.UnknownVerdicts))
	}
	fmt.Println()
	if rep.Uncovered > 0 {
		fmt.Println("           an unscored sample is not a pass — recall below is over the scored subset only")
		// Grouped by source, not listed by id. 127 ids tell a reader nothing; "127 from
		// cisco-mcp-scanner-evals" tells them a whole source is missing from the denominator,
		// which is either a deliberate de-contamination or an accident, and both are things
		// they need to see at the top rather than infer from a list further down.
		printUncoveredBySource(labels, rep.UncoveredIDs)
	}

	fmt.Println("\ndetection — recall per dimension. collected and constructed never merge:")
	fmt.Println("  a rate is a claim about the world; coverage is how many chosen shapes were caught.")
	printRecall(rep.RecallByDimension)

	fmt.Println("\n  per source — a rate over one source is a rate ABOUT that source, not the world:")
	printGroups(rep.RecallBySource, true)

	fmt.Println("\nfalse positives per population — the benign pool, an estimate, reported per source:")
	printGroups(rep.FPByPopulation, false)

	fmt.Println("\nhard negatives — the precision probe, a census, never pooled with the estimate above:")
	g := rep.HardNegFlagged
	if g.N == 0 {
		fmt.Println("  none scored")
	} else {
		fmt.Printf("  flagged %d of %d (%.0f%%) — each one a false positive on a deliberate near-miss\n",
			g.Hits, g.N, g.Point*100)
	}

	fmt.Println("\nattribution — of caught malicious with a read-basis dimension, was the KIND named:")
	a := rep.Attribution
	if a.Scoreable == 0 {
		fmt.Println("  nothing scoreable: no caught sample carries a dimension resting on `read`")
	} else {
		fmt.Printf("  %d of %d correct (%.0f%%, [%.0f, %.0f])\n",
			a.Correct, a.Scoreable, a.Point*100, a.Lo*100, a.Hi*100)
	}

	if rep.Uncovered > 0 {
		fmt.Printf("\n%d uncovered sample(s):\n", rep.Uncovered)
		printList(rep.UncoveredIDs)
	}
	if len(rep.UnknownVerdicts) > 0 {
		fmt.Printf("\n%d verdict(s) for a sample not in the corpus:\n", len(rep.UnknownVerdicts))
		printList(rep.UnknownVerdicts)
	}
}

// printUncoveredBySource says WHICH sources the missing samples came from. The corpus's citation
// rule requires an exclusion to appear in the conclusion with both numbers; this is the line that
// makes the first of those two numbers impossible to miss, whether the exclusion was intended
// (`corpus samples --exclude-source`) or is a runner quietly dropping a whole shape.
func printUncoveredBySource(labels []*label.Label, uncovered []string) {
	if len(uncovered) == 0 {
		return
	}
	missing := make(map[string]bool, len(uncovered))
	for _, id := range uncovered {
		missing[id] = true
	}
	counts := map[string]int{}
	totals := map[string]int{}
	for _, l := range labels {
		src := populationOf(l)
		totals[src]++
		if missing[l.ID] {
			counts[src]++
		}
	}
	names := make([]string, 0, len(counts))
	for name := range counts {
		names = append(names, name)
	}
	sort.Strings(names)

	fmt.Println("           the unscored, by source — a whole source missing is either a")
	fmt.Println("           deliberate exclusion or a runner dropping a shape; both need saying:")
	for _, name := range names {
		note := ""
		if counts[name] == totals[name] {
			note = "  (the entire source)"
		}
		fmt.Printf("           %5d of %-5d %s%s\n", counts[name], totals[name], name, note)
	}
}

// printRecall prints the dimension table with collected and constructed on their own rows, so
// the eye never adds a constructed coverage count to a collected rate.
func printRecall(gs []score.Group) {
	fmt.Printf("  %-16s %-12s %6s   %s\n", "dimension", "evidence", "n", "result")
	for _, g := range gs {
		fmt.Printf("  %-16s %-12s %6d   %s\n", g.Key, g.Evidence, g.N, result(g))
	}
}

func printGroups(gs []score.Group, recall bool) {
	if len(gs) == 0 {
		fmt.Println("  none scored")
		return
	}
	for _, g := range gs {
		fmt.Printf("  %-28s %6d   %s\n", g.Key, g.N, result(g))
	}
}

// result renders one proportion honestly: a rate with its interval when the interval is tight
// enough to be a figure, a bare count when it is not. The constructed evidence class is always
// a count — it is coverage by construction, never a rate, regardless of n.
func result(g score.Group) string {
	if g.N == 0 {
		return "no samples"
	}
	if g.Evidence == score.Constructed {
		return fmt.Sprintf("caught %d of %d (coverage of chosen shapes, not a rate)", g.Hits, g.N)
	}
	if !g.Figure {
		return fmt.Sprintf("caught %d of %d (n too small for a rate; ±%.0f pts)",
			g.Hits, g.N, score.HalfWidthPoints(g.Point, g.Lo, g.Hi))
	}
	return fmt.Sprintf("%.0f%%  [%.0f, %.0f]  (%d/%d)",
		g.Point*100, g.Lo*100, g.Hi*100, g.Hits, g.N)
}

func printList(ids []string) {
	const perLine = 4
	for i := 0; i < len(ids); i += perLine {
		end := i + perLine
		if end > len(ids) {
			end = len(ids)
		}
		fmt.Println("  " + strings.Join(ids[i:end], "  "))
	}
}
