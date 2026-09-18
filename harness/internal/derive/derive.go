// SPDX-License-Identifier: MIT

// Package derive turns one upstream dataset's own labels into our three-axis coordinates.
//
// It exists because most of the corpus cannot be hand-pinned: skillsgoat alone is 76 samples,
// skillmd-138k is six figures. But an upstream label is not our label. Upstream taxonomies
// conflate the three axes we deliberately split — skillsgoat's category field mixes what an
// attack achieves (data-exfiltration), how it hides (obfuscation-encoding) and how deep it
// sits (deferred-resolution). So derivation is per-axis: the honest axes (tier from an id
// prefix, severity and class from named fields) are read mechanically, and the lossy one
// (dimension and evasion, from a category map) is read through a stated, checkable mapping.
//
// Every coordinate this package produces is marked origin.type `derived`, carries a
// derived_from pointer, and is reported at a lower credibility tier than a hand-pinned truth.
// Nothing here runs a scanner: the coordinates come from the upstream's own labels, so there
// is no run whose result could leak into the answer.
package derive

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// upstreamLabel is the subset of an upstream expected.yaml we read. Unknown fields are
// ignored on purpose here — an upstream file carries much we do not use, and rejecting it
// would couple us to their whole schema.
type upstreamLabel struct {
	ID         string   `yaml:"id"`
	Verdict    string   `yaml:"verdict"`
	Severity   string   `yaml:"severity"`
	Categories []string `yaml:"categories"`
}

// Coord is the coordinate set derived for one upstream sample. It is deliberately not a
// label.Label: this package decides coordinates, and turning them into on-disk labels (and
// deciding which get vendored) is a later, separate step.
type Coord struct {
	UpstreamID string
	SamplePath string // relative to the fetched root
	Class      string
	Dimensions []string
	Evasion    []string
	Tier       string
	Severity   string

	// Source is the originating repository when the entry is a collection of them. Empty means
	// the entry itself is the source.
	Source string

	// HandReadDimension is true when the dimension came from a dimension_overrides entry
	// rather than the category map: a person read the sample because the upstream labelled it
	// by technique and never said what it achieves. It is tracked so the two kinds of
	// confidence are never summed into one "derived" number.
	HandReadDimension bool

	// DimensionEvidence is the quote backing a hand-read dimension, when the override records
	// one. Nil means the judgement was made and its reasoning lives somewhere no checker can
	// reach — which is the state 79 overrides started in.
	DimensionEvidence *manifest.Evidence
}

// Result is a derivation's output together with the accounting a reviewer needs: which
// upstream categories were seen and how often, so the mapping's coverage is inspectable
// rather than assumed.
type Result struct {
	Coords       []Coord
	CategorySeen map[string]int

	// HandRead counts samples whose dimension came from a hand-read override.
	HandRead int

	// Excluded counts samples left out by exclude_tokens. Declared exclusions are counted so a
	// shrinking denominator is never invisible.
	Excluded int

	// ExcludedByName carries the reason for each per-sample exclusion, because a count alone
	// turns a judgement about ten specific files into an anonymous number.
	ExcludedByName []string

	// Skipped counts layout matches that carried no upstream label. skillsgoat's pasture holds
	// 66 single-artifact samples with an expected.yaml and 35 compound-chain nodes without
	// one; the chains need a different, multi-node derivation. Skipping them is correct but it
	// must be visible, not silent, or the recall denominator quietly shrinks.
	Skipped int
}

