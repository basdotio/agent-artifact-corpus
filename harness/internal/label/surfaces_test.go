// SPDX-License-Identifier: MIT

package label

import (
	"fmt"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestSurfaceParsesScalarAndList(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name string
		in   string
		want []string
	}{
		// The scalar form must keep working untouched: 3,079 generated labels and 17
		// hand-pinned ones are written that way, and a schema change that rewrites all of
		// them to say the same thing is churn masquerading as progress.
		{"scalar", "surface: skills\n", []string{"skills"}},
		{"list", "surface: [hooks, permission]\n", []string{"hooks", "permission"}},
		{"block list", "surface:\n  - hooks\n  - permission\n", []string{"hooks", "permission"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			var l Label
			if err := yaml.Unmarshal([]byte(tc.in), &l); err != nil {
				t.Fatalf("unmarshal: %v", err)
			}
			if got := strings.Join(l.Surface, ","); got != strings.Join(tc.want, ",") {
				t.Errorf("surface = %v, want %v", l.Surface, tc.want)
			}
		})
	}
}

// A single surface must round-trip as a scalar. Marshalling it back as a one-element list
// would turn any future rewrite of the corpus into a three-thousand-file diff.
func TestSingleSurfaceRoundTripsAsScalar(t *testing.T) {
	t.Parallel()
	out, err := yaml.Marshal(Surfaces{"skills"})
	if err != nil {
		t.Fatal(err)
	}
	if strings.TrimSpace(string(out)) != "skills" {
		t.Errorf("marshalled %q, want the bare scalar", strings.TrimSpace(string(out)))
	}
	out, err = yaml.Marshal(Surfaces{"hooks", "permission"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(out), "- hooks") {
		t.Errorf("marshalled %q, want a list", string(out))
	}
}

func TestSurfaceValidation(t *testing.T) {
	t.Parallel()
	cases := []struct {
		name    string
		in      Surfaces
		wantErr string
	}{
		{"empty", Surfaces{}, "surface is empty"},
		{"unknown", Surfaces{"widgets"}, `surface "widgets" is not one of`},
		{"unknown in list", Surfaces{"hooks", "widgets"}, `surface "widgets" is not one of`},
		// One artifact counted twice in a per-surface report is the same defect as vendoring
		// the tree twice, and much harder to notice.
		{"duplicate", Surfaces{"hooks", "hooks"}, "listed twice"},
		{"valid pair", Surfaces{"hooks", "permission"}, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			var got []string
			tc.in.validate(func(f string, a ...any) { got = append(got, fmt.Sprintf(f, a...)) })
			joined := strings.Join(got, "\n")
			if tc.wantErr == "" {
				if len(got) != 0 {
					t.Errorf("unexpected problems: %s", joined)
				}
				return
			}
			if !strings.Contains(joined, tc.wantErr) {
				t.Errorf("problems %q, want one containing %q", joined, tc.wantErr)
			}
		})
	}
}

func TestPrimaryOwnsTheDirectory(t *testing.T) {
	t.Parallel()
	s := Surfaces{"permission", "hooks"}
	if s.Primary() != "permission" {
		t.Errorf("Primary() = %q, want the first entry — it decides the path", s.Primary())
	}
	if !s.Has("hooks") || !s.Has("permission") {
		t.Errorf("Has() missed a listed surface: %v", s)
	}
	if s.Has("skills") {
		t.Errorf("Has() reported an unlisted surface")
	}
	if Surfaces(nil).Primary() != "" {
		t.Errorf("Primary() of an empty set must be empty, not panic")
	}
}
