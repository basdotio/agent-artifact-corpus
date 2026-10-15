// SPDX-License-Identifier: MIT
package main

import (
	"strings"
	"testing"
)

// A label may carry blocks AFTER its refutation record — `reviewed:` is one — and replacing
// the record must leave them alone. The first regex ran to the end of the file.
func TestReplaceRefutationBlockKeepsWhatFollows(t *testing.T) {
	label := "id: x\nclass: benign\n\nbasis:\n  class: assumed\n\n" +
		"refutation_search:\n  ruleset_version: 1\n  matched: []\n  scanned_bytes: 1\n\n" +
		"reviewed:\n  date: 2026-09-23\n  verdict: would-fire\n  note: \"kept\"\n"
	block := "refutation_search:\n  ruleset_version: 2\n  matched: []\n  scanned_bytes: 1\n"
	got := replaceRefutationBlock(label, block)
	if !strings.Contains(got, "ruleset_version: 2") {
		t.Fatalf("record not replaced:\n%s", got)
	}
	if strings.Contains(got, "ruleset_version: 1") {
		t.Fatalf("old record survived:\n%s", got)
	}
	if !strings.Contains(got, "reviewed:\n  date: 2026-09-23") {
		t.Fatalf("the reviewed block after the record was lost:\n%s", got)
	}
	// Idempotent: the same block again changes nothing.
	if again := replaceRefutationBlock(got, block); again != got {
		t.Fatalf("second replacement differs:\n%s\n---\n%s", got, again)
	}
	// A label with no record gets one appended.
	if !strings.HasSuffix(replaceRefutationBlock("id: y\n", block), block) {
		t.Fatal("a label without a record should get the block appended")
	}
}
