// SPDX-License-Identifier: MIT

package refute

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func shipped(t *testing.T) *Ruleset {
	t.Helper()
	r, err := Load(filepath.Join("..", "..", "..", "taxonomy"))
	if err != nil {
		t.Fatalf("load shipped refutation.yaml: %v", err)
	}
	return r
}

func TestShippedRulesetIsWellFormed(t *testing.T) {
	r := shipped(t)
	if r.Version < 1 {
		t.Errorf("version %d — a benign rate is only meaningful alongside the ruleset "+
			"version that failed to refute it", r.Version)
	}
	if len(r.Patterns) == 0 {
		t.Fatal("no patterns")
	}
	for _, p := range r.Patterns {
		if strings.TrimSpace(p.What) == "" {
			t.Errorf("pattern %q has no `what`", p.ID)
		}
		if strings.TrimSpace(p.Not) == "" {
			t.Errorf("pattern %q has no `not` — without the boundary, a pattern meant to "+
				"catch one unfit sample starts disqualifying the 39%% that are working as "+
				"intended", p.ID)
		}
		if p.OnMatch == "" {
			t.Errorf("pattern %q has no `on_match`", p.ID)
		}
		if !r.KnownAction(p.OnMatch) {
			t.Errorf("pattern %q has on_match %q, which is not a declared action", p.ID, p.OnMatch)
		}
	}
}

// The corpus's own audit found the canary by its shared PREFIX, not by whole tokens: each
// marker carries a unique per-sample suffix, so every full token has support 1. A detector
// that only tokenises cannot see it, which is exactly what happened.
func TestLabelBearingMarkerFoundBySharedPrefix(t *testing.T) {
	samples := []Sample{
		{ID: "b1", Class: "benign", Content: "# doc\n<!-- GOAT-CANARY-benign-installer -->\n"},
		{ID: "b2", Class: "benign", Content: "# doc\n<!-- GOAT-CANARY-benign-logo -->\n"},
		{ID: "b3", Class: "benign", Content: "# doc\n<!-- GOAT-CANARY-benign-notes -->\n"},
		{ID: "m1", Class: "malicious", Content: "# doc\n<!-- GOAT-CANARY-200-harvest -->\n"},
		{ID: "m2", Class: "malicious", Content: "# doc\n<!-- GOAT-CANARY-300-pack -->\n"},
		{ID: "m3", Class: "malicious", Content: "# doc\n<!-- GOAT-CANARY-100-fetch -->\n"},
	}
	got := LabelBearingMarkers(samples, 3, 0.95)
	if len(got) == 0 {
		t.Fatal("no marker found — a shared prefix perfectly predicting the class is the " +
			"one content leak this corpus has actually shipped")
	}
	var found bool
	for _, m := range got {
		if strings.Contains(m.Substring, "GOAT-CANARY-benign") {
			found = true
			if m.Purity < 0.99 {
				t.Errorf("purity %.2f for %q, want 1.0", m.Purity, m.Substring)
			}
		}
	}
	if !found {
		t.Errorf("markers %v do not include the benign prefix", got)
	}
}

// Whole-token scanning is what missed it. Asserting the negative keeps the reason for the
// substring approach from being optimised away later by someone who finds it expensive.
func TestWholeTokenScanningMissesTheMarker(t *testing.T) {
	samples := []Sample{
		{ID: "b1", Class: "benign", Content: "<!-- GOAT-CANARY-benign-installer -->"},
		{ID: "b2", Class: "benign", Content: "<!-- GOAT-CANARY-benign-logo -->"},
		{ID: "b3", Class: "benign", Content: "<!-- GOAT-CANARY-benign-notes -->"},
	}
	// Every full token is unique, so at any support threshold above 1 there is nothing.
	if got := wholeTokenLeaks(samples, 3, 0.95); len(got) != 0 {
		t.Errorf("whole-token scan found %v; the point of the substring scan is that this "+
			"finds nothing", got)
	}
}

func TestLabelBearingMarkerIgnoresLowSupport(t *testing.T) {
	samples := []Sample{
		{ID: "b1", Class: "benign", Content: "<!-- MARK-benign-a -->"},
		{ID: "m1", Class: "malicious", Content: "nothing"},
	}
	if got := LabelBearingMarkers(samples, 8, 0.95); len(got) != 0 {
		t.Errorf("found %v below the support floor — every one-off string would otherwise "+
			"be reported as a leak", got)
	}
}

// A single-class population cannot have a feature that predicts the class. Reporting one
// would be a false alarm of the worst kind: confident and unfalsifiable.
func TestLabelBearingMarkerSkipsSingleClass(t *testing.T) {
	var samples []Sample
	for i := 0; i < 20; i++ {
		samples = append(samples, Sample{ID: "b", Class: "benign", Content: "<!-- SAME-MARK -->"})
	}
	if got := LabelBearingMarkers(samples, 3, 0.95); len(got) != 0 {
		t.Errorf("found %v in a single-class population", got)
	}
}

