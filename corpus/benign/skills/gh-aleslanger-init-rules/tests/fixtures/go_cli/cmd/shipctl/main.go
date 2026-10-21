package main

import (
	"fmt"
	"os"

	"example.com/shipctl/internal/config"
)

func main() {
	if err := config.SaveToken(os.Args[1], os.Getenv("SHIPCTL_TOKEN")); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
