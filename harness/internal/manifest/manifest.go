// SPDX-License-Identifier: MIT

// Package manifest describes layer 2: external corpora referenced by url+commit+sha256 and
// never vendored.
//
// The layer exists for a legal reason and a measurement reason, and they point the same way.
// Recording a URL and a hash is not distribution, so this layer may reference no-license,
// NonCommercial, ShareAlike and copyleft corpora that layer 1 must never contain. And the
// corpora that matter most for false-positive and recall rates are exactly the ones we did
// not write, so the layer that carries them is the layer the published numbers come from.
package manifest

import (
	"fmt"
	"os"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

type File struct {
	Entries []Entry `yaml:"entries"`

	// Adjudications are decisions about refutation matches, keyed by sample id. Top level
	// rather than per-entry because a match is about a SAMPLE, and the same pattern fires
	// across populations — keying them under one upstream would put the record in a place
	// nobody would think to look for the others.
	Adjudications map[string]Adjudication `yaml:"adjudications"`
}

type Entry struct {
	ID      string `yaml:"id"`
	Name    string `yaml:"name"`
	URL     string `yaml:"url"`
	Commit  string `yaml:"commit"`
	SHA256  string `yaml:"sha256"`
	License string `yaml:"license"`
	Role    string `yaml:"role"` // fp-denominator | recall | hard-negative | touchstone | probe

	// Provenance is whether this upstream's artifacts EXISTED IN THE WORLD or were authored as
	// test cases, and it is separate from Role and from who wrote them on purpose.
	//
	// It exists because `derived` conflated two things that must not share a number. A sample
	// not written by us is not therefore a draw from the world: cisco's 127 are `Example 5`,
	// `Example 10` — numbered fixtures Cisco authored to exercise its own scanner — and
	// skillsgoat is a training range that ships deliberate decoys. Both are external, neither
	// is wild. Before this field the scorer put all 248 such samples in the bucket whose header
	// said "a rate is a claim about the world", alongside the 22 that actually are.
	//
	// `wild`    the artifact existed because somebody made it for real — a committed config, a
	//           captured attack. Only these can back a claim about the world.
	// `fixture` a third party authored it as a test case. Real enough to be worth catching and
	//           not ours to imagine, but coverage of THEIR chosen shapes, not a sample of the
	//           world's.
	//
	// Samples we author ourselves never reach here: their labels carry origin.type
	// `reconstruction` or `synthetic` and the scorer classes them from that.
	Provenance string `yaml:"provenance"`

	// Counts are what the source claims, recorded so that a later fetch disagreeing with
	// them is visible rather than silently changing a denominator.
	Malicious int `yaml:"malicious"`
	Benign    int `yaml:"benign"`

	// Subset narrows the fetch to the part that is actually corpus.
	Subset string `yaml:"subset"`

	// Overlaps names other entry IDs that share samples. make stats refuses to pool totals
	// across overlapping entries, because that sum errs in the safe-looking direction.
	Overlaps []string `yaml:"overlaps"`

	// Hazards are the traps that produce a good score for a bad reason. Every entry must
	// declare at least one or explicitly say none; an undeclared hazard is how a corpus
	// gets used wrong by the next person.
	Hazards []string `yaml:"hazards"`

	// Prep is the mandatory preparation before the entry may be counted — deduplication,
	// deleting a leaking file. Empty means none needed.
	Prep []string `yaml:"prep"`

	Vendorable bool `yaml:"vendorable"`

	// Derive states how this upstream's own labels map onto our three axes, so a rule can
	// produce derived coordinates instead of a person hand-pinning every sample. Absent means
	// this corpus cannot be derived from and its samples, if used, must be pinned by hand.
	Derive *Derive `yaml:"derive"`
}

// Targets is one or more axis placements for a single upstream token, written in YAML as
// either a scalar or a list. One token frequently carries two facts at once: skillcraft-audit's
// `hard` says both how deep the sample sits and that a compliance narrative is what buries it.
// Forcing a single target would mean dropping one of them, and a silently dropped mechanism is
// exactly the quiet loss this corpus exists to refuse.
type Targets []string

func (t *Targets) UnmarshalYAML(value *yaml.Node) error {
	var one string
	if err := value.Decode(&one); err == nil {
		*t = Targets{one}
		return nil
	}
	var many []string
	if err := value.Decode(&many); err != nil {
		return fmt.Errorf("category_axis_map value must be a string or a list of strings: %w", err)
	}
	*t = many
	return nil
}

// Derive is the rule that turns one upstream dataset's labels into our coordinates.
//
// It is per-axis on purpose. Upstream taxonomies conflate the three axes we deliberately
// split: skillsgoat's category list mixes what an attack achieves (data-exfiltration), how
// it hides (obfuscation-encoding) and how deep it sits (deferred-resolution) on one field.
// So there is no single mapping; each axis is read from wherever that dataset happens to
// keep it, and the honest ones (tier from an id prefix, severity from a field) are separated
// from the lossy one (dimension and evasion from a category map).
// Transform is one declared edit to the vendored bytes.
//
// AppliedTo is the count we claim it makes, and it is checked against the count actually
// made. That pairing is the whole point: a declaration nobody verifies is how the manifest
// ends up describing a corpus that no longer exists, which this repository has already had
// to correct once across five documents.
type Transform struct {
	ID      string `yaml:"id"`
	Pattern string `yaml:"pattern"`

	// Reason must say why the bytes may be changed. Editing somebody else's artifact without
	// a recorded reason is indistinguishable from tampering, however good the motive.
	Reason string `yaml:"reason"`

	AppliedTo int `yaml:"applied_to"`
}

type Derive struct {
	// Layout says where the sample tree and the upstream label sit, relative to the fetched
	// root, e.g. "pasture/<category>/<id>/{expected.yaml, skill/}".
	Layout string `yaml:"layout"`

	// TreeSubdir is the directory inside each sample that holds the artifact itself, as
	// opposed to the upstream's own label. skillsgoat keeps expected.yaml beside a skill/
	// directory; only the latter is the sample a scanner is pointed at. Copying the upstream
	// label in would repeat the mistake that corrupted this corpus once already, when a label
	// inside the tree was read as part of the sample.
	TreeSubdir string `yaml:"tree_subdir"`

	// Transforms are edits applied to the vendored bytes, declared so that anyone holding the
	// upstream can reproduce exactly what ships here.
	//
	// TreeSubdir above keeps the upstream's label OUT of the sample tree. Transforms exist
	// because that is not always enough: an upstream can write its label INTO the artifact,
	// and skillsgoat does — every SKILL.md ends with a marker naming the class and the tier.
	// Keeping the directory clean while shipping the same information inside the file is the
	// same mistake in a place TreeSubdir cannot reach.
	//
	// The bar for adding one is high and deliberately narrow: a transform may remove the
	// upstream's own LABEL, never anything about the artifact's behaviour. Removing an attack
	// would make the corpus a fiction; removing an answer key makes it measurable.
	Transforms []Transform `yaml:"transforms"`

	// Surface is the load surface every sample from this upstream lands on.
	Surface string `yaml:"surface"`

	// IDPrefix namespaces derived sample ids so they cannot collide with hand-pinned ones and
	// so their source is visible at a glance, e.g. "sg" for skillsgoat.
	IDPrefix string `yaml:"id_prefix"`

	// LabelFile is the upstream's own per-sample label, read for the fields below. Empty means
	// the upstream ships no per-sample label at all — skillcraft-audit is that case — and then
	// every axis has to come from the path or from a constant, which is a weaker derivation
	// and must say so in Fidelity.
	// A pointer so that "absent" and "explicitly empty" are different statements. Absent means
	// the entry predates this field and wants the expected.yaml default; `label_file: ""` means
	// the upstream genuinely ships no per-sample label. Inferring the difference from unrelated
	// fields was tried and silently skipped 483 samples whose only sin was needing no tier.
	LabelFile *string `yaml:"label_file"`

	// TierFrom / SeverityFrom / ClassFrom name where each axis is read. Each takes one of:
	//
	//   field:<name>        a field in the upstream label file
	//   id-prefix           the leading numeric token of the sample directory name
	//   constant:<value>    asserted by us, not read from anywhere
	//
	// `constant:` is the weakest and is called out for that reason: it is a judgement applied
	// uniformly to every sample in the entry, not something the upstream told us.
	TierFrom     string `yaml:"tier_from"`
	SeverityFrom string `yaml:"severity_from"`
	ClassFrom    string `yaml:"class_from"`

	// IDFrom says what identifies a sample when the upstream ships no label to read an id
	// from. `path-segments:1,0` joins the directory names at those depths, which is how a
	// corpus identified by its layout gets a stable name: skillcraft-audit's samples are
	// T11-hook-weaponize/easy, and neither segment alone is unique.
	IDFrom string `yaml:"id_from"`

	// SampleIsFile says each sample is a single file rather than a directory. cisco's MCP
	// evals ship one .py per test case; wrapping each in a directory of its own is what makes
	// it a sample tree a scanner can be pointed at.
	SampleIsFile bool `yaml:"sample_is_file"`

	// ExcludeTokens names upstream categories whose samples are left out entirely, with the
	// reason belonging in Fidelity. It exists because some upstream categories name a technique
	// with no outcome (cisco's defense-evasion is anti-debugging and nothing else) or a concept
	// this corpus deliberately does not model (description/code mismatch). Excluding them by
	// name keeps the decision visible; excluding them by quietly narrowing a glob would not.
	ExcludeTokens []string `yaml:"exclude_tokens"`

	// BenignNote is what a benign sample from this entry actually means, written into every
	// benign label. It is per-entry because the meaning differs sharply and getting it wrong
	// corrupts a false positive rate: skillsgoat's benign entries are deliberate decoys chosen
	// to trip a scanner, while skillet's are ordinary public skills. Reading the first as a
	// neutral denominator would overstate over-alerting; reading the second as adversarial
	// would understate it.
	BenignNote string `yaml:"benign_note"`

	// SourceFrom recovers the ORIGINATING repository of each sample, which matters whenever an
	// entry is a collection of other people's repositories rather than one corpus.
	//
	// Without it every sample in such an entry collapses to a single source, and a false
	// positive rate computed over them is the pooled figure this repository forbids: design.md
	// requires every rate to be reported per source, with n and with the source count, because
	// a machine-wide 12.9% once turned out to be 7 sources with two of them at 87%.
	//
	//   dirname-parts:<n>        the first n "__"-separated parts of the sample directory
	//                            name, joined with "/" — skillet names its trees owner__repo__…
	//   sidecar:<file>:<field>   a JSON file BESIDE the sample tree, not inside it. An
	//                            extraction step that slugs its directory names loses the real
	//                            repository, and a provenance file placed inside the tree would
	//                            be read as part of the sample — the mistake that corrupted
	//                            this corpus's measurements once already.
	SourceFrom string `yaml:"source_from"`

	// CategoryFrom says where the tokens fed to CategoryAxisMap come from:
	//
	//   field:<name>            a list field in the upstream label file (the default)
	//   path-segments:<a,b,…>   directory names at those depths above the sample, 0 being the
	//                           sample directory itself
	//
	// Path segments are how a corpus that labels by directory layout gets read without
	// inventing a label file for it.
	CategoryFrom string `yaml:"category_from"`

	// CategoryAxisMap is the lossy part: each upstream category maps to one of our axis
	// values, written as "dim:<x>", "evasion:<y>", "tier:<z>" or "ignore". A category present
	// upstream but absent here fails derivation rather than being silently dropped — the same
	// rule the tool dimension_map follows.
	CategoryAxisMap map[string]Targets `yaml:"category_axis_map"`

	// DimensionOverrides assigns a dimension to a named upstream sample that the category map
	// cannot place, keyed by upstream sample id.
	//
	// It exists because some upstream samples are labelled by TECHNIQUE, not by outcome:
	// skillsgoat categorises 200-split-across-files as `dispersion-splitting`, which says how
	// the payload hides and nothing about what it achieves. Our axes need both, so a person
	// reads the sample and records the dimension here. Each entry is therefore a hand-read
	// judgement standing in the open, countable and reviewable, rather than a guess buried in
	// the category map. `corpus derive` reports these separately from mechanically derived
	// coordinates, because they carry a different kind of confidence.
	// Targets, not string: a sample can achieve more than one thing, and forcing one value made
	// the override mechanism unable to express what the dimension definitions themselves
	// require — `reconnaissance.not` says a sample reading /etc/passwd earns both that and
	// `filesystem`, "and should carry both".
	DimensionOverrides map[string]DimensionOverride `yaml:"dimension_overrides"`

	// EvasionOverrides and TierOverrides exist for the same reason as DimensionOverrides, and
	// were added after an audit showed the category map getting both axes wrong in a way the
	// map cannot express.
	//
	// An upstream category is often a FAMILY. skillsgoat's `obfuscation-encoding` covers
	// homoglyphs, zero-width characters, RTL overrides, charcode rebuilding and shell
	// splicing; the map could only pin it to one member, so five samples all claimed
	// `base64-wrapper` and not one of them contained base64. Meanwhile `unicode-confusable`,
	// `bidi-override`, `zero-width` and `quote-splitting` — the values that were exactly right
	// — went unused. A closed vocabulary whose precise values are never reachable is a
	// vocabulary that describes nothing.
	//
	// TierOverrides carries the sharper case. `implies_tier` is meant to stop a base64-wrapped
	// payload from being filed as `plain` and landing in the calibration set, where a miss is
	// defined to mean the scanner is broken. It cannot: the rule only fires when an evasion
	// value is PRESENT, and the same map that got the tier wrong also omitted the evasion
	// value. Eleven calibration samples were contaminated exactly that way. A hand-read tier,
	// recorded here beside its evasion, is what closes that loop.
	// ExcludeSamples drops named upstream samples, where ExcludeTokens drops whole path
	// segments. It exists because an upstream category is not always homogeneous: cisco's
	// `defense-evasion` directory was excluded entire on the rationale that it "names a
	// technique, not something achieved", and six of its ten files install a rootkit, escape a
	// container, disable SELinux or truncate /var/log. The rationale was right about four of
	// them. Dropping ten to be right about four is the kind of exclusion red line 2 exists to
	// make visible, so the four are now named one by one with the reason beside each.
	ExcludeSamples map[string]string `yaml:"exclude_samples"`

	EvasionOverrides map[string][]string `yaml:"evasion_overrides"`
	TierOverrides    map[string]string   `yaml:"tier_overrides"`

	// Fidelity is the aggregate honesty statement for the whole entry: which axes are
	// mechanical, which are lossy, and how much of the derivation was spot-checked by hand.
	// An empty Derive with no Fidelity is not "derivable with no caveats"; it is a
	// contradiction the validator rejects, because a derivation with no stated loss is the
	// most dangerous kind.
	Fidelity string `yaml:"fidelity"`
}

func Load(path string) (*File, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read manifest: %w", err)
	}
	var f File
	dec := yaml.NewDecoder(strings.NewReader(string(b)))
	dec.KnownFields(true)
	if err := dec.Decode(&f); err != nil {
		return nil, fmt.Errorf("parse manifest: %w", err)
	}
	return &f, nil
}

