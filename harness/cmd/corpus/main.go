// SPDX-License-Identifier: MIT

// Command corpus validates and summarises the corpus.
//
// It deliberately does not score anything. Running a scanner over the corpus belongs
// elsewhere, and keeping the scorer out means the corpus validates with no build of any
// scanner present — which is now load-bearing rather than tidy, because a label's `truth`
// block is written in a vocabulary no scanner owns and has to be checkable on its own.
package main

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/derive"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/fetch"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/leakage"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}
	root, err := repoRoot()
	if err != nil {
		fatal(err)
	}
	switch os.Args[1] {
	case "validate":
		os.Exit(cmdValidate(root))
	case "stats":
		os.Exit(cmdStats(root))
	case "fetch":
		os.Exit(cmdFetch(root, os.Args[2:]))
	case "derive":
		os.Exit(cmdDerive(root, os.Args[2:]))
	default:
		usage()
		os.Exit(2)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, `corpus <command>

  validate   check every label and manifest entry, and run the leakage gate
  stats      corpus composition
  fetch      materialise named layer-2 entries into ./cache (network)
  derive     dry-run the coordinate derivation for a fetched entry and report coverage`)
}

// ---------- validate ----------

func cmdValidate(root string) int {
	tax, err := taxonomy.Load(filepath.Join(root, "taxonomy"))
	if err != nil {
		fatal(err)
	}
	labels, err := loadLabels(root)
	if err != nil {
		fatal(err)
	}

	var problems []string
	for _, e := range tax.Validate() {
		problems = append(problems, fmt.Sprintf("taxonomy: %v", e))
	}
	verified, carried := 0, 0
	for _, l := range labels {
		for _, e := range l.Validate(tax) {
			problems = append(problems, fmt.Sprintf("%s: %v", l.Rel, e))
		}
		// Layer 1 holds the bytes, so a hash on a vendored sample is checkable — and an
		// unchecked hash is worse than none, because it reads like integrity.
		if errs := l.VerifySha256(); len(errs) > 0 {
			for _, e := range errs {
				problems = append(problems, fmt.Sprintf("%s: %v", l.Rel, e))
			}
		} else if l.Origin.Sha256 != "" {
			verified++
		}
		if l.Origin.Sha256 != "" {
			// Counted whether or not it verified. Incrementing only on success made the summary
			// line say "392 of 3489 carry a hash" when 393 do — understating the claim being
			// made while a failure was printed separately. The sentence has to stay true.
			carried++
		}
	}

	// Rule ids are resolved per tool, against that tool's own generated reference. A tool
	// with no reachable reference is reported as unchecked rather than assumed correct.
	knownRules := map[string]*taxonomy.RuleIndex{}
	var ruleLines []string
	for _, id := range sortedKeys(tax.Tools) {
		tool := tax.Tools[id]
		idx := tool.ReadRules(root)
		if idx.Len() == 0 {
			ruleLines = append(ruleLines, fmt.Sprintf("  %-10s not checked — no rule reference reachable", id))
			continue
		}
		knownRules[id] = idx

		// Measurement part 2 needs every rule to resolve to one of our dimensions or to be
		// deliberately unmapped. Count both: a tool whose findings mostly map to nothing can
		// pass part 1 on every sample and still never say what kind of problem it found.
		mapped := 0
		for _, d := range idx.Dimension {
			if d != nil {
				mapped++
			}
		}
		ruleLines = append(ruleLines, fmt.Sprintf(
			"  %-10s %d ids, %d carry a dimension (from %s)", id, idx.Len(), mapped, idx.Source))

		// A section mapped to nil is a decision. A section missing from the map is an
		// oversight, and the two must not look alike.
		for _, sec := range idx.Unmapped {
			problems = append(problems, fmt.Sprintf(
				"taxonomy/tools.yaml: %s emits rules under %q, which has no dimension_map "+
					"entry. Map it to one of our dimensions, or to null to record that it "+
					"names no kind of attack — leaving it out makes an oversight look like "+
					"a decision", id, sec))
		}
	}
	for _, e := range label.ValidateSet(labels, tax, knownRules) {
		problems = append(problems, e.Error())
	}

	// Neutrality. Not behind a flag: a check nobody remembers to run proves the thing on the
	// days it does not matter. See neutrality.go, including what was deliberately NOT built.
	// A count corrected in the manifest and left stale in the five documents that quote it was
	// 47 of the ~355 wrong numbers an audit found. Fixing them again would fix nothing.
	classTotals := map[string]int{}
	for _, l := range labels {
		classTotals[string(l.Class)]++
	}
	problems = append(problems, ManifestClaimsInProse(root, classTotals)...)

	neutralProblems := ToolNamesInNeutralHalf(labels, tax)
	neutralProblems = append(neutralProblems, ToolNamesInHarnessCode(root, tax)...)
	neutralProblems = append(neutralProblems, ToolNamesInBuildFiles(root, tax)...)
	neutralProblems = append(neutralProblems, CIDependsOnAScanner(root, tax)...)
	problems = append(problems, neutralProblems...)

	// Layer 2
	var pinStatuses []PinStatus
	manifests, _ := filepath.Glob(filepath.Join(root, "manifest", "*.yaml"))
	for _, mp := range manifests {
		f, err := manifest.Load(mp)
		if err != nil {
			problems = append(problems, fmt.Sprintf("%s: %v", rel(root, mp), err))
			continue
		}
		for _, e := range f.Validate() {
			problems = append(problems, fmt.Sprintf("%s: %v", rel(root, mp), e))
		}
		pinStatuses = append(pinStatuses, CheckPins(root, f.Entries)...)
	}

	// Leakage gate
	var samples []leakage.Sample
	for _, l := range labels {
		files, ferr := treeFiles(l.Path)
		if ferr != nil {
			// Not swallowed. An unreadable tree silently becomes a zero-file sample, which
			// moves the file-count distribution the gate is reading and changes its verdict
			// for a reason that has nothing to do with the corpus.
			problems = append(problems, fmt.Sprintf("%s: cannot walk the sample tree: %v",
				l.Rel, ferr))
			continue
		}
		// The group is the POPULATION a sample belongs to — where the ARTIFACT came from —
		// because the gate asks whether the classes are separable without reading content, and
		// that question only means anything inside one batch.
		//
		// The third case was added after an audit found a 100%-pure feature in what used to be
		// a catch-all: five 14-24KB Turkish reference documents from one upstream sat in the
		// same "hand-pinned" bucket as twelve sub-1.1KB fixtures we wrote ourselves, and
		// document length alone then separated five of the nine hard negatives with a 12.9x
		// margin and no overlap. Nothing was wrong with the samples. The bucket was wrong: it
		// pooled two batches that were built by different people for different reasons, which
		// is exactly the pooling this gate exists to detect in other people's corpora.
		group := "hand-written"
		switch {
		case l.Origin.DerivedFrom != nil && l.Origin.DerivedFrom.Entry != "":
			group = l.Origin.DerivedFrom.Entry
		case l.Origin.Type == "harvested":
			// One batch by construction: all collected by the same script from the same search.
			group = "harvested"
		default:
			// A hand-pinned label can still describe somebody else's artifact. When the source
			// names an upstream, that upstream is the batch; only samples with no external
			// source at all were written here.
			if repo := originOf(l); repo != "" {
				group = repo
			}
		}
		samples = append(samples, leakage.Sample{
			ID: l.ID, Class: string(l.Class), Files: files, Group: group,
		})
	}
	leaks := leakage.Check(samples)
	crossPop := leakage.CrossPopulation(samples)

	fmt.Printf("labels      %d\n", len(labels))
	fmt.Printf("techniques  %d across %d dimensions\n", len(tax.Techniques), len(tax.Dimensions))
	// Said out loud including when it is zero, so "no hash failures" can never be mistaken
	// for "the hashes were checked".
	fmt.Printf("sha256      %d of %d label(s) carry a hash; %d verified against the vendored "+
		"bytes\n", carried, len(labels), verified)
	// Named even when clean, because the point of these three is that they were each added
	// after the property they guard had already silently broken.
	if len(neutralProblems) == 0 {
		fmt.Printf("neutral     %d scanner(s) registered, and none appears in any truth block, in the "+
			"vocabulary, in the harness code, in the build files or in CI\n", len(tax.Tools))
	} else {
		fmt.Printf("neutral     FAILED — %d place(s) where one scanner has become part of the "+
			"shared half\n", len(neutralProblems))
	}
	problems = append(problems, reportPins(pinStatuses)...)
	fmt.Println("rule ids")
	for _, line := range ruleLines {
		fmt.Println(line)
	}

	// The gate needs more samples than it has before it can say anything. Printing "ok"
	// without saying so lets an inactive gate read as a passed one — the same failure the
	// gate exists to catch, one level up.
	// "active over 3489 samples" was the line here, and it was false in the way that matters:
	// the gate can only reach a verdict inside a population that holds more than one class and
	// is not already past the purity threshold. 86% of the corpus sat outside that, so the
	// line reported the corpus's size as if it were the gate's reach. An inactive gate reading
	// as a passed one is the exact failure this gate exists to catch, one level up.
	judgeable := leakage.Judgeable(samples)
	single := leakage.SingleClass(samples)
	imbalanced := leakage.Imbalanced(samples)
	if len(samples) < leakage.MinSupport {
		fmt.Printf("leakage     INACTIVE — %d samples, gate needs %d before any feature has support\n",
			len(samples), leakage.MinSupport)
	} else {
		fmt.Printf("leakage     judged %d of %d sample(s) (%.1f%%); the rest sit in populations "+
			"where no verdict is possible\n", judgeable, len(samples),
			float64(judgeable)/float64(len(samples))*100)
		for _, g := range single {
			fmt.Printf("  no comparison  %s — one class, so no feature can predict it\n", g)
		}
		for _, g := range imbalanced {
			fmt.Printf("  not judgeable  %s — one class already exceeds the %.0f%% purity "+
				"threshold\n", g, leakage.MaxPurity*100)
		}
	}

	// `entry` says what a scanner is pointed at, and until an audit probed it nothing ever
	// resolved it: `entry: no/such/file.md` validated cleanly, and so did a sample tree holding
	// no files at all. Both make a sample that cannot be scored while looking scoreable.
	for _, l := range labels {
		if l.Path == "" {
			continue
		}
		files, ferr := treeFiles(l.Path)
		if ferr != nil {
			continue // reported by the leakage pass below
		}
		if len(files) == 0 {
			problems = append(problems, fmt.Sprintf(
				"%s: the sample tree holds no files. There is nothing for a scanner to read, so "+
					"this sample cannot be passed or failed — it can only be counted, which is "+
					"worse than not existing", l.Rel))
			continue
		}
		if l.Entry == "" || l.Entry == "." {
			continue // the whole tree, which exists by the check above
		}
		if _, err := os.Stat(filepath.Join(l.Path, l.Entry)); err != nil {
			problems = append(problems, fmt.Sprintf(
				"%s: entry %q does not exist in the sample tree. It is the one field that says "+
					"what to point a scanner at, so an entry naming nothing makes the sample "+
					"unusable by the protocol this corpus publishes", l.Rel, l.Entry))
		}
	}

	// Duplicates: cross-class is an error, same-class is named and counted.
	problems = append(problems, reportDuplicates(DuplicateTrees(labels))...)

	// A pair that guards nothing passes every structural check. It is reported, named and
	// counted rather than rejected, because the twin's known_gap is an honest declaration
	// and the problem is only that its consequence was invisible.
	unguarded := label.UnguardedPairs(labels)
	if len(unguarded) > 0 {
		fmt.Printf("\n%d unguarded pair(s) — structurally valid, currently proving nothing:\n", len(unguarded))
		for _, u := range unguarded {
			fmt.Printf("  %s quiets %s, and its twin %s is on record failing them for %s (%s).\n"+
				"    Deleting those rules from %s today breaks neither sample.\n",
				u.HardNegative, strings.Join(u.SharedRules, ", "), u.Twin, u.Tool, u.GapItem, u.Tool)
		}
	}

	for _, f := range leaks {
		problems = append(problems, fmt.Sprintf(
			"leakage in %s: %q appears in %d of its samples and %d of them are %s (%.0f%% pure) "+
				"— within one population a classifier can separate the classes without reading content",
			f.Group, f.Name, f.Total, f.With, f.Class, f.Purity()*100))
	}

	// Not a failure, and not silenced either. These features separate the classes only once
	// populations are pooled, which measures how differently the two halves are BUILT: the
	// benign side is real public repositories with licences, TypeScript and twenty files, the
	// malicious side is purpose-built fixtures with three. It is the reason a single rate over
	// the whole corpus would be meaningless, and it is printed so nobody computes one.
	if len(crossPop) > 0 {
		fmt.Printf("\ncross-population structure — %d feature(s) separate the classes only when\n"+
			"populations are pooled. They are not defects; they are why a pooled rate is invalid:\n", len(crossPop))
		for i, f := range crossPop {
			if i == 5 {
				fmt.Printf("  … and %d more\n", len(crossPop)-5)
				break
			}
			fmt.Printf("  %-22s %d samples, %d %s (%.0f%%)\n", f.Name, f.Total, f.With, f.Class, f.Purity()*100)
		}
	}

	if len(problems) == 0 {
		fmt.Println("\nok")
		return 0
	}
	sort.Strings(problems)
	fmt.Printf("\n%d problem(s):\n", len(problems))
	for _, p := range problems {
		fmt.Printf("  - %s\n", p)
	}
	return 1
}

