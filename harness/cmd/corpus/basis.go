// SPDX-License-Identifier: MIT

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/refute"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// populationOf is the batch a sample came from — where the ARTIFACT originated.
//
// Several checks group by it, and they must group the SAME way or their verdicts are about
// different partitions while looking comparable. It was inlined in the leakage gate until a
// second consumer needed it.
//
// The third case exists because an audit found a 100%-pure feature inside what used to be a
// catch-all bucket: five large reference documents from one upstream sat alongside twelve
// small fixtures written here, and document length alone then separated them. Nothing was
// wrong with the samples; the bucket pooled two batches built by different people for
// different reasons, which is the pooling these checks exist to detect elsewhere.
func populationOf(l *label.Label) string {
	switch {
	case l.Origin.DerivedFrom != nil && l.Origin.DerivedFrom.Entry != "":
		return l.Origin.DerivedFrom.Entry
	case l.Origin.Type == "harvested":
		// One batch by construction: collected by the same script from the same search.
		return "harvested"
	default:
		// A hand-pinned label can still describe somebody else's artifact. When the source
		// names an upstream, that upstream is the batch.
		if repo := originOf(l); repo != "" {
			return repo
		}
		return "hand-written"
	}
}

// reportBasis prints how much of the corpus rests on something per-sample, and returns the
// labels whose basis block is malformed as problems.
//
// The counts are the point. Before this existed, a coordinate a person read off an artifact
// and a coordinate a batch constant supplied were indistinguishable in a label file, and the
// summary line could say "3,494 samples" as though that were 3,494 judgements.
func reportBasis(labels []*label.Label, spec *taxonomy.BasisSpec) []string {
	var problems []string
	for _, l := range labels {
		for _, e := range l.ValidateBasis(spec) {
			problems = append(problems, fmt.Sprintf("%s: %v", l.Rel, e))
		}
		for _, e := range l.VerifyEvidence() {
			problems = append(problems, fmt.Sprintf("%s: %v", l.Rel, e))
		}
	}

	d := label.BasisDebt(labels, spec)
	recorded := d.Total - d.NoBasis
	fmt.Printf("basis       %d of %d label(s) record what their class rests on\n",
		recorded, d.Total)
	if recorded > 0 {
		var parts []string
		for _, id := range spec.Order {
			if n := d.ByBasis[id]; n > 0 {
				parts = append(parts, fmt.Sprintf("%s %d", id, n))
			}
		}
		fmt.Printf("  by basis      %s\n", strings.Join(parts, ", "))
	}
	if d.NoBasis > 0 {
		fmt.Printf("  not recorded  %d — the axis is unscoreable for these until it is stated\n",
			d.NoBasis)
	}
	// Attribution is reported on its own line because it is the axis this whole vocabulary was
	// built to protect, and it moves one located quote at a time. Folding it into the class
	// figure would hide exactly the number worth watching.
	if scoreable, withDim := label.ScoreableOnDimension(labels, spec); withDim > 0 {
		fmt.Printf("  attribution   %d of %d sample(s) with a dimension can be scored on it "+
			"(only `read` qualifies)\n", scoreable, withDim)
	}
	if scoreable, withSev := label.ScoreableOnSeverity(labels, spec); withSev > 0 {
		fmt.Printf("  severity      %d of %d sample(s) with a severity can be scored on it "+
			"(a constant is not a measurement)\n", scoreable, withSev)
	}
	// The explanatory axes, reported because being unscored does not make a wrong value free.
	for _, ax := range []struct {
		name string
		has  func(*label.Label) bool
		get  func(*label.Basis) string
	}{
		{"tier", func(l *label.Label) bool { return l.Truth.Tier != "" },
			func(b *label.Basis) string { return b.Tier }},
		{"evasion", func(l *label.Label) bool { return len(l.Truth.Evasion) > 0 },
			func(b *label.Basis) string { return b.Evasion }},
	} {
		if n, tot := label.ScoreableOnAxis(labels, spec, ax.name, ax.has, ax.get); tot > 0 {
			fmt.Printf("  %-13s %d of %d rest on a reading, not a rule (explanatory, never scored)\n",
				ax.name, n, tot)
		}
	}
	if d.AssumedRisky > 0 {
		// Reported every run, deliberately. A malicious label with no per-sample confirmation
		// asserts an attack nobody has exhibited, and it can sit in a recall denominator for
		// years while a scanner that correctly stays quiet is charged a miss.
		fmt.Printf("  outstanding   %d risky sample(s) whose class rests on a batch constant, "+
			"not on this sample\n", d.AssumedRisky)
	}
	return problems
}

