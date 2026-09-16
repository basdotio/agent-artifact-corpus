// SPDX-License-Identifier: MIT

// Package label parses and validates the <id>.yaml files that annotate every corpus sample.
//
// A label has two halves and they belong to different people.
//
// `truth` says what the sample IS, in technique names from taxonomy/techniques.yaml that no
// scanner owns. It is enough on its own to score any scanner: a runner asks "did the tool
// report this sample at or above truth.severity" without knowing a single rule id.
//
// `expect.<tool>` says what one named scanner should emit about it, in that scanner's own
// rule ids and on that scanner's own severity ladder. It is optional precision layered on
// top of truth, and an absent block means "not measured here", which is a different
// statement from "passed".
//
// Before the split there was only the second half, so every assertion in the corpus was
// phrased in one product's vocabulary, `known_gap` recorded one product's shortfall as a
// property of the sample, and the pairing invariant was expressed as an overlap between rule
// id lists — which made the corpus unable to describe a sample to anyone who had not built
// that product.
//
// The validation here is the corpus's own invariant: a corpus whose labels can drift away
// from what the samples actually are is worse than no corpus, because its numbers look
// exactly the same either way. Every rule enforced below exists because the corresponding
// mistake produces a plausible-looking measurement rather than an error.
package label

import (
	"fmt"
	"os"
	"slices"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
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

	// Truth is the tool-neutral half: what the sample is, not what any scanner should say
	// about it.
	Truth Truth `yaml:"truth"`

	// Expect is per-tool and optional, keyed by a tool id from taxonomy/tools.yaml.
	Expect map[string]*ToolExpect `yaml:"expect"`

	// PairsWith names a malicious sample that must still be caught. Required for
	// hard-negative: without it, "reduce false positives" degrades into "delete the rule"
	// and nothing notices. The pairing is checked through truth — the twin must actually
	// perform a technique this sample merely resembles — so it holds for every scanner
	// rather than only for the one whose rule ids happened to be listed.
	PairsWith string `yaml:"pairs_with"`

	// Path is the sample tree the label sits beside, as an absolute path. Not serialised.
	Path string `yaml:"-"`

	// Rel is the same location, repository-relative, and it is what messages use. Without it
	// half the validator's output was absolute and half relative, which makes two lines
	// about the same sample look like two samples.
	Rel string `yaml:"-"`
}

// where names the sample in a message.
func (l *Label) where() string {
	if l.Rel != "" {
		return l.Rel
	}
	return l.Path
}

type Origin struct {
	Type    string `yaml:"type"` // real-world | promoted | reconstruction | synthetic
	Source  string `yaml:"source"`
	License string `yaml:"license"`
	Note    string `yaml:"note"`
	Added   string `yaml:"added"`

	// LabeledBeforeRun must be true. Labelling after running treats a tool's current
	// behaviour as the correct answer, which measures 100% every time. Note that under the
	// split this is a claim about `truth`, which is the half that must not be derived from
	// any run.
	LabeledBeforeRun bool `yaml:"labeled_before_run"`
}

// Truth is what the sample is. Nothing in here names a scanner, a rule, or a score.
type Truth struct {
	// Techniques is what a malicious sample actually does, drawn from
	// taxonomy/techniques.yaml. It is also the recall axis: classification.md requires
	// recall per dimension rather than pooled, and taking the dimension from a scanner's own
	// rule taxonomy would make every cross-tool comparison circular.
	Techniques []string `yaml:"techniques"`

	// Resembles is what a hard negative LOOKS like. The pairing invariant runs through this
	// field rather than through rule ids, which is what makes it a statement about the two
	// samples instead of a statement about one tool's regex.
	Resembles []string `yaml:"resembles"`

	// DiffersBy names the element that is absent and makes it benign. This is the
	// discrimination test written out, and it is the field the author of another scanner
	// actually needs from us.
	DiffersBy string `yaml:"differs_by"`

	// Severity is how bad the sample is, independent of any tool, on the ordinary
	// critical/high/medium/low ladder. A runner with no `expect` block scores against this:
	// "was it reported at or above here". Malicious samples only.
	Severity string `yaml:"severity"`

	// Tier is how deeply the attack is buried, from taxonomy/techniques.yaml. It is the axis
	// that turns "this scanner misses 40% of exfiltration" into "this scanner catches every
	// plain exfiltration and misses every encoded one" — the first is a score, the second
	// tells you what to fix.
	//
	// On a hard negative the same scale reads as how strongly it resembles the attack: at the
	// calibration tier it is obviously benign and only a broken scanner fires, at the deepest
	// tier telling it apart needs semantics rather than matching.
	Tier string `yaml:"tier"`

	// Evasion names the mechanisms doing the burying, from the closed vocabulary. An empty
	// list means none, which is what the calibration tier requires.
	Evasion []string `yaml:"evasion"`

	Note string `yaml:"note"`
}

