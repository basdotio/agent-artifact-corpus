---
name: Spatia Protocol
description: Tools for interacting with the Spatia Atomic System
---

# Spatia Protocol

This skill provides access to the Spatia toolchain for managing the Atomic Semantic Graph.

## Tools

### Shatter (File System -> DB)
Ingest the current state of the file system into the Sentinel DB.
This handles all files not in the ignore list (.git, .spatia, .agent).

```bash
devbox run .spatia/bin/spatia-shatter.py
```

### Materialize (DB -> File System)
Reconstruct the file system from the Sentinel DB.
Useful for deploying or resetting the workspace to a specific state.

```bash
devbox run .spatia/bin/spatia-materialize.py
```

### Endorse (Status Update)
Mark atoms as endorsed (approved).
Usage: `devbox run .spatia/bin/spatia-endorse.py [atom_id]`
If no atom_id is provided, endorses all pending atoms.

```bash
devbox run .spatia/bin/spatia-endorse.py
```

## Setup
Ensure the environment is initialized:
```bash
devbox run make setup
```