// maxScanBytes caps per-file reading. The corpus holds single files over 1 MB, and the
// patterns below all decide on shape rather than on completeness.
const maxScanBytes = 200 << 10

// refuteSamples reads the sample trees once for every content-level check.
//
// It returns the byte count alongside the samples, and reportRefutation prints it, because
// the first version of this function did not. treeFiles yields paths RELATIVE to the sample
// directory; passing them straight to os.ReadFile resolved them against the process working
// directory, every read failed, the failures were swallowed by a bare `continue`, and the
// check printed "no substring gives a class away" having scanned zero bytes. It was
// confidently reporting a clean result about content it never opened — the exact defect
// this repository keeps finding in its own instrumentation.
//
// Two things stop it recurring: the paths are joined, and the volume is stated. A scan that
// reads nothing can no longer look like a scan that found nothing.
func refuteSamples(labels []*label.Label) (map[string][]refute.Sample, int64, []string) {
	byPop := map[string][]refute.Sample{}
	var scanned int64
	var problems []string

	for _, l := range labels {
		files, err := treeFiles(l.Path)
		if err != nil {
			continue // already reported by the leakage gate's own walk
		}
		var content strings.Builder
		var hashes []string
		for _, rel := range files {
			b, err := readSampleFile(filepath.Join(l.Path, rel))
			if err != nil {
				// Not swallowed. An unreadable file silently shrinks the content a pattern
				// sees, which changes the verdict for a reason unrelated to the corpus.
				problems = append(problems, fmt.Sprintf(
					"%s: cannot read %s for the refutation scan: %v", l.Rel, rel, err))
				continue
			}
			scanned += int64(len(b))
			sum := sha256.Sum256(b)
			hashes = append(hashes, hex.EncodeToString(sum[:]))
			if len(b) > maxScanBytes {
				b = b[:maxScanBytes]
			}
			content.Write(b)
			content.WriteByte('\n')
		}
		pop := populationOf(l)
		byPop[pop] = append(byPop[pop], refute.Sample{
			ID: l.ID, Class: string(l.Class), Content: content.String(), Hashes: hashes,
		})
	}
	return byPop, scanned, problems
}