// Derive reads the upstream at root according to e.Derive and returns our coordinates. A
// non-empty error slice means the derivation is not trustworthy as-is: an upstream category
// with no mapping, an axis target that is not in the vocabulary, or a malicious sample from
// which no dimension could be read. None of these are dropped silently — an unmapped category
// left out would quietly shrink a recall denominator.
func Derive(e manifest.Entry, root string, tax *taxonomy.Set) (*Result, []error) {
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	d := e.Derive
	if d == nil {
		return nil, []error{fmt.Errorf("%s: no derive block; this entry cannot be derived from", e.ID)}
	}

	// Semantic check of the map targets, which the manifest package could not do without a
	// taxonomy dependency. The value after the colon must be a real member of its axis.
	for cat, targets := range d.CategoryAxisMap {
		for _, target := range targets {
			axis, val, ok := splitTarget(target)
			if !ok {
				continue // shape already reported by manifest.Validate
			}
			switch axis {
			case "dim":
				if !oneOf(val, tax.Dimensions) {
					bad("%s: category_axis_map[%q] targets dimension %q, which is not in the vocabulary", e.ID, cat, val)
				}
			case "evasion":
				if _, ok := tax.Evasions[val]; !ok {
					bad("%s: category_axis_map[%q] targets evasion %q, which is not in the vocabulary", e.ID, cat, val)
				}
			case "tier":
				if _, ok := tax.Tiers[val]; !ok {
					bad("%s: category_axis_map[%q] targets tier %q, which is not in the vocabulary", e.ID, cat, val)
				}
			}
		}
	}

	for id, ov := range d.DimensionOverrides {
		for _, dim := range ov.Dimensions {
			if !oneOf(dim, tax.Dimensions) {
				bad("%s: dimension_overrides[%q] names %q, which is not a dimension in the vocabulary", e.ID, id, dim)
			}
		}
	}
	for id, evs := range d.EvasionOverrides {
		for _, ev := range evs {
			if _, ok := tax.Evasions[ev]; !ok {
				bad("%s: evasion_overrides[%q] names %q, which is not in the closed vocabulary", e.ID, id, ev)
			}
		}
	}
	for id, t := range d.TierOverrides {
		if _, ok := tax.Tiers[t]; !ok {
			bad("%s: tier_overrides[%q] is %q, which is not a tier", e.ID, id, t)
		}
	}

	// An override keyed on a sample that does not exist does nothing at all, silently — a typo
	// in a hand-read judgement would simply not apply, and the coordinate it was written to fix
	// would ship wrong while the manifest looked like it had been handled.
	usedOverride := map[string]bool{}

	// Absent means the default; explicitly empty means the upstream has no per-sample label.
	labelFile := "expected.yaml"
	if d.LabelFile != nil {
		labelFile = *d.LabelFile
	}

	dirs, skipped, err := sampleDirs(root, d.Layout, labelFile, d.SampleIsFile)
	if err != nil {
		return nil, []error{fmt.Errorf("%s: %w", e.ID, err)}
	}

	res := &Result{CategorySeen: map[string]int{}, Skipped: skipped}
	for _, dir := range dirs {
		up, err := readUpstream(dir, labelFile)
		if err != nil {
			bad("%s: %v", e.ID, err)
			continue
		}
		if d.SampleIsFile {
			base := filepath.Base(dir)
			up.ID = strings.TrimSuffix(base, filepath.Ext(base))
		}
		if rest, ok := strings.CutPrefix(d.IDFrom, "path-segments:"); ok {
			var parts []string
			for _, n := range strings.Split(rest, ",") {
				if seg := pathSegment(dir, strings.TrimSpace(n)); seg != "" {
					parts = append(parts, seg)
				}
			}
			if len(parts) > 0 {
				up.ID = strings.Join(parts, "-")
			}
		}
		rel, _ := filepath.Rel(root, dir)
		c := Coord{UpstreamID: up.ID, SamplePath: rel}
		if spec, ok := strings.CutPrefix(d.SourceFrom, "sidecar:"); ok {
			file, field, found := strings.Cut(spec, ":")
			if !found {
				bad("%s: source_from %q must be sidecar:<file>:<field>", e.ID, d.SourceFrom)
			} else {
				// The sidecar sits beside the tree, named after it, exactly as a label does.
				name := filepath.Base(dir)
				sc := filepath.Join(filepath.Dir(dir), strings.ReplaceAll(file, "<name>", name))
				b, rerr := os.ReadFile(sc)
				if rerr != nil {
					bad("%s/%s: source_from sidecar %s is missing", e.ID, up.ID, filepath.Base(sc))
				} else {
					var m map[string]any
					if jerr := json.Unmarshal(b, &m); jerr != nil {
						bad("%s/%s: sidecar %s is not JSON: %v", e.ID, up.ID, filepath.Base(sc), jerr)
					} else if v, has := m[field]; !has {
						bad("%s/%s: sidecar %s has no field %q", e.ID, up.ID, filepath.Base(sc), field)
					} else {
						c.Source = fmt.Sprint(v)
					}
				}
			}
		}
		if n, ok := strings.CutPrefix(d.SourceFrom, "dirname-parts:"); ok {
			want := 0
			fmt.Sscanf(n, "%d", &want)
			if parts := strings.Split(filepath.Base(dir), "__"); want > 0 && len(parts) >= want {
				c.Source = strings.Join(parts[:want], "/")
			}
		}

		verdict := resolve(d.ClassFrom, up.Verdict, dir)
		switch verdict {
		case "malicious":
			c.Class = "malicious"
		case "benign":
			// An upstream benign is a plain benign to us. Some are deliberate decoys, which is
			// hard-negative-shaped, but we cannot derive resembles/differs_by from an upstream
			// that does not record them, and inventing them would be a hand-pin wearing a
			// derived label. So it lands as benign, and its decoy nature travels in prose.
			c.Class = "benign"
		default:
			bad("%s/%s: resolved class %q is neither malicious nor benign", e.ID, up.ID, verdict)
			continue
		}

		if c.Class == "malicious" {
			c.Severity = resolve(d.SeverityFrom, up.Severity, dir)
			// Tier goes through the same sources as every other axis. It did not, and a
			// `constant:` tier fell through silently: 121 samples would have been written with
			// no tier at all, for the validator to reject one step later.
			switch {
			case strings.HasPrefix(d.TierFrom, "constant:"):
				c.Tier = strings.TrimPrefix(d.TierFrom, "constant:")
				if _, ok := tax.Tiers[c.Tier]; !ok {
					bad("%s: tier_from asserts %q, which is not a tier in the vocabulary", e.ID, c.Tier)
				}
			case d.TierFrom == "id-prefix" || d.TierFrom == "":
				if tok := prefixToken(filepath.Base(dir)); tok != "" {
					if t, ok := tax.TierByMapsToken(tok); ok {
						c.Tier = t.ID
					} else {
						bad("%s/%s: id prefix %q maps to no tier via any tier's maps_to", e.ID, up.ID, tok)
					}
				} else {
					bad("%s/%s: no numeric id prefix to read a tier from", e.ID, up.ID)
				}
			}
		}

		tokens := categoryTokens(d, up, dir)
		if slices.ContainsFunc(tokens, func(t string) bool { return slices.Contains(d.ExcludeTokens, t) }) {
			res.Excluded++
			continue
		}
		for _, cat := range tokens {
			res.CategorySeen[cat]++
			targets, mapped := d.CategoryAxisMap[cat]
			if !mapped {
				bad("%s: upstream category %q has no category_axis_map entry — map it to dim:, "+
					"evasion:, tier: or ignore; leaving it out silently drops the axis it carries", e.ID, cat)
				continue
			}
			for _, target := range targets {
				axis, val, ok := splitTarget(target)
				if !ok {
					continue
				}
				switch axis {
				case "dim":
					if c.Class == "malicious" {
						c.Dimensions = appendUnique(c.Dimensions, val)
					}
				case "evasion":
					if c.Class == "malicious" {
						c.Evasion = appendUnique(c.Evasion, val)
					}
				case "tier":
					// Where an id prefix gave a tier it is authoritative and a disagreement is
					// surfaced. Where it did not, the token is the only tier source there is.
					switch {
					case c.Tier == "":
						c.Tier = val
					case c.Tier != val:
						bad("%s/%s: id prefix says tier %q but token %q says %q", e.ID, up.ID, c.Tier, cat, val)
					}
				case "ignore":
				}
			}
		}

		if reason, ok := d.ExcludeSamples[up.ID]; ok {
			usedOverride[up.ID] = true
			res.Excluded++
			res.ExcludedByName = append(res.ExcludedByName, fmt.Sprintf("%s — %s", up.ID, reason))
			continue
		}

		if override, ok := d.DimensionOverrides[up.ID]; ok {
			usedOverride[up.ID] = true
			switch {
			case sameSet(c.Dimensions, override.Dimensions):
				// Stale means the override says what the RULE already says. It used to mean
				// "the rule produced anything at all", which made the mechanism able to fill a
				// gap and unable to correct an error — and correcting errors is most of what a
				// hand-read dimension is for: a category that is right for eight of its members
				// and wrong for two needs the two overridden, not the category deleted.
				bad("%s/%s: dimension_overrides says %v and the category map already yields the "+
					"same — remove the override, it is stale", e.ID, up.ID, override.Dimensions)
			case c.Class != "malicious":
				bad("%s/%s: has a dimension_overrides entry but is not malicious; only malicious "+
					"samples sit on the recall axis", e.ID, up.ID)
			default:
				// Replaces, like evasion_overrides. A hand-read dimension is the considered
				// value for this sample; appending would leave the rejected one beside it.
				c.Dimensions = append([]string{}, override.Dimensions...)
				c.HandReadDimension = true
				// The evidence travels with the coordinate so the generated label can carry a
				// `read` basis. Absent evidence is not an error: the override is still a real
				// hand-read judgement, it simply cannot be verified, and the label says so by
				// claiming no basis for the axis rather than one it cannot support.
				c.DimensionEvidence = override.Evidence
				res.HandRead++
			}
		}

		// A hand-read evasion REPLACES whatever the category map produced rather than adding
		// to it: the map's value is the family, the override is the member, and keeping both
		// would assert two mechanisms where the sample has one.
		if override, ok := d.EvasionOverrides[up.ID]; ok {
			usedOverride[up.ID] = true
			if c.Class != "malicious" {
				bad("%s/%s: has an evasion_overrides entry but is not malicious", e.ID, up.ID)
			} else {
				c.Evasion = append([]string{}, override...)
				res.HandRead++
			}
		}
		if override, ok := d.TierOverrides[up.ID]; ok {
			usedOverride[up.ID] = true
			switch {
			case c.Class != "malicious":
				bad("%s/%s: has a tier_overrides entry but is not malicious", e.ID, up.ID)
			case c.Tier == override:
				// The mechanical rule now agrees, so the hand-read entry is doing nothing and
				// would outlive the reason it was written.
				bad("%s/%s: tier_overrides says %q and the derivation already yields %q — remove "+
					"the override, it is stale", e.ID, up.ID, override, c.Tier)
			default:
				c.Tier = override
				res.HandRead++
			}
		}

		// Caught here rather than left for the validator, so a derivation reports its own
		// incompleteness instead of writing labels that fail one step later.
		if c.Class == "malicious" && c.Tier == "" {
			bad("%s/%s: no tier could be resolved from tier_from %q", e.ID, up.ID, d.TierFrom)
		}
		if c.Class == "malicious" && len(c.Dimensions) == 0 {
			bad("%s/%s: no category mapped to a dimension and no dimension_overrides entry, so "+
				"this malicious sample sits on no recall axis. Its categories were %v — either "+
				"map a category to a dimension, or read the sample and record what it achieves "+
				"in dimension_overrides", e.ID, up.ID, up.Categories)
		}
		res.Coords = append(res.Coords, c)
	}

	for _, m := range []struct {
		name string
		keys []string
	}{
		{"exclude_samples", keysOf(d.ExcludeSamples)},
		{"dimension_overrides", keysOfOverrides(d.DimensionOverrides)},
		{"evasion_overrides", keysOfSlice(d.EvasionOverrides)},
		{"tier_overrides", keysOf(d.TierOverrides)},
	} {
		for _, k := range m.keys {
			if !usedOverride[k] {
				bad("%s: %s[%q] matched no upstream sample. A hand-read judgement keyed on a "+
					"sample that does not exist applies to nothing and says so nowhere", e.ID, m.name, k)
			}
		}
	}

	sort.Slice(res.Coords, func(i, j int) bool { return res.Coords[i].UpstreamID < res.Coords[j].UpstreamID })
	return res, errs
}

