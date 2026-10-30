package main

import (
	"archive/zip"
	"encoding/xml"
	"io"
	"path/filepath"
	"strings"
	"testing"
)

func TestXMLTextEscapesAndDropsControlCharacters(t *testing.T) {
	if got := xmlText("a<b>&\"c\x01\x1bd\te"); got != "a&lt;b&gt;&amp;&quot;cd\te" {
		t.Fatalf("got %q", got)
	}
	if got := xmlText(strings.Repeat("x", 40000)); len([]rune(got)) != 32001 {
		t.Fatalf("a long cell must be cut under Excel's limit, got %d runes", len([]rune(got)))
	}
}

// Every part of the workbook has to be well-formed XML, or Excel refuses the whole file.
func TestWriteXLSXIsWellFormed(t *testing.T) {
	path := filepath.Join(t.TempDir(), "t.xlsx")
	rows := [][]string{{"id", "quote"}, {"a", "curl <x> & \x00 \"y\""}}
	if err := writeXLSX(path, []sheet{{"included", rows}, {"excluded", rows[:1]}}); err != nil {
		t.Fatal(err)
	}
	z, err := zip.OpenReader(path)
	if err != nil {
		t.Fatal(err)
	}
	defer z.Close()
	if len(z.File) != 6 {
		t.Fatalf("want 6 parts for two sheets, got %d", len(z.File))
	}
	for _, f := range z.File {
		r, err := f.Open()
		if err != nil {
			t.Fatal(err)
		}
		d := xml.NewDecoder(r)
		for {
			if _, err := d.Token(); err == io.EOF {
				break
			} else if err != nil {
				t.Fatalf("%s: %v", f.Name, err)
			}
		}
		r.Close()
	}
}