// reportRefutation runs the content-level checks the structural leakage gate cannot reach.
//
// leakage.go states its own scope in its type: "Contents are deliberately not available
// here — the whole question is what is learnable without them." That is a sound boundary for
// a structural gate and it leaves one blind spot, which is where the only content leak this
// corpus has actually shipped lives.
func reportRefutation(labels []*label.Label, rs *refute.Ruleset, entries []manifest.Entry,
	adj map[string]manifest.Adjudication) []string {
	var problems []string
	for _, e := range rs.Validate() {
		problems = append(problems, fmt.Sprintf("taxonomy/refutation.yaml: %v", e))
	}

	missing, stale := label.RefutationCoverage(labels, rs.Version)
	for _, id := range capList(missing, 3) {
		problems = append(problems, fmt.Sprintf(
			"%s is benign and carries no refutation_search record, so the word means only "+
				"\"collected from a batch we treat as benign\". Run `corpus refute --write`", id))
	}
	if len(missing) > 3 {
		problems = append(problems, fmt.Sprintf("… and %d more benign label(s) with no "+
			"refutation_search record", len(missing)-3))
	}
	for _, id := range capList(stale, 3) {
		problems = append(problems, fmt.Sprintf(
			"%s records a refutation_search from a different ruleset version than v%d. Rates "+
				"measured under two rulesets are not comparable; re-run `corpus refute --write`",
			id, rs.Version))
	}

	byPop, scanned, readProblems := refuteSamples(labels)
	problems = append(problems, readProblems...)
	var all []refute.Sample
	for _, s := range byPop {
		all = append(all, s...)
	}
	if scanned == 0 && len(all) > 0 {
		problems = append(problems, "refutation scan read 0 bytes across a non-empty corpus "+
			"— every pattern below would report clean without having opened anything")
	}

	// Markers are searched WITHIN a population, for the same reason the structural gate is:
	// a feature separating two batches is a fact about the batches, not a giveaway.
	type popMarker struct {
		pop string
		m   refute.Marker
	}
	var markers []popMarker
	for _, pop := range sortedPopulations(byPop) {
		for _, m := range refute.LabelBearingMarkers(byPop[pop], minMarkerSupport, maxMarkerPurity) {
			markers = append(markers, popMarker{pop, m})
		}
	}

	problems = append(problems, checkTransformResidue(entries, byPop)...)

	// Only the benign half is scanned by these three. A malicious sample containing a real
	// credential or a dangling path is the attack working as intended; the question these
	// patterns ask is whether a sample is fit to sit in the FALSE-POSITIVE denominator.
	hits := benignPatternHits(labels)

	dupes := refute.DuplicateOrContained(all)
	// The byte count is printed on purpose: "found nothing" and "opened nothing" have to be
	// distinguishable at a glance, and for one revision of this function they were not.
	fmt.Printf("refutation  ruleset v%d over %d sample(s) in %d population(s), %s scanned\n",
		rs.Version, len(all), len(byPop), humanBytes(scanned))

	if len(markers) == 0 {
		fmt.Printf("  markers       none — no substring gives a class away inside its population\n")
	}
	for _, pm := range markers {
		// An error, not a note. A sample carrying its own label means a scanner can score it
		// without reading it, and any figure computed over that population is then a
		// measurement of grep.
		problems = append(problems, fmt.Sprintf(
			"taxonomy/refutation.yaml label-bearing-marker: in population %q the substring %q "+
				"appears in %d sample(s) and predicts class %q at %.0f%% — the sample carries "+
				"its own answer, so a scanner can score this population without reading any "+
				"content. Strip it under a declared transform, or exclude the population",
			pm.pop, pm.m.Substring, pm.m.Support, pm.m.Class, pm.m.Purity*100))
	}
	if len(dupes) > 0 {
		fmt.Printf("  duplicates    %d sample(s) identical to or contained in another\n", len(dupes))
	}
	for _, pat := range sortedKeys(hits) {
		fmt.Printf("  %-13s %d benign sample(s) matched\n", pat, len(hits[pat]))
	}

	// Every match needs a recorded decision. Without this the patterns would be a report
	// nobody acts on, which is the exact defect this repository keeps finding in its own
	// instrumentation — a check that runs, prints, and changes nothing.
	for _, pat := range sortedKeys(hits) {
		for _, id := range hits[pat] {
			if _, ok := adj[id]; !ok {
				problems = append(problems, fmt.Sprintf(
					"%s matched refutation pattern %q and has no adjudication. Decide whether "+
						"it stays in the denominator or leaves it, and record the reason in "+
						"manifest `adjudications` — most matches should be `keep`, since 39%% "+
						"of benign samples contain something a defensible scanner fires on",
					id, pat))
			}
		}
	}
	for _, id := range sortedKeys(adj) {
		matched := false
		for _, ids := range hits {
			for _, h := range ids {
				if h == id {
					matched = true
				}
			}
		}
		if !matched {
			problems = append(problems, fmt.Sprintf(
				"adjudications[%q] matches nothing — the pattern stopped firing or the sample "+
					"is gone, and a decision about neither is a decision about nothing", id))
		}
	}
	return problems
}

