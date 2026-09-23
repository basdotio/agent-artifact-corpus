// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
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

	// Provenance travels from the manifest, not from the label. "Are this upstream's artifacts
	// wild or test fixtures" is a reading of the UPSTREAM, made once where that reading was
	// written down, rather than re-decided per sample.
	mf, err := manifest.Load(filepath.Join(root, "manifest", "corpora.yaml"))
	if err != nil {
		fatal(err)
	}
	prov := map[string]string{}
	for _, e := range mf.Entries {
		if e.Provenance != "" {
			prov[e.ID] = e.Provenance
		}
	}

	rep := score.Score(labels, verdicts, tax, basisSpec, populationOf, prov)
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

	fmt.Println("\ndetection — recall per dimension, split by what the samples rest on:")
	fmt.Println("  wild        the artifact existed because somebody made it for real. ONLY these")
	fmt.Println("              can back a claim about the world.")
	fmt.Println("  fixture     a third party wrote it as a test case — coverage of THEIR shapes.")
	fmt.Println("  constructed we wrote it — coverage of OURS.")
	fmt.Println("  The three never merge. Adding them produces a number that means nothing.")
	printRecall(rep.RecallByDimension)

	fmt.Println("\n  per source — a rate over one source is a rate ABOUT that source, not the world:")
	printGroups(rep.RecallBySource)

	// FLAG RATE, not false-positive rate, and the distinction is the corpus's own. A benign
	// label here means "somebody committed this to be loaded" and its class rests on `assumed`
	// — nobody read it and no security review of it exists. Calling a flag on such a sample a
	// false positive would assert we know the artifact is harmless, which is exactly the claim
	// the benign half refuses to make. The number below is what the scanner DID; how much of it
	// is error is a question the labels cannot answer.
	fmt.Println("\nflag rate on the benign pool — an estimate, reported per source:")
	fmt.Println("  benign here means `somebody runs this`, on an `assumed` basis — these are flags,")
	fmt.Println("  not confirmed false positives. Read one before you count it as an error.")
	printGroups(rep.FPByPopulation)
	printReviewed(rep)

	fmt.Println("\nhard negatives — the precision probe, a census, never pooled with the estimate above:")
	g := rep.HardNegFlagged
	if g.N == 0 {
		fmt.Println("  none scored")
	} else {
		// Here `false positive` IS earned: every hard negative was read by a person and carries
		// a `differs_by` naming what makes it benign despite wearing an attack's shape.
		fmt.Printf("  flagged %d of %d (%.0f%%) — each one a confirmed false positive: these were read\n",
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
	gaps := uncoveredBySource(labels, uncovered)
	if len(gaps) == 0 {
		return
	}
	fmt.Println("           the unscored, by source — a whole source missing is either a")
	fmt.Println("           deliberate exclusion or a runner dropping a shape; both need saying:")
	for _, g := range gaps {
		note := ""
		if g.Whole {
			note = "  (the entire source)"
		}
		fmt.Printf("           %5d of %-5d %s%s\n", g.Missing, g.Total, g.Source, note)
	}
}

// sourceGap is one source's share of the unscored samples. Whole is the claim worth being right
// about: it says the denominator lost this source entirely, and a reader acts differently on
// that than on "9 of 387 went missing".
type sourceGap struct {
	Source  string
	Missing int
	Total   int
	Whole   bool
}

// uncoveredBySource is the arithmetic, split out from the printing so the Whole claim can be
// tested. Sources with nothing missing are omitted rather than listed with a zero: the section
// exists to name what is absent.
func uncoveredBySource(labels []*label.Label, uncovered []string) []sourceGap {
	if len(uncovered) == 0 {
		return nil
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

	out := make([]sourceGap, 0, len(names))
	for _, name := range names {
		out = append(out, sourceGap{
			Source: name, Missing: counts[name], Total: totals[name],
			Whole: counts[name] == totals[name],
		})
	}
	return out
}

// printRecall prints the dimension table with collected and constructed on their own rows, so
// the eye never adds a constructed coverage count to a collected rate.
func printRecall(gs []score.Group) {
	fmt.Printf("  %-16s %-12s %6s   %s\n", "dimension", "evidence", "n", "result")
	for _, g := range gs {
		fmt.Printf("  %-16s %-12s %6d   %s\n", g.Key, g.Evidence, g.N, result(g))
	}
}

func printGroups(gs []score.Group) {
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
		fmt.Println("  " + strings.Join(ids[i:min(i+perLine, len(ids))], "  "))
	}
}

// printReviewed reports the reviewed subset — the only part of the benign pool where a flag can
// be called a false positive outright. It prints even when the subset is empty, and says so in
// words, because a silent zero here reads as "no confirmed false positives" when what it means
// is "nobody has read one yet". Those are opposite claims.
func printReviewed(rep score.Report) {
	if rep.BenignReviewed == 0 {
		fmt.Println("  reviewed subset: none. No benign sample has been read by a person, so NONE")
		fmt.Println("  of the flags above is a confirmed false positive — not one is confirmed to")
		fmt.Println("  be an error, and not one is confirmed to be correct.")
		return
	}
	fmt.Printf("  reviewed subset: %d of the benign pool has been read by a person; %d flag(s) "+
		"landed there.\n", rep.BenignReviewed, rep.FlagsOnReviewed)
	fmt.Printf("  those %d ARE confirmed false positives. The rest of the flags above remain "+
		"unadjudicated.\n", rep.FlagsOnReviewed)
}
