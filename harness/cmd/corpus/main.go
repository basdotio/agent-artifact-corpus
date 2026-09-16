// SPDX-License-Identifier: MIT

// Command corpus validates and summarises the corpus.
//
// It deliberately does not score anything. Running aguard over the corpus belongs in the
// tool repository, where the scanner lives and where a drift gate can compare a generated
// report against a committed one. This repository owns the samples and the rules about
// them, and keeping the scorer out means the corpus can be validated with no build of the
// tool present.
package main

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"github.com/basdotio/agent-guard-corpus/harness/internal/fetch"
	"github.com/basdotio/agent-guard-corpus/harness/internal/label"
	"github.com/basdotio/agent-guard-corpus/harness/internal/leakage"
	"github.com/basdotio/agent-guard-corpus/harness/internal/manifest"
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
	default:
		usage()
		os.Exit(2)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, `corpus <command>

  validate   check every _label.yaml and manifest entry, and run the leakage gate
  stats      corpus composition
  fetch      materialise named layer-2 entries into ./cache (network)`)
}

// ---------- validate ----------

func cmdValidate(root string) int {
	labels, err := loadLabels(filepath.Join(root, "corpus"))
	if err != nil {
		fatal(err)
	}

	var problems []string
	for _, l := range labels {
		for _, e := range l.Validate() {
			problems = append(problems, fmt.Sprintf("%s: %v", rel(root, l.Path), e))
		}
	}

	known, ruleSrc := knownRules(root)
	for _, e := range label.ValidateSet(labels, known) {
		problems = append(problems, e.Error())
	}

	// Layer 2
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
	}

	// Leakage gate
	var samples []leakage.Sample
	for _, l := range labels {
		files, _ := treeFiles(l.Path)
		samples = append(samples, leakage.Sample{ID: l.ID, Class: string(l.Class), Files: files})
	}
	leaks := leakage.Check(samples)

	fmt.Printf("labels    %d\n", len(labels))
	if len(known) > 0 {
		fmt.Printf("rule ids  %d known (from %s)\n", len(known), ruleSrc)
	} else {
		fmt.Printf("rule ids  not checked — no generated rules.md found; see -h\n")
	}

	for _, f := range leaks {
		problems = append(problems, fmt.Sprintf(
			"leakage: %q appears in %d samples and %d of them are %s (%.0f%% pure) — "+
				"a classifier can separate the classes without reading content",
			f.Name, f.Total, f.With, f.Class, f.Purity()*100))
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
	labels, err := loadLabels(filepath.Join(root, "corpus"))
	if err != nil {
		fatal(err)
	}
	byClass := map[string]int{}
	bySurface := map[string]map[string]int{}
	byOrigin := map[string]int{}
	gaps, oos := 0, 0
	for _, l := range labels {
		byClass[string(l.Class)]++
		if bySurface[l.Surface] == nil {
			bySurface[l.Surface] = map[string]int{}
		}
		bySurface[l.Surface][string(l.Class)]++
		byOrigin[l.Origin.Type]++
		if l.KnownGap != nil {
			gaps++
		}
		if l.OutOfScope != "" {
			oos++
		}
	}

	fmt.Println("Layer 1 — vendored")
	fmt.Printf("  samples          %d\n", len(labels))
	for _, c := range []string{"malicious", "benign", "hard-negative"} {
		fmt.Printf("    %-14s %d\n", c, byClass[c])
	}
	fmt.Println("  by surface")
	var surfaces []string
	for s := range bySurface {
		surfaces = append(surfaces, s)
	}
	sort.Strings(surfaces)
	for _, s := range surfaces {
		m := bySurface[s]
		fmt.Printf("    %-14s mal %-4d ben %-4d hard-neg %d\n", s, m["malicious"], m["benign"], m["hard-negative"])
	}
	fmt.Println("  by origin")
	for _, o := range []string{"real-world", "promoted", "reconstruction", "synthetic"} {
		if byOrigin[o] > 0 {
			fmt.Printf("    %-14s %d\n", o, byOrigin[o])
		}
	}
	// These two are printed always, including as zero. A count that only appears when
	// non-zero reads as "none exist" when the real state is "nobody looked".
	fmt.Printf("  known gaps       %d  (expected failures, attributed to a work item)\n", gaps)
	fmt.Printf("  out of scope     %d  (malicious but out of this tool's stated reach)\n", oos)

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
			fmt.Printf("  %-26s %-16s mal %-6d ben %-7d %-14s %s\n",
				e.ID, e.Role, e.Malicious, e.Benign, e.License, v)
			total++
		}
		groups := f.PoolableGroups()
		var overlapping [][]string
		for _, g := range groups {
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
		fmt.Println("Name the entries to fetch. Available:\n")
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
func loadLabels(dir string) ([]*label.Label, error) {
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
		l, lerr := label.Load(p)
		if lerr != nil {
			return fmt.Errorf("%s: %w", p, lerr)
		}
		// The sample tree is the sibling directory with the same stem.
		l.Path = strings.TrimSuffix(p, ".yaml")
		if fi, serr := os.Stat(l.Path); serr != nil || !fi.IsDir() {
			return fmt.Errorf("%s: no sample tree at %s", p, filepath.Base(l.Path))
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

// ruleIDRE matches the tool's rule IDs. The suffix is NOT always numeric: REP-GOOD
// (dimension 0) and REP-BAD (dimension 3, scoring) are reputation verdicts. A digits-only
// pattern finds 71 of the 73 IDs and then rejects any label citing those two as "not a rule
// the tool can emit" — a validator confidently wrong about the thing it validates.
var ruleIDRE = regexp.MustCompile(`\b([A-Z]{2,10}-[A-Z0-9]{3,4})\b`)

// knownRules reads the tool's generated rule reference so that a renamed or retired rule
// turns the corpus red instead of silently never matching. It is optional: this repository
// must validate with no checkout of the tool present, so a missing reference downgrades to
// "not checked" and says so, rather than silently passing everything.
func knownRules(root string) (map[string]bool, string) {
	candidates := []string{
		os.Getenv("AGUARD_RULES_MD"),
		filepath.Join(root, "..", "agent-guard", "docs", "rules.md"),
	}
	for _, c := range candidates {
		if c == "" {
			continue
		}
		b, err := os.ReadFile(c)
		if err != nil {
			continue
		}
		out := map[string]bool{}
		for _, m := range ruleIDRE.FindAllStringSubmatch(string(b), -1) {
			out[m[1]] = true
		}
		if len(out) > 0 {
			return out, filepath.Clean(c)
		}
	}
	return nil, ""
}

func repoRoot() (string, error) {
	d, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for i := 0; i < 6; i++ {
		if _, err := os.Stat(filepath.Join(d, "corpus")); err == nil {
			return d, nil
		}
		d = filepath.Dir(d)
	}
	return "", fmt.Errorf("could not find the repository root (no corpus/ above the working directory)")
}

func rel(root, p string) string {
	r, err := filepath.Rel(root, p)
	if err != nil {
		return p
	}
	return r
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "error:", err)
	os.Exit(2)
}
