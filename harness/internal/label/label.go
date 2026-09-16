// SPDX-License-Identifier: MIT

// Package label parses and validates the _label.yaml files that annotate every corpus
// sample.
//
// The validation here is the corpus's own invariant #5: a corpus whose labels can drift
// away from what the samples actually are is worse than no corpus, because its numbers look
// exactly the same either way. Every rule enforced in Validate exists because the
// corresponding mistake produces a plausible-looking measurement rather than an error.
package label

import (
	"fmt"
	"os"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

type Class string

const (
	Malicious    Class = "malicious"
	Benign       Class = "benign"
	HardNegative Class = "hard-negative"
)

type Label struct {
	ID      string `yaml:"id"`
	Class   Class  `yaml:"class"`
	Surface string `yaml:"surface"`
	Kind    string `yaml:"kind"`
	Entry   string `yaml:"entry"`

	Origin Origin `yaml:"origin"`
	Expect Expect `yaml:"expect"`

	// PairsWith names a malicious sample that must still fire. Required for hard-negative:
	// without it, "reduce false positives" degrades into "delete the rule" and nothing
	// notices.
	PairsWith string `yaml:"pairs_with"`

	// OutOfScope, when non-empty, means the sample is malicious in a way this tool states
	// it does not detect. It leaves the recall denominator AND is named in the report.
	OutOfScope string `yaml:"out_of_scope"`

	// KnownGap, when present, means we currently fail this sample on purpose-of-record.
	KnownGap *KnownGap `yaml:"known_gap"`

	// Path is the directory the label was read from. Not serialised.
	Path string `yaml:"-"`
}

type Origin struct {
	Type    string `yaml:"type"` // real-world | promoted | reconstruction | synthetic
	Source  string `yaml:"source"`
	License string `yaml:"license"`
	Note    string `yaml:"note"`
	Added   string `yaml:"added"`

	// LabeledBeforeRun must be true. Labelling after running treats the tool's current
	// behaviour as the correct answer, which measures 100% every time.
	LabeledBeforeRun bool `yaml:"labeled_before_run"`
}

type Expect struct {
	Rules []string `yaml:"rules"`
	Quiet []string `yaml:"quiet"`

	// Notes are dimension-0 note IDs that must be present: COV-000, IO-000, SCOPE-001 and
	// the rest. This is the whole of measurement class 3 (disclosure), which asks whether
	// the tool admits what it did not read. A sample that injects a coverage gap asserts
	// here that the gap was announced; without this field the corpus cannot express the
	// class at all. The tool's own adversarial suite has carried the equivalent (wantNote)
	// from the start, so the corpus was the side that was missing it.
	Notes []string `yaml:"notes"`

	MinSeverity string `yaml:"min_severity"`
	MaxSeverity string `yaml:"max_severity"`
}

type KnownGap struct {
	Item     string `yaml:"item"`
	Since    string `yaml:"since"`
	Observed string `yaml:"observed"`
}

var (
	validSurfaces   = []string{"skills", "hooks", "permission", "mcp", "connector", "instruction"}
	validOrigins    = []string{"real-world", "promoted", "reconstruction", "synthetic"}
	validSeverities = []string{"critical", "high", "medium", "low", "none"}

	// permissiveLicenses may be vendored into layer 1. Everything else belongs in
	// manifest/ — see docs/licensing.md. No-license material is the strictest case
	// (zero grant), not the loosest.
	permissiveLicenses = []string{"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "CC-BY-4.0", "CC0-1.0", "ISC"}
)

func Load(path string) (*Label, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read label: %w", err)
	}
	var l Label
	dec := yaml.NewDecoder(strings.NewReader(string(b)))
	dec.KnownFields(true) // a typo'd field is a silently ignored expectation
	if err := dec.Decode(&l); err != nil {
		return nil, fmt.Errorf("parse label: %w", err)
	}
	return &l, nil
}

// Validate checks one label in isolation. Cross-sample checks (pairs_with resolution, rule
// IDs existing, id uniqueness) need the whole set and live in ValidateSet.
func (l *Label) Validate() []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	if l.ID == "" {
		bad("id is empty")
	}
	switch l.Class {
	case Malicious, Benign, HardNegative:
	case "":
		bad("class is empty")
	default:
		bad("class %q is not malicious, benign or hard-negative", l.Class)
	}
	if !oneOf(l.Surface, validSurfaces) {
		bad("surface %q is not one of %s", l.Surface, strings.Join(validSurfaces, ", "))
	}
	if l.Entry == "" {
		bad("entry is empty — it must say what `aguard check` is pointed at")
	}

	if !oneOf(l.Origin.Type, validOrigins) {
		bad("origin.type %q is not one of %s", l.Origin.Type, strings.Join(validOrigins, ", "))
	}
	if !l.Origin.LabeledBeforeRun {
		bad("origin.labeled_before_run must be true — labelling after running treats the " +
			"tool's current behaviour as the correct answer, which measures 100% every time")
	}
	if l.Origin.Added == "" {
		bad("origin.added is empty")
	}
	if l.Origin.License == "" {
		bad("origin.license is empty")
	} else if !oneOf(l.Origin.License, permissiveLicenses) {
		bad("origin.license %q may not be vendored into layer 1 — reference it from manifest/ "+
			"instead (docs/licensing.md)", l.Origin.License)
	}

	// Expectations must not contradict themselves. An ID in both lists makes the sample
	// unfalsifiable: it passes whatever the tool does.
	for _, r := range intersect(l.Expect.Rules, l.Expect.Quiet) {
		bad("rule %s is in both expect.rules and expect.quiet", r)
	}
	if l.Expect.MinSeverity != "" && !oneOf(l.Expect.MinSeverity, validSeverities) {
		bad("expect.min_severity %q is not a severity", l.Expect.MinSeverity)
	}
	if l.Expect.MaxSeverity != "" && !oneOf(l.Expect.MaxSeverity, validSeverities) {
		bad("expect.max_severity %q is not a severity", l.Expect.MaxSeverity)
	}

	switch l.Class {
	case Malicious:
		if len(l.Expect.Rules) == 0 && l.OutOfScope == "" {
			bad("malicious sample lists no expect.rules and is not marked out_of_scope — " +
				"it asserts nothing")
		}
		if l.Expect.MaxSeverity != "" {
			bad("malicious sample sets max_severity; it wants min_severity")
		}
		if l.PairsWith != "" {
			bad("pairs_with is for hard-negative samples, not malicious ones")
		}
	case Benign, HardNegative:
		if l.Expect.MaxSeverity == "" {
			bad("%s sample must set expect.max_severity — the expectation for a benign "+
				"sample is 'not above this', never 'silent'", l.Class)
		}
		if l.Expect.MinSeverity != "" {
			bad("%s sample sets min_severity", l.Class)
		}
		if len(l.Expect.Rules) > 0 {
			bad("%s sample lists expect.rules; benign samples assert quiet, not fire", l.Class)
		}
		if l.OutOfScope != "" {
			bad("out_of_scope applies to malicious samples only")
		}
	}

	if l.Class == HardNegative {
		if l.PairsWith == "" {
			bad("hard-negative sample must set pairs_with — a suppression and the proof " +
				"that the rule still works land together or not at all")
		}
		if len(l.Expect.Quiet) == 0 {
			bad("hard-negative sample must list expect.quiet — that is the whole assertion")
		}
	}

	if l.KnownGap != nil {
		if l.KnownGap.Item == "" {
			bad("known_gap.item is empty — an expected failure must name the work item it " +
				"is attributed to, or it is indistinguishable from a broken sample")
		}
		if l.KnownGap.Observed == "" {
			bad("known_gap.observed is empty — record what the tool actually does today")
		}
	}
	return errs
}

