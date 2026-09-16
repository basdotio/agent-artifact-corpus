// SPDX-License-Identifier: MIT

// Package taxonomy loads the tool-neutral vocabulary a label draws on: the technique names
// that say what a sample is, and the scanners that may carry rule-level expectations about
// it.
//
// The split this package exists to serve: `truth` in a label is written in technique names
// from techniques.yaml and belongs to nobody, while `expect.<tool>` is written in one
// scanner's rule ids and belongs to that scanner. Before the split there was only the second
// kind, so every assertion in the corpus was phrased in one product's vocabulary and the
// corpus could not describe a sample to anyone who had not built that product.
package taxonomy

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// Technique is one entry in the tool-neutral vocabulary.
type Technique struct {
	ID        string `yaml:"id"`
	Title     string `yaml:"title"`
	Dimension string `yaml:"dimension"`
	What      string `yaml:"what"`

	// BenignLookalike is the discrimination test in prose: what an honest artifact with the
	// same surface shape looks like, and which element actually separates them. Stated once
	// here rather than repeated in every label.
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

	// SeverityLadder is this tool's own ladder, ordered most to least severe. Expectation
	// bounds are checked against the ladder of the tool whose block they sit in, so two
	// scanners with different ladders can annotate the same sample without either adopting
	// the other's.
	SeverityLadder []string `yaml:"severity_ladder"`

	RuleIDPattern string      `yaml:"rule_id_pattern"`
	RulesSource   RulesSource `yaml:"rules_source"`
	NativeFormat  string      `yaml:"native_format"`
}

// HasSeverity reports whether s is on this tool's ladder.
func (t Tool) HasSeverity(s string) bool { return slices.Contains(t.SeverityLadder, s) }

// KnownRules reads the tool's generated rule reference and returns the ids it can emit,
// with the path they came from. A missing reference returns nil and an empty source: this
// repository must validate with no checkout of any scanner present, so an unreachable
// reference downgrades to "not checked" rather than silently passing everything.
func (t Tool) KnownRules(repoRoot string) (map[string]bool, string) {
	if t.RuleIDPattern == "" {
		return nil, ""
	}
	re, err := regexp.Compile(t.RuleIDPattern)
	if err != nil {
		return nil, ""
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
		b, err := os.ReadFile(c)
		if err != nil {
			continue
		}
		out := map[string]bool{}
		for _, m := range re.FindAllStringSubmatch(string(b), -1) {
			out[m[len(m)-1]] = true
		}
		if len(out) > 0 {
			return out, filepath.Clean(c)
		}
	}
	return nil, ""
}

type techniqueFile struct {
	Dimensions []string    `yaml:"dimensions"`
	Techniques []Technique `yaml:"techniques"`
}

type toolFile struct {
	Tools []Tool `yaml:"tools"`
}

// Set is the loaded vocabulary.
type Set struct {
	Dimensions []string
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
		Techniques: map[string]Technique{},
		Tools:      map[string]Tool{},
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

	for _, id := range sortedKeys(s.Techniques) {
		t := s.Techniques[id]
		if t.ID == "" {
			bad("a technique has no id")
			continue
		}
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
		if t.ID == "" {
			bad("a tool has no id")
			continue
		}
		if t.Name == "" {
			bad("tool %s has no name", t.ID)
		}
		if len(t.SeverityLadder) == 0 {
			bad("tool %s declares no severity_ladder — expectation bounds in a label are "+
				"checked against it, so without one every bound is unvalidated", t.ID)
		}
		if t.RuleIDPattern != "" {
			if _, err := regexp.Compile(t.RuleIDPattern); err != nil {
				bad("tool %s: rule_id_pattern does not compile: %v", t.ID, err)
			}
		}
	}
	return errs
}

// Dimension returns the recall axis a technique sits on.
func (s *Set) Dimension(techniqueID string) string {
	return s.Techniques[techniqueID].Dimension
}

func sortedKeys[V any](m map[string]V) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