func TestHiddenCodepointAllowsEmojiZWJ(t *testing.T) {
	// U+1F9DC U+200D U+2642 U+FE0F — the merman. The audit's only U+200D in 376 files was
	// this, doing its ordinary job.
	if hits := HiddenCodepoints("a \U0001F9DC‍♂️ b"); len(hits) != 0 {
		t.Errorf("emoji ZWJ sequence reported as hidden codepoint: %v", hits)
	}
}

func TestHiddenCodepointCatchesBidiAndZeroWidth(t *testing.T) {
	cases := map[string]string{
		"bidi override":     "safe‮esrever‬",
		"zero width space":  "cu​rl evil.example",
		"tag character":     "x\U000E0041y",
		"zwj outside emoji": "cu‍rl",
	}
	for name, s := range cases {
		if hits := HiddenCodepoints(s); len(hits) == 0 {
			t.Errorf("%s not reported", name)
		}
	}
}

func TestNoJudgeableContent(t *testing.T) {
	cases := []struct {
		name  string
		files map[string]string
		want  bool
	}{
		{"empty tree", map[string]string{}, true},
		{"path as content", map[string]string{
			"SKILL.md": "../../../product-team/product-discovery/SKILL.md"}, true},
		{"one line repeated", map[string]string{
			"SKILL.md": strings.Repeat("Standard operating procedure step.\n", 900)}, true},
		{"short but real", map[string]string{
			"SKILL.md": "---\nname: x\n---\n\n# X\n\nRun `npm test` before pushing.\n"}, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			dir := t.TempDir()
			for n, b := range c.files {
				if err := os.WriteFile(filepath.Join(dir, n), []byte(b), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			if got := NoJudgeableContent(dir); got != c.want {
				t.Errorf("NoJudgeableContent = %v, want %v", got, c.want)
			}
		})
	}
}

// The boundary that keeps this from becoming a scanner: placeholders stay in the
// denominator. A scanner firing on them is producing the false positive being measured.
func TestLiveCredentialKeepsPlaceholders(t *testing.T) {
	keep := []string{
		"aws_access_key_id = AKIAIOSFODNN7EXAMPLE",
		`ANTHROPIC_AUTH_TOKEN: "sk-xxxxxxxxx"`,
		`GOOGLE_CLIENT_SECRET="GOCSPX-xxx"`,
		`RESEND_API_KEY="re_xxxxxxxxxxxxxxxx"`,
		"password: ${DB_PASSWORD}",
		"password: YOUR_PASSWORD",
		"password: changeme",
	}
	for _, s := range keep {
		if hits := LiveCredentials(s); len(hits) != 0 {
			t.Errorf("placeholder %q was flagged (%v) — it belongs in the denominator", s, hits)
		}
	}
}

func TestLiveCredentialFlagsRealAssignment(t *testing.T) {
	// The one real instance in 250 audited samples. No vendor prefix, no token shape — which
	// is why every automated sweep missed it and a reader did not.
	if hits := LiveCredentials("- **Password**: datpt"); len(hits) == 0 {
		t.Error("a non-placeholder password assignment was not flagged")
	}
}

func TestDuplicateAndContained(t *testing.T) {
	a := Sample{ID: "a", Hashes: []string{"h1", "h2"}}
	b := Sample{ID: "b", Hashes: []string{"h1", "h2"}} // exact duplicate
	c := Sample{ID: "c", Hashes: []string{"h1"}}       // contained in a
	d := Sample{ID: "d", Hashes: []string{"h9"}}       // independent
	got := DuplicateOrContained([]Sample{a, b, c, d})
	if len(got) == 0 {
		t.Fatal("no duplicates found")
	}
	ids := map[string]bool{}
	for _, f := range got {
		ids[f.ID] = true
	}
	if !ids["c"] {
		t.Error("the contained sample was not reported — a subset tree inflates the " +
			"denominator exactly like an exact duplicate")
	}
	if ids["d"] {
		t.Error("an independent sample was reported")
	}
}

func TestLoadRejectsMalformed(t *testing.T) {
	dir := t.TempDir()
	body := "version: 1\npatterns: [{id: x, what: w, not: n, on_match: nonexistent-action}]\n"
	if err := os.WriteFile(filepath.Join(dir, "refutation.yaml"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	r, err := Load(dir)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if errs := r.Validate(); len(errs) == 0 {
		t.Fatal("a pattern naming an undeclared on_match action validated")
	}
}
