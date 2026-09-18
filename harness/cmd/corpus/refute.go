// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/derive"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/refute"
)

// cmdRefute writes a `refutation_search` record into every benign label.
//
// It exists so there is ONE implementation. Derived labels get their record when `derive`
// materialises them; harvested labels are written by a Python script, and reimplementing the
// patterns there would have produced two answers to the same question that drift apart
// silently. This command runs the Go patterns over every benign sample regardless of how its
// label was produced.
//
// Idempotent: an existing block is replaced, so re-running after a ruleset change refreshes
// every record rather than leaving a mix of versions.
func cmdRefute(root string, args []string) int {
	write := false
	for _, a := range args {
		if a == "--write" {
			write = true
		}
	}

	rs, err := refute.Load(root + "/taxonomy")
	if err != nil {
		fatal(err)
	}
	labels, err := loadLabels(root)
	if err != nil {
		fatal(err)
	}

	written, matched := 0, 0
	for _, l := range labels {
		if l.Class != "benign" || l.Path == "" {
			continue
		}
		block := derive.RefutationBlock(l.Path, rs.Version)
		if strings.Contains(block, "matched: [") && !strings.Contains(block, "matched: []") {
			matched++
		}
		if !write {
			written++
			continue
		}
		b, rerr := os.ReadFile(l.Path + ".yaml")
		if rerr != nil {
			fmt.Fprintf(os.Stderr, "  %s: %v\n", l.Rel, rerr)
			continue
		}
		out := replaceRefutationBlock(string(b), block)
		if out == string(b) {
			continue
		}
		if werr := os.WriteFile(l.Path+".yaml", []byte(out), 0o644); werr != nil {
			fmt.Fprintf(os.Stderr, "  %s: %v\n", l.Rel, werr)
			continue
		}
		written++
	}

	verb := "would write"
	if write {
		verb = "wrote"
	}
	fmt.Printf("refutation ruleset v%d: %s %d benign record(s); %d matched at least one pattern\n",
		rs.Version, verb, written, matched)
	if !write {
		fmt.Println("re-run with --write to apply")
	}
	return 0
}

var existingRefutation = regexp.MustCompile(`(?ms)\nrefutation_search:\n(?:  .*\n)*`)

// replaceRefutationBlock swaps an existing record or appends a new one.
func replaceRefutationBlock(label, block string) string {
	if existingRefutation.MatchString(label) {
		return existingRefutation.ReplaceAllString(label, "\n"+block)
	}
	return strings.TrimRight(label, "\n") + "\n\n" + block
}
