// SPDX-License-Identifier: MIT

package score

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

// Verdict is one line of a scanner's output: what it decided about one sample. The format is
// JSONL — one object per line — because that is what a scanner can emit without knowing
// anything about this corpus's internals, which is the whole point of a tool-neutral bench.
//
// Only Sample and Verdict are required. Severity and Dimensions are optional and unlock the
// two secondary scores (did it report severely enough, did it name the right kind); a scanner
// that emits neither is still fully scored on detection.
type Verdict struct {
	Sample     string   `json:"sample"`
	Verdict    string   `json:"verdict"`
	Severity   string   `json:"severity"`
	Dimensions []string `json:"dimensions"`
}

// Flagged is true when the scanner called this sample an attack. A scanner's own richer states
// (needs-review, low-confidence) collapse to the one decision the corpus scores: did you or did
// you not raise it. That collapse belongs to the scanner's adapter, not here, so the input is
// already one of the two words by the time it reaches this package.
func (v Verdict) Flagged() bool { return v.Verdict == string(classMalicious) }

// classMalicious/classBenign are the only two verdict words. They are lower-cased strings
// rather than the label package's Class type to keep this package free of that dependency: a
// verdict is the scanner's claim, not a corpus label, and conflating the two types is how a
// scorer starts trusting the scanner's word for what a sample IS.
const (
	classMalicious = "malicious"
	classBenign    = "benign"
)

// ParseVerdicts reads JSONL from r and validates every line at the boundary: a line that is not
// an object, is missing a sample id, or carries a verdict that is neither word is an error
// naming the line number, not a silently dropped record. A scorer that skips malformed input
// reports a rate over an unknown denominator, which is worse than refusing to run.
//
// Duplicate sample ids are rejected for the same reason: two verdicts for one sample means the
// scanner's output is ambiguous, and picking one would invent an answer.
func ParseVerdicts(r io.Reader) ([]Verdict, error) {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	var out []Verdict
	seen := map[string]int{}
	line := 0
	for sc.Scan() {
		line++
		text := strings.TrimSpace(sc.Text())
		if text == "" || strings.HasPrefix(text, "#") {
			continue
		}
		var v Verdict
		dec := json.NewDecoder(strings.NewReader(text))
		dec.DisallowUnknownFields()
		if err := dec.Decode(&v); err != nil {
			return nil, fmt.Errorf("line %d: not a verdict object (%v): %s", line, err, clip(text))
		}
		if v.Sample == "" {
			return nil, fmt.Errorf("line %d: no `sample` id", line)
		}
		if v.Verdict != classMalicious && v.Verdict != classBenign {
			return nil, fmt.Errorf("line %d: verdict %q is neither %q nor %q",
				line, v.Verdict, classMalicious, classBenign)
		}
		if prev, dup := seen[v.Sample]; dup {
			return nil, fmt.Errorf("line %d: sample %q already had a verdict on line %d",
				line, v.Sample, prev)
		}
		seen[v.Sample] = line
		out = append(out, v)
	}
	if err := sc.Err(); err != nil {
		return nil, fmt.Errorf("reading verdicts: %w", err)
	}
	return out, nil
}

func clip(s string) string {
	if len(s) > 80 {
		return s[:80] + "…"
	}
	return s
}
