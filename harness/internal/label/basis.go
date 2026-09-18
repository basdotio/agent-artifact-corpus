// SPDX-License-Identifier: MIT

package label

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// Basis records what each of a label's axes rests on, drawn from taxonomy/basis.yaml.
//
// Every axis carries its own value because the axes were established differently and a
// single field would force one answer to several questions. A cisco sample is the plain
// case: its `class` came from `constant:malicious` (assumed), its `dimension` was read off
// the artifact by hand (read), and its `severity` came from `constant:high` (assumed again,
// and carrying no information about the sample at all).
//
// The block is OPTIONAL. 3,494 samples predate it, and a check that fails all of them on
// the day it lands cannot be landed. Absence is counted by BasisDebt instead, so "not yet
// recorded" stays visible without being fatal.
type Basis struct {
	// Class is the basis for the risky/not-risky judgement — the one every sample has.
	Class string `yaml:"class"`

	// Dimension and Severity are per-axis and may be empty when the label does not carry
	// that axis. An empty basis on an axis the label DOES carry means the axis cannot be
	// scored, which is reported rather than failed.
	Dimension string `yaml:"dimension"`
	Severity  string `yaml:"severity"`

	// Evidence belongs to `read` and to nothing else. See validateEvidencePlacement.
	Evidence *Evidence `yaml:"evidence"`

	Assumption  string `yaml:"assumption"`   // `assumed`
	SourceField string `yaml:"source_field"` // `upstream`
	SourceValue string `yaml:"source_value"` // `upstream`
	Rule        string `yaml:"rule"`         // `derived`
}

// Evidence locates the deciding element inside the sample. The quote is what separates
// `read` from a claim of having read: VerifyEvidence goes and finds it in the bytes.
type Evidence struct {
	File  string `yaml:"file"`
	Lines string `yaml:"lines"`
	Quote string `yaml:"quote"`
}

// RefutationSearch is what a benign sample records after the refutation ruleset has been run
// over it. It is the difference between "nobody looked" and "searched with this ruleset, at
// this version, and found nothing" — which is the corpus's third red line applied to itself.
type RefutationSearch struct {
	RulesetVersion int      `yaml:"ruleset_version"`
	Matched        []string `yaml:"matched"`
	ScannedBytes   int      `yaml:"scanned_bytes"`
}

// axisValues returns the per-axis basis values actually set on this label.
func (b *Basis) axisValues() map[string]string {
	out := map[string]string{}
	if b.Class != "" {
		out["class"] = b.Class
	}
	if b.Dimension != "" {
		out["dimension"] = b.Dimension
	}
	if b.Severity != "" {
		out["severity"] = b.Severity
	}
	return out
}

// has reports whether the field named by a `requires` entry is populated.
func (b *Basis) has(field string) bool {
	switch field {
	case "evidence.file":
		return b.Evidence != nil && b.Evidence.File != ""
	case "evidence.lines":
		return b.Evidence != nil && b.Evidence.Lines != ""
	case "evidence.quote":
		return b.Evidence != nil && b.Evidence.Quote != ""
	case "assumption":
		return b.Assumption != ""
	case "source_field":
		return b.SourceField != ""
	case "source_value":
		return b.SourceValue != ""
	case "rule":
		return b.Rule != ""
	default:
		// An unknown requirement is a vocabulary bug, not a label bug. Report it as
		// unsatisfiable rather than silently treating it as met, which would let a typo in
		// basis.yaml quietly switch a requirement off.
		return false
	}
}

// ValidateBasis checks the label's basis block against the vocabulary.
func (l *Label) ValidateBasis(spec *taxonomy.BasisSpec) []error {
	if l.Basis == nil || spec == nil {
		return nil
	}
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	for _, axis := range []string{"class", "dimension", "severity"} {
		v, set := l.Basis.axisValues()[axis]
		if !set {
			continue
		}
		if !spec.Known(v) {
			bad("basis.%s is %q, which is not in the vocabulary (%s)",
				axis, v, strings.Join(spec.Order, ", "))
			continue
		}
		for _, field := range spec.RequiredFields(v) {
			if !l.Basis.has(field) {
				bad("basis.%s is %q but %s is absent — a basis claimed with nothing "+
					"attached is an assertion a reader cannot check", axis, v, field)
			}
		}
	}
	errs = append(errs, l.validateEvidencePlacement()...)
	return errs
}

