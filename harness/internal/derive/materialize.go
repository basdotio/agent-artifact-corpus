// SPDX-License-Identifier: MIT

package derive

import (
	"fmt"
	"io"
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
		name := d.IDPrefix + "-" + strings.TrimPrefix(stripTierPrefix(c.UpstreamID), "-")

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
			if err := copyFile(src, filepath.Join(absDir, filepath.Base(src))); err != nil {
				errs = append(errs, fmt.Errorf("%s: copy %s: %w", e.ID, p.Dir, err))
				continue
			}
		} else if err := copyTree(src, absDir); err != nil {
			errs = append(errs, fmt.Errorf("%s: copy %s: %w", e.ID, p.Dir, err))
			continue
		}
		if err := os.WriteFile(absLabel, []byte(renderLabel(e, p)), 0o644); err != nil {
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
	return written, removed, errs
}

// renderLabel writes the label by hand rather than marshalling the struct, so the generated
// file reads like the hand-written ones and can carry the comments that explain what a derived
// coordinate is worth.
func renderLabel(e manifest.Entry, p Plan) string {
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
	note := "coordinates derived from the upstream's own labels; the artifact is vendored unchanged"
	if c.HandReadDimension {
		note = "dimension hand-read from the sample because the upstream labels this by technique only; other axes derived"
	}
	if c.Class == "benign" {
		note = e.Derive.BenignNote
		if note == "" {
			note = "upstream benign; this entry does not state what that label was based on"
		}
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
	switch {
	case c.Class == "benign":
		fid = "class is a constant and benign labels carry no coordinates, so nothing is mapped; " +
			"the judgement is in this entry's sampling design"
	case c.HandReadDimension:
		fid = "tier, severity and class mechanical; dimension hand-read into dimension_overrides"
	}
	fmt.Fprintf(&b, "    fidelity: %q\n", fid)

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

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}

func copyTree(src, dst string) error {
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
		if !fi.Mode().IsRegular() {
			// Non-regular files are not corpus content and copying them would import a
			// filesystem-level hazard we did not choose.
			return nil
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return err
		}
		in, err := os.Open(p)
		if err != nil {
			return err
		}
		defer in.Close()
		out, err := os.Create(target)
		if err != nil {
			return err
		}
		defer out.Close()
		_, err = io.Copy(out, in)
		return err
	})
}