// ---------- stats ----------

func cmdStats(root string) int {
	tax, err := taxonomy.Load(filepath.Join(root, "taxonomy"))
	if err != nil {
		fatal(err)
	}
	labels, err := loadLabels(root)
	if err != nil {
		fatal(err)
	}

	byClass := map[string]int{}
	bySurface := map[string]map[string]int{}
	byOrigin := map[string]int{}
	performed := map[string]int{} // technique -> malicious samples performing it
	resembled := map[string]int{} // technique -> hard negatives resembling it
	// grid[dimension][tier] is the primary reporting surface: it is the pair of axes that
	// turns "this scanner is weak at exfiltration" into "it catches plain exfiltration and
	// misses every encoded one". Surface is reported separately rather than as a third
	// dimension of the same table — 8 x 4 x 6 is 192 cells for a handful of samples, and a
	// hole-naming discipline that emits 190 lines of noise is one people learn to ignore.
	grid := map[string]map[string]int{}
	byEvasion := map[string]int{}
	// Credibility is tracked apart from every other count. A hand-pinned truth and a coordinate
	// derived from someone else's label are both "in the corpus", and summing them into one
	// number is exactly the flattering arithmetic this repository exists to refuse.
	selfPinned, derivedCount, harvested := 0, 0, 0
	// depthUnnamed counts derived malicious samples buried past the calibration tier whose
	// burying mechanism the upstream never recorded. The tier is the upstream's rating; the
	// mechanism is simply unknown. It is a declared hole, not a clean row.
	depthUnnamed := 0
	type toolStat struct{ samples, gaps, oos int }
	tools := map[string]*toolStat{}

	for _, l := range labels {
		byClass[string(l.Class)]++
		// A multi-surface artifact is counted once under each load path it sits on. The
		// columns therefore do not sum to the sample count, and the report says so — the
		// alternative, picking one surface per artifact, is what made the permission surface
		// mean "settings files with no hooks".
		for _, sf := range l.Surface {
			if bySurface[sf] == nil {
				bySurface[sf] = map[string]int{}
			}
			bySurface[sf][string(l.Class)]++
		}
		byOrigin[l.Origin.Type]++
		switch l.Origin.Type {
		case "derived":
			derivedCount++
			if l.Class == label.Malicious && l.Truth.Tier != "" && len(l.Truth.Evasion) == 0 {
				if t, ok := tax.Tiers[l.Truth.Tier]; ok && !t.Calibration {
					depthUnnamed++
				}
			}
		case "harvested":
			// `harvested` describes where the ARTIFACT came from; this report is about where
			// the COORDINATES came from, and the two come apart. A real config collected from
			// a public repository and then read by hand into a hard negative — with
			// `resembles` and `differs_by` that no rule could produce — belongs in the
			// hand-pinned tier, because that is the claim a reader is weighing. Keying this
			// on origin.type alone would have understated the corpus's own best evidence.
			if l.Truth.HandWritten() {
				selfPinned++
			} else {
				harvested++
			}
		default:
			selfPinned++
		}

		for _, t := range l.Truth.Techniques {
			performed[t]++
			addCell(grid, tax.Dimension(t), l.Truth.Tier)
		}
		// Derived samples name their dimension directly: the upstream knew its category, not
		// which technique the sample uses.
		for _, d := range l.Truth.Dimensions {
			addCell(grid, d, l.Truth.Tier)
		}
		for _, t := range l.Truth.Resembles {
			resembled[t]++
			// A hard negative sits in the cell of what it imitates. That is the point of it:
			// the pair is what tests whether a hit is on the difference rather than the topic.
			addCell(grid, tax.Dimension(t), l.Truth.Tier)
		}
		for _, e := range l.Truth.Evasion {
			byEvasion[e]++
		}
		for id, e := range l.Expect {
			if tools[id] == nil {
				tools[id] = &toolStat{}
			}
			tools[id].samples++
			if e.KnownGap != nil {
				tools[id].gaps++
			}
			if e.OutOfScope != "" {
				tools[id].oos++
			}
		}
	}

	fmt.Println("Layer 1 — vendored")
	fmt.Printf("  samples          %d\n", len(labels))
	for _, c := range []string{"malicious", "benign", "hard-negative"} {
		fmt.Printf("    %-14s %d\n", c, byClass[c])
	}

	fmt.Println("  by coordinate credibility — never summed")
	fmt.Printf("    %-34s %d\n", "hand-pinned (we wrote the truth)", selfPinned)
	fmt.Printf("    %-34s %d\n", "derived (upstream label + rule)", derivedCount)
	if harvested > 0 {
		fmt.Printf("    %-34s %d\n", "harvested (collected, not written)", harvested)
	}
	if depthUnnamed > 0 {
		fmt.Printf("    of the derived, %d are buried past the calibration tier with no evasion\n", depthUnnamed)
		fmt.Printf("      mechanism recorded upstream — the depth is known, the mechanism is not\n")
	}

	reportSources(labels)

	fmt.Println("  by surface — an artifact on two load paths is counted under both, so these")
	fmt.Println("    do not sum to the sample count above")
	for _, s := range sortedKeys(bySurface) {
		m := bySurface[s]
		fmt.Printf("    %-14s mal %-4d ben %-4d hard-neg %d\n", s, m["malicious"], m["benign"], m["hard-negative"])
	}

	fmt.Println("  by origin")
	for _, o := range []string{"real-world", "promoted", "reconstruction", "synthetic", "harvested", "derived"} {
		if byOrigin[o] > 0 {
			fmt.Printf("    %-14s %d\n", o, byOrigin[o])
		}
	}

	// Truth-side composition. This is the half that describes the corpus to someone who has
	// never run any scanner of ours, so every value in the vocabulary is listed including the
	// ones with no sample: a named hole is actionable, an omitted one reads as covered.
	fmt.Println("  by technique (truth — tool-neutral)")
	for _, t := range sortedKeys(tax.Techniques) {
		fmt.Printf("    %-22s performed %-4d resembled %d\n", t, performed[t], resembled[t])
	}

	fmt.Printf("\n  dimension x tier — the grid a scanner's failures are read off\n")
	fmt.Printf("    %-16s", "")
	for _, t := range tax.TierOrder {
		fmt.Printf(" %9s", t)
	}
	fmt.Println("   total")
	empty := 0
	for _, d := range tax.Dimensions {
		fmt.Printf("    %-16s", d)
		row := 0
		for _, t := range tax.TierOrder {
			n := grid[d][t]
			row += n
			if n == 0 {
				empty++
				fmt.Printf(" %9s", ".")
				continue
			}
			fmt.Printf(" %9d", n)
		}
		fmt.Printf("   %d\n", row)
	}
	fmt.Printf("    %d of %d cells have no sample. A dot is a question no measurement here can answer.\n",
		empty, len(tax.Dimensions)*len(tax.TierOrder))

	fmt.Println("\n  by evasion mechanism (which transformation a miss would be attributed to)")
	for _, e := range sortedKeys(tax.Evasions) {
		mark := " "
		if byEvasion[e] == 0 {
			mark = "."
		}
		fmt.Printf("    %-26s %s %d  (implies tier %s)\n", e, mark, byEvasion[e], tax.Evasions[e].ImpliesTier)
	}

	// Expectation-side composition, per tool. A tool absent from a sample means not
	// measured, which is why this is reported as a count of samples carrying a block rather
	// than as coverage.
	fmt.Println("  per-tool expectations (optional precision on top of truth)")
	if len(tools) == 0 {
		fmt.Println("    none — every sample is scored from truth alone")
	}
	for _, id := range sortedKeys(tools) {
		t := tools[id]
		fmt.Printf("    %-14s %d/%d samples · %d known gap(s) · %d out of scope\n",
			id, t.samples, len(labels), t.gaps, t.oos)
	}
	if u := label.UnguardedPairs(labels); len(u) > 0 {
		fmt.Printf("  unguarded pairs  %d  (twin is on record failing the shared rules; the suppression is currently unproven)\n", len(u))
	} else {
		fmt.Printf("  unguarded pairs  0\n")
	}

	manifests, _ := filepath.Glob(filepath.Join(root, "manifest", "*.yaml"))
	total := 0
	for _, mp := range manifests {
		f, err := manifest.Load(mp)
		if err != nil {
			continue
		}
		fmt.Printf("\nLayer 2 — %s\n", rel(root, mp))
		for _, e := range f.Entries {
			v := "ref"
			if e.Vendorable {
				v = "vendorable"
			}
			fmt.Printf("  %-28s %-16s mal %-6d ben %-7d %-16s %s\n",
				e.ID, e.Role, e.Malicious, e.Benign, e.License, v)
			total++
		}
		var overlapping [][]string
		for _, g := range f.PoolableGroups() {
			if len(g) > 1 {
				overlapping = append(overlapping, g)
			}
		}
		if len(overlapping) > 0 {
			fmt.Println("\n  These entries share samples and must NOT be summed:")
			for _, g := range overlapping {
				fmt.Printf("    %s\n", strings.Join(g, " + "))
			}
		}
	}
	if total == 0 {
		fmt.Println("\nLayer 2 — no manifest entries yet")
	}
	return 0
}