// benignPatternHits runs the per-sample refutation patterns over the benign half.
//
// Reported, not failed. Each of these routes to `adjudicate` or
// `exclude_from_denominator` in taxonomy/refutation.yaml, and both end in a decision a person
// records — an exclusion with no written reason is how a corpus quietly starts flattering
// itself. Failing the build before those decisions exist would just force them to be made in
// a hurry.
func benignPatternHits(labels []*label.Label) map[string][]string {
	out := map[string][]string{}
	for _, l := range labels {
		if l.Class != label.Benign {
			continue
		}
		if refute.NoJudgeableContent(l.Path) {
			out["no-content"] = append(out["no-content"], l.ID)
		}
		files, err := treeFiles(l.Path)
		if err != nil {
			continue
		}
		for _, rel := range files {
			b, err := readSampleFile(filepath.Join(l.Path, rel))
			if err != nil {
				continue
			}
			if len(b) > maxScanBytes {
				b = b[:maxScanBytes]
			}
			body := string(b)
			if len(refute.LiveCredentials(body)) > 0 {
				out["credential"] = append(out["credential"], l.ID)
				break
			}
			if len(refute.HiddenCodepoints(body)) > 0 {
				out["codepoint"] = append(out["codepoint"], l.ID)
				break
			}
		}
	}
	return out
}

// Thresholds match the structural gate's: enough support to be more than an accident, and
// enough purity to be a giveaway.
const (
	minMarkerSupport = 8
	maxMarkerPurity  = 0.95
)

// readSampleFile returns the bytes a scanner would see at path.
//
// For a symlink that is the TARGET PATH, not the target's contents, and the distinction is
// load-bearing rather than defensive. `sg-symlink-escape` is a deliberately dangling link
// pointing at `../../fixtures/escape-target.yaml`: escaping the sample directory IS the
// attack, the target does not exist on purpose, and following the link fails. Treating that
// failure as a read error reported the corpus's own attack as broken instrumentation — and
// resolving the link instead would scan somebody else's file while the payload, which is the
// path string itself, went unexamined.
func readSampleFile(path string) ([]byte, error) {
	fi, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if fi.Mode()&os.ModeSymlink != 0 {
		target, err := os.Readlink(path)
		if err != nil {
			return nil, err
		}
		return []byte(target), nil
	}
	return os.ReadFile(path)
}

// checkTransformResidue verifies that what an entry declares it strips is actually absent.
//
// This exists because the marker scan CANNOT do it. That scan needs support >= 8 before it
// will call a substring a leak, which is right for discovery — every one-off string would
// otherwise be reported — and useless for regression: putting a single canary back into one
// sample produced no finding at all when it was tried.
//
// A declared transform needs no threshold. The pattern is written down, so the correct
// residue count is zero and one occurrence is a failure. The two checks answer different
// questions: the marker scan asks "is something here giving the class away that we have not
// noticed?", this one asks "is the thing we said we removed actually gone?"
func checkTransformResidue(entries []manifest.Entry, byPop map[string][]refute.Sample) []string {
	var problems []string
	for _, e := range entries {
		if e.Derive == nil || len(e.Derive.Transforms) == 0 {
			continue
		}
		samples := byPop[e.ID]
		if len(samples) == 0 {
			continue
		}
		for _, t := range e.Derive.Transforms {
			re, err := regexp.Compile("(?m)" + t.Pattern)
			if err != nil {
				continue // already reported by ValidateTransforms
			}
			var hit []string
			for _, s := range samples {
				if re.MatchString(s.Content) {
					hit = append(hit, s.ID)
				}
			}
			if len(hit) == 0 {
				continue
			}
			shown := hit
			if len(shown) > 3 {
				shown = shown[:3]
			}
			problems = append(problems, fmt.Sprintf(
				"%s: transform %q is declared but its pattern still matches %d vendored "+
					"sample(s) (%s). Either the derivation has not been re-run since the "+
					"declaration, or something reintroduced what it removes",
				e.ID, t.ID, len(hit), strings.Join(shown, ", ")))
		}
	}
	return problems
}

func capList(in []string, n int) []string {
	if len(in) > n {
		return in[:n]
	}
	return in
}

func humanBytes(n int64) string {
	switch {
	case n >= 1<<20:
		return fmt.Sprintf("%.1f MB", float64(n)/(1<<20))
	case n >= 1<<10:
		return fmt.Sprintf("%.0f KB", float64(n)/(1<<10))
	default:
		return fmt.Sprintf("%d B", n)
	}
}

func sortedPopulations(m map[string][]refute.Sample) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
