// SPDX-License-Identifier: MIT

package derive

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// testTax mirrors the shape of the real vocabulary: tiers whose maps_to carry the upstream
// token, a couple of dimensions and evasions.
func testTax() *taxonomy.Set {
	return &taxonomy.Set{
		Dimensions: []string{"backdoor", "exfiltration", "supply-chain", "filesystem"},
		TierOrder:  []string{"plain", "evasive", "structural"},
		Tiers: map[string]taxonomy.Tier{
			"plain":      {ID: "plain", Rank: 0, MapsTo: "skillsgoat / cisco 000", Calibration: true},
			"evasive":    {ID: "evasive", Rank: 1, MapsTo: "skillsgoat / cisco 200"},
			"structural": {ID: "structural", Rank: 2, MapsTo: "skillsgoat / cisco 300"},
		},
		Evasions: map[string]taxonomy.Evasion{
			"base64-wrapper":  {ID: "base64-wrapper", ImpliesTier: "evasive"},
			"judge-targeting": {ID: "judge-targeting", ImpliesTier: "structural"},
		},
	}
}

// writeSample creates root/<layoutDir>/<id>/expected.yaml with the given body.
func writeSample(t *testing.T, root, category, id, body string) {
	t.Helper()
	dir := filepath.Join(root, "pasture", category, id)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "expected.yaml"), []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
}

func entry(m map[string]manifest.Targets) manifest.Entry {
	return manifest.Entry{
		ID: "skillsgoat",
		Derive: &manifest.Derive{
			Layout:          "pasture/*/*",
			Fidelity:        "tier mechanical from prefix; dimension/evasion via category map",
			CategoryAxisMap: m,
		},
	}
}

func TestDerive(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	// A malicious evasive sample whose two categories split across axes: one is what it does
	// (dimension), the other is how it hides (evasion). This is the whole reason the map is
	// per-axis rather than one-to-one.
	writeSample(t, root, "obfuscation-encoding", "200-wrapped-backdoor", `
id: 200-wrapped-backdoor
verdict: malicious
severity: high
categories: [persistence-backdoor, obfuscation-encoding]
`)
	// A benign decoy: no tier, no dimension, class benign.
	writeSample(t, root, "benign", "000-base64-logo", `
id: 000-base64-logo
verdict: benign
categories: [benign]
`)

	m := map[string]manifest.Targets{
		"persistence-backdoor": {"dim:backdoor"},
		"obfuscation-encoding": {"evasion:base64-wrapper"},
		"benign":               {"ignore"},
	}
	res, errs := Derive(entry(m), root, testTax())
	if len(errs) != 0 {
		t.Fatalf("expected clean derivation, got:\n%v", errs)
	}
	if len(res.Coords) != 2 {
		t.Fatalf("expected 2 coords, got %d", len(res.Coords))
	}

	// Coords are sorted by upstream id, so 000-base64-logo is first.
	benign := res.Coords[0]
	if benign.Class != "benign" || benign.Tier != "" || len(benign.Dimensions) != 0 {
		t.Fatalf("benign decoy derived wrong: %+v", benign)
	}

	mal := res.Coords[1]
	if mal.Class != "malicious" || mal.Tier != "evasive" || mal.Severity != "high" {
		t.Fatalf("malicious axes wrong: %+v", mal)
	}
	if len(mal.Dimensions) != 1 || mal.Dimensions[0] != "backdoor" {
		t.Fatalf("dimension should come from persistence-backdoor, got %v", mal.Dimensions)
	}
	if len(mal.Evasion) != 1 || mal.Evasion[0] != "base64-wrapper" {
		t.Fatalf("evasion should come from obfuscation-encoding, got %v", mal.Evasion)
	}
}

func TestDeriveRefusesUnmappedCategory(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "misc", "200-x", `
id: 200-x
verdict: malicious
severity: high
categories: [persistence-backdoor, something-new]
`)
	m := map[string]manifest.Targets{"persistence-backdoor": {"dim:backdoor"}}
	_, errs := Derive(entry(m), root, testTax())
	if !containsErr(errs, `category "something-new" has no category_axis_map entry`) {
		t.Fatalf("an unmapped category must fail derivation, got:\n%v", errs)
	}
}

