---
name: templui
description: templui CLI workflows and component usage for Go templ + Tailwind UI. Use when asked to install or use templui, initialize .templui.json, add/update/list components, integrate JS assets, set up Tailwind or themes, or when a project needs templui components.
---

# templui

## Overview

Use templui to add accessible UI components to Go templ projects. Prefer the CLI to install components into the codebase so they can be customized and owned locally.

## Workflow

1) Decide if the user wants a new project or to integrate into an existing app.
2) For new projects, run `templui new` and follow the generated setup.
3) For existing projects, verify requirements, install the CLI, run `templui init`, and add components.
4) Wire JS assets and base styles, then update components as needed.

## Component Selection

- Use `references/components.md` to pick component names and open the matching docs link.
- Use `templui list` to confirm availability or check a specific version.

## Integration Details

- Add the `Script()` template function for components that ship JavaScript.
- Serve `jsDir` at `jsPublicPath` and confirm routing matches your server setup.
- If module name or paths are unknown, read `go.mod` and `.templui.json`.

## References

- Read `references/how-to-use.md` for CLI commands, init config, JS routing, and dev workflow hints.
- Read `references/components.md` for the component catalog and doc links.