// validateEvidencePlacement keeps evidence attached only to `read`.
//
// This is the failure the vocabulary exists to prevent. Evidence sitting on an `assumed`
// coordinate makes a batch constant look like something a person verified, and once that is
// permitted every distinction the file draws can be borrowed by the value below it.
func (l *Label) validateEvidencePlacement() []error {
	if l.Basis.Evidence == nil {
		return nil
	}
	for _, v := range l.Basis.axisValues() {
		if v == "read" {
			return nil
		}
	}
	return []error{fmt.Errorf(
		"basis.evidence is set but no axis rests on `read` — evidence attached to a weaker "+
			"basis dresses it in a stronger claim. Axes here: %v", l.Basis.axisValues())}
}

// VerifyEvidence locates the quote in the sample's own bytes.
//
// A `read` basis asserts that a person saw the deciding element. If the quoted string is not
// in the artifact, either the label is wrong or the artifact changed under it, and both are
// worth failing over: this is the one basis allowed to score the attribution axis.
func (l *Label) VerifyEvidence() []error {
	if l.Basis == nil || l.Basis.Evidence == nil || l.Basis.Evidence.Quote == "" {
		return nil
	}
	if l.Path == "" {
		return nil
	}
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	ev := l.Basis.Evidence
	if ev.File != "" {
		full := filepath.Join(l.Path, filepath.FromSlash(ev.File))
		b, err := os.ReadFile(full)
		if err != nil {
			bad("basis.evidence.file %q cannot be read from the sample tree: %v", ev.File, err)
			return errs
		}
		if !strings.Contains(string(b), ev.Quote) {
			bad("basis.evidence.quote %q does not occur in %s — `read` means the deciding "+
				"element was seen in the artifact, so a quote that is not there makes the "+
				"basis unsupported", ev.Quote, ev.File)
		}
		return errs
	}

	// No file named: accept the quote anywhere in the tree, but say so when it is nowhere.
	files, err := regularFiles(l.Path)
	if err != nil {
		bad("basis.evidence is set but the sample tree cannot be read: %v", err)
		return errs
	}
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err == nil && strings.Contains(string(b), ev.Quote) {
			return nil
		}
	}
	bad("basis.evidence.quote %q occurs in no file of the sample tree", ev.Quote)
	return errs
}

// Debt is the outstanding-work summary over a set of labels.
type Debt struct {
	Total   int
	NoBasis int

	// AssumedRisky counts malicious and hard-negative samples whose class rests on a batch
	// constant. Benign samples resting on `assumed` are NOT debt: they cannot be proven
	// harmless one by one, and they carry a refutation search instead.
	AssumedRisky int
	ByBasis      map[string]int
}

// BasisDebt summarises how much of a corpus still rests on nothing per-sample.
func BasisDebt(labels []*Label, spec *taxonomy.BasisSpec) Debt {
	d := Debt{Total: len(labels), ByBasis: map[string]int{}}
	for _, l := range labels {
		if l.Basis == nil || l.Basis.Class == "" {
			d.NoBasis++
			continue
		}
		d.ByBasis[l.Basis.Class]++
		if spec != nil {
			if _, isDebt := spec.IsDebt(l.Basis.Class, string(l.Class)); isDebt {
				d.AssumedRisky++
			}
		}
	}
	return d
}

// ScoreableOnDimension counts the samples whose attribution axis may actually be scored,
// against the samples that carry a dimension at all.
//
// Reported separately from the class axis on purpose. Detection and attribution are the two
// things this corpus measures, they rest on different evidence, and a single "3,494 labels"
// figure hides the one that is hard to move: a dimension may only be scored from `read`, so
// this number grows one located quote at a time.
func ScoreableOnDimension(labels []*Label, spec *taxonomy.BasisSpec) (scoreable, withDimension int) {
	for _, l := range labels {
		if len(l.Truth.Dimensions) == 0 && len(l.Truth.Techniques) == 0 {
			continue
		}
		withDimension++
		if l.Basis != nil && spec.AllowsAxis("dimension", l.Basis.Dimension) {
			scoreable++
		}
	}
	return scoreable, withDimension
}

// RefutationCoverage reports benign labels with no search record, and records written under a
// different ruleset version.
//
// Both matter for the same reason. "Benign" is the only claim 3,228 samples make, and its
// entire content is which patterns were run and what they found. A missing record makes the
// word mean "nobody looked"; a record from ruleset v1 sitting beside one from v2 makes two
// samples look comparable when the question asked of them was different.
func RefutationCoverage(labels []*Label, wantVersion int) (missing, stale []string) {
	for _, l := range labels {
		if l.Class != Benign {
			continue
		}
		if l.RefutationSearch == nil {
			missing = append(missing, l.ID)
			continue
		}
		if l.RefutationSearch.RulesetVersion != wantVersion {
			stale = append(stale, l.ID)
		}
	}
	return missing, stale
}
