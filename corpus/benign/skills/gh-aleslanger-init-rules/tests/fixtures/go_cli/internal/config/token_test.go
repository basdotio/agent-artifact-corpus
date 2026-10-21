package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestSaveTokenPermissions(t *testing.T) {
	path := filepath.Join(t.TempDir(), "token")
	if err := SaveToken(path, "test-token"); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0600 {
		t.Fatalf("want 0600, got %o", info.Mode().Perm())
	}
}
