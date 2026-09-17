// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// This file pins the claim the corpus rests on: that it is a general-purpose test set, not one
// project's QA fixtures with a schema around them. Saying so in a README is not the same as it
// being true, and it has already not been true twice — both times green, because drift of this
// kind is invisible by construction.
//
// What is NOT here, and why: a pass that strips every `expect` block and revalidates. It was
// written, and then deleted, because it could not fail. Nothing in the validator requires an
// expect block, so removing them only removes checks; the pass would have printed a reassuring
// line every run while guarding nothing. That is the same hollow-invariant defect this
// repository already removed once from the pairing check.
//
// The self-sufficiency of `truth` is already enforced, per class, in label.validateTruth: a
// malicious sample must name a technique or dimension AND a severity, a hard negative must
// name resembles AND differs_by. Those are the checks that make a label scoreable by someone
// who has never heard of any scanner, and they fail loudly. The three checks below cover what
// they do not.

// ToolNamesInNeutralHalf reports a registered scanner's id appearing where it must not.
//
// `truth` is the half that belongs to nobody, so a scanner's name inside one is a category
// error even when it reads as harmless prose: the moment a sample's truth explains what some
// scanner misses, that scanner's model has become part of the ground truth, and the next tool
// measured against it is being scored on a description of its competitor.
//
// `origin.source` is exempt, deliberately. A sample reconstructed from a scanner's issue
// tracker has to cite it; provenance is a fact about where an artifact came from, not an
// assertion about what it is. `expect.<tool>` is exempt because it IS the per-tool slot.
func ToolNamesInNeutralHalf(labels []*label.Label, tax *taxonomy.Set) []string {
	ids := toolIDs(tax)
	if len(ids) == 0 {
		return nil
	}

	var problems []string
	for _, l := range labels {
		// The rendered struct rather than the file text, which is what keeps `expect` and
		// `origin.source` out of scope without parsing the YAML a second time.
		fields := append([]string{l.Truth.Note, l.Truth.DiffersBy}, l.Truth.Techniques...)
		fields = append(fields, l.Truth.Resembles...)
		fields = append(fields, l.Truth.Dimensions...)
		fields = append(fields, l.Truth.Evasion...)

		for _, id := range ids {
			for _, f := range fields {
				if containsFold(f, id) {
					problems = append(problems, fmt.Sprintf(
						"%s: truth names the scanner %q. `truth` is the tool-neutral half — it is "+
							"what lets somebody measure a scanner we did not write — so a scanner's "+
							"name in it makes that scanner's model part of the ground truth. Move "+
							"the observation into expect.%s, which is the slot for it",
						l.Rel, id, id))
					break
				}
			}
		}
	}

	// The vocabulary itself. A dimension or technique named after somebody's rules would make
	// every measurement taken with it circular, and no per-label check would notice.
	for _, id := range ids {
		for _, d := range tax.Dimensions {
			if containsFold(d, id) {
				problems = append(problems, fmt.Sprintf(
					"taxonomy/techniques.yaml: dimension %q contains the scanner id %q — a "+
						"vocabulary named after one tool's rules makes every comparison with it "+
						"circular", d, id))
			}
		}
		for t := range tax.Techniques {
			if containsFold(t, id) {
				problems = append(problems, fmt.Sprintf(
					"taxonomy/techniques.yaml: technique %q contains the scanner id %q", t, id))
			}
		}
	}
	return problems
}