// ToolExpect is one scanner's expected output for one sample.
type ToolExpect struct {
	Rules []string `yaml:"rules"` // must fire
	Quiet []string `yaml:"quiet"` // must not fire

	// Notes are dimension-0 note ids that must be present. This carries measurement class 3
	// (disclosure), which asks whether the tool admits what it did not read. It is
	// deliberately inside the per-tool block: almost no other scanner has the concept, and
	// hoisting it to the top level would have asserted a property of the sample that is
	// really a property of one product.
	Notes []string `yaml:"notes"`

	MinSeverity string `yaml:"min_severity"`
	MaxSeverity string `yaml:"max_severity"`

	// KnownGap means this tool currently fails this sample on purpose-of-record. It lives
	// per-tool because a shortfall is per-tool by definition: one scanner's gap is not
	// another's, and recording it at the top level stated one product's weakness as a fact
	// about the artifact.
	KnownGap *KnownGap `yaml:"known_gap"`

	// OutOfScope, when non-empty, means the sample is malicious in a way THIS tool states it
	// does not detect. It leaves that tool's recall denominator and is named in the report.
	// Also per-tool: pure runtime behaviour is out of scope for a static scanner and in
	// scope for a dynamic one.
	OutOfScope string `yaml:"out_of_scope"`
}

type KnownGap struct {
	Item     string `yaml:"item"`
	Since    string `yaml:"since"`
	Observed string `yaml:"observed"`
}

var (
	validSurfaces = []string{"skills", "hooks", "permission", "mcp", "connector", "instruction"}
	validOrigins  = []string{"real-world", "promoted", "reconstruction", "synthetic"}

	// truthSeverities is the tool-neutral ladder. Per-tool bounds are checked against that
	// tool's own ladder from taxonomy/tools.yaml instead.
	truthSeverities = []string{"critical", "high", "medium", "low"}

	// permissiveLicenses may be vendored into layer 1. Everything else belongs in manifest/
	// — see docs/licensing.md. No-license material is the strictest case (zero grant), not
	// the loosest.
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

// Validate checks one label against the vocabulary. Cross-sample checks (pairs_with
// resolution, id uniqueness, unguarded pairs) need the whole set and live in ValidateSet.
func (l *Label) Validate(tax *taxonomy.Set) []error {
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
		bad("entry is empty — it must say what the scanner is pointed at")
	}

	if !oneOf(l.Origin.Type, validOrigins) {
		bad("origin.type %q is not one of %s", l.Origin.Type, strings.Join(validOrigins, ", "))
	}
	if !l.Origin.LabeledBeforeRun {
		// 100%% is not a typo: bad() is a printf wrapper, so a bare % here is parsed as a
		// verb and the message renders as "100%!e(MISSING)very time". It did, until this
		// comment was written.
		bad("origin.labeled_before_run must be true — labelling after running treats the " +
			"tool's current behaviour as the correct answer, which measures 100%% every time")
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

	errs = append(errs, l.validateTruth(tax)...)
	errs = append(errs, l.validateExpect(tax)...)
	return errs
}

func (l *Label) validateTruth(tax *taxonomy.Set) []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	for _, t := range append(append([]string{}, l.Truth.Techniques...), l.Truth.Resembles...) {
		if _, ok := tax.Techniques[t]; !ok {
			bad("truth names technique %q, which is not in taxonomy/techniques.yaml", t)
		}
	}
	for _, t := range intersect(l.Truth.Techniques, l.Truth.Resembles) {
		bad("technique %s is in both truth.techniques and truth.resembles — a sample either "+
			"performs it or merely looks like it", t)
	}

	errs = append(errs, l.validateDepth(tax)...)

	switch l.Class {
	case Malicious:
		if len(l.Truth.Techniques) == 0 {
			bad("malicious sample lists no truth.techniques — without one it asserts nothing " +
				"that any scanner other than ours could be measured against, and it sits on no " +
				"recall axis")
		}
		if len(l.Truth.Resembles) > 0 {
			bad("truth.resembles is for benign look-alikes, not for malicious samples")
		}
		if l.Truth.DiffersBy != "" {
			bad("truth.differs_by is for hard negatives — it names what is absent that makes " +
				"a sample benign")
		}
		if l.Truth.Severity == "" {
			bad("malicious sample must set truth.severity — it is what a scanner with no " +
				"expect block here is scored against, and it is the only tool-neutral " +
				"statement of how bad this is")
		} else if !oneOf(l.Truth.Severity, truthSeverities) {
			bad("truth.severity %q is not one of %s", l.Truth.Severity,
				strings.Join(truthSeverities, ", "))
		}

	case Benign, HardNegative:
		if len(l.Truth.Techniques) > 0 {
			bad("%s sample lists truth.techniques — a benign sample performs none; if it "+
				"looks like one, that is truth.resembles", l.Class)
		}
		if l.Truth.Severity != "" {
			bad("%s sample sets truth.severity — the correct report on it is no finding, "+
				"which is not a point on the ladder", l.Class)
		}
	}

	if l.Class == HardNegative {
		if len(l.Truth.Resembles) == 0 {
			bad("hard-negative sample must list truth.resembles — resembling an attack is " +
				"the entire definition of the class, and it is what the pairing is checked " +
				"through")
		}
		if l.Truth.DiffersBy == "" {
			bad("hard-negative sample must set truth.differs_by — naming the element that is " +
				"absent is the discrimination test, and it is the one thing the author of " +
				"another scanner needs from this sample")
		}
	}
	return errs
}

