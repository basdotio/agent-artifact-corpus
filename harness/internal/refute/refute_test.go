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

// The one real credential in 250 audited samples is NOT matched here, on purpose.
//
// `password: datpt` has no vendor prefix and no token shape, and is textually identical in
// form to `password: mypassword` and `password: secret123`, which appear throughout the
// benign half as tutorial examples and must stay in the denominator. Trying to separate them
// by regex produced 192 false positives against one true one. It is excluded by name with a
// recorded reason instead — `adjudicate`, which is what refutation.yaml routes it to.
func TestLiveCredentialDoesNotGuessAtBareAssignments(t *testing.T) {
	for _, s := range []string{
		"- **Password**: datpt",
		"password: mypassword",
		"password: secret123",
		"password: 12345",
	} {
		if hits := LiveCredentials(s); len(hits) != 0 {
			t.Errorf("%q flagged (%v) — bare assignments are adjudicated, not matched", s, hits)
		}
	}
}

func TestLiveCredentialFlagsSelfIdentifyingShapes(t *testing.T) {
	for _, s := range []string{
		"aws_access_key_id = AKIA1234567890ABCDEF",
		"token: ghp_abcdefghijklmnopqrstuvwxyz0123",
		"-----BEGIN RSA PRIVATE KEY-----",
	} {
		if hits := LiveCredentials(s); len(hits) == 0 {
			t.Errorf("%q not flagged — the shape identifies itself", s)
		}
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

// Every string below was taken from the corpus when this pattern first ran over the benign
// half and matched 209 samples — 6.4%, against a stated target of under 0.5% and an audited
// truth of exactly one. The hit rate is the guard described in refutation.yaml's header, and
// it worked: it said the pattern had become a scanner before anyone acted on its output.
//
// The distinction it was missing: a credential is a LITERAL VALUE. Everything here is a
// reference to a value stored elsewhere, or a type, and reading a secret from the environment
// is the correct thing for a benign sample to do.
func TestLiveCredentialKeepsReferencesAndTypes(t *testing.T) {
	keep := []string{
		`api_key = os.environ.get("OPENAI_API_KEY")`,
		`api_key = os.environ["OPENAI_API_KEY"]`,
		"token = os.getenv('GITHUB_TOKEN')",
		"apikey: process.env.OPENROUTER_API_KEY",
		"token: module.ctx.creds.aws.session_token",
		"password: string",
		"password: str",
		"password: string)",
		"token: str)",
		"password: bool",
		"token: required",
		"pass=true",
		"password: None",
		"token: null",
		"password: raise",
		"token: await client.fetch()",
		"token: TOKEN_DA_INSTANCIA",
		"api_key: ${{ secrets.OPENAI_KEY }}",
	}
	for _, s := range keep {
		if hits := LiveCredentials(s); len(hits) != 0 {
			t.Errorf("%q flagged (%v) — it names where a value comes from, it is not a value", s, hits)
		}
	}
}

// The threshold is one distinct line, not two, and the boundary is real content versus none.
func TestNoJudgeableContentKeepsTerseButRealSkills(t *testing.T) {
	cases := map[string]struct {
		body string
		want bool
	}{
		"two-line skill":   {"# Coding\n\nWrite production-quality code.\n", false},
		"fetch error page": {"404: Not Found", true},
	}
	for name, c := range cases {
		t.Run(name, func(t *testing.T) {
			dir := t.TempDir()
			if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte(c.body), 0o644); err != nil {
				t.Fatal(err)
			}
			if got := NoJudgeableContent(dir); got != c.want {
				t.Errorf("NoJudgeableContent(%q) = %v, want %v", c.body, got, c.want)
			}
		})
	}
}