// ---------- fetch ----------

// cmdFetch materialises named entries. It deliberately has no "fetch everything" default:
// the manifest holds 138,133 skills in one entry and 7,944 in another, so a bare `fetch`
// that pulled all thirteen would be several gigabytes triggered by a command that reads
// like a no-op. Naming what you want is one word of typing and removes the trap.
func cmdFetch(root string, want []string) int {
	manifests, _ := filepath.Glob(filepath.Join(root, "manifest", "*.yaml"))
	cache := filepath.Join(root, "cache")

	var all []manifest.Entry
	rc := 0
	for _, mp := range manifests {
		f, err := manifest.Load(mp)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%s: %v\n", rel(root, mp), err)
			rc = 1
			continue
		}
		all = append(all, f.Entries...)
	}

	if len(want) == 0 {
		fmt.Print("Name the entries to fetch. Available:\n\n")
		fmt.Printf("  %-28s %-16s %-8s %s\n", "ID", "ROLE", "SAMPLES", "LICENSE")
		for _, e := range all {
			fmt.Printf("  %-28s %-16s %-8d %s\n", e.ID, e.Role, e.Malicious+e.Benign, e.License)
		}
		fmt.Println("\n  corpus fetch <id> [<id>...]")
		return 2
	}

	byID := map[string]manifest.Entry{}
	for _, e := range all {
		byID[e.ID] = e
	}
	for _, id := range want {
		e, ok := byID[id]
		if !ok {
			fmt.Fprintf(os.Stderr, "  %-28s no such entry\n", id)
			rc = 1
			continue
		}
		dst, err := fetch.Get(e, cache)
		if err != nil {
			fmt.Fprintf(os.Stderr, "  %-28s FAILED %v\n", e.ID, err)
			rc = 1
			continue
		}
		fmt.Printf("  %-28s %s\n", e.ID, rel(root, dst))
		for _, p := range e.Prep {
			fmt.Printf("  %-28s PREP REQUIRED: %s\n", "", p)
		}
	}
	return rc
}