func TestDeriveRefusesBadAxisTarget(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "x", "200-x", `
id: 200-x
verdict: malicious
severity: high
categories: [persistence-backdoor]
`)
	m := map[string]manifest.Targets{"persistence-backdoor": {"dim:telepathy"}}
	_, errs := Derive(entry(m), root, testTax())
	if !containsErr(errs, `dimension "telepathy", which is not in the vocabulary`) {
		t.Fatalf("an axis target outside the vocabulary must fail, got:\n%v", errs)
	}
}

func TestDeriveRefusesMaliciousWithoutDimension(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	// All its categories are evasion or ignore, so it lands on no recall axis.
	writeSample(t, root, "x", "300-judge", `
id: 300-judge
verdict: malicious
severity: critical
categories: [llm-judge-manipulation]
`)
	m := map[string]manifest.Targets{"llm-judge-manipulation": {"evasion:judge-targeting"}}
	_, errs := Derive(entry(m), root, testTax())
	if !containsErr(errs, "sits on no recall axis") {
		t.Fatalf("a malicious sample with no dimension must be flagged, got:\n%v", errs)
	}
}

// The id prefix is authoritative for tier; a category hint that disagrees is surfaced, not
// silently resolved.
func TestDeriveTierConflict(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "x", "200-x", `
id: 200-x
verdict: malicious
severity: high
categories: [persistence-backdoor, deferred-resolution]
`)
	m := map[string]manifest.Targets{
		"persistence-backdoor": {"dim:backdoor"},
		"deferred-resolution":  {"tier:structural"}, // disagrees with the 200 prefix -> evasive
	}
	_, errs := Derive(entry(m), root, testTax())
	if !containsErr(errs, "id prefix says tier") {
		t.Fatalf("a tier conflict must be surfaced, got:\n%v", errs)
	}
}

func ptr(s string) *string { return &s }

func containsErr(errs []error, sub string) bool {
	for _, e := range errs {
		if strings.Contains(e.Error(), sub) {
			return true
		}
	}
	return false
}

// Some upstream samples are categorised by technique alone — "dispersion-splitting" says how
// the payload hides and nothing about what it achieves. The category map cannot place them, so
// a person reads the sample and records the dimension. These stay countable and separate from
// mechanically derived coordinates.
func TestDimensionOverrides(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "dispersion-splitting", "200-split", `
id: 200-split
verdict: malicious
severity: high
categories: [dispersion-splitting]
`)
	e := entry(map[string]manifest.Targets{"dispersion-splitting": {"evasion:base64-wrapper"}})
	e.Derive.DimensionOverrides = map[string]manifest.Targets{"200-split": {"exfiltration"}}

	res, errs := Derive(e, root, testTax())
	if len(errs) != 0 {
		t.Fatalf("an override should place the sample, got:\n%v", errs)
	}
	c := res.Coords[0]
	if len(c.Dimensions) != 1 || c.Dimensions[0] != "exfiltration" {
		t.Fatalf("expected the hand-read dimension, got %v", c.Dimensions)
	}
	if !c.HandReadDimension || res.HandRead != 1 {
		t.Fatalf("a hand-read dimension must be marked and counted: %+v / %d", c, res.HandRead)
	}
}

// An override that the category map has since made redundant is stale, and saying so stops it
// outliving the reason it was written.
func TestStaleOverrideIsReported(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "x", "200-x", `
id: 200-x
verdict: malicious
severity: high
categories: [persistence-backdoor]
`)
	e := entry(map[string]manifest.Targets{"persistence-backdoor": {"dim:backdoor"}})
	// Stale means the override says what the RULE already says. The earlier definition was
	// "the rule produced anything at all", which made the mechanism able to fill a gap and
	// unable to correct an error — and correcting errors is most of what a hand-read dimension
	// turned out to be for.
	e.Derive.DimensionOverrides = map[string]manifest.Targets{"200-x": {"backdoor"}}

	_, errs := Derive(e, root, testTax())
	if !containsErr(errs, "it is stale") {
		t.Fatalf("a redundant override must be reported, got:\n%v", errs)
	}
}

