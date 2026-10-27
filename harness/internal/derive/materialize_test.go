// SPDX-License-Identifier: MIT

package derive

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
)

func materialEntry() manifest.Entry {
	e := entry(map[string]manifest.Targets{"persistence-backdoor": {"dim:backdoor"}})
	e.URL = "https://github.com/optimuslabs-io/skillsgoat"
	e.Commit = "c03d70d80c32f37617ce5739ebf2e782b1ac94ce"
	e.License = "MIT"
	e.Derive.Surface = "skills"
	e.Derive.IDPrefix = "sg"
	e.Derive.TreeSubdir = "skill"
	// The strip only applies to an entry that READS its tier from that prefix, which is what
	// makes the digits a tier rather than part of a name.
	e.Derive.TierFrom = "id-prefix"
	return e
}

// The tier prefix is stripped from the local name on purpose: leaving "200-" in the directory
// would put part of the answer in the path, which is the shortcut feature this corpus refuses
// in other people's datasets.
func TestPlanStripsTierPrefixFromPath(t *testing.T) {
	t.Parallel()
	res := &Result{Coords: []Coord{
		{UpstreamID: "200-wrapped", Class: "malicious", SamplePath: "pasture/x/200-wrapped"},
		{UpstreamID: "000-logo", Class: "benign", SamplePath: "pasture/benign/000-logo"},
	}}
	plans, errs := PlanMaterialize(materialEntry(), res)
	if len(errs) != 0 {
		t.Fatalf("expected a clean plan, got %v", errs)
	}
	byID := map[string]Plan{}
	for _, p := range plans {
		byID[p.LocalID] = p
	}
	mal, ok := byID["mal-skill-sg-wrapped"]
	if !ok {
		t.Fatalf("expected mal-skill-sg-wrapped, got %v", plans)
	}
	if strings.Contains(mal.Dir, "200") {
		t.Fatalf("the tier must not appear in the path: %s", mal.Dir)
	}
	if mal.Dir != filepath.Join("corpus", "malicious", "skills", "sg-wrapped") {
		t.Fatalf("unexpected location %s", mal.Dir)
	}
	if _, ok := byID["ben-skill-sg-logo"]; !ok {
		t.Fatalf("benign should use the ben- prefix, got %v", plans)
	}
}

// Two upstream ids that collapse to the same local name would leave one sample silently
// missing from the corpus.
func TestPlanRefusesCollision(t *testing.T) {
	t.Parallel()
	res := &Result{Coords: []Coord{
		{UpstreamID: "200-dup", Class: "malicious", SamplePath: "a"},
		{UpstreamID: "300-dup", Class: "malicious", SamplePath: "b"},
	}}
	_, errs := PlanMaterialize(materialEntry(), res)
	if !containsErr(errs, "upstream ids collide once the tier prefix is stripped") {
		t.Fatalf("a collision must be refused, got %v", errs)
	}
}