// ToolNamesInHarnessCode reports a scanner's id appearing in the harness's own code.
//
// This guards the specific mistake that prompted the check. A CI step was added that pinned
// the literal string "aguard" as the set of scanners whose rule ids could not be verified,
// which made one project's name part of the machinery that validates everybody's samples.
// The harness must treat every entry in taxonomy/tools.yaml identically; the moment it names
// one, it has a favourite.
//
// Only string literals and identifiers are examined. COMMENTS ARE EXEMPT, and that is not a
// loophole: the comments in this repository carry the reasoning, and several of them have to
// name the scanner whose path or pin caused a rule to exist. Explaining a mistake is the
// opposite of repeating it.
func ToolNamesInHarnessCode(repoRoot string, tax *taxonomy.Set) []string {
	ids := toolIDs(tax)
	if len(ids) == 0 {
		return nil
	}
	var problems []string

	err := filepath.WalkDir(filepath.Join(repoRoot, "harness"), func(p string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() || filepath.Ext(p) != ".go" {
			return nil
		}
		// Test fixtures legitimately use a tool id as data: taxonomy_test.go builds a tools.yaml
		// to validate, and it has to put some id in it.
		if strings.HasSuffix(p, "_test.go") {
			return nil
		}
		fset := token.NewFileSet()
		f, perr := parser.ParseFile(fset, p, nil, 0) // no ParseComments: comments are exempt
		if perr != nil {
			problems = append(problems, fmt.Sprintf("%s: cannot parse to check for scanner "+
				"names: %v", rel(repoRoot, p), perr))
			return nil
		}
		ast.Inspect(f, func(n ast.Node) bool {
			var text string
			switch v := n.(type) {
			case *ast.BasicLit:
				if v.Kind == token.STRING {
					text = v.Value
				}
			case *ast.Ident:
				text = v.Name
			}
			if text == "" {
				return true
			}
			for _, id := range ids {
				if containsFold(text, id) {
					problems = append(problems, fmt.Sprintf(
						"%s:%d: the harness names the scanner %q in its code. Every entry in "+
							"taxonomy/tools.yaml has to be treated identically — code that names "+
							"one tool makes that tool's presence part of how everybody else's "+
							"samples are validated. Drive it from the registry instead",
						rel(repoRoot, p), fset.Position(n.Pos()).Line, id))
				}
			}
			return true
		})
		return nil
	})
	if err != nil {
		problems = append(problems, fmt.Sprintf("cannot walk harness/: %v", err))
	}
	return problems
}

// CIDependsOnAScanner reports a workflow that makes a scanner reachable to CI.
//
// `rules_source.env` exists so that somebody with a local checkout of a scanner can verify
// its rule ids. Setting that variable in CI would mean the shared gate verifies one project's
// rules and nobody else's — the asymmetry that the rules_source.path rule already forbids,
// arriving through the front door instead.
//
// Checked by name, so a comment explaining why the variable is not set does not trip it.
func CIDependsOnAScanner(repoRoot string, tax *taxonomy.Set) []string {
	var vars []string
	for _, id := range toolIDs(tax) {
		if v := tax.Tools[id].RulesSource.Env; v != "" {
			vars = append(vars, v)
		}
	}
	if len(vars) == 0 {
		return nil
	}

	files, _ := filepath.Glob(filepath.Join(repoRoot, ".github", "workflows", "*.yml"))
	more, _ := filepath.Glob(filepath.Join(repoRoot, ".github", "workflows", "*.yaml"))
	files = append(files, more...)

	var problems []string
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			continue
		}
		for i, line := range strings.Split(string(b), "\n") {
			code := line
			if h := strings.Index(code, "#"); h >= 0 {
				code = code[:h] // a comment saying why the variable is unset is not setting it
			}
			for _, v := range vars {
				if strings.Contains(code, v+":") || strings.Contains(code, v+"=") {
					problems = append(problems, fmt.Sprintf(
						"%s:%d sets %s, which points CI at one scanner's rule list. The shared "+
							"gate would then verify that project's rule ids and no other "+
							"project's — checking a scanner's own expect blocks belongs in that "+
							"scanner's repository", rel(repoRoot, f), i+1, v))
				}
			}
		}
	}
	return problems
}

func toolIDs(tax *taxonomy.Set) []string {
	ids := make([]string, 0, len(tax.Tools))
	for id := range tax.Tools {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func containsFold(haystack, needle string) bool {
	return needle != "" && strings.Contains(strings.ToLower(haystack), strings.ToLower(needle))
}
