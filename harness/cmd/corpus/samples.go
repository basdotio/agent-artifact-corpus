// SPDX-License-Identifier: MIT

package main

import (
	"encoding/json"
	"fmt"
	"os"
)

// cmdSamples emits the corpus as a JSONL work list — one object per sample with its id, tree
// path, class and surface — so a runner living beside a scanner can iterate the corpus without
// re-implementing how a label maps to a tree. It is the input side of the scoring loop that
// `corpus score` closes: a runner reads this, points its scanner at each `path`, and emits
// `{"sample": id, "verdict": ...}` back for scoring.
//
// It names no scanner and makes no judgement — it only says what is here. That is why it belongs
// in this repository while the runner that consumes it does not.
func cmdSamples(root string, _ []string) int {
	labels, err := loadLabels(root)
	if err != nil {
		fatal(err)
	}
	enc := json.NewEncoder(os.Stdout)
	for _, l := range labels {
		rec := struct {
			Sample   string   `json:"sample"`
			Path     string   `json:"path"`
			Class    string   `json:"class"`
			Surface  []string `json:"surface"`
			Severity string   `json:"severity,omitempty"`
		}{
			Sample:   l.ID,
			Path:     l.Rel,
			Class:    string(l.Class),
			Surface:  []string(l.Surface),
			Severity: l.Truth.Severity,
		}
		if err := enc.Encode(rec); err != nil {
			fmt.Fprintf(os.Stderr, "%v\n", err)
			return 1
		}
	}
	return 0
}