// sampleDirs expands the layout glob to the sample directories under root, and returns how
// many matches were skipped for having no expected.yaml. A sample directory is defined as one
// that carries an upstream label; a layout match without one is an intermediate directory
// (skillsgoat's compound-chain nodes are the case) and is counted, not read.
func sampleDirs(root, layout, labelFile string, isFile bool) (dirs []string, skipped int, err error) {
	if layout == "" {
		return nil, 0, fmt.Errorf("derive.layout is empty")
	}
	matches, err := filepath.Glob(filepath.Join(root, filepath.FromSlash(layout)))
	if err != nil {
		return nil, 0, fmt.Errorf("layout glob %q: %w", layout, err)
	}
	for _, m := range matches {
		fi, err := os.Stat(m)
		if err != nil {
			continue
		}
		if isFile {
			// Each match is the sample itself; it gets wrapped in a directory when written.
			if fi.Mode().IsRegular() {
				dirs = append(dirs, m)
			}
			continue
		}
		if !fi.IsDir() {
			continue
		}
		if labelFile != "" {
			if _, err := os.Stat(filepath.Join(m, labelFile)); err != nil {
				skipped++
				continue
			}
		}
		dirs = append(dirs, m)
	}
	sort.Strings(dirs)
	if len(dirs) == 0 {
		return nil, skipped, fmt.Errorf("layout %q matched no sample directories under %s — is the corpus fetched?", layout, root)
	}
	return dirs, skipped, nil
}

