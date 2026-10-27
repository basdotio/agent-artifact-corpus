// SPDX-License-Identifier: MIT

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// harvestPinsRel is the inventory scripts/harvest-mcp-servers.py writes: one pin per harvested
// tree, each carrying tree_sha256 because a label's sha256 can only name one file.
//
// Nothing in validate read it until the re-harvest showed why it has to. Thirteen trees had
// committed bytes that no longer matched their pins — their own .gitignore had made `git add`
// skip files the hash counted — and the harvester then deleted three more trees in that state
// while keeping their pins. A pin nobody checks is not an integrity claim.
const harvestPinsRel = "manifest/pins/mcp-servers.json"

type harvestPin struct {
	Name       string `json:"name"`
	Surface    string `json:"surface"`
	TreeSHA256 string `json:"tree_sha256"`
}

// TreeDrift is a pinned tree whose bytes are not what its pin claims: "missing" when the tree
// is gone, "drifted" when it hashes to something else.
type TreeDrift struct {
	Name, State string
}

// CheckHarvestTrees recomputes tree_sha256 for every pinned tree under root. A checkout with
// no pins file has nothing to check.
func CheckHarvestTrees(root string) (checked int, drift []TreeDrift, err error) {
	b, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(harvestPinsRel)))
	if errors.Is(err, fs.ErrNotExist) {
		return 0, nil, nil
	}
	if err != nil {
		return 0, nil, err
	}
	var doc struct {
		Pins []harvestPin `json:"pins"`
	}
	if err := json.Unmarshal(b, &doc); err != nil {
		return 0, nil, fmt.Errorf("%s: %w", harvestPinsRel, err)
	}
	for _, p := range doc.Pins {
		tree := filepath.Join(root, "corpus", "benign", p.Surface, p.Name)
		checked++
		sum, err := treeSHA256(tree)
		switch {
		case errors.Is(err, fs.ErrNotExist):
			drift = append(drift, TreeDrift{p.Name, "missing"})
		case err != nil:
			return checked, drift, fmt.Errorf("%s: %w", p.Name, err)
		case sum != p.TreeSHA256:
			drift = append(drift, TreeDrift{p.Name, "drifted"})
		}
	}
	return checked, drift, nil
}

// treeSHA256 is the harvester's formula: sha256 over the sorted list of
// "<relative path>\0<sha256 of content>\n" for every regular file in the tree.
func treeSHA256(dir string) (string, error) {
	if _, err := os.Stat(dir); err != nil {
		return "", err
	}
	var lines []string
	err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil || !d.Type().IsRegular() {
			return err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		sum := sha256.Sum256(data)
		lines = append(lines, filepath.ToSlash(rel)+"\x00"+hex.EncodeToString(sum[:])+"\n")
		return nil
	})
	if err != nil {
		return "", err
	}
	sort.Strings(lines)
	sum := sha256.Sum256([]byte(strings.Join(lines, "")))
	return hex.EncodeToString(sum[:]), nil
}

// reportHarvestTrees prints the result, including when clean, so "no drift" can never be read
// as "never checked", and returns a problem per drifted or missing tree.
func reportHarvestTrees(root string) []string {
	checked, drift, err := CheckHarvestTrees(root)
	if err != nil {
		return []string{fmt.Sprintf("%s: cannot verify harvested trees: %v", harvestPinsRel, err)}
	}
	if checked == 0 {
		fmt.Println("trees       no harvest pins file; no harvested tree to verify")
		return nil
	}
	fmt.Printf("trees       %d of %d harvested tree(s) match their pinned tree_sha256\n",
		checked-len(drift), checked)
	var problems []string
	for _, d := range drift {
		problems = append(problems, fmt.Sprintf("%s: %s is %s — the committed bytes are not what its pin "+
			"claims, so the pin no longer vouches for the tree and a re-harvest would treat it as drift; "+
			"compare it with its pinned commit before re-pinning", harvestPinsRel, d.Name, d.State))
	}
	return problems
}
