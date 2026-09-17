// SPDX-License-Identifier: MIT

// Package taxonomy loads the tool-neutral vocabulary a label draws on: the three axes a
// sample is placed on, and the scanners that may carry rule-level expectations about it.
//
// The split this package exists to serve: `truth` in a label is written in this vocabulary
// and belongs to nobody, while `expect.<tool>` is written in one scanner's rule ids and
// belongs to that scanner. Before the split there was only the second kind, so every
// assertion in the corpus was phrased in one product's vocabulary and the corpus could not
// describe a sample to anyone who had not built that product.
package taxonomy

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// Tier is how deeply an attack is buried. The slice order in techniques.yaml is the order:
// later is harder.
type Tier struct {
	ID     string `yaml:"id"`
	MapsTo string `yaml:"maps_to"`
	What   string `yaml:"what"`
	Rank   int    `yaml:"-"`
	// Calibration marks the level every scanner must catch. A miss there is a property
	// failure rather than a low score: it says the scanner is broken, not weak, and the two
	// must never land in the same number.
	Calibration bool `yaml:"calibration"`
}

// Evasion is one mechanism that does the burying. Closed vocabulary: an open field degrades
// into free text, and free text cannot be aggregated, which defeats the only reason the axis
// exists.
type Evasion struct {
	ID          string `yaml:"id"`
	ImpliesTier string `yaml:"implies_tier"`
	What        string `yaml:"what"`
}

type Technique struct {
	ID        string `yaml:"id"`
	Title     string `yaml:"title"`
	Dimension string `yaml:"dimension"`
	What      string `yaml:"what"`

	// BenignLookalike is the discrimination test in prose: what an honest artifact with the
	// same surface shape looks like, and which element actually separates them.
	BenignLookalike string `yaml:"benign_lookalike"`
}

// RulesSource locates a tool's generated rule reference. Both fields are optional: a tool
// with no reachable reference downgrades to "not checked" and says so.
type RulesSource struct {
	Env  string `yaml:"env"`
	Path string `yaml:"path"` // relative to the repository root
}

type Tool struct {
	ID   string `yaml:"id"`
	Name string `yaml:"name"`
	URL  string `yaml:"url"`

	SeverityLadder []string    `yaml:"severity_ladder"`
	RuleIDPattern  string      `yaml:"rule_id_pattern"`
	SectionPattern string      `yaml:"section_pattern"`
	RulesSource    RulesSource `yaml:"rules_source"`
	NativeFormat   string      `yaml:"native_format"`

	// DimensionMap translates this tool's own finding categories into our dimensions, keyed
	// on the section name in its generated reference. A nil value means the category maps to
	// no dimension of ours, which is a real outcome and not a gap: a scanner whose only
	// finding on a wrapped reverse shell is "Obfuscation" detected that something was hidden,
	// not that there was a backdoor.
	DimensionMap map[string]*string `yaml:"dimension_map"`
}

// HasSeverity reports whether s is on this tool's ladder.
func (t Tool) HasSeverity(s string) bool { return slices.Contains(t.SeverityLadder, s) }

type techniqueFile struct {
	Dimensions []string    `yaml:"dimensions"`
	Tiers      []Tier      `yaml:"tiers"`
	Evasion    []Evasion   `yaml:"evasion"`
	Techniques []Technique `yaml:"techniques"`
}

type toolFile struct {
	Tools []Tool `yaml:"tools"`
}

// Set is the loaded vocabulary.
type Set struct {
	Dimensions []string
	TierOrder  []string // ordinal, easiest first
	Tiers      map[string]Tier
	Evasions   map[string]Evasion
	Techniques map[string]Technique
	Tools      map[string]Tool
}

// Load reads taxonomy/techniques.yaml and taxonomy/tools.yaml from dir.
func Load(dir string) (*Set, error) {
	var tf techniqueFile
	if err := decodeFile(filepath.Join(dir, "techniques.yaml"), &tf); err != nil {
		return nil, err
	}
	var lf toolFile
	if err := decodeFile(filepath.Join(dir, "tools.yaml"), &lf); err != nil {
		return nil, err
	}

	s := &Set{
		Dimensions: tf.Dimensions,
		Tiers:      map[string]Tier{},
		Evasions:   map[string]Evasion{},
		Techniques: map[string]Technique{},
		Tools:      map[string]Tool{},
	}
	for i, t := range tf.Tiers {
		t.Rank = i
		s.Tiers[t.ID] = t
		s.TierOrder = append(s.TierOrder, t.ID)
	}
	for _, e := range tf.Evasion {
		s.Evasions[e.ID] = e
	}
	for _, t := range tf.Techniques {
		s.Techniques[t.ID] = t
	}
	for _, t := range lf.Tools {
		s.Tools[t.ID] = t
	}
	return s, nil
}

func decodeFile(path string, into any) error {
	b, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read taxonomy: %w", err)
	}
	dec := yaml.NewDecoder(strings.NewReader(string(b)))
	dec.KnownFields(true) // a typo'd field is a silently ignored definition
	if err := dec.Decode(into); err != nil {
		return fmt.Errorf("parse %s: %w", filepath.Base(path), err)
	}
	return nil
}

