// SPDX-License-Identifier: MIT

package derive

import (
	"os"
	"path/filepath"
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