// The case the old semantics could not express: a category that is right for most of its
// members and wrong for this one. A census of 253 samples found 86 of these; refusing them
// would have meant deleting categories that are mostly correct.
func TestOverrideCorrectsTheCategoryMap(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "x", "200-x", `
id: 200-x
verdict: malicious
severity: high
categories: [persistence-backdoor]
`)
	e := entry(map[string]manifest.Targets{"persistence-backdoor": {"dim:backdoor"}})
	e.Derive.DimensionOverrides = map[string]manifest.Targets{"200-x": {"exfiltration", "filesystem"}}

	res, errs := Derive(e, root, testTax())
	if len(errs) != 0 {
		t.Fatalf("an override correcting the map must be accepted, got:\n%v", errs)
	}
	got := res.Coords[0].Dimensions
	if len(got) != 2 || got[0] != "exfiltration" || got[1] != "filesystem" {
		t.Errorf("dimensions = %v, want [exfiltration filesystem] — the override REPLACES the "+
			"map's value; appending would leave the rejected one beside it", got)
	}
	if !res.Coords[0].HandReadDimension {
		t.Errorf("a corrected dimension must be marked hand-read, or stats will report it as mechanical")
	}
}

func TestOverrideTargetMustExist(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "x", "200-x", `
id: 200-x
verdict: malicious
severity: high
categories: [persistence-backdoor]
`)
	e := entry(map[string]manifest.Targets{"persistence-backdoor": {"dim:backdoor"}})
	e.Derive.DimensionOverrides = map[string]manifest.Targets{"200-other": {"telepathy"}}

	_, errs := Derive(e, root, testTax())
	if !containsErr(errs, `names "telepathy", which is not a dimension`) {
		t.Fatalf("an override outside the vocabulary must fail, got:\n%v", errs)
	}
}

