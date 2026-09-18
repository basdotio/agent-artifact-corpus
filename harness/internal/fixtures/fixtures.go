// SPDX-License-Identifier: MIT

// Package fixtures constructs the adversarial sample trees that cannot be checked into git:
// traverse-only directories, FIFOs standing in for a config file, symlink cycles and escapes,
// and files that never end. Git carries neither a 0111 directory bit nor a named pipe, and BSD
// tar cannot reproduce them either (measured), so this family exists only as code that builds it
// on demand. It is the injected-fault half of the corpus — measurement classes 3 (disclosure)
// and 5-7 (invariants, gate, robustness) — where a single counterexample settles the question:
// a scanner either admits it could not read the 0111 directory, or it does not.
//
// Nothing here runs a scanner. A constructor materialises the tree and states, tool-neutrally,
// what a correct scanner must do with it; a runner living beside a scanner points that scanner
// at the tree and checks the claim.
package fixtures

// Class is which measurement class a fixture backs, using the numbers from classification.md.
// It is recorded so a report can say which property has evidence and which is still a bare
// directory — the same declared-hole discipline the rest of the corpus keeps.
type Class int

const (
	// Disclosure: did the scanner ADMIT what it could not read, rather than score the readable
	// remainder as if it were the whole.
	Disclosure Class = 3
	// Robustness: did the scanner survive a malformed or hostile tree without crashing, hanging
	// or following a path out of the sample.
	Robustness Class = 7
)

func (c Class) String() string {
	switch c {
	case Disclosure:
		return "disclosure"
	case Robustness:
		return "robustness"
	default:
		return "unknown"
	}
}

// Fixture is one constructible adversarial tree. Construct builds it under root and returns the
// path a scanner should be pointed at (usually root itself). Expected is the tool-neutral truth:
// what a correct scanner does, phrased so it holds for any scanner rather than naming rule ids.
type Fixture struct {
	Name      string
	Class     Class
	What      string // what the tree is
	Expected  string // what a correct scanner must do — the pass condition, tool-neutral
	Construct func(root string) (entry string, err error)
}

// All returns every fixture in registration order made deterministic by name.
func All() []Fixture {
	return append([]Fixture(nil), registry...)
}

var registry []Fixture

func register(f Fixture) { registry = append(registry, f) }
