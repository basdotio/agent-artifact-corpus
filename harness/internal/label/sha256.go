// SPDX-License-Identifier: MIT

package label

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
)

// The corpus has carried "`sha256` is never verified" as a declared gap since the manifest was
// written, and for layer 2 that is unavoidable — a reference has no bytes to hash. Layer 1 is
// different: the bytes are right there, so a hash on a vendored sample is a claim that can be
// checked, and an unchecked hash is worse than no hash because it reads like integrity.
//
// This closes the gap for the samples that carry one. It does not close it for the manifest,
// and README says so.

var hexSha = regexp.MustCompile(`^[0-9a-f]{64}$`)

// VerifySha256 checks a label's origin.sha256 against the bytes actually vendored. Samples
// without the field are skipped, not failed: most of the corpus came from upstreams that
// published no hash, and inventing one from our own copy would only prove we can hash a file.
func (l *Label) VerifySha256() []error {
	if l.Origin.Sha256 == "" {
		return nil
	}
	var errs []error
	bad := func(f string, a ...any) { errs = append(errs, fmt.Errorf(f, a...)) }

	if !hexSha.MatchString(l.Origin.Sha256) {
		bad("origin.sha256 %q is not a 64-character lowercase hex digest", l.Origin.Sha256)
		return errs
	}
	if l.Path == "" {
		return nil
	}

	files, err := regularFiles(l.Path)
	if err != nil {
		bad("origin.sha256 is set but the sample tree cannot be read: %v", err)
		return errs
	}
	switch len(files) {
	case 0:
		bad("origin.sha256 is set but the sample tree holds no file to hash")
		return errs
	case 1:
	default:
		bad("origin.sha256 is set but the sample tree holds %d files — the field names the "+
			"hash of ONE artifact, and there is no concatenation order a reader could guess. "+
			"Remove it, or split the sample", len(files))
		return errs
	}

	got, err := hashFile(files[0])
	if err != nil {
		bad("origin.sha256: %v", err)
		return errs
	}
	if got != l.Origin.Sha256 {
		// This is the whole point of the field: the vendored copy is not what the label says
		// came from upstream, so either the file was edited after collection or the pin is
		// wrong. Either way every number published against this sample is suspect.
		bad("origin.sha256 says %s but %s hashes to %s — the vendored artifact is not the one "+
			"that was collected", short(l.Origin.Sha256), filepath.Base(files[0]), short(got))
	}
	return errs
}

func short(s string) string {
	if len(s) > 12 {
		return s[:12]
	}
	return s
}

func regularFiles(dir string) ([]string, error) {
	var out []string
	err := filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		fi, err := d.Info()
		if err != nil {
			return err
		}
		if fi.Mode().IsRegular() {
			out = append(out, p)
		}
		return nil
	})
	return out, err
}

func hashFile(p string) (string, error) {
	f, err := os.Open(p)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
