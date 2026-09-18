// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/fixtures"
)

// cmdFixtures lists the injected-fault fixtures, or materialises them under a directory so a
// scanner runner can point at real hostile trees. It builds; it does not run a scanner or judge
// one — the Expected line is the tool-neutral pass condition a runner checks.
func cmdFixtures(_ string, args []string) int {
	all := fixtures.All()

	if len(args) == 0 {
		fmt.Printf("%d injected-fault fixtures — the part of layer 1 that cannot be a file:\n\n", len(all))
		for _, f := range all {
			fmt.Printf("  %-20s class %d (%s)\n", f.Name, int(f.Class), f.Class)
			fmt.Printf("      is:     %s\n", f.What)
			fmt.Printf("      expect: %s\n\n", f.Expected)
		}
		fmt.Println("materialise them with:  corpus fixtures --materialize <dir>")
		fmt.Println("then, after scanning, restore permissions so the dir is removable:")
		fmt.Println("  corpus fixtures --restore <dir>")
		return 0
	}

	switch args[0] {
	case "--materialize", "--materialise":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "usage: corpus fixtures --materialize <dir>")
			return 2
		}
		return materialize(all, args[1])
	case "--restore":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "usage: corpus fixtures --restore <dir>")
			return 2
		}
		fixtures.Restore(args[1])
		fmt.Printf("restored permissions under %s\n", args[1])
		return 0
	default:
		fmt.Fprintf(os.Stderr, "unknown argument %q\n", args[0])
		return 2
	}
}

func materialize(all []fixtures.Fixture, dir string) int {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		return 2
	}
	for _, f := range all {
		root := filepath.Join(dir, f.Name)
		if err := os.RemoveAll(root); err != nil {
			// A previous materialise may have left a 0111 dir; try to unstick it first.
			fixtures.Restore(root)
			_ = os.RemoveAll(root)
		}
		entry, err := f.Construct(root)
		if err != nil {
			fmt.Fprintf(os.Stderr, "%s: %v\n", f.Name, err)
			return 1
		}
		fmt.Printf("  %-20s -> %s\n", f.Name, entry)
	}
	fmt.Printf("\n%d fixtures materialised under %s\n", len(all), dir)
	fmt.Println("REMEMBER: `corpus fixtures --restore` before deleting — a 0111 dir blocks rm -rf.")
	return 0
}
