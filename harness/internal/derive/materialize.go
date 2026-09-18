// SPDX-License-Identifier: MIT

package derive

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

// Plan is one upstream sample turned into a layer-1 location and label.
type Plan struct {
	Coord    Coord
	LocalID  string // the label id, e.g. mal-skill-sg-split-across-files
	Dir      string // repo-relative sample tree
	LabelRel string // repo-relative label path
}

// surfaceShort keeps generated ids in the shape the hand-pinned ones already use
// (mal-skill-…, mal-instr-…) rather than inventing a second convention.
var surfaceShort = map[string]string{
	"skills":      "skill",
	"instruction": "instr",
	"hooks":       "hook",
	"permission":  "perm",
	"mcp":         "mcp",
	"connector":   "conn",
}

// PlanMaterialize works out where each derived coordinate would land, without touching disk.
// Collisions are an error rather than a silent overwrite: two upstream samples whose names
// collapse to the same local id would otherwise leave one of them missing from the corpus and
// nothing would say so.
func PlanMaterialize(e manifest.Entry, res *Result) ([]Plan, []error) {
	var errs []error
	d := e.Derive
	if d.Surface == "" || d.IDPrefix == "" {
		return nil, []error{fmt.Errorf("%s: derive.surface and derive.id_prefix are required to materialise", e.ID)}
	}
	short, ok := surfaceShort[d.Surface]
	if !ok {
		return nil, []error{fmt.Errorf("%s: derive.surface %q is not a known surface", e.ID, d.Surface)}
	}

	seen := map[string]string{}
	var plans []Plan
	for _, c := range res.Coords {
		// The tier prefix is stripped from the directory name on purpose. Tier lives in the
		// label; leaving "200-" in the path would put the answer in the filename, which is the
		// shortcut feature this corpus rejects in other people's datasets. Traceability is not
		// lost: derived_from records the full upstream path.
		// The leading-digit strip removes a TIER PREFIX, and only an entry that reads its tier
		// from that prefix has one. Applied to every entry it was identity corruption: the
		// upstream `12306-mcp` (China Railway) became `ben-mcp-am-mcp`, and `2389-research`
		// lost the owner's name. Seven samples, no collisions, provenance intact in
		// origin.source — but the id is what a person cites, and it named the wrong thing.
		upstreamID := c.UpstreamID
		if d.TierFrom == "id-prefix" {
			upstreamID = strings.TrimPrefix(stripTierPrefix(upstreamID), "-")
		}
		name := d.IDPrefix + "-" + upstreamID

		classPrefix := "mal"
		if c.Class == "benign" {
			classPrefix = "ben"
		} else if c.Class == "hard-negative" {
			classPrefix = "hn"
		}
		localID := fmt.Sprintf("%s-%s-%s", classPrefix, short, name)

		if prev, dup := seen[localID]; dup {
			errs = append(errs, fmt.Errorf("%s: %q and %q both become %q — upstream ids collide once the tier prefix is stripped",
				e.ID, prev, c.UpstreamID, localID))
			continue
		}
		seen[localID] = c.UpstreamID

		dir := filepath.Join("corpus", c.Class, d.Surface, name)
		plans = append(plans, Plan{
			Coord:    c,
			LocalID:  localID,
			Dir:      dir,
			LabelRel: dir + ".yaml",
		})
	}
	sort.Slice(plans, func(i, j int) bool { return plans[i].LocalID < plans[j].LocalID })
	return plans, errs
}