// Validate checks the vocabulary itself. It is small and it is still worth checking: a
// technique with a misspelled dimension silently creates a one-member recall axis, and a
// recall axis with one sample in it reads as full coverage of that axis.
func (s *Set) Validate() []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	dims := map[string]bool{}
	for _, d := range s.Dimensions {
		if dims[d] {
			bad("dimension %q is listed twice", d)
		}
		dims[d] = true
	}
	if len(dims) == 0 {
		bad("techniques.yaml declares no dimensions")
	}
	if dims["obfuscation"] {
		bad("`obfuscation` is a dimension, but it describes how an attack hides rather than " +
			"what it achieves. On one axis with the rest, a sample is either a backdoor or " +
			"obfuscated and never both, so the question \"does this scanner handle an " +
			"obfuscated backdoor\" becomes inexpressible. It belongs on the tier/evasion axes")
	}

	if len(s.TierOrder) == 0 {
		bad("techniques.yaml declares no tiers — without them every sample is equally deep " +
			"and a miss cannot be attributed to literal matching")
	}
	calib := 0
	for _, id := range s.TierOrder {
		t := s.Tiers[id]
		if t.What == "" {
			bad("tier %s has no `what`", id)
		}
		if t.MapsTo == "" {
			bad("tier %s has no `maps_to` — using our own words costs the ability to "+
				"cross-reference the published figures of corpora numbered on the same "+
				"scale, and this field is what buys it back", id)
		}
		if t.Calibration {
			calib++
		}
	}
	if calib != 1 {
		bad("exactly one tier must carry `calibration: true`; %d do. It marks the level where "+
			"a miss means broken rather than weak, and that reading only works if there is "+
			"one such level", calib)
	}

	for _, id := range sortedKeys(s.Evasions) {
		e := s.Evasions[id]
		if e.What == "" {
			bad("evasion %s has no `what`", id)
		}
		if _, ok := s.Tiers[e.ImpliesTier]; !ok {
			bad("evasion %s implies tier %q, which is not a tier", id, e.ImpliesTier)
		}
		if s.Tiers[e.ImpliesTier].Calibration {
			bad("evasion %s implies the calibration tier, but that tier means nothing hides "+
				"the attack. A mechanism cannot imply the absence of a mechanism", id)
		}
	}

	for _, id := range sortedKeys(s.Techniques) {
		t := s.Techniques[id]
		if t.Title == "" {
			bad("technique %s has no title", t.ID)
		}
		if t.What == "" {
			bad("technique %s has no `what` — a name without a definition is not a shared "+
				"vocabulary, it is a label only its author can read", t.ID)
		}
		if !dims[t.Dimension] {
			bad("technique %s has dimension %q, which is not in the dimensions list", t.ID, t.Dimension)
		}
		if t.BenignLookalike == "" {
			bad("technique %s has no `benign_lookalike` — every technique in this corpus needs "+
				"one, because a hard negative is defined as the lookalike and there is no way "+
				"to write the pair without saying what the two differ by", t.ID)
		}
	}

	for _, id := range sortedKeys(s.Tools) {
		t := s.Tools[id]
		if t.Name == "" {
			bad("tool %s has no name", t.ID)
		}
		if len(t.SeverityLadder) == 0 {
			bad("tool %s declares no severity_ladder — expectation bounds in a label are "+
				"checked against it, so without one every bound is unvalidated", t.ID)
		}
		// A rules_source.path must stay INSIDE this repository, and this check exists because
		// one did not. aguard's was `../agent-guard/docs/rules.md`, a sibling of the corpus on
		// one particular machine. The effect was not a broken build — it was worse: on that
		// machine `make validate` reported "73 ids, 56 carry a dimension", and everywhere else
		// in the world it reported "not checked" and stayed green. The corpus's own validation
		// result depended on the author's directory layout.
		//
		// A scanner's rule list belongs to that scanner. Pointing at a checkout of it from
		// here makes a tool-neutral corpus's output conditional on having that tool, which is
		// the one property this repository is built to refuse. Use `env` instead: then the
		// extra check is opt-in, visibly so, and the default is identical for everyone.
		if p := t.RulesSource.Path; p != "" {
			if filepath.IsAbs(p) || strings.HasPrefix(filepath.ToSlash(filepath.Clean(p)), "../") {
				bad("tool %s: rules_source.path %q leaves this repository. A path outside it "+
					"makes `make validate` report one thing on the machine that has the "+
					"scanner checked out and another thing everywhere else, so the corpus "+
					"would validate differently per machine. Use rules_source.env for a local "+
					"checkout, and let the scanner's own repository verify its rule ids", t.ID, p)
			}
		}

		for _, pat := range []struct{ name, expr string }{
			{"rule_id_pattern", t.RuleIDPattern},
			{"section_pattern", t.SectionPattern},
		} {
			if pat.expr == "" {
				continue
			}
			if _, err := regexp.Compile(pat.expr); err != nil {
				bad("tool %s: %s does not compile: %v", t.ID, pat.name, err)
			}
		}
		for section, dim := range t.DimensionMap {
			if dim == nil {
				continue // deliberately unmapped, which is a result and not a gap
			}
			if !dims[*dim] {
				bad("tool %s: dimension_map sends %q to %q, which is not one of our dimensions",
					t.ID, section, *dim)
			}
		}
	}
	return errs
}