// validateDepth checks the tier and evasion axes.
//
// These two answer a different question from `dimension`. Dimension says the scanner is
// missing a capability; tier says its matching is too literal; evasion says exactly which
// transformation to handle. A corpus with only the first axis can report that a scanner is
// weak but never why.
func (l *Label) validateDepth(tax *taxonomy.Set) []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	if l.Class == Benign {
		// An ordinary benign sample is not hiding anything and is not imitating anything, so
		// neither axis applies to it.
		if l.Truth.Tier != "" {
			bad("benign sample sets truth.tier — the axis measures how deeply an attack is " +
				"buried, and a sample with no attack has no depth. A benign sample that " +
				"resembles one is class hard-negative")
		}
		if len(l.Truth.Evasion) > 0 {
			bad("benign sample lists truth.evasion")
		}
		return errs
	}

	if l.Truth.Tier == "" {
		bad("%s sample must set truth.tier — without it every sample is equally deep, and a "+
			"miss cannot be attributed to literal matching rather than to a missing rule",
			l.Class)
		return errs
	}
	tier, known := tax.Tiers[l.Truth.Tier]
	if !known {
		bad("truth.tier %q is not a tier in taxonomy/techniques.yaml (%s)",
			l.Truth.Tier, strings.Join(tax.TierOrder, ", "))
		return errs
	}

	seen := map[string]bool{}
	for _, e := range l.Truth.Evasion {
		if seen[e] {
			bad("truth.evasion lists %s twice", e)
			continue
		}
		seen[e] = true

		mech, ok := tax.Evasions[e]
		if !ok {
			bad("truth.evasion names %q, which is not in the closed vocabulary in "+
				"taxonomy/techniques.yaml. Adding a mechanism means adding it there, in the "+
				"same change as the sample that needs it — an open field degrades into free "+
				"text, and free text cannot be aggregated", e)
			continue
		}
		// The bound that matters. Without it a wrapped payload could be labelled at the
		// calibration tier, where a miss is supposed to mean the scanner is broken.
		if !tax.TierAtLeast(l.Truth.Tier, mech.ImpliesTier) {
			bad("truth.tier is %s but evasion %s implies at least %s — %s",
				l.Truth.Tier, e, mech.ImpliesTier, mech.What)
		}
	}

	if tier.Calibration && len(l.Truth.Evasion) > 0 {
		bad("tier %s means nothing hides the attack, so truth.evasion must be empty; it "+
			"lists %s", l.Truth.Tier, strings.Join(l.Truth.Evasion, ", "))
	}

	// The "name the mechanism" rule binds malicious samples only.
	//
	// A hard negative is not burying anything — it has no attack to bury. Its tier reads as
	// how deep an analysis has to go before it can be told apart: at the calibration level a
	// surface check suffices, at the deepest one no amount of matching wins and the reader
	// needs semantics. What makes it hard is already written out in truth.differs_by, which
	// is required for the class and is better prose than any vocabulary term would be.
	if l.Class == Malicious && !tier.Calibration && len(l.Truth.Evasion) == 0 {
		bad("tier %s is past the calibration level, so something is doing the burying and "+
			"truth.evasion must name it. If nothing does, the sample belongs at the "+
			"calibration tier", l.Truth.Tier)
	}
	return errs
}

