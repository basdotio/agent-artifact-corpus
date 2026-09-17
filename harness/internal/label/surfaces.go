// SPDX-License-Identifier: MIT

package label

import (
	"fmt"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// Surfaces is the set of agent load paths one artifact sits on, written in YAML as either a
// scalar or a list. The scalar form stays the normal case — most artifacts sit on exactly one
// load path, and `surface: skills` reads better than `surface: [skills]` three thousand times
// over. The list form exists for the artifacts that genuinely span two, which the world
// produces and the schema previously could not record. See Label.Surface.
type Surfaces []string

func (s *Surfaces) UnmarshalYAML(value *yaml.Node) error {
	var one string
	if err := value.Decode(&one); err == nil {
		*s = Surfaces{one}
		return nil
	}
	var many []string
	if err := value.Decode(&many); err != nil {
		return fmt.Errorf("surface must be a string or a list of strings: %w", err)
	}
	*s = many
	return nil
}

// MarshalYAML writes a single surface back as a scalar, so a round-trip does not rewrite
// three thousand labels into a form nobody asked for.
func (s Surfaces) MarshalYAML() (any, error) {
	if len(s) == 1 {
		return s[0], nil
	}
	return []string(s), nil
}

// Primary is the surface that owns the sample's directory. A multi-surface artifact still
// lives at exactly one path — duplicating the tree would put the same bytes in two samples,
// which is the leakage the corpus rejects elsewhere — so the first entry decides where, and
// validate() checks the path against it.
func (s Surfaces) Primary() string {
	if len(s) == 0 {
		return ""
	}
	return s[0]
}

func (s Surfaces) Has(surface string) bool {
	for _, v := range s {
		if v == surface {
			return true
		}
	}
	return false
}

func (s Surfaces) String() string { return strings.Join(s, "+") }

// validate reports every problem with the set rather than the first, and rejects a duplicate
// outright: `[hooks, hooks]` would double-count one artifact in a per-surface report, which is
// the same defect as vendoring the tree twice, only harder to see.
func (s Surfaces) validate(bad func(string, ...any)) {
	if len(s) == 0 {
		bad("surface is empty — it must say which load path(s) the artifact sits on, one of %s",
			strings.Join(validSurfaces, ", "))
		return
	}
	seen := map[string]bool{}
	for _, v := range s {
		if !oneOf(v, validSurfaces) {
			bad("surface %q is not one of %s", v, strings.Join(validSurfaces, ", "))
		}
		if seen[v] {
			bad("surface %q is listed twice — a per-surface count would credit one artifact twice", v)
		}
		seen[v] = true
	}
}

// sortedSurfaces is a stable ordering for reports, by the canonical order in validSurfaces so
// the columns of `corpus stats` do not move when a new surface gains its first sample.
func sortedSurfaces(set map[string]bool) []string {
	rank := map[string]int{}
	for i, v := range validSurfaces {
		rank[v] = i
	}
	out := make([]string, 0, len(set))
	for v := range set {
		out = append(out, v)
	}
	sort.Slice(out, func(i, j int) bool { return rank[out[i]] < rank[out[j]] })
	return out
}
