package config

import "os"

// SaveToken never makes the token readable by other users.
func SaveToken(path, token string) error {
	return os.WriteFile(path, []byte(token), 0600)
}
