// SPDX-License-Identifier: MIT

package manifest

import (
	"fmt"

	"gopkg.in/yaml.v3"
)

// Adjudication is a person's decision about one refutation match.
//
// The refutation patterns route every hit to a human decision, and this is where it lands. A
// hit with no adjudication fails the build, so a match cannot age into a silent pass — which
// is the shape of the defect this repository keeps finding in its own instrumentation: a
// check that reports something nobody ever acts on.
//
// `keep` is a real verdict, not a way of dismissing a finding. Most matches should be `keep`:
// the audit found 39% of benign samples contain something a defensible scanner fires on, and
// all of those belong in the denominator. What `keep` buys is that the reasoning was written
// down once, by someone who looked.
type Adjudication struct {
	Pattern string `yaml:"pattern"`
	Verdict string `yaml:"verdict"` // keep | exclude
	Reason  string `yaml:"reason"`
}

func (a *Adjudication) UnmarshalYAML(value *yaml.Node) error {
	if value.Kind != yaml.MappingNode {
		return fmt.Errorf("adjudication must be a mapping of pattern/verdict/reason")
	}
	for i := 0; i+1 < len(value.Content); i += 2 {
		switch k := value.Content[i].Value; k {
		case "pattern", "verdict", "reason":
		default:
			return fmt.Errorf("adjudication has unknown field %q", k)
		}
	}
	type raw Adjudication
	var r raw
	if err := value.Decode(&r); err != nil {
		return err
	}
	switch r.Verdict {
	case "keep", "exclude":
	default:
		return fmt.Errorf("adjudication verdict %q is not `keep` or `exclude`", r.Verdict)
	}
	if r.Reason == "" {
		return fmt.Errorf("adjudication for pattern %q has no reason — a decision nobody "+
			"can audit is the thing this record exists to prevent", r.Pattern)
	}
	if r.Pattern == "" {
		return fmt.Errorf("adjudication has no pattern")
	}
	*a = Adjudication(r)
	return nil
}
