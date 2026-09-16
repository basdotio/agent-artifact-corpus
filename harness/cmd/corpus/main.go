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
		os.Exit(cmdFetch(root))
	default:
		usage()
		os.Exit(2)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, `corpus <command>

  validate   check every _label.yaml and manifest entry, and run the leakage gate
  stats      corpus composition
  fetch      materialise layer 2 into ./cache (network)`)
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

func cmdFetch(root string) int {
	manifests, _ := filepath.Glob(filepath.Join(root, "manifest", "*.yaml"))
	cache := filepath.Join(root, "cache")
	rc := 0
	for _, mp := range manifests {
		f, err := manifest.Load(mp)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%s: %v\n", rel(root, mp), err)
			rc = 1
			continue
		}
		for _, e := range f.Entries {
			dst, err := fetch.Get(e, cache)
			if err != nil {
				fmt.Fprintf(os.Stderr, "  %-26s FAILED %v\n", e.ID, err)
				rc = 1
				continue
			}
			fmt.Printf("  %-26s %s\n", e.ID, rel(root, dst))
		}
	}
	return rc
}

// ---------- helpers ----------

func loadLabels(dir string) ([]*label.Label, error) {
	var out []*label.Label
	err := filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || d.Name() != "_label.yaml" {
			return nil
		}
		l, lerr := label.Load(p)
		if lerr != nil {
			return fmt.Errorf("%s: %w", p, lerr)
		}
		l.Path = filepath.Dir(p)
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

var ruleIDRE = regexp.MustCompile(`\b([A-Z]{2,10}-[0-9]{3})\b`)

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
