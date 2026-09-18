// SPDX-License-Identifier: MIT

package taxonomy

import (
	"fmt"
	"path/filepath"
	"slices"
)

// BasisSpec is taxonomy/basis.yaml: what a data point's truth rests on.
//
// The corpus already had four axes describing WHAT a sample is. None of them recorded HOW
// that was established, and the difference was invisible in a label file: a coordinate a
// person read off the artifact and a coordinate a constant supplied looked identical. They
// are not remotely the same claim, and a scorer has to be able to tell them apart.
//
// The values are not ranked and nothing may average them. The only defined operations are
// FILTER (score this axis only from these bases) and REPORT SEPARATELY.
type BasisSpec struct {
	Version int

	// Order is the declaration order, which reports follow so that two runs list the bases
	// the same way.
	Order  []string
	Values map[string]BasisValue

	// Requires maps a basis to the fields a label must supply to claim it. Claiming a basis
	// without them would make it an assertion with nothing attached that a reader could
	// check, which is the condition this whole vocabulary exists to end.
	Requires map[string][]string

	// Scores maps a scoring axis to the bases allowed to support it.
	Scores map[string][]string

	// Debt names basis/class combinations that are reported as outstanding rather than
	// accepted. They do not fail the build — they are the honest description of the corpus
	// today — but they must stay visible or they become permanent by inattention.
	Debt []DebtRule
}

// BasisValue is one member of the vocabulary. `Not` carries the same weight it does for a
// dimension: it names the confusable neighbour and the element that decides between them.
type BasisValue struct {
	ID   string `yaml:"id"`
	What string `yaml:"what"`
	Not  string `yaml:"not"`
}

// DebtRule marks a combination that is tolerated and counted, never silently accepted.
type DebtRule struct {
	Basis string   `yaml:"basis"`
	Class []string `yaml:"class"`
	Why   string   `yaml:"why"`
}

type basisFile struct {
	Version  int                 `yaml:"version"`
	Values   []BasisValue        `yaml:"values"`
	Requires map[string][]string `yaml:"requires"`
	Scores   map[string][]string `yaml:"scores"`
	Debt     []DebtRule          `yaml:"report_as_debt"`
}

// LoadBasis reads taxonomy/basis.yaml from dir.
func LoadBasis(dir string) (*BasisSpec, error) {
	var bf basisFile
	if err := decodeFile(filepath.Join(dir, "basis.yaml"), &bf); err != nil {
		return nil, err
	}

	s := &BasisSpec{
		Version:  bf.Version,
		Values:   map[string]BasisValue{},
		Requires: bf.Requires,
		Scores:   bf.Scores,
		Debt:     bf.Debt,
	}
	for _, v := range bf.Values {
		if _, dup := s.Values[v.ID]; dup {
			// A duplicate silently drops one definition, and the one that survives depends on
			// map iteration — a vocabulary that means something different per run.
			return nil, fmt.Errorf("basis.yaml: %q is defined twice", v.ID)
		}
		s.Values[v.ID] = v
		s.Order = append(s.Order, v.ID)
	}
	if len(s.Order) == 0 {
		return nil, fmt.Errorf("basis.yaml: no values defined")
	}
	if s.Requires == nil {
		s.Requires = map[string][]string{}
	}
	if s.Scores == nil {
		s.Scores = map[string][]string{}
	}
	return s, nil
}

// Known reports whether id is in the closed vocabulary.
func (b *BasisSpec) Known(id string) bool {
	_, ok := b.Values[id]
	return ok
}

// AllowsAxis reports whether a coordinate resting on this basis may be scored on this axis.
// An unknown axis returns false: a scorer asking about an axis nobody declared should get a
// refusal, not a permissive default.
func (b *BasisSpec) AllowsAxis(axis, basis string) bool {
	allowed, ok := b.Scores[axis]
	if !ok {
		return false
	}
	return slices.Contains(allowed, basis)
}

// RequiredFields lists the fields a label must carry to claim this basis.
func (b *BasisSpec) RequiredFields(basis string) []string {
	return b.Requires[basis]
}

// IsDebt reports whether this basis/class pair is outstanding work, with the reason.
func (b *BasisSpec) IsDebt(basis, class string) (string, bool) {
	for _, d := range b.Debt {
		if d.Basis == basis && slices.Contains(d.Class, class) {
			return d.Why, true
		}
	}
	return "", false
}

// ValidateBasis checks the vocabulary itself. A vocabulary that references values it does
// not define produces validation errors nobody can act on, and a value with no `not` lets
// two bases be used interchangeably — which is precisely how `assumed` ends up recorded as
// `derived`.
func (b *BasisSpec) ValidateBasis() []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	if b.Version < 1 {
		bad("basis.yaml: version must be >= 1, got %d", b.Version)
	}
	for _, id := range b.Order {
		v := b.Values[id]
		if v.What == "" {
			bad("basis %q has no `what`", id)
		}
		if v.Not == "" {
			bad("basis %q has no `not` — the neighbouring value it must not be confused "+
				"with, and the element that decides between them", id)
		}
		if len(b.Requires[id]) == 0 {
			bad("basis %q requires no companion field — it could then be claimed with "+
				"nothing attached for a reader to check", id)
		}
	}
	for id := range b.Requires {
		if !b.Known(id) {
			bad("`requires` names basis %q, which is not defined", id)
		}
	}
	for axis, allowed := range b.Scores {
		if len(allowed) == 0 {
			bad("axis %q is scored from no basis at all, so it can never be scored", axis)
		}
		for _, id := range allowed {
			if !b.Known(id) {
				bad("axis %q is scored from %q, which is not a defined basis", axis, id)
			}
		}
	}
	for _, d := range b.Debt {
		if !b.Known(d.Basis) {
			bad("`report_as_debt` names basis %q, which is not defined", d.Basis)
		}
		if d.Why == "" {
			bad("debt rule for basis %q has no `why` — an outstanding item with no stated "+
				"cost is indistinguishable from an accepted one", d.Basis)
		}
	}
	return errs
}
