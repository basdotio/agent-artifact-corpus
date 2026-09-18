// SPDX-License-Identifier: MIT

package main

import (
	"encoding/json"
	"io"
	"os"
	"strings"
	"testing"
)

// captureStdout runs f with os.Stdout redirected and returns what it wrote.
func captureStdout(t *testing.T, f func()) string {
	t.Helper()
	old := os.Stdout
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	os.Stdout = w
	done := make(chan string, 1)
	go func() {
		b, _ := io.ReadAll(r)
		done <- string(b)
	}()
	f()
	w.Close()
	os.Stdout = old
	return <-done
}

// The work list a runner iterates must round-trip: every line valid JSON with an id, a path and
// a class, one per label. A missing field would send a runner's scanner at nothing.
func TestSamplesEmitsCompleteWorkList(t *testing.T) {
	root, err := repoRoot()
	if err != nil {
		t.Skipf("no repo root from the test working directory: %v", err)
	}
	out := captureStdout(t, func() { cmdSamples(root, nil) })

	lines := strings.Split(strings.TrimSpace(out), "\n")
	if len(lines) < 100 {
		t.Fatalf("only %d sample lines; the corpus is larger than that", len(lines))
	}
	seen := map[string]bool{}
	for i, ln := range lines {
		var rec struct {
			Sample, Path, Class string
		}
		if err := json.Unmarshal([]byte(ln), &rec); err != nil {
			t.Fatalf("line %d not JSON: %v", i+1, err)
		}
		if rec.Sample == "" || rec.Path == "" || rec.Class == "" {
			t.Errorf("line %d missing a field: %q", i+1, ln)
		}
		if seen[rec.Sample] {
			t.Errorf("duplicate sample id %q — a runner would scan it twice", rec.Sample)
		}
		seen[rec.Sample] = true
	}
}