// A second upstream shape: no per-sample label at all, everything encoded in the directory
// layout. skillcraft-audit is this case, and reading it must not require inventing a label
// file for it.
func TestDeriveFromLayoutWithoutLabelFile(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	for _, lvl := range []string{"easy", "hard"} {
		dir := filepath.Join(root, "poc", "T11-hook-weaponize", lvl)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("# s\n"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	e := manifest.Entry{ID: "skillcraft-audit", Derive: &manifest.Derive{
		Layout:       "poc/T*/*",
		LabelFile:    ptr(""), // there is none
		Fidelity:     "class and severity are constants we assert",
		ClassFrom:    "constant:malicious",
		SeverityFrom: "constant:high",
		TierFrom:     "path-segment",
		IDFrom:       "path-segments:1,0",
		CategoryFrom: "path-segments:0,1",
		CategoryAxisMap: map[string]manifest.Targets{
			"easy":               {"tier:plain"},
			"hard":               {"tier:evasive", "evasion:judge-targeting"},
			"T11-hook-weaponize": {"dim:backdoor"},
		},
	}}
	tax := testTax()
	tax.Evasions["judge-targeting"] = taxonomy.Evasion{ID: "judge-targeting", ImpliesTier: "evasive"}

	res, errs := Derive(e, root, tax)
	if len(errs) != 0 {
		t.Fatalf("expected a clean derivation, got:\n%v", errs)
	}
	if len(res.Coords) != 2 {
		t.Fatalf("expected 2 coords, got %d", len(res.Coords))
	}

	byID := map[string]Coord{}
	for _, c := range res.Coords {
		byID[c.UpstreamID] = c
	}
	// Neither path segment alone is unique, so the id is the join of both.
	easy, ok := byID["T11-hook-weaponize-easy"]
	if !ok {
		t.Fatalf("expected a composite id, got %v", byID)
	}
	if easy.Class != "malicious" || easy.Severity != "high" {
		t.Fatalf("constants should supply class and severity: %+v", easy)
	}
	if easy.Tier != "plain" || len(easy.Evasion) != 0 {
		t.Fatalf("easy should be plain with no mechanism: %+v", easy)
	}

	// One token carrying two facts: how deep, and what does the burying.
	hard := byID["T11-hook-weaponize-hard"]
	if hard.Tier != "evasive" {
		t.Fatalf("hard should be evasive, got %q", hard.Tier)
	}
	if len(hard.Evasion) != 1 || hard.Evasion[0] != "judge-targeting" {
		t.Fatalf("hard should also carry its mechanism, got %v", hard.Evasion)
	}
	if len(hard.Dimensions) != 1 || hard.Dimensions[0] != "backdoor" {
		t.Fatalf("dimension should come from the technique segment, got %v", hard.Dimensions)
	}
}

// A third upstream shape: each sample is a single file, and the directory holding it is the
// category. cisco's MCP evals ship one .py per test case.
func TestDeriveFileShapedSamples(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	for cat, name := range map[string]string{"backdoor": "dns_tunnel.py", "defense-evasion": "anti_debug.py"} {
		dir := filepath.Join(root, "data", cat)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dir, name), []byte("# server\n"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	e := manifest.Entry{ID: "cisco", Derive: &manifest.Derive{
		Layout:        "data/*/*.py",
		SampleIsFile:  true,
		LabelFile:     ptr(""),
		Fidelity:      "dimension from the category directory; class, severity and tier asserted",
		ClassFrom:     "constant:malicious",
		SeverityFrom:  "constant:high",
		TierFrom:      "constant:plain",
		CategoryFrom:  "path-segments:1",
		ExcludeTokens: []string{"defense-evasion"},
		CategoryAxisMap: map[string]manifest.Targets{
			"backdoor":        {"dim:backdoor"},
			"defense-evasion": {"ignore"},
		},
	}}

	res, errs := Derive(e, root, testTax())
	if len(errs) != 0 {
		t.Fatalf("expected a clean derivation, got:\n%v", errs)
	}
	if len(res.Coords) != 1 {
		t.Fatalf("one sample survives the exclusion, got %d", len(res.Coords))
	}
	// An exclusion shrinks the denominator, so it is counted rather than invisible.
	if res.Excluded != 1 {
		t.Fatalf("the excluded sample must be counted, got %d", res.Excluded)
	}
	c := res.Coords[0]
	if c.UpstreamID != "dns_tunnel" {
		t.Fatalf("a file-shaped sample is identified by its filename, got %q", c.UpstreamID)
	}
	if c.Tier != "plain" || c.Severity != "high" || c.Class != "malicious" {
		t.Fatalf("constants should supply class, severity and tier: %+v", c)
	}
	if len(c.Dimensions) != 1 || c.Dimensions[0] != "backdoor" {
		t.Fatalf("dimension should come from the category directory, got %v", c.Dimensions)
	}
}

// A constant tier that is not in the vocabulary, and a tier that resolves to nothing, are both
// caught here rather than left for the validator to reject one step later.
func TestDeriveCatchesUnresolvableTier(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	writeSample(t, root, "x", "no-prefix-here", `
verdict: malicious
severity: high
categories: [persistence-backdoor]
`)
	e := entry(map[string]manifest.Targets{"persistence-backdoor": {"dim:backdoor"}})
	e.Derive.TierFrom = "constant:sneaky"
	if _, errs := Derive(e, root, testTax()); !containsErr(errs, `tier_from asserts "sneaky"`) {
		t.Fatalf("a constant tier outside the vocabulary must fail, got %v", errs)
	}

	e2 := entry(map[string]manifest.Targets{"persistence-backdoor": {"dim:backdoor"}})
	if _, errs := Derive(e2, root, testTax()); !containsErr(errs, "no numeric id prefix") {
		t.Fatalf("an unreadable tier must be reported, got %v", errs)
	}
}
