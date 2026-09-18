// SPDX-License-Identifier: MIT

// Package refute runs taxonomy/refutation.yaml over the benign half of the corpus.
//
// 3,241 benign samples cannot each be proven harmless. What can be done is to search for a
// small closed set of things whose presence means a sample is UNFIT TO BE COUNTED, and to
// record that the search ran. "Benign" then stops meaning "nobody looked" and starts meaning
// "searched with this ruleset, at this version, nothing matched".
//
// THE TRAP, restated here because it is easy to undo by accident:
//
// If these patterns drifted into "suspicious content" rules, the corpus would be defining
// truth with its own scanner, and every figure it produced would measure agreement with us
// rather than detection. The guard is arithmetic, not discipline. An audit read 250 benign
// samples: 97 of them (39%) contain something a defensible scanner would fire on, and ALL 97
// MUST STAY — they are the precision test. Exactly one was genuinely unfit.
//
//	Target hit rate is about 1%. A change that moves it toward 39% has turned this into a
//	scanner and must be reverted rather than tuned.
//
// So each pattern answers "is this sample, as an object, fit to be counted?" — never "would
// a scanner alert here?"
package refute

import (
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"
)

// Ruleset is taxonomy/refutation.yaml.
type Ruleset struct {
	Version  int
	Actions  []Action
	Patterns []Pattern
}

// Action is what happens on a match. Every one of them ends in a decision that gets written
// down: an exclusion with no recorded reason is how a corpus quietly starts flattering
// itself.
type Action struct {
	ID   string `yaml:"id"`
	What string `yaml:"what"`
}

// Pattern is one disqualifying shape. `Not` carries the boundary, and it is the field that
// keeps the hit rate near 1% instead of 39%.
type Pattern struct {
	ID           string `yaml:"id"`
	What         string `yaml:"what"`
	Not          string `yaml:"not"`
	Signal       string `yaml:"signal"`
	OnMatch      string `yaml:"on_match"`
	ExpectedRate string `yaml:"expected_rate"`
}

type refutationFile struct {
	Version  int       `yaml:"version"`
	Actions  []Action  `yaml:"on_match_actions"`
	Patterns []Pattern `yaml:"patterns"`
	// SearchRecordShape documents the per-sample record. It is read so that KnownFields does
	// not reject the file, and is not otherwise used here.
	SearchRecordShape map[string]string `yaml:"search_record_shape"`
}

// Sample is what the engine sees. Content is the concatenated text of the sample tree and
// Hashes are the per-file content digests — enough for every pattern that can be decided
// mechanically, and nothing that would let a pattern reach for a label.
type Sample struct {
	ID      string
	Class   string
	Content string
	Hashes  []string
}

// Load reads taxonomy/refutation.yaml from dir.
func Load(dir string) (*Ruleset, error) {
	b, err := os.ReadFile(filepath.Join(dir, "refutation.yaml"))
	if err != nil {
		return nil, fmt.Errorf("read refutation.yaml: %w", err)
	}
	dec := yaml.NewDecoder(strings.NewReader(string(b)))
	dec.KnownFields(true) // a typo'd field is a silently disabled pattern
	var rf refutationFile
	if err := dec.Decode(&rf); err != nil {
		return nil, fmt.Errorf("parse refutation.yaml: %w", err)
	}
	return &Ruleset{Version: rf.Version, Actions: rf.Actions, Patterns: rf.Patterns}, nil
}

// KnownAction reports whether id is a declared on_match action.
func (r *Ruleset) KnownAction(id string) bool {
	return slices.ContainsFunc(r.Actions, func(a Action) bool { return a.ID == id })
}

// Validate checks the ruleset itself.
func (r *Ruleset) Validate() []error {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	if r.Version < 1 {
		bad("refutation.yaml: version must be >= 1, got %d", r.Version)
	}
	if len(r.Patterns) == 0 {
		bad("refutation.yaml: no patterns, so every benign label would record a search that " +
			"could not have found anything")
	}
	seen := map[string]bool{}
	for _, p := range r.Patterns {
		if seen[p.ID] {
			bad("refutation.yaml: pattern %q is defined twice", p.ID)
		}
		seen[p.ID] = true
		if p.What == "" {
			bad("pattern %q has no `what`", p.ID)
		}
		if p.Not == "" {
			bad("pattern %q has no `not` — the boundary is what keeps a disqualifier from "+
				"growing into a scanner", p.ID)
		}
		if !r.KnownAction(p.OnMatch) {
			bad("pattern %q has on_match %q, which is not a declared action", p.ID, p.OnMatch)
		}
	}
	return errs
}