func readUpstream(dir, labelFile string) (*upstreamLabel, error) {
	// An upstream with no per-sample label is a legitimate shape, not an error: skillcraft-audit
	// encodes everything in its directory layout. The sample directory name still identifies it.
	if labelFile == "" {
		return &upstreamLabel{ID: filepath.Base(dir)}, nil
	}
	b, err := os.ReadFile(filepath.Join(dir, labelFile))
	if err != nil {
		return nil, fmt.Errorf("read %s in %s: %w", labelFile, filepath.Base(dir), err)
	}
	var up upstreamLabel
	if err := yaml.Unmarshal(b, &up); err != nil {
		return nil, fmt.Errorf("parse expected.yaml in %s: %w", filepath.Base(dir), err)
	}
	if up.ID == "" {
		up.ID = filepath.Base(dir)
	}
	return &up, nil
}

// resolve reads one axis from its configured source. An empty spec falls back to the value
// already read from the upstream label, which keeps entries written before these sources
// existed working unchanged.
func resolve(spec, fromLabel, dir string) string {
	switch {
	case spec == "":
		return fromLabel
	case strings.HasPrefix(spec, "constant:"):
		return strings.TrimPrefix(spec, "constant:")
	case strings.HasPrefix(spec, "field:"):
		return fromLabel
	case strings.HasPrefix(spec, "path-segment:"):
		return pathSegment(dir, strings.TrimPrefix(spec, "path-segment:"))
	}
	return fromLabel
}