// ---------- derive ----------

// cmdDerive is a dry run: it reads a fetched upstream, applies its derive rule, and reports
// what coordinates would be produced and where the mapping is incomplete. It writes no
// labels. Turning derived coordinates into on-disk labels — and deciding which get vendored
// into layer 1 versus derived locally from a reference — is a deliberate later step, not a
// side effect of inspecting coverage.
func cmdDerive(root string, want []string) int {
	// --write is opt-in. Reading coverage must never have the side effect of rewriting the
	// corpus, so the dry run is the default and materialising is a thing you ask for.
	write := false
	var args []string
	for _, a := range want {
		if a == "--write" {
			write = true
			continue
		}
		args = append(args, a)
	}
	want = args

	tax, err := taxonomy.Load(filepath.Join(root, "taxonomy"))
	if err != nil {
		fatal(err)
	}
	manifests, _ := filepath.Glob(filepath.Join(root, "manifest", "*.yaml"))
	var all []manifest.Entry
	for _, mp := range manifests {
		f, err := manifest.Load(mp)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%s: %v\n", rel(root, mp), err)
			return 1
		}
		all = append(all, f.Entries...)
	}

	byID := map[string]manifest.Entry{}
	var derivable []string
	for _, e := range all {
		byID[e.ID] = e
		if e.Derive != nil {
			derivable = append(derivable, e.ID)
		}
	}

	if len(want) == 0 {
		sort.Strings(derivable)
		if len(derivable) == 0 {
			fmt.Println("No manifest entry has a derive block yet.")
			return 2
		}
		fmt.Println("Entries with a derive rule:")
		for _, id := range derivable {
			fmt.Printf("  %s\n", id)
		}
		fmt.Println("\n  corpus derive <id>   (the entry must be fetched first)")
		return 2
	}

	rc := 0
	for _, id := range want {
		e, ok := byID[id]
		if !ok {
			fmt.Fprintf(os.Stderr, "%s: no such entry\n", id)
			rc = 1
			continue
		}
		if e.Derive == nil {
			// Most entries have no derive rule and never will — a corpus whose labels a rule
			// cannot reproduce is the normal case here, not an omission.
			fmt.Fprintf(os.Stderr, "%s: has no derive rule — its coordinates cannot be produced "+
				"mechanically. Run `corpus derive` with no argument to list the entries that can.\n", id)
			rc = 1
			continue
		}
		upRoot := filepath.Join(root, "cache", id)
		if _, err := os.Stat(upRoot); err != nil {
			fmt.Fprintf(os.Stderr, "%s: not fetched — run `make fetch E=%q` first\n", id, id)
			rc = 1
			continue
		}

		res, errs := derive.Derive(e, upRoot, tax)
		fmt.Printf("%s — %s\n", id, e.Derive.Fidelity)
		if res != nil {
			reportDerived(tax, res)
		}

		if write && res != nil {
			if len(errs) > 0 {
				// Materialising a derivation that already has problems would write labels whose
				// coordinates we have just been told not to trust.
				fmt.Fprintf(os.Stderr, "  refusing to write: resolve the %d problem(s) below first\n", len(errs))
			} else {
				plans, perrs := derive.PlanMaterialize(e, res)
				errs = append(errs, perrs...)
				if len(perrs) == 0 {
					n, removedStale, werrs := derive.Materialize(root, upRoot, e, plans)
					errs = append(errs, werrs...)
					fmt.Printf("  wrote %d sample(s) into corpus/\n", n)
					if len(removedStale) > 0 {
						fmt.Printf("  removed %d label(s) this entry no longer produces: %s\n",
							len(removedStale), strings.Join(removedStale, ", "))
					}
				}
			}
		}

		if len(errs) > 0 {
			sort.Slice(errs, func(i, j int) bool { return errs[i].Error() < errs[j].Error() })
			fmt.Printf("\n  %d problem(s) — the derivation is not trustworthy until these are resolved:\n", len(errs))
			for _, e := range errs {
				fmt.Printf("    - %v\n", e)
			}
			rc = 1
		}
	}
	return rc
}