var validRoles = []string{"fp-denominator", "recall", "hard-negative", "touchstone", "probe"}

// validProvenance is deliberately two words and not three. "Ours" is not an option here: a
// sample this repository authored carries it in its own label (origin.type reconstruction or
// synthetic) and never reaches a manifest entry, so offering the value would create a second
// place to make the same claim — and eventually two places that disagree.
var validProvenance = []string{"wild", "fixture"}

// validAxisTarget checks the shape of a category_axis_map value. The value after the colon
// (the actual axis member) is checked against the taxonomy in the derive package, where the
// taxonomy is in scope; here we only reject a malformed prefix.
func validAxisTarget(t string) bool {
	if t == "ignore" {
		return true
	}
	for _, prefix := range []string{"dim:", "evasion:", "tier:"} {
		if strings.HasPrefix(t, prefix) && len(t) > len(prefix) {
			return true
		}
	}
	return false
}

func (f *File) Validate() []error {
	var errs []error
	bad := func(fs string, a ...any) { errs = append(errs, fmt.Errorf(fs, a...)) }

	seen := map[string]bool{}
	for _, e := range f.Entries {
		if e.ID == "" {
			bad("an entry has no id")
			continue
		}
		if seen[e.ID] {
			bad("%s: duplicate id", e.ID)
		}
		seen[e.ID] = true

		if e.URL == "" {
			bad("%s: url is empty", e.ID)
		}
		if e.License == "" {
			bad("%s: license is empty — the license decides whether it may ever be vendored", e.ID)
		}
		if !oneOf(e.Role, validRoles) {
			bad("%s: role %q is not one of %s", e.ID, e.Role, strings.Join(validRoles, ", "))
		}
		// An entry whose samples reach layer 1 must say whether they existed in the world or
		// were authored as test cases, because the scorer reports the two apart and a missing
		// answer would silently default one of them into the other. Reference-only entries are
		// exempt: nothing of theirs is scored.
		if e.Vendorable && !oneOf(e.Provenance, validProvenance) {
			bad("%s: provenance %q is not one of %s — a vendorable entry must say whether its "+
				"artifacts existed in the world or were written as test cases, because only the "+
				"first can back a claim about the world", e.ID, e.Provenance,
				strings.Join(validProvenance, ", "))
		}
		if len(e.Hazards) == 0 {
			bad("%s: hazards is empty — write \"none known\" explicitly. An undeclared hazard "+
				"is how the next person uses the corpus wrong", e.ID)
		}
		// commit is what makes the reference reproducible; without it the corpus silently
		// changes under the numbers already published against it.
		if e.Commit == "" && e.Role != "probe" {
			bad("%s: commit is empty — a moving reference makes published numbers irreproducible", e.ID)
		}

		// Derive is format-checked here; the semantic check (do the axis targets exist, is
		// every upstream category covered) needs the taxonomy and lives in the derive package,
		// so that this package stays free of a taxonomy dependency and validates on its own.
		if d := e.Derive; d != nil {
			if d.Fidelity == "" {
				bad("%s: has a derive block but no derive.fidelity — a derivation with no "+
					"stated loss is the most dangerous kind, because it reads as exact. State "+
					"which axes are mechanical, which are lossy, and how much was spot-checked", e.ID)
			}
			if d.Layout == "" {
				bad("%s: derive.layout is empty — it must say where the sample tree and the "+
					"upstream label sit within the fetched root", e.ID)
			}
			for cat, targets := range d.CategoryAxisMap {
				if len(targets) == 0 {
					bad("%s: derive.category_axis_map[%q] is empty", e.ID, cat)
				}
				for _, target := range targets {
					if !validAxisTarget(target) {
						bad("%s: derive.category_axis_map[%q] is %q — it must be dim:<x>, "+
							"evasion:<y>, tier:<z> or ignore", e.ID, cat, target)
					}
				}
			}
		}
	}

	for _, e := range f.Entries {
		for _, o := range e.Overlaps {
			if !seen[o] {
				bad("%s: overlaps %q which is not an entry here", e.ID, o)
			}
		}
	}
	return errs
}

// PoolableGroups partitions entries into sets that may be summed. Entries that overlap end
// up in the same group, and a group with more than one entry may not be pooled.
func (f *File) PoolableGroups() [][]string {
	parent := map[string]string{}
	var find func(string) string
	find = func(x string) string {
		if parent[x] == "" || parent[x] == x {
			return x
		}
		parent[x] = find(parent[x])
		return parent[x]
	}
	for _, e := range f.Entries {
		parent[e.ID] = e.ID
	}
	for _, e := range f.Entries {
		for _, o := range e.Overlaps {
			if _, ok := parent[o]; !ok {
				continue
			}
			a, b := find(e.ID), find(o)
			if a != b {
				parent[a] = b
			}
		}
	}
	groups := map[string][]string{}
	for _, e := range f.Entries {
		r := find(e.ID)
		groups[r] = append(groups[r], e.ID)
	}
	var out [][]string
	for _, g := range groups {
		sort.Strings(g)
		out = append(out, g)
	}
	sort.Slice(out, func(i, j int) bool { return out[i][0] < out[j][0] })
	return out
}

func oneOf(v string, set []string) bool {
	for _, s := range set {
		if v == s {
			return true
		}
	}
	return false
}