func (l *Label) validateExpect(tax *taxonomy.Set) []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	// An empty expect map is legitimate and common: truth alone scores any scanner. What is
	// NOT legitimate is a block for a tool nobody declared, because its rule ids and its
	// severity bounds would then go unchecked forever.
	for _, toolID := range sortedExpectKeys(l.Expect) {
		e := l.Expect[toolID]
		tool, known := tax.Tools[toolID]
		if !known {
			bad("expect names tool %q, which is not in taxonomy/tools.yaml — add it there, "+
				"or drop the block: an unknown tool's rule ids and severity bounds cannot be "+
				"checked against anything", toolID)
			continue
		}
		if e == nil {
			bad("expect.%s is empty — remove the key instead. An empty block reads as "+
				"'measured and clean', and absence is supposed to mean 'not measured'", toolID)
			continue
		}

		for _, r := range intersect(e.Rules, e.Quiet) {
			bad("expect.%s: rule %s is in both rules and quiet, which makes the sample "+
				"unfalsifiable for this tool — it passes whatever the tool does", toolID, r)
		}
		if e.MinSeverity != "" && !tool.HasSeverity(e.MinSeverity) {
			bad("expect.%s: min_severity %q is not on %s's ladder (%s)", toolID, e.MinSeverity,
				toolID, strings.Join(tool.SeverityLadder, ", "))
		}
		if e.MaxSeverity != "" && !tool.HasSeverity(e.MaxSeverity) {
			bad("expect.%s: max_severity %q is not on %s's ladder (%s)", toolID, e.MaxSeverity,
				toolID, strings.Join(tool.SeverityLadder, ", "))
		}

		switch l.Class {
		case Malicious:
			if len(e.Rules) == 0 && e.OutOfScope == "" {
				bad("expect.%s: lists no rules and is not marked out_of_scope — the block "+
					"asserts nothing. Drop it and let truth carry the assertion, or say "+
					"which rule must fire", toolID)
			}
			if e.MaxSeverity != "" {
				bad("expect.%s: malicious sample sets max_severity; it wants min_severity", toolID)
			}
		case Benign, HardNegative:
			if len(e.Rules) > 0 {
				bad("expect.%s: %s sample lists rules — a benign sample asserts quiet, not fire",
					toolID, l.Class)
			}
			if e.MinSeverity != "" {
				bad("expect.%s: %s sample sets min_severity", toolID, l.Class)
			}
			if e.MaxSeverity == "" {
				bad("expect.%s: %s sample must set max_severity — the expectation for a benign "+
					"sample is 'not above this', never 'silent'. Setting it too tight is the "+
					"common mistake: set it to what a correct tool would emit and let quiet "+
					"carry the real claim", toolID, l.Class)
			}
			if e.OutOfScope != "" {
				bad("expect.%s: out_of_scope applies to malicious samples only", toolID)
			}
		}

		if e.KnownGap != nil {
			if e.KnownGap.Item == "" {
				bad("expect.%s: known_gap.item is empty — an expected failure must name the "+
					"work item it is attributed to, or it is indistinguishable from a broken "+
					"sample", toolID)
			}
			if e.KnownGap.Observed == "" {
				bad("expect.%s: known_gap.observed is empty — record what the tool actually "+
					"does today", toolID)
			}
		}
	}
	return errs
}

// Unguarded is a hard negative whose pairing currently proves nothing for one tool, because
// that tool is on record as failing the twin.
//
// This state is legitimate and must be recorded rather than rejected: the twin's known_gap
// is an honest declaration. What is not acceptable is that it be invisible. A pair in this
// state passes every structural check while guaranteeing nothing — delete the shared rule
// and both samples still pass — so it is reported, named and counted, on the same principle
// as the tool's own coverage notes: a declared hole is something an operator can act on, a
// hidden one is a lie.
type Unguarded struct {
	HardNegative string
	Twin         string
	Tool         string
	GapItem      string
	SharedRules  []string
}