// reportDerived prints the dimension x tier grid the derived coordinates land in, plus the
// upstream category tally so a reviewer can see the mapping's coverage rather than trust it.
func reportDerived(tax *taxonomy.Set, res *derive.Result) {
	grid := map[string]map[string]int{}
	byClass := map[string]int{}
	for _, c := range res.Coords {
		byClass[c.Class]++
		for _, d := range c.Dimensions {
			if grid[d] == nil {
				grid[d] = map[string]int{}
			}
			grid[d][c.Tier]++
		}
	}
	fmt.Printf("  %d sample(s): ", len(res.Coords))
	for _, cl := range []string{"malicious", "benign", "hard-negative"} {
		if byClass[cl] > 0 {
			fmt.Printf("%s %d  ", cl, byClass[cl])
		}
	}
	fmt.Println()

	fmt.Printf("    %-16s", "")
	for _, t := range tax.TierOrder {
		fmt.Printf(" %9s", t)
	}
	fmt.Println()
	for _, d := range tax.Dimensions {
		if grid[d] == nil {
			continue
		}
		fmt.Printf("    %-16s", d)
		for _, t := range tax.TierOrder {
			if n := grid[d][t]; n > 0 {
				fmt.Printf(" %9d", n)
			} else {
				fmt.Printf(" %9s", ".")
			}
		}
		fmt.Println()
	}

	// The category tally is the honest counterpart to the grid: it shows what the upstream
	// actually carried, so an over-broad ignore or a lopsided map is visible.
	var cats []string
	for c := range res.CategorySeen {
		cats = append(cats, c)
	}
	sort.Slice(cats, func(i, j int) bool {
		if res.CategorySeen[cats[i]] != res.CategorySeen[cats[j]] {
			return res.CategorySeen[cats[i]] > res.CategorySeen[cats[j]]
		}
		return cats[i] < cats[j]
	})
	// Mechanical and hand-read dimensions are never summed into one "derived" number: one
	// came from the upstream's own field through a stated rule, the other from a person
	// reading the sample because the upstream never recorded what it achieves.
	if res.HandRead > 0 {
		mech := 0
		for _, c := range res.Coords {
			if c.Class == "malicious" && !c.HandReadDimension {
				mech++
			}
		}
		fmt.Printf("  dimension source: %d from the category map, %d hand-read (dimension_overrides)\n",
			mech, res.HandRead)
	}
	fmt.Printf("  upstream categories seen: %d distinct\n", len(cats))
	if res.Excluded > 0 {
		fmt.Printf("  excluded %d sample(s) by exclude_tokens — declared, not quietly dropped\n", res.Excluded)
	}
	if res.Skipped > 0 {
		fmt.Printf("  skipped %d layout match(es) with no upstream label (e.g. compound-chain nodes)\n", res.Skipped)
	}
}