// TierByMapsToken finds the tier whose maps_to lists the given upstream token (e.g. "000").
// A derivation reads tier from an upstream id prefix without restating the mapping: it is
// already declared in each tier's maps_to ("skillsgoat / cisco 000"), so the one place the
// correspondence lives is the vocabulary, not a second table in the derive rule.
func (s *Set) TierByMapsToken(token string) (Tier, bool) {
	for _, id := range s.TierOrder {
		if slices.Contains(strings.Fields(s.Tiers[id].MapsTo), token) {
			return s.Tiers[id], true
		}
	}
	return Tier{}, false
}

// TierAtLeast reports whether tier a is at least as deep as tier b. Unknown tiers are not
// comparable and answer false, so a typo fails the bound rather than passing it.
func (s *Set) TierAtLeast(a, b string) bool {
	ta, oka := s.Tiers[a]
	tb, okb := s.Tiers[b]
	if !oka || !okb {
		return false
	}
	return ta.Rank >= tb.Rank
}

// Dimension returns the recall axis a technique sits on.
func (s *Set) Dimension(techniqueID string) string {
	return s.Techniques[techniqueID].Dimension
}

// RuleIndex is what a tool's generated reference yields: every rule id it can emit, and the
// dimension of ours that a finding on that rule attributes to. A nil entry means the rule
// maps to no dimension of ours — the tool found something but did not say what kind, which
// is measurement part 2 failing while part 1 passes.
type RuleIndex struct {
	Source    string
	Dimension map[string]*string

	// Unmapped names sections that DEFINE at least one rule and have no dimension_map entry.
	// A section mapped to null is a decision; one missing from the map is an oversight, and
	// the two must not look alike.
	//
	// "Define" means the rule's first occurrence. AgentGuard's reference ends with a prose
	// section listing what it does not cover, which mentions `SUP-004` and `COV-000` — both
	// defined earlier. Counting mentions reported that section as an unmapped category,
	// which is the check crying wolf about its own document's prose.
	Unmapped []string
}

// Has reports whether the tool can emit this rule id.
func (r *RuleIndex) Has(id string) bool {
	if r == nil {
		return false
	}
	_, ok := r.Dimension[id]
	return ok
}

// Len is the number of rule ids read.
func (r *RuleIndex) Len() int {
	if r == nil {
		return 0
	}
	return len(r.Dimension)
}

// ReadRules parses the tool's generated rule reference into rule id -> our dimension.
//
// The per-rule dimension is taken from the tool's own document rather than written here, so
// it cannot drift from the tool. This file only maps the tool's dimension NAMES onto ours,
// which is a dozen lines instead of one per rule. Keying on rule id prefix would be wrong:
// in AgentGuard `PERM-*` rules sit under three different dimensions.
//
// Returns nil when no reference is reachable. This repository must validate with no checkout
// of any scanner present, so that downgrades to "not checked" rather than passing everything.
func (t Tool) ReadRules(repoRoot string) *RuleIndex {
	if t.RuleIDPattern == "" {
		return nil
	}
	ruleRE, err := regexp.Compile(t.RuleIDPattern)
	if err != nil {
		return nil
	}
	var secRE *regexp.Regexp
	if t.SectionPattern != "" {
		if secRE, err = regexp.Compile(t.SectionPattern); err != nil {
			return nil
		}
	}

	var candidates []string
	if t.RulesSource.Env != "" {
		candidates = append(candidates, os.Getenv(t.RulesSource.Env))
	}
	if t.RulesSource.Path != "" {
		candidates = append(candidates, filepath.Join(repoRoot, t.RulesSource.Path))
	}

	for _, c := range candidates {
		if c == "" {
			continue
		}
		f, err := os.Open(c)
		if err != nil {
			continue
		}
		idx := &RuleIndex{Source: filepath.Clean(c), Dimension: map[string]*string{}}
		defining := map[string]bool{}
		section := ""
		sc := bufio.NewScanner(f)
		sc.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
		for sc.Scan() {
			line := sc.Text()
			if secRE != nil {
				if m := secRE.FindStringSubmatch(line); m != nil {
					section = strings.TrimSpace(m[len(m)-1])
					continue
				}
			}
			for _, m := range ruleRE.FindAllStringSubmatch(line, -1) {
				id := m[len(m)-1]
				if _, seen := idx.Dimension[id]; seen {
					continue
				}
				idx.Dimension[id] = t.DimensionMap[section]
				if section != "" {
					defining[section] = true
				}
			}
		}
		f.Close()
		if len(idx.Dimension) > 0 {
			for sec := range defining {
				if _, ok := t.DimensionMap[sec]; !ok {
					idx.Unmapped = append(idx.Unmapped, sec)
				}
			}
			sort.Strings(idx.Unmapped)
			return idx
		}
	}
	return nil
}

func sortedKeys[V any](m map[string]V) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
