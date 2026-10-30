package main

import (
	"archive/zip"
	"bytes"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/basdotio/agent-artifact-corpus/harness/internal/label"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/manifest"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/score"
	"github.com/basdotio/agent-artifact-corpus/harness/internal/taxonomy"
)

// cmdTable writes the corpus as three tables a person can sort and filter: the malicious
// samples (table/malicious.csv), the benign and hard-negative ones (table/benign.csv), and
// every upstream sample that was read and left out (table/excluded.csv), plus all three as the
// sheets of out/corpus-table.xlsx. Malicious and benign are apart because most columns of one
// mean nothing for the other: a benign row has no dimension, tier or deciding line.
//
// Nothing in the tables is written by hand. They are rendered from the labels, the manifest's
// exclude_samples and the ClawHub intake state, which stay the records of truth; a table kept
// by hand would drift from them the first time an entry was re-derived, and nothing would
// notice. CI re-renders the CSVs and fails when the committed ones differ. The workbook is
// binary and lives under out/, which is not committed.
func cmdTable(root string, args []string) int {
	if len(args) != 0 {
		fmt.Fprintln(os.Stderr, "usage: corpus table")
		return 2
	}
	mal, ben, err := sampleRows(root)
	if err != nil {
		fatal(err)
	}
	excluded, err := excludedRows(root)
	if err != nil {
		fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "table"), 0o755); err != nil {
		fatal(err)
	}
	for name, rows := range map[string][][]string{"malicious.csv": mal, "benign.csv": ben, "excluded.csv": excluded} {
		if err := writeCSV(filepath.Join(root, "table", name), rows); err != nil {
			fatal(err)
		}
	}
	if err := os.MkdirAll(filepath.Join(root, "out"), 0o755); err != nil {
		fatal(err)
	}
	xlsx := filepath.Join(root, "out", "corpus-table.xlsx")
	if err := writeXLSX(xlsx, []sheet{{"malicious", mal}, {"benign", ben}, {"excluded", excluded}}); err != nil {
		fatal(err)
	}
	fmt.Printf("table/malicious.csv %d samples\ntable/benign.csv    %d samples (benign and hard-negative)\ntable/excluded.csv  %d left out\n%s  all three, as sheets\n",
		len(mal)-1, len(ben)-1, len(excluded)-1, rel(root, xlsx))
	return 0
}

var malHeader = []string{
	"id", "surface", "kind", "dimensions", "techniques", "tier", "evasion", "locus",
	"severity", "evidence_file", "evidence_lines", "evidence_quote", "dimension_basis",
	"provenance", "origin", "entry", "source", "license", "added", "path",
}

// A hard negative is listed with the benign samples; resembles and differs_by say what it
// looks like and what makes it harmless, and are empty for every other benign row.
var benHeader = []string{
	"id", "class", "surface", "kind", "resembles", "differs_by",
	"provenance", "origin", "entry", "source", "license", "added", "path",
}

func sampleRows(root string) (mal, ben [][]string, err error) {
	labels, err := loadLabels(root)
	if err != nil {
		return nil, nil, err
	}
	tax, err := taxonomy.Load(filepath.Join(root, "taxonomy"))
	if err != nil {
		return nil, nil, err
	}
	prov := provenanceMap(root)
	sort.Slice(labels, func(i, j int) bool { return labels[i].ID < labels[j].ID })
	mal, ben = [][]string{malHeader}, [][]string{benHeader}
	for _, l := range labels {
		t := l.Truth
		var file, lines, quote []string
		basis := ""
		if l.Basis != nil {
			basis = l.Basis.Dimension
			for _, e := range l.Basis.Evidence {
				file, lines, quote = append(file, e.File), append(lines, e.Lines), append(quote, e.Quote)
			}
		}
		entry := ""
		if l.Origin.DerivedFrom != nil {
			entry = l.Origin.DerivedFrom.Entry
		}
		where := []string{score.EvidenceClass(l, prov), l.Origin.Type, entry, l.Origin.Source,
			l.Origin.License, l.Origin.Added, l.Rel}
		if l.Class != label.Malicious {
			ben = append(ben, append([]string{l.ID, string(l.Class), strings.Join(l.Surface, ";"), l.Kind,
				strings.Join(t.Resembles, ";"), t.DiffersBy}, where...))
			continue
		}
		mal = append(mal, append([]string{
			l.ID, strings.Join(l.Surface, ";"), l.Kind,
			strings.Join(dimensionsFor(l, tax), ";"), strings.Join(t.Techniques, ";"), t.Tier,
			strings.Join(t.Evasion, ";"), strings.Join(t.Locus, ";"), t.Severity,
			strings.Join(file, "\n"), strings.Join(lines, "\n"), strings.Join(quote, "\n"), basis,
		}, where...))
	}
	return mal, ben, nil
}

// dimensionsFor names a sample's dimensions whether its label gives them directly (derived) or
// through techniques (hand-pinned), so every malicious row says what kind of harm it is.
func dimensionsFor(l *label.Label, tax *taxonomy.Set) []string {
	set := map[string]bool{}
	for _, d := range l.Truth.Dimensions {
		set[d] = true
	}
	for _, id := range l.Truth.Techniques {
		if tc, ok := tax.Techniques[id]; ok && tc.Dimension != "" {
			set[tc.Dimension] = true
		}
	}
	out := make([]string, 0, len(set))
	for d := range set {
		out = append(out, d)
	}
	sort.Strings(out)
	return out
}

