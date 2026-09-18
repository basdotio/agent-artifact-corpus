// SPDX-License-Identifier: MIT

//go:build unix

package fixtures

import (
	"io/fs"
	"os"
	"path/filepath"
)

// Restore makes a materialised fixture tree removable again. Some fixtures deliberately leave
// the filesystem in a state ordinary cleanup cannot undo — a 0111 directory denies the very
// enumeration RemoveAll needs — so any consumer that builds one must call this before deleting
// it. It chmods every directory back to 0755, ignoring the errors that a hostile tree throws on
// the way (a symlink cycle is walked with SkipDir), because its only job is to unstick cleanup.
func Restore(root string) {
	filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			// Cannot enter it? Try to make it enterable, then move on without recursing.
			os.Chmod(p, 0o755)
			return fs.SkipDir
		}
		if d.IsDir() {
			os.Chmod(p, 0o755)
		}
		return nil
	})
}