// ValidateSet checks the properties that only exist across the whole corpus.
//
// knownRules, when non-empty, is the set of rule IDs the tool can actually emit (read from
// its generated docs/rules.md). A renamed or retired rule then turns the corpus red instead
// of silently never matching.
func ValidateSet(labels []*Label, knownRules map[string]bool) []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	byID := map[string]*Label{}
	for _, l := range labels {
		if prev, dup := byID[l.ID]; dup {
			bad("id %s is used by both %s and %s — ids are never reused", l.ID, prev.Path, l.Path)
			continue
		}
		byID[l.ID] = l
	}

	for _, l := range labels {
		if l.PairsWith == "" {
			continue
		}
		twin, ok := byID[l.PairsWith]
		if !ok {
			bad("%s: pairs_with %q does not exist", l.Path, l.PairsWith)
			continue
		}
		if twin.Class != Malicious {
			bad("%s: pairs_with %q is %s, not malicious — the pair exists to prove the rule "+
				"still fires", l.Path, l.PairsWith, twin.Class)
			continue
		}
		// The pairing is only meaningful if the twin fires one of the rules this sample
		// silences. Otherwise the two samples are unrelated and the suppression is unguarded.
		if len(intersect(l.Expect.Quiet, twin.Expect.Rules)) == 0 {
			bad("%s: pairs_with %q shares no rule with this sample's expect.quiet %v — "+
				"the pair does not guard anything", l.Path, l.PairsWith, l.Expect.Quiet)
		}
	}

	if len(knownRules) > 0 {
		for _, l := range labels {
			for _, r := range append(append([]string{}, l.Expect.Rules...), l.Expect.Quiet...) {
				if !knownRules[r] {
					bad("%s: rule %s is not a rule the tool can emit", l.Path, r)
				}
			}
		}
	}
	return errs
}

func oneOf(v string, set []string) bool {
	for _, s := range set {
		if v == s {
			return true
		}
	}
	return false
}

func intersect(a, b []string) []string {
	in := map[string]bool{}
	for _, s := range a {
		in[s] = true
	}
	var out []string
	for _, s := range b {
		if in[s] {
			out = append(out, s)
		}
	}
	sort.Strings(out)
	return out
}