var excludedHeader = []string{"entry", "sample", "status", "decided", "reason"}

// excludedRows lists every sample the manifest names in exclude_samples, with the reason it
// gives, and the ClawHub candidates the intake never queued (publisher cap, duplicate,
// held-out). Whole categories dropped by exclude_tokens are not listed: they are dropped by
// path before anyone reads them, and the manifest states each token.
func excludedRows(root string) ([][]string, error) {
	type intakeRow struct {
		Tree, Status, Decision, Decided, Reason string
	}
	var state struct {
		Rows map[string]intakeRow `json:"rows"`
	}
	byTree := map[string]intakeRow{}
	if b, err := os.ReadFile(filepath.Join(root, "manifest", "pins", "clawhub-intake.json")); err == nil {
		if err := json.Unmarshal(b, &state); err != nil {
			return nil, fmt.Errorf("clawhub-intake.json: %w", err)
		}
		for _, r := range state.Rows {
			byTree[r.Tree] = r
		}
	}
	var rows [][]string
	manifests, _ := filepath.Glob(filepath.Join(root, "manifest", "*.yaml"))
	for _, mp := range manifests {
		f, err := manifest.Load(mp)
		if err != nil {
			return nil, err
		}
		for _, e := range f.Entries {
			if e.Derive == nil {
				continue
			}
			for s, why := range e.Derive.ExcludeSamples {
				rows = append(rows, []string{e.ID, s, "excluded", byTree[s].Decided, why})
			}
		}
	}
	for _, r := range state.Rows {
		if r.Status != "decided" && r.Status != "queued" {
			rows = append(rows, []string{"clawhub-live", r.Tree, r.Status, r.Decided, r.Reason})
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i][0] != rows[j][0] {
			return rows[i][0] < rows[j][0]
		}
		return rows[i][1] < rows[j][1]
	})
	return append([][]string{excludedHeader}, rows...), nil
}

func writeCSV(path string, rows [][]string) error {
	var b bytes.Buffer
	w := csv.NewWriter(&b)
	if err := w.WriteAll(rows); err != nil {
		return err
	}
	return os.WriteFile(path, b.Bytes(), 0o644)
}

type sheet struct {
	name string
	rows [][]string
}

// writeXLSX writes the smallest workbook Excel, Numbers and LibreOffice all open: inline
// strings, no styles. Hand-rolled because the harness depends on yaml.v3 alone and one table
// is not worth a spreadsheet library.
func writeXLSX(path string, sheets []sheet) error {
	var buf bytes.Buffer
	z := zip.NewWriter(&buf)
	add := func(name, body string) error {
		w, err := z.Create(name)
		if err != nil {
			return err
		}
		_, err = w.Write([]byte(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` + "\n" + body))
		return err
	}
	const ns = `xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"`
	var ct, wbSheets, wbRels strings.Builder
	for i := range sheets {
		n := i + 1
		fmt.Fprintf(&ct, `<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`, n)
		fmt.Fprintf(&wbSheets, `<sheet name="%s" sheetId="%d" r:id="rId%d"/>`, xmlText(sheets[i].name), n, n)
		fmt.Fprintf(&wbRels, `<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>`, n, n)
	}
	parts := [][2]string{
		{"[Content_Types].xml", `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
			`<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
			`<Default Extension="xml" ContentType="application/xml"/>` +
			`<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
			ct.String() + `</Types>`},
		{"_rels/.rels", `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
			`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`},
		{"xl/workbook.xml", `<workbook ` + ns + `><sheets>` + wbSheets.String() + `</sheets></workbook>`},
		{"xl/_rels/workbook.xml.rels", `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` + wbRels.String() + `</Relationships>`},
	}
	for _, p := range parts {
		if err := add(p[0], p[1]); err != nil {
			return err
		}
	}
	for i, s := range sheets {
		var b strings.Builder
		// The header row stays in view while scrolling.
		b.WriteString(`<worksheet ` + ns + `><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews><sheetData>`)
		for r, row := range s.rows {
			fmt.Fprintf(&b, `<row r="%d">`, r+1)
			for _, v := range row {
				b.WriteString(`<c t="inlineStr"><is><t xml:space="preserve">` + xmlText(v) + `</t></is></c>`)
			}
			b.WriteString(`</row>`)
		}
		b.WriteString(`</sheetData></worksheet>`)
		if err := add(fmt.Sprintf("xl/worksheets/sheet%d.xml", i+1), b.String()); err != nil {
			return err
		}
	}
	if err := z.Close(); err != nil {
		return err
	}
	return os.WriteFile(path, buf.Bytes(), 0o644)
}

// xmlText escapes a cell for XML, drops the control characters XML 1.0 cannot carry (some
// quotes are copied from files that contain them), and keeps under Excel's 32,767-character
// cell limit.
func xmlText(s string) string {
	var b strings.Builder
	n := 0
	for _, r := range s {
		if n >= 32000 {
			b.WriteString("…")
			break
		}
		switch {
		case r == '&':
			b.WriteString("&amp;")
		case r == '<':
			b.WriteString("&lt;")
		case r == '>':
			b.WriteString("&gt;")
		case r == '"':
			b.WriteString("&quot;")
		case r < 0x20 && r != '\t' && r != '\n' && r != '\r', r == 0xFFFE, r == 0xFFFF:
			continue
		default:
			b.WriteRune(r)
		}
		n++
	}
	return b.String()
}
