// SPDX-License-Identifier: MIT

package leakage

import (
	"bytes"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

// Why content features exist beside the structural ones.
//
// Check reads a tree's shape — names, extensions, counts — because that is what two public
// corpora leaked through. The next batch this corpus takes in is different: hard negatives
// and their malicious twins that we write ourselves, and an author's habits sit in the TEXT,
// not in the tree. Every attack fixture pointing at `evil.com` while every look-alike points
// at `api.github.com`; every payload calling its function `exfiltrate`; every malicious skill
// being 40 lines against 300; one template stamped out under different names. A tree walk
// sees none of that, and a scanner that greps for `evil` scores perfectly on it.
//
// So a sample also carries content features, extracted from the bytes with the same rules of
// evidence as the structural ones — presence, support, purity within a population — and the
// gate treats them identically. What is extracted is deliberately the material of
// CONSTRUCTION rather than of attack: a host literal, an address class, a self-describing word,
// a length bucket, a character-set tell. `curl | bash` is not here, because a corpus where
// every malicious sample pipes curl into bash may simply be a corpus of malicious samples;
// `attacker.example.com` is here, because no real campaign is hosted there.

// MaxContentFile is the largest file read for content features. Bigger files are vendored
// bundles and data, and a fixture is never one of them; the cap also keeps validate's extra
// read pass to seconds rather than tens of them over a 267 MB corpus.
const MaxContentFile = 256 << 10

var (
	// These run over the lower-cased text, so none is case-insensitive itself: `(?i)` costs
	// a case fold per rune and was a third of the pass over the corpus.
	urlHostRE = regexp.MustCompile(`\b(?:https?|ftp|wss?|ssh|git)://(?:[^/\s"'<>@]+@)?([a-z0-9.\-\[\]:]+)`)
	ipv4RE    = regexp.MustCompile(`\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b`)
	emailRE   = regexp.MustCompile(`\b[a-z0-9._%+\-]+@([a-z0-9\-]+\.)+[a-z]{2,}\b`)
	// Self-describing vocabulary: the names an author gives a thing when writing a fixture,
	// as opposed to the names a thing has when it is really being done to someone.
	wordRE = regexp.MustCompile(`\b(attacker|evil|malicious|malware|exfil\w*|payload|backdoor|pwn\w*|victim|c2|stage2|dropper|keylog\w*|hacker|botnet|ransom\w*|trojan|rootkit|implant|beacon|lorem ipsum|placeholder|todo)\b`)
)

// wordStem folds the inflections wordRE admits to one feature each.
func wordStem(w string) string {
	w = strings.ToLower(w)
	for _, p := range []string{"exfil", "pwn", "keylog", "ransom"} {
		if strings.HasPrefix(w, p) {
			return p
		}
	}
	return strings.ReplaceAll(w, " ", "-")
}

// ContentFeatures extracts the content features of the sample tree at root, whose files are
// the tree-relative paths Check already sees. entry is the label's entry point, used for the
// entry-file length bucket when it names a file. The result is sorted and deduplicated.
//
// Files that fail the text test (a NUL in the first 8 KiB, or invalid UTF-8) and files over
// MaxContentFile contribute only to the file count, never to the text.
func ContentFeatures(root, entry string, files []string) ([]string, error) {
	seen := map[string]bool{}
	add := func(f string) { seen[f] = true }
	var textBytes int64
	entryClean := filepath.ToSlash(filepath.Clean(entry))
	for _, rel := range files {
		if filepath.Base(rel) == "_label.yaml" {
			continue
		}
		p := filepath.Join(root, rel)
		fi, err := os.Lstat(p)
		if err != nil {
			return nil, err
		}
		if !fi.Mode().IsRegular() || fi.Size() > MaxContentFile {
			continue
		}
		b, err := os.ReadFile(p)
		if err != nil {
			return nil, err
		}
		if !isText(b) {
			continue
		}
		textBytes += int64(len(b))
		if filepath.ToSlash(rel) == entryClean {
			add("entrysize:" + sizeBucket(len(b)))
		}
		for _, f := range textFeatures(b) {
			add(f)
		}
	}
	add("textbytes:" + sizeBucket(int(textBytes)))
	out := make([]string, 0, len(seen))
	for f := range seen {
		out = append(out, f)
	}
	sort.Strings(out)
	return out, nil
}

func isText(b []byte) bool {
	head := b
	if len(head) > 8192 {
		head = head[:8192]
	}
	if bytes.IndexByte(head, 0) >= 0 {
		return false
	}
	return utf8.Valid(b)
}

// textFeatures is the per-file extraction; features are per sample, so duplicates across
// files collapse in the caller.
func textFeatures(b []byte) []string {
	var out []string
	s := string(b)
	lower := strings.ToLower(s)

	// Asking strings first is cheaper than asking the regexp, over most of the corpus's files.
	if strings.Contains(lower, "://") {
		for _, m := range urlHostRE.FindAllStringSubmatch(lower, -1) {
			host := m[1]
			// A port, a `${PORT}` left after lower-casing, or a bare trailing colon: everything
			// from the first colon on is not the host. IPv6 literals keep their brackets.
			if !strings.HasPrefix(host, "[") {
				if i := strings.Index(host, ":"); i >= 0 {
					host = host[:i]
				}
			}
			host = strings.TrimSuffix(host, ".")
			if host == "" {
				continue
			}
			if ipv4RE.MatchString(host) && isIPv4(host) {
				out = append(out, "hostclass:raw-ip")
			} else {
				out = append(out, "host:"+host)
				if c := hostClass(host); c != "" {
					out = append(out, "hostclass:"+c)
				}
			}
		}
	}
	for _, m := range ipv4RE.FindAllStringSubmatch(s, -1) {
		if !isIPv4(m[0]) {
			continue
		}
		out = append(out, "ip:"+m[0])
		if c := ipClass(m); c != "" {
			out = append(out, "ipclass:"+c)
		}
	}
	if strings.Contains(lower, "@") {
		for _, m := range emailRE.FindAllString(lower, -1) {
			out = append(out, "email:"+m)
		}
	}
	for _, m := range wordRE.FindAllString(lower, -1) {
		out = append(out, "word:"+wordStem(m))
	}
	out = append(out, charsetFeatures(s)...)
	return out
}

func isIPv4(s string) bool {
	m := ipv4RE.FindStringSubmatch(s)
	if m == nil || m[0] != s {
		return false
	}
	for _, oct := range m[1:] {
		n, _ := strconv.Atoi(oct)
		if n > 255 {
			return false
		}
	}
	return true
}

// hostClass names the host families that mark a fixture: the names reserved for
// documentation (RFC 2606, RFC 6761), which no campaign is hosted at, and the loopback name.
func hostClass(host string) string {
	switch {
	case host == "localhost" || strings.HasSuffix(host, ".localhost"):
		return "localhost"
	case host == "example.com" || host == "example.net" || host == "example.org" ||
		strings.HasSuffix(host, ".example.com") || strings.HasSuffix(host, ".example.net") ||
		strings.HasSuffix(host, ".example.org") ||
		strings.HasSuffix(host, ".example") || strings.HasSuffix(host, ".test") ||
		strings.HasSuffix(host, ".invalid"):
		return "reserved"
	}
	return ""
}

// ipClass names the address families: documentation ranges (RFC 5737), private (RFC 1918),
// loopback. A public address is left unclassed and reported only as its literal.
func ipClass(m []string) string {
	a, _ := strconv.Atoi(m[1])
	b, _ := strconv.Atoi(m[2])
	c, _ := strconv.Atoi(m[3])
	switch {
	case a == 192 && b == 0 && c == 2, a == 198 && b == 51 && c == 100, a == 203 && b == 0 && c == 113:
		return "documentation"
	case a == 10, a == 172 && b >= 16 && b <= 31, a == 192 && b == 168:
		return "private"
	case a == 127:
		return "loopback"
	case a == 0 && b == 0 && c == 0:
		return "unspecified"
	}
	return ""
}

// charsetFeatures reports the characters a reader does not see — zero-width, bidi overrides,
// Unicode tag characters — and whether any non-ASCII text is present at all. The first three
// are evasion material; the last separates an English-only fixture batch from a corpus of the
// world's skills.
func charsetFeatures(s string) []string {
	var zero, bidi, tag, nonASCII bool
	for _, r := range s {
		switch {
		case r == 0x200B || r == 0x200C || r == 0x200D || r == 0x2060 || r == 0xFEFF:
			zero = true
		case (r >= 0x202A && r <= 0x202E) || (r >= 0x2066 && r <= 0x2069):
			bidi = true
		case r >= 0xE0000 && r <= 0xE007F:
			tag = true
		case r >= 0x80:
			nonASCII = true // visible text in some script, not one of the hidden ones above
		}
	}
	var out []string
	if zero {
		out = append(out, "charset:zero-width")
	}
	if bidi {
		out = append(out, "charset:bidi")
	}
	if tag {
		out = append(out, "charset:tag")
	}
	if nonASCII {
		out = append(out, "charset:non-ascii")
	}
	return out
}

// sizeBucket coarsens a byte count the way bucket coarsens a file count: enough to show "the
// fixtures are 600 bytes and the real ones are 20 KB", not so fine that every length is its
// own feature.
func sizeBucket(n int) string {
	switch {
	case n < 1<<10:
		return "<1K"
	case n < 4<<10:
		return "1-4K"
	case n < 16<<10:
		return "4-16K"
	case n < 64<<10:
		return "16-64K"
	default:
		return "64K+"
	}
}

// ContentFeatureKind names the family a content feature belongs to, for the report.
func ContentFeatureKind(name string) string {
	if i := strings.Index(name, ":"); i > 0 {
		return name[:i]
	}
	return name
}