func TestMaterializeCopiesTreeAndWritesLabel(t *testing.T) {
	t.Parallel()
	upRoot := t.TempDir()
	repo := t.TempDir()

	// Upstream layout: the artifact under skill/, the upstream's own label beside it.
	sample := filepath.Join(upRoot, "pasture", "x", "200-wrapped")
	if err := os.MkdirAll(filepath.Join(sample, "skill", "scripts"), 0o755); err != nil {
		t.Fatal(err)
	}
	write := func(p, body string) {
		if err := os.WriteFile(p, []byte(body), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	write(filepath.Join(sample, "expected.yaml"), "id: 200-wrapped\nverdict: malicious\n")
	write(filepath.Join(sample, "skill", "SKILL.md"), "# sample\n")
	write(filepath.Join(sample, "skill", "scripts", "run.sh"), "echo hi\n")

	res := &Result{Coords: []Coord{{
		UpstreamID: "200-wrapped", Class: "malicious", SamplePath: "pasture/x/200-wrapped",
		Dimensions: []string{"backdoor"}, Evasion: []string{"base64-wrapper"},
		Tier: "evasive", Severity: "high", HandReadDimension: true,
	}}}
	e := materialEntry()
	plans, errs := PlanMaterialize(e, res)
	if len(errs) != 0 {
		t.Fatalf("plan: %v", errs)
	}
	n, _, werrs := Materialize(repo, upRoot, e, plans)
	if len(werrs) != 0 || n != 1 {
		t.Fatalf("materialise: wrote %d, errs %v", n, werrs)
	}

	dir := filepath.Join(repo, "corpus", "malicious", "skills", "sg-wrapped")
	if _, err := os.Stat(filepath.Join(dir, "scripts", "run.sh")); err != nil {
		t.Fatalf("nested file not copied: %v", err)
	}
	// The upstream's own label must never land inside the tree: a scanner reads the whole
	// target, so a label in there injects its own text as evidence.
	if _, err := os.Stat(filepath.Join(dir, "expected.yaml")); err == nil {
		t.Fatal("the upstream label was copied into the sample tree")
	}

	got, err := os.ReadFile(dir + ".yaml")
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{
		"id: mal-skill-sg-wrapped",
		"type: derived",
		"labeled_before_run: false",
		"entry: skillsgoat",
		"sample: pasture/x/200-wrapped",
		"dimensions: [backdoor]",
		"tier: evasive",
		"evasion: [base64-wrapper]",
		"dimension hand-read",
	} {
		if !strings.Contains(string(got), want) {
			t.Fatalf("label missing %q:\n%s", want, got)
		}
	}
}

// A hand-pinned label carries judgements a rule cannot reproduce. A re-derivation flattening
// one would destroy the most valuable kind of sample in the corpus.
func TestMaterializeRefusesToOverwriteHandPinned(t *testing.T) {
	t.Parallel()
	upRoot := t.TempDir()
	repo := t.TempDir()

	sample := filepath.Join(upRoot, "pasture", "x", "200-wrapped")
	if err := os.MkdirAll(filepath.Join(sample, "skill"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sample, "skill", "SKILL.md"), []byte("# s\n"), 0o600); err != nil {
		t.Fatal(err)
	}

	labelDir := filepath.Join(repo, "corpus", "malicious", "skills")
	if err := os.MkdirAll(labelDir, 0o755); err != nil {
		t.Fatal(err)
	}
	handPinned := "id: mal-skill-sg-wrapped\norigin:\n  type: reconstruction\n"
	if err := os.WriteFile(filepath.Join(labelDir, "sg-wrapped.yaml"), []byte(handPinned), 0o600); err != nil {
		t.Fatal(err)
	}

	res := &Result{Coords: []Coord{{
		UpstreamID: "200-wrapped", Class: "malicious", SamplePath: "pasture/x/200-wrapped",
		Dimensions: []string{"backdoor"}, Tier: "plain", Severity: "high",
	}}}
	e := materialEntry()
	plans, _ := PlanMaterialize(e, res)
	n, _, werrs := Materialize(repo, upRoot, e, plans)
	if n != 0 || !containsErr(werrs, "refusing to overwrite hand-pinned label") {
		t.Fatalf("expected a refusal, wrote %d, errs %v", n, werrs)
	}
	after, _ := os.ReadFile(filepath.Join(labelDir, "sg-wrapped.yaml"))
	if string(after) != handPinned {
		t.Fatal("the hand-pinned label was modified")
	}
}

// The counterpart to TestPlanStripsTierPrefixFromPath, and the reason that test needed a
// companion. The strip removes a TIER PREFIX; an entry that does not read its tier from the id
// has no such prefix, so leading digits there are part of the upstream's NAME. Applied to
// every entry it was identity corruption: `12306-mcp` (China Railway) became `am-mcp`, and
// `2389-research/ourocodus` lost its owner.
func TestLeadingDigitsSurviveWhenTheyAreNotATier(t *testing.T) {
	t.Parallel()
	e := materialEntry()
	e.Derive.IDPrefix = "am"
	e.Derive.TierFrom = "" // this entry's tier comes from somewhere else, so digits are a name

	res := &Result{Coords: []Coord{
		{UpstreamID: "12306-mcp", Class: "benign", SamplePath: "extracted/12306-mcp"},
		{UpstreamID: "2389-research__ourocodus", Class: "benign", SamplePath: "x/2389-research__ourocodus"},
	}}
	plans, errs := PlanMaterialize(e, res)
	if len(errs) != 0 {
		t.Fatalf("expected a clean plan, got %v", errs)
	}
	got := map[string]bool{}
	for _, p := range plans {
		got[p.LocalID] = true
	}
	for _, want := range []string{"ben-skill-am-12306-mcp", "ben-skill-am-2389-research__ourocodus"} {
		if !got[want] {
			t.Errorf("%s was not produced; the upstream's own name lost its leading digits. Got %v", want, keysOfBool(got))
		}
	}
}

func keysOfBool(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// An upstream whose samples sit under two globs, some directories and some single files, is
// one entry: the python-sdk's examples/servers/ holds directories and examples/snippets/servers/
// holds files. Each sample takes the shape it has, a file is wrapped exactly as sample_is_file
// wraps one, and the label carries the entry's kind rather than the historical `skill`.
func TestMaterializeMixedShapesAcrossLayouts(t *testing.T) {
	t.Parallel()
	upRoot := t.TempDir()
	repo := t.TempDir()
	write := func(p, body string) {
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(body), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	write(filepath.Join(upRoot, "examples", "servers", "simple-tool", "server.py"), "# dir-shaped\n")
	write(filepath.Join(upRoot, "examples", "snippets", "servers", "basic_tool.py"), "# file-shaped\n")
	write(filepath.Join(upRoot, "examples", "snippets", "servers", "README.md"), "not a .py\n")

	e := manifest.Entry{ID: "python-sdk-examples", URL: "https://example.invalid/sdk", Commit: "c9356a2a8fb805ac2202e44c05371cf005edc923",
		License: "MIT", Derive: &manifest.Derive{
			Layouts:     []string{"examples/servers/*", "examples/snippets/servers/*.py"},
			MixedShapes: true,
			LabelFile:   ptr(""),
			Surface:     "mcp",
			Kind:        "server",
			IDPrefix:    "sdk",
			ClassFrom:   "constant:benign",
			BenignNote:  "an example server",
			Fidelity:    "class is a constant",
		}}
	res, errs := Derive(e, upRoot, testTax())
	if len(errs) != 0 {
		t.Fatalf("derive: %v", errs)
	}
	if len(res.Coords) != 2 {
		t.Fatalf("one directory and one file, got %d: %+v", len(res.Coords), res.Coords)
	}
	plans, perrs := PlanMaterialize(e, res)
	if len(perrs) != 0 {
		t.Fatalf("plan: %v", perrs)
	}
	n, _, werrs := Materialize(repo, upRoot, e, plans)
	if len(werrs) != 0 || n != 2 {
		t.Fatalf("materialise: wrote %d, errs %v", n, werrs)
	}
	base := filepath.Join(repo, "corpus", "benign", "mcp")
	if _, err := os.Stat(filepath.Join(base, "sdk-simple-tool", "server.py")); err != nil {
		t.Fatalf("directory-shaped sample not copied: %v", err)
	}
	if _, err := os.Stat(filepath.Join(base, "sdk-basic_tool", "basic_tool.py")); err != nil {
		t.Fatalf("file-shaped sample not wrapped in a directory of its own: %v", err)
	}
	got, err := os.ReadFile(filepath.Join(base, "sdk-basic_tool.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{"id: ben-mcp-sdk-basic_tool", "kind: server", "surface: mcp", "entry: python-sdk-examples"} {
		if !strings.Contains(string(got), want) {
			t.Fatalf("label missing %q:\n%s", want, got)
		}
	}
}

// Without mixed_shapes the historical contract holds: a regular file under a directory layout
// is not a sample, so an entry that never asked for files cannot start producing them.
func TestSampleDirsIgnoresFilesUnlessAsked(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "ex", "a"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "ex", "b.py"), []byte("x"), 0o600); err != nil {
		t.Fatal(err)
	}
	got, _, err := sampleDirs(root, []string{"ex/*"}, "", false, false)
	if err != nil || len(got) != 1 || got[0].isFile {
		t.Fatalf("directory layout: want the one directory, got %+v (%v)", got, err)
	}
	got, _, err = sampleDirs(root, []string{"ex/*"}, "", false, true)
	if err != nil || len(got) != 2 {
		t.Fatalf("mixed: want both, got %+v (%v)", got, err)
	}
	got, _, err = sampleDirs(root, []string{"ex/*", "ex/*.py"}, "", false, true)
	if err != nil || len(got) != 2 {
		t.Fatalf("overlapping globs name a sample once, got %+v (%v)", got, err)
	}
}

// A dimension read by a machine must not be published as "hand-read": the label is what a
// consumer reads, and `read` is defined as a person's reading. The note names the reader and
// leaves the basis to the maintainer, as the benign review records read by an AI assistant do.
func TestMachineReadDimensionIsDisclosedInTheLabel(t *testing.T) {
	c := Coord{Class: "malicious", Dimensions: []string{"execution"}, HandReadDimension: true,
		ReadBy: "an AI assistant for the corpus maintainer"}
	got := originNote(materialEntry(), c)
	for _, want := range []string{"read from the sample by an AI assistant for the corpus maintainer",
		"a person's reading", "maintainer's call"} {
		if !strings.Contains(got, want) {
			t.Fatalf("note missing %q: %s", want, got)
		}
	}
	if strings.Contains(got, "hand-read") {
		t.Fatalf("a machine reading must not be called hand-read: %s", got)
	}
	// The derivation's fidelity line travels with the label too, and must not say it either.
	label := renderLabel(materialEntry(), Plan{Coord: c, LocalID: "mal-skill-x"}, "")
	if strings.Contains(label, "hand-read") || !strings.Contains(label, "dimension read into dimension_overrides by an AI assistant") {
		t.Fatalf("the rendered label must name the reader everywhere it describes the reading:\n%s", label)
	}
}
