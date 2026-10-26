// SPDX-License-Identifier: MIT

package main

import (
	"strings"
	"testing"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/leakage"
)

// A blind spot is the one language state that fails validate: it is how the mcp surface looked
// before it had malicious TypeScript, and a warning alone would let it come back.
func TestBlindSpotIsAProblem(t *testing.T) {
	rows := []leakage.LanguageRow{{Surface: "mcp", Family: "js/ts",
		Malicious: 130, MaliciousWith: 0, Benign: 1000, BenignWith: 220}}
	got := reportLanguageSkew(rows)
	if len(got) != 1 || !strings.Contains(got[0], "blind spot on mcp: js/ts") {
		t.Fatalf("want one blind-spot problem, got %q", got)
	}
	if !strings.Contains(got[0], "none of the 130 malicious") {
		t.Fatalf("the problem must say which side lacks the language: %q", got[0])
	}
}

// Skew without a blind spot is printed and does not fail the build — it describes how the
// halves were collected, the same standing as the cross-population structure.
func TestSkewAloneIsNotAProblem(t *testing.T) {
	rows := []leakage.LanguageRow{
		{Surface: "skills", Family: "python", Malicious: 393, MaliciousWith: 152, Benign: 2882, BenignWith: 194},
		{Surface: "mcp", Family: "shell", Malicious: 139, MaliciousWith: 0, Benign: 1244, BenignWith: 50},
	}
	if got := reportLanguageSkew(rows); len(got) != 0 {
		t.Fatalf("skew and a rare one-sided language are warnings, not problems: %q", got)
	}
}

// The mirror case: a language only malicious samples carry, often enough to be a blind spot
// for a scanner that skips it on the benign side.
func TestBlindSpotTowardMalicious(t *testing.T) {
	rows := []leakage.LanguageRow{{Surface: "skills", Family: "shell",
		Malicious: 100, MaliciousWith: 30, Benign: 500, BenignWith: 0}}
	got := reportLanguageSkew(rows)
	if len(got) != 1 || !strings.Contains(got[0], "none of the 500 benign") {
		t.Fatalf("want a blind spot naming the benign side as the one that lacks it, got %q", got)
	}
	if note := skewNote(rows[0]); note != "absent from benign — BLIND SPOT" {
		t.Fatalf("unexpected note %q", note)
	}
}

// Said out loud when clean, so "nothing printed" cannot be mistaken for "nothing checked".
func TestNoSkewIsNotAProblem(t *testing.T) {
	if got := reportLanguageSkew(nil); got != nil {
		t.Fatalf("no rows, no problems: %q", got)
	}
}