// Materialize copies each sample tree into layer 1, writes its derived label beside it, and
// removes labels this entry no longer produces. The removals are returned so a caller can say
// what disappeared rather than letting samples vanish quietly.
//
// It refuses to overwrite a label that is not itself derived. Hand-pinned labels carry
// judgements a rule cannot reproduce, and a re-derivation quietly flattening one would destroy
// the most valuable kind of sample in the corpus.
func Materialize(repoRoot, upRoot string, e manifest.Entry, plans []Plan) (written int, removed []string, errs []error) {
	d := e.Derive
	// Counted across every sample, then reconciled against what the manifest declares. A
	// transform is a change to somebody else's bytes; the count is how a reader confirms the
	// change is the one that was reviewed.
	tCounts := map[string]int{}
	for _, p := range plans {
		absDir := filepath.Join(repoRoot, p.Dir)
		absLabel := filepath.Join(repoRoot, p.LabelRel)

		if existing, err := os.ReadFile(absLabel); err == nil {
			if !strings.Contains(string(existing), "type: derived") {
				errs = append(errs, fmt.Errorf("%s: refusing to overwrite hand-pinned label %s", e.ID, p.LabelRel))
				continue
			}
		}

		src := filepath.Join(upRoot, p.Coord.SamplePath)
		if d.TreeSubdir != "" {
			src = filepath.Join(src, d.TreeSubdir)
		}
		fi, serr := os.Stat(src)
		if serr != nil {
			errs = append(errs, fmt.Errorf("%s/%s: upstream sample %s is missing", e.ID, p.Coord.UpstreamID, src))
			continue
		}
		if fi.IsDir() == d.SampleIsFile {
			errs = append(errs, fmt.Errorf("%s/%s: sample_is_file is %v but %s is not that shape",
				e.ID, p.Coord.UpstreamID, d.SampleIsFile, src))
			continue
		}

		if err := os.RemoveAll(absDir); err != nil {
			errs = append(errs, fmt.Errorf("%s: clear %s: %w", e.ID, p.Dir, err))
			continue
		}
		// A file-shaped sample becomes a directory holding that one file, because `entry: .`
		// points a scanner at a directory and every other sample in the corpus is one.
		if d.SampleIsFile {
			if err := os.MkdirAll(absDir, 0o755); err != nil {
				errs = append(errs, fmt.Errorf("%s: create %s: %w", e.ID, p.Dir, err))
				continue
			}
			if err := copyFile(src, filepath.Join(absDir, filepath.Base(src)), d.Transforms, tCounts); err != nil {
				errs = append(errs, fmt.Errorf("%s: copy %s: %w", e.ID, p.Dir, err))
				continue
			}
		} else if err := copyTree(src, absDir, d.Transforms, tCounts); err != nil {
			errs = append(errs, fmt.Errorf("%s: copy %s: %w", e.ID, p.Dir, err))
			continue
		}
		if err := os.WriteFile(absLabel, []byte(renderLabel(e, p, absDir)), 0o644); err != nil {
			errs = append(errs, fmt.Errorf("%s: write %s: %w", e.ID, p.LabelRel, err))
			continue
		}
		written++
	}
	// Reconciliation. A sample dropped from the derivation — by exclude_samples, by an upstream
	// that no longer ships it, or by a layout change — leaves its label and tree behind unless
	// something removes them. Without this, an exclusion is a statement the corpus contradicts:
	// `derive` reports the sample as excluded while `validate` goes on counting it.
	//
	// Only labels belonging to THIS entry and carrying `type: derived` are touched. A
	// hand-pinned label, or one derived from a different upstream, is never in scope.
	keep := map[string]bool{}
	for _, p := range plans {
		keep[filepath.Join(repoRoot, p.LabelRel)] = true
	}
	for _, class := range []string{"malicious", "benign", "hard-negative"} {
		dir := filepath.Join(repoRoot, "corpus", class, d.Surface)
		labels, _ := filepath.Glob(filepath.Join(dir, "*.yaml"))
		for _, lab := range labels {
			if keep[lab] {
				continue
			}
			b, err := os.ReadFile(lab)
			if err != nil || !strings.Contains(string(b), "type: derived") {
				continue
			}
			if !strings.Contains(string(b), "entry: "+e.ID+"\n") {
				continue
			}
			tree := strings.TrimSuffix(lab, ".yaml")
			if err := os.RemoveAll(tree); err != nil {
				errs = append(errs, fmt.Errorf("%s: remove stale tree %s: %w", e.ID, tree, err))
				continue
			}
			if err := os.Remove(lab); err != nil {
				errs = append(errs, fmt.Errorf("%s: remove stale label %s: %w", e.ID, lab, err))
				continue
			}
			removed = append(removed, filepath.Base(tree))
		}
	}
	// Reconciled only after every sample has been through, because the declaration is about
	// the entry as a whole. Checking per sample would report 74 separate failures for one
	// upstream that grew by a sample.
	errs = append(errs, checkTransformCounts(e.ID, d.Transforms, tCounts)...)
	return written, removed, errs
}