// ---------- helpers ----------

// loadLabels reads every <id>.yaml under corpus/. The label sits BESIDE its sample tree,
// never inside it.
//
// It used to live inside, as _label.yaml, and that silently corrupted every measurement.
// The scanner reads the whole target directory, so each sample was injecting its own
// annotation as evidence. The reverse-shell sample scored 83 with BD-003 apparently caught
// — on the words "textbook reverse shell" in its own note field, while the actual payload
// went undetected. The environ-copy hard negative scored 63 on a high EXFIL-001 whose two
// evidence lines were the label's own `source:` URL and `note:` prose. The contamination
// ran both ways: malicious samples looked better caught than they were, benign samples
// looked like false positives they were not.
func loadLabels(root string) ([]*label.Label, error) {
	dir := filepath.Join(root, "corpus")
	var out []*label.Label
	err := filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		if d.Name() == "_label.yaml" {
			return fmt.Errorf("%s: a label inside the sample tree is scanned as part of the "+
				"sample and injects its own text as evidence — move it beside the tree as "+
				"<id>.yaml", p)
		}
		if filepath.Ext(p) != ".yaml" {
			return nil
		}
		// A label is defined by its POSITION, not by its extension: it sits beside its tree at
		// corpus/<class>/<surface>/<id>.yaml, exactly three components deep. Anything deeper is
		// inside a sample tree and is sample content — real skills ship yaml of their own, and
		// one vendored sample carries a promptfoo config that parsed as a malformed label and
		// failed the whole run. Reading by extension only worked while every sample was ours.
		if r, rerr := filepath.Rel(dir, p); rerr != nil || len(strings.Split(filepath.ToSlash(r), "/")) != 3 {
			return nil
		}
		l, lerr := label.Load(p)
		if lerr != nil {
			return fmt.Errorf("%s: %w", p, lerr)
		}
		// The sample tree is the sibling directory with the same stem.
		l.Path = strings.TrimSuffix(p, ".yaml")
		l.Rel = rel(root, l.Path)
		if fi, serr := os.Stat(l.Path); serr != nil || !fi.IsDir() {
			return fmt.Errorf("%s: no sample tree at %s", p, filepath.Base(l.Path))
		}
		// The directory layout is corpus/<class>/<surface>/, and it is not decoration: the
		// class in the path is what a reader sees first. A label whose class disagrees with
		// its own location files the sample under one heading and counts it under another.
		if err := checkLayout(dir, p, l); err != nil {
			return err
		}
		out = append(out, l)
		return nil
	})
	if err != nil && !os.IsNotExist(err) {
		return nil, err
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func checkLayout(corpusDir, labelPath string, l *label.Label) error {
	r, err := filepath.Rel(corpusDir, labelPath)
	if err != nil {
		return nil
	}
	parts := strings.Split(filepath.ToSlash(r), "/")
	if len(parts) < 3 {
		return fmt.Errorf("%s: expected corpus/<class>/<surface>/<id>.yaml", labelPath)
	}
	if parts[0] != string(l.Class) {
		return fmt.Errorf("%s: label says class %q but it is filed under %q",
			labelPath, l.Class, parts[0])
	}
	// A sample spanning two load paths still lives at one path: its FIRST surface owns the
	// directory. Copying the tree into both would put identical bytes in two samples, and a
	// scanner scored on both would be scored twice on one artifact.
	if parts[1] != l.Surface.Primary() {
		if l.Surface.Has(parts[1]) {
			return fmt.Errorf("%s: label lists surfaces %s and is filed under %q, which is one "+
				"of them but not the first — put the owning surface first so the path is predictable",
				labelPath, l.Surface, parts[1])
		}
		return fmt.Errorf("%s: label says surface %s but it is filed under %q",
			labelPath, l.Surface, parts[1])
	}
	return nil
}

func treeFiles(dir string) ([]string, error) {
	var out []string
	err := filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() {
			r, _ := filepath.Rel(dir, p)
			out = append(out, r)
		}
		return nil
	})
	return out, err
}

func repoRoot() (string, error) {
	d, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for range 6 {
		if _, err := os.Stat(filepath.Join(d, "corpus")); err == nil {
			if _, err := os.Stat(filepath.Join(d, "taxonomy")); err == nil {
				return d, nil
			}
		}
		d = filepath.Dir(d)
	}
	return "", fmt.Errorf("could not find the repository root (no corpus/ and taxonomy/ above the working directory)")
}

func rel(root, p string) string {
	r, err := filepath.Rel(root, p)
	if err != nil {
		return p
	}
	return r
}

func sortedKeys[V any](m map[string]V) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "error:", err)
	os.Exit(2)
}

// addCell records one sample in the dimension x tier grid. A sample with no tier (an
// ordinary benign one) has no cell, which is correct: the axis measures how deeply an
// attack is buried and there is no attack.
func addCell(grid map[string]map[string]int, dimension, tier string) {
	if dimension == "" || tier == "" {
		return
	}
	if grid[dimension] == nil {
		grid[dimension] = map[string]int{}
	}
	grid[dimension][tier]++
}