// ValidateSet checks the properties that only exist across the whole corpus.
func ValidateSet(labels []*Label, tax *taxonomy.Set, knownRules map[string]*taxonomy.RuleIndex) []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	byID := map[string]*Label{}
	for _, l := range labels {
		if prev, dup := byID[l.ID]; dup {
			bad("id %s is used by both %s and %s — ids are never reused", l.ID, prev.where(), l.where())
			continue
		}
		byID[l.ID] = l
	}

	for _, l := range labels {
		if l.Class == HardNegative && l.PairsWith == "" {
			bad("%s: hard-negative sample must set pairs_with — a suppression and the proof "+
				"that the rule still works land together or not at all", l.where())
		}
		if l.PairsWith == "" {
			continue
		}
		if l.Class == Malicious {
			bad("%s: pairs_with is for benign look-alikes, not for malicious samples", l.where())
			continue
		}
		twin, ok := byID[l.PairsWith]
		if !ok {
			bad("%s: pairs_with %q does not exist", l.where(), l.PairsWith)
			continue
		}
		if twin.Class != Malicious {
			bad("%s: pairs_with %q is %s, not malicious — the pair exists to prove the attack "+
				"is still caught", l.where(), l.PairsWith, twin.Class)
			continue
		}
		// The pairing is checked through truth, not through rule ids. The twin must actually
		// perform a technique this sample merely resembles, which is a statement about the
		// two artifacts and therefore holds for every scanner. The old check compared one
		// product's rule id lists, so a pair was "valid" whenever two labels happened to
		// mention the same regex name.
		if len(intersect(l.Truth.Resembles, twin.Truth.Techniques)) == 0 {
			bad("%s: pairs_with %q performs %v, and this sample resembles %v — they share no "+
				"technique, so the pair does not guard anything",
				l.where(), l.PairsWith, twin.Truth.Techniques, l.Truth.Resembles)
		}
	}

	// Rule ids are checked per tool, against that tool's own reference. A tool with no
	// reachable reference is skipped rather than assumed wrong.
	for _, l := range labels {
		for _, toolID := range sortedExpectKeys(l.Expect) {
			rules := knownRules[toolID]
			if rules.Len() == 0 {
				continue
			}
			e := l.Expect[toolID]
			cited := append(append([]string{}, e.Rules...), e.Quiet...)
			cited = append(cited, e.Notes...)
			for _, r := range cited {
				if !rules.Has(r) {
					bad("%s: expect.%s cites %s, which is not something %s can emit",
						l.where(), toolID, r, toolID)
				}
			}
		}
	}
	return errs
}

// UnguardedPairs finds the pairs that pass every check while proving nothing, per tool.
func UnguardedPairs(labels []*Label) []Unguarded {
	byID := map[string]*Label{}
	for _, l := range labels {
		byID[l.ID] = l
	}

	var out []Unguarded
	for _, l := range labels {
		if l.PairsWith == "" {
			continue
		}
		twin, ok := byID[l.PairsWith]
		if !ok {
			continue
		}
		for _, toolID := range sortedExpectKeys(l.Expect) {
			te, measured := twin.Expect[toolID]
			if !measured || te == nil || te.KnownGap == nil {
				continue
			}
			shared := intersect(l.Expect[toolID].Quiet, te.Rules)
			if len(shared) == 0 {
				continue
			}
			out = append(out, Unguarded{
				HardNegative: l.ID,
				Twin:         twin.ID,
				Tool:         toolID,
				GapItem:      te.KnownGap.Item,
				SharedRules:  shared,
			})
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].HardNegative != out[j].HardNegative {
			return out[i].HardNegative < out[j].HardNegative
		}
		return out[i].Tool < out[j].Tool
	})
	return out
}

func sortedExpectKeys(m map[string]*ToolExpect) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func oneOf(v string, set []string) bool { return slices.Contains(set, v) }

func intersect(a, b []string) []string {
	in := map[string]bool{}
	for _, s := range a {
		in[s] = true
	}
	seen := map[string]bool{}
	var out []string
	for _, s := range b {
		if in[s] && !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	sort.Strings(out)
	return out
}