// renderLabel writes the label by hand rather than marshalling the struct, so the generated
// file reads like the hand-written ones and can carry the comments that explain what a derived
// coordinate is worth.
func renderLabel(e manifest.Entry, p Plan, treeDir string) string {
	c := p.Coord
	var b strings.Builder
	fmt.Fprintf(&b, "# Generated by `corpus derive %s --write`. Do not hand-edit:\n", e.ID)
	fmt.Fprintf(&b, "# a re-derivation overwrites this file. To correct a coordinate, fix the\n")
	fmt.Fprintf(&b, "# derive rule in manifest/corpora.yaml and re-run.\n")
	fmt.Fprintf(&b, "id: %s\n", p.LocalID)
	fmt.Fprintf(&b, "class: %s\n", c.Class)
	fmt.Fprintf(&b, "surface: %s\n", e.Derive.Surface)
	fmt.Fprintf(&b, "kind: skill\n")
	fmt.Fprintf(&b, "entry: .\n\n")

	fmt.Fprintf(&b, "origin:\n")
	fmt.Fprintf(&b, "  type: derived\n")
	src := fmt.Sprintf("%s @ %s", e.URL, short12(e.Commit))
	if c.Source != "" {
		// The originating repository, not the collection that pinned it. A false positive rate
		// has to be reported per source, and that is impossible if every sample names the
		// aggregator instead of where it actually came from.
		src = fmt.Sprintf("https://github.com/%s (via %s @ %s)", c.Source, e.ID, short12(e.Commit))
	}
	fmt.Fprintf(&b, "  source: %q\n", src)
	fmt.Fprintf(&b, "  license: %s\n", e.License)
	// An entry with `label_file: ""` has NO per-sample upstream label, so its class and
	// severity are constants this repository asserts. 163 labels — every cisco and skillcraft
	// one — used to say "coordinates derived from the upstream's own labels" regardless, and
	// carried a `derived_from.fidelity` string byte-identical to skillsgoat's. A reader
	// inspecting one label could not tell a severity READ from an upstream field from a
	// severity ASSERTED here. The entry-level fidelity block was honest about it; that honesty
	// did not travel with the label, and the label is what a consumer reads.
	hasUpstreamLabels := e.Derive.LabelFile == nil || *e.Derive.LabelFile != ""
	note := "coordinates derived from the upstream's own labels; the artifact is vendored unchanged"
	if !hasUpstreamLabels {
		note = "the upstream ships no per-sample label, so class and severity are CONSTANTS this " +
			"repository asserts rather than values it read; tier and dimension come from the " +
			"category map. The artifact is vendored unchanged"
	}
	if c.HandReadDimension {
		note = "dimension hand-read from the sample because the upstream labels this by technique only; other axes derived"
	}
	if c.Class == "benign" {
		note = e.Derive.BenignNote
		if note == "" {
			note = "upstream benign; this entry does not state what that label was based on"
		}
	}
	// A declared transform makes "vendored unchanged" false, and the label is what a consumer
	// actually reads. An audit already found 163 labels carrying a fidelity string that
	// described a different entry entirely; a note that survives a change to the bytes it
	// describes is that same defect with a shorter fuse.
	if len(e.Derive.Transforms) > 0 {
		note = strings.TrimRight(strings.TrimSpace(
			strings.ReplaceAll(note, "; the artifact is vendored unchanged", "")), ";. ")
		note = strings.TrimRight(strings.TrimSpace(
			strings.ReplaceAll(note, "The artifact is vendored unchanged", "")), ";. ")
		ids := make([]string, 0, len(e.Derive.Transforms))
		for _, t := range e.Derive.Transforms {
			ids = append(ids, t.ID)
		}
		note += fmt.Sprintf("; the artifact is vendored with %s applied, declared in the manifest",
			strings.Join(ids, " and "))
	}
	fmt.Fprintf(&b, "  note: %q\n", note)
	fmt.Fprintf(&b, "  added: %s\n", time.Now().Format("2006-01-02"))
	// Derived coordinates come from an upstream label through a stated rule, not from running
	// a scanner, so there is no run whose result could have leaked into the answer.
	fmt.Fprintf(&b, "  labeled_before_run: false\n")
	fmt.Fprintf(&b, "  derived_from:\n")
	fmt.Fprintf(&b, "    entry: %s\n", e.ID)
	fmt.Fprintf(&b, "    sample: %s\n", filepath.ToSlash(c.SamplePath))
	// The per-sample fidelity has to describe THIS sample's derivation, not the entry's
	// general shape. Telling a benign sample it came through a category map when the entry has
	// none, and when benign labels carry no dimension or evasion at all, is the same defect as
	// an unearned coordinate: a claim about provenance that the data does not support.
	fid := "tier, severity and class mechanical; dimension and evasion via the category map"
	if !hasUpstreamLabels {
		fid = "class and severity are constants this entry asserts, NOT values read from an " +
			"upstream label; tier and dimension come from the category map"
	}
	switch {
	case c.Class == "benign":
		fid = "class is a constant and benign labels carry no coordinates, so nothing is mapped; " +
			"the judgement is in this entry's sampling design"
	case c.HandReadDimension:
		fid = "tier, severity and class mechanical; dimension hand-read into dimension_overrides"
	}
	fmt.Fprintf(&b, "    fidelity: %q\n", fid)

	// What each axis rests on, generated from the same rules that produced the coordinates.
	// It sits between origin and truth because that is the order of the three questions: where
	// the sample came from, how we know, and what it is.
	//
	// Outside the malicious branch on purpose. A benign sample has no truth block at all, and
	// it is the one that most needs this: 3,231 of them rest on "collected from a batch we
	// treat as benign" and nothing recorded that.
	if bb := basisBlock(e, c); bb != "" {
		fmt.Fprintf(&b, "\n%s", bb)
	}

	// Only the benign half. A malicious sample's class rests on evidence of what it does; the
	// refutation ruleset asks the opposite question — was anything looked for before the word
	// "benign" was written — and that question has no meaning for a sample labelled by what
	// was found in it.
	if c.Class == "benign" && treeDir != "" {
		fmt.Fprintf(&b, "\n%s", RefutationBlock(treeDir, refutationRulesetVersion))
	}

	if c.Class == "malicious" {
		fmt.Fprintf(&b, "\ntruth:\n")
		fmt.Fprintf(&b, "  dimensions: [%s]\n", strings.Join(c.Dimensions, ", "))
		fmt.Fprintf(&b, "  severity: %s\n", c.Severity)
		fmt.Fprintf(&b, "  tier: %s\n", c.Tier)
		fmt.Fprintf(&b, "  evasion: [%s]\n", strings.Join(c.Evasion, ", "))
	}
	return b.String()
}