// categoryTokens are the strings fed to category_axis_map. They come from a list field in the
// upstream label, or from directory names when the upstream labels by layout.
func categoryTokens(d *manifest.Derive, up *upstreamLabel, dir string) []string {
	spec := d.CategoryFrom
	if spec == "" || strings.HasPrefix(spec, "field:") {
		return up.Categories
	}
	if rest, ok := strings.CutPrefix(spec, "path-segments:"); ok {
		var out []string
		for _, n := range strings.Split(rest, ",") {
			if seg := pathSegment(dir, strings.TrimSpace(n)); seg != "" {
				out = append(out, seg)
			}
		}
		return out
	}
	return up.Categories
}

// pathSegment returns the directory name n levels above the sample directory; 0 is the sample
// directory itself.
// pathSegment returns the directory name n levels above the sample; 0 is the sample itself.
// For a file-shaped sample, 0 is the file and 1 is the directory holding it, which is where a
// corpus that labels by layout keeps its category.
func pathSegment(dir, n string) string {
	depth := 0
	fmt.Sscanf(n, "%d", &depth)
	p := filepath.Clean(dir)
	for range depth {
		p = filepath.Dir(p)
	}
	return filepath.Base(p)
}

// prefixToken returns the leading numeric token of a directory name ("200-foo" -> "200"), or
// "" if there is none.
func prefixToken(name string) string {
	i := strings.IndexByte(name, '-')
	if i <= 0 {
		return ""
	}
	tok := name[:i]
	for _, r := range tok {
		if r < '0' || r > '9' {
			return ""
		}
	}
	return tok
}

// splitTarget parses "dim:backdoor" into ("dim", "backdoor", true). "ignore" parses to
// ("ignore", "", true).
func splitTarget(t string) (axis, val string, ok bool) {
	if t == "ignore" {
		return "ignore", "", true
	}
	i := strings.IndexByte(t, ':')
	if i <= 0 || i == len(t)-1 {
		return "", "", false
	}
	return t[:i], t[i+1:], true
}

func appendUnique(xs []string, x string) []string {
	if slices.Contains(xs, x) {
		return xs
	}
	return append(xs, x)
}

func oneOf(v string, set []string) bool { return slices.Contains(set, v) }

func keysOf(m map[string]string) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func keysOfSlice(m map[string][]string) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func keysOfOverrides(m map[string]manifest.DimensionOverride) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func keysOfTargets(m map[string]manifest.Targets) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// sameSet reports whether two dimension lists carry the same members, order aside.
func sameSet(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	seen := map[string]int{}
	for _, x := range a {
		seen[x]++
	}
	for _, x := range b {
		seen[x]--
	}
	for _, n := range seen {
		if n != 0 {
			return false
		}
	}
	return true
}
