// SPDX-License-Identifier: MIT

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
)

// `surfaces.go` says duplicating a tree "would put the same bytes in two samples, which is the
// leakage the corpus rejects elsewhere". An audit checked, and it was rejected nowhere: a tree
// copied verbatim under a new id passed cleanly. The comment described an intention.
//
// Two cases, treated differently on purpose:
//
//   - THE SAME BYTES IN TWO CLASSES is an error. It would make a scanner simultaneously right
//     and wrong about one artifact, and no score computed over such a corpus means anything.
//   - THE SAME BYTES TWICE IN ONE CLASS is reported, named and counted, not rejected. Five
//     groups exist today, all benign, and they are real: one upstream repository publishing
//     the same skill at two paths, and two different repositories shipping a copy of the same
//     one. Deleting them would quietly shrink a published denominator; leaving them unsaid
//     would let that denominator overcount. So they are said out loud.

// DupGroup is a set of samples whose trees hash identically.
type DupGroup struct {
	Digest  string
	IDs     []string
	Classes []string
}

// CrossClass reports whether one artifact is filed under more than one class.
func (g DupGroup) CrossClass() bool { return len(g.Classes) > 1 }

// DuplicateTrees groups the samples whose trees are byte-for-byte identical.
//
// The digest covers each file's path relative to the tree AND its content, so two samples that
// hold the same bytes under different names are correctly NOT duplicates — the load path is
// part of what a sample is.
func DuplicateTrees(labels []*label.Label) []DupGroup {
	byDigest := map[string][]*label.Label{}
	for _, l := range labels {
		d, err := treeDigest(l.Path)
		if err != nil || d == "" {
			continue
		}
		byDigest[d] = append(byDigest[d], l)
	}

	var out []DupGroup
	for d, ls := range byDigest {
		if len(ls) < 2 {
			continue
		}
		g := DupGroup{Digest: d[:12]}
		seen := map[string]bool{}
		for _, l := range ls {
			g.IDs = append(g.IDs, l.ID)
			if !seen[string(l.Class)] {
				seen[string(l.Class)] = true
				g.Classes = append(g.Classes, string(l.Class))
			}
		}
		sort.Strings(g.IDs)
		sort.Strings(g.Classes)
		out = append(out, g)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].IDs[0] < out[j].IDs[0] })
	return out
}

func treeDigest(dir string) (string, error) {
	var files []string
	err := filepath.Walk(dir, func(p string, fi os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if fi.Mode().IsRegular() {
			files = append(files, p)
		}
		return nil
	})
	if err != nil || len(files) == 0 {
		return "", err
	}
	sort.Strings(files)

	h := sha256.New()
	for _, p := range files {
		rel, _ := filepath.Rel(dir, p)
		fmt.Fprintf(h, "%s\x00", filepath.ToSlash(rel))
		f, err := os.Open(p)
		if err != nil {
			return "", err
		}
		if _, err := io.Copy(h, f); err != nil {
			f.Close()
			return "", err
		}
		f.Close()
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

// reportDuplicates prints the same-class groups and returns the cross-class ones as problems.
// excluded names the samples a recorded `verdict: exclude` adjudication holds out of the
// false-positive denominator — the redundant copies of a group, so its bytes count once.
func reportDuplicates(groups []DupGroup, excluded map[string]bool) []string {
	var problems []string
	var sameClass []DupGroup
	for _, g := range groups {
		if g.CrossClass() {
			problems = append(problems, fmt.Sprintf(
				"the same bytes are filed under %s: %s. One artifact cannot be both — a scanner "+
					"would be scored right and wrong for the same input, and no rate over this "+
					"corpus would mean anything",
				strings.Join(g.Classes, " and "), strings.Join(g.IDs, ", ")))
			continue
		}
		sameClass = append(sameClass, g)
		// "Counted once" is what excluding the redundant copies is for. Excluding every copy
		// takes the shared bytes out of the denominator altogether while each recorded reason
		// still says "counted once", so it fails rather than passing as a tidy-up.
		if heldOut(g, excluded) == len(g.IDs) {
			problems = append(problems, fmt.Sprintf(
				"every copy of a duplicate group is excluded by an adjudication: %s. Keep one "+
					"counted, or the shared bytes leave the false-positive denominator entirely",
				strings.Join(g.IDs, ", ")))
		}
	}

	if len(sameClass) > 0 {
		fmt.Print(duplicateHeader(sameClass, excluded))
		for _, g := range sameClass {
			fmt.Printf("  %s  %s\n", g.Classes[0], strings.Join(g.IDs, " = "))
		}
	}
	return problems
}

// duplicateHeader states how much the same-class duplicates still inflate a denominator, net
// of the copies an `exclude` adjudication already holds out — so validate and score describe
// the same corpus. With nothing excluded the wording is what it always was.
func duplicateHeader(sameClass []DupGroup, excluded map[string]bool) string {
	redundant, held := 0, 0
	for _, g := range sameClass {
		redundant += len(g.IDs) - 1
		held += min(heldOut(g, excluded), len(g.IDs)-1)
	}
	if held == 0 {
		return fmt.Sprintf("\n%d duplicate group(s) — identical bytes under different ids, inflating a "+
			"denominator by %d sample(s):\n", len(sameClass), redundant)
	}
	return fmt.Sprintf("\n%d duplicate group(s) — identical bytes under different ids: %d redundant "+
		"cop(ies), %d held out of the false-positive denominator by an `exclude` adjudication, "+
		"%d still inflating it:\n", len(sameClass), redundant, held, redundant-held)
}

func heldOut(g DupGroup, excluded map[string]bool) int {
	n := 0
	for _, id := range g.IDs {
		if excluded[id] {
			n++
		}
	}
	return n
}