func stripTierPrefix(id string) string {
	if tok := prefixToken(id); tok != "" {
		return id[len(tok):]
	}
	return id
}

func short12(s string) string {
	if len(s) > 12 {
		return s[:12]
	}
	return s
}

// copyFile copies one file, applying the declared transforms on the way through.
//
// It reads the whole file rather than streaming it. The transforms are line-oriented and a
// marker can sit anywhere, so there is no window size that would be correct; the largest
// single artifact in the corpus is a few megabytes and correctness is worth the memory.
func copyFile(src, dst string, ts []manifest.Transform, counts map[string]int) error {
	b, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	out, applied, err := applyTransforms(b, ts)
	if err != nil {
		return err
	}
	for id, n := range applied {
		counts[id] += n
	}
	return os.WriteFile(dst, out, 0o644)
}

// target2 is just the destination path; named so the symlink branch reads in one line.
func target2(_, dst, rel string) string { return filepath.Join(dst, rel) }

// copyTree copies the artifact, applying the entry's declared transforms to text files
// and counting each application into counts.
func copyTree(src, dst string, ts []manifest.Transform, counts map[string]int) error {
	// filepath.Walk uses Lstat, so a symlink arrives as a symlink rather than as its target.
	return filepath.Walk(src, func(p string, fi os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, p)
		if err != nil {
			return err
		}
		target := filepath.Join(dst, rel)
		if fi.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		if fi.Mode()&os.ModeSymlink != 0 {
			// Symlinks ARE copied, as links, and this reversed an earlier decision. The old
			// rule dropped every non-regular file on the reasoning that copying one imports a
			// filesystem hazard we did not choose — true in general, and false for exactly the
			// sample that proved it: skillsgoat's `200-symlink-escape` IS a symlink escaping
			// its own directory, and vendoring it without the link left a 230-byte SKILL.md
			// telling the agent to read a file that no longer exists. The sample sat in the
			// malicious recall denominator carrying no attack at all, and its label said "the
			// artifact is vendored unchanged".
			//
			// Copying the link is safe and faithful: git stores the link text, the target is
			// outside the tree so it dangles, and a dangling symlink escaping a skill
			// directory is precisely the artifact a scanner is supposed to notice.
			target, rerr := os.Readlink(p)
			if rerr != nil {
				return rerr
			}
			if err := os.MkdirAll(filepath.Dir(target2(target, dst, rel)), 0o755); err != nil {
				return err
			}
			return os.Symlink(target, filepath.Join(dst, rel))
		}
		if !fi.Mode().IsRegular() {
			// Sockets, devices, fifos. These are not corpus content and nothing upstream ships
			// them; importing one would be a filesystem hazard we did not choose.
			return nil
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return err
		}
		return copyFile(p, target, ts, counts)
	})
}
