// SPDX-License-Identifier: MIT

package score

import (
	"slices"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// OutOfScopeGroup is one reason samples left a tool's denominator: a declared selector, or the
// per-sample marks on the labels themselves. IDs are in label order, and a sample appears under
// the FIRST group that matched it, so the group sizes add up to the excluded total.
type OutOfScopeGroup struct {
	Selector string
	Reason   string
	IDs      []string
}

// OutOfScopeReport carries BOTH denominators. There is no field for the narrow recall alone: a
// denominator a tool draws for itself means something only beside the one it did not draw.
type OutOfScopeReport struct {
	Tool     string
	Groups   []OutOfScopeGroup
	Excluded int // distinct malicious labels declared out of scope, with or without a verdict

	All, AllHits         int // covered malicious samples, and how many the tool flagged
	InScope, InScopeHits int // the same after the declared ones are removed
}

// OutOfScope applies toolID's declaration to the malicious labels. A label leaves the denominator
// when its population (source) or one of its evasions matches a selector, or when its own
// expect.<tool>.out_of_scope is set. Only covered samples enter either denominator, as with every
// other recall figure: an unscored sample is not a pass, and it is not a miss either.
func OutOfScope(labels []*label.Label, verdicts []Verdict, toolID string, tool taxonomy.Tool,
	population func(*label.Label) string) OutOfScopeReport {

	rep := OutOfScopeReport{Tool: toolID}
	verdictOf := make(map[string]Verdict, len(verdicts))
	for _, v := range verdicts {
		verdictOf[v.Sample] = v
	}

	groups := make([]OutOfScopeGroup, len(tool.OutOfScope))
	for i, o := range tool.OutOfScope {
		groups[i] = OutOfScopeGroup{Selector: o.Label(), Reason: o.Reason}
	}
	perSample := OutOfScopeGroup{Selector: "expect." + toolID + ".out_of_scope"}

	for _, l := range labels {
		if l.Class != label.Malicious {
			continue
		}
		v, covered := verdictOf[l.ID]
		out := false
		if toolID != "" {
			for i, o := range tool.OutOfScope {
				if (o.Source != "" && population(l) == o.Source) ||
					(o.Evasion != "" && slices.Contains(l.Truth.Evasion, o.Evasion)) {
					groups[i].IDs = append(groups[i].IDs, l.ID)
					out = true
					break
				}
			}
			if e := l.Expect[toolID]; !out && e != nil && e.OutOfScope != "" {
				perSample.IDs = append(perSample.IDs, l.ID)
				if perSample.Reason == "" {
					perSample.Reason = e.OutOfScope
				}
				out = true
			}
		}
		if out {
			rep.Excluded++
		}
		if !covered {
			continue
		}
		rep.All++
		if v.Flagged() {
			rep.AllHits++
		}
		if !out {
			rep.InScope++
			if v.Flagged() {
				rep.InScopeHits++
			}
		}
	}

	// Every declared selector is reported, matched or not: a declaration that matched nothing is
	// exactly what a reader needs to see, because it means the tool's claim covers no sample here.
	rep.Groups = append(rep.Groups, groups...)
	if len(perSample.IDs) > 0 {
		rep.Groups = append(rep.Groups, perSample)
	}
	return rep
}
