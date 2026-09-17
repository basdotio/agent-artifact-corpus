---
name: developing-with-docker
description: Debugging-first guidance for professional Docker development across CLI, Compose, Docker Desktop, and Rancher Desktop. Use when asked to "debug Docker", "troubleshoot containers", "fix Docker networking", "resolve volume permissions", or "Docker Compose issues", and when explaining cross-platform runtime behavior (Linux, macOS, Windows/WSL2) or Docker runtime architecture.
license: MIT
metadata:
  version: 1.0.0
---

# Developing With Docker

## Overview

Provide deterministic, debugging-first guidance for Docker CLI and Compose, focusing on root causes that vary by platform and runtime. Prefer concise, actionable checks and commands, and reference the corpus for deeper explanations.

## Quick Start

- Load the split references for deep dives:
  - `references/guide-foundations.md`
  - `references/guide-installation-connectivity.md`
  - `references/guide-cli-debugging.md`
  - `references/guide-advanced-debugging.md`
  - `references/guide-networking-compose-ops.md`
- Use the workflow below for most troubleshooting requests; branch into the relevant section.

## Example Requests

- "Containers can't reach my host database on Linux."
- "Docker Desktop on Mac can't access container IPs."
- "My bind mount is slow on Windows with WSL2."
- "Compose service keeps restarting after depends_on."

## Debugging Workflow (Default)

1. Identify platform and runtime
   - Ask for OS, Docker Desktop vs Rancher Desktop, and runtime backend (dockerd vs containerd/nerdctl).
   - Clarify where the daemon runs (native Linux vs VM/WSL2) before suggesting network or file fixes.
2. Validate daemon and context
   - Check `docker context ls` and current context.
   - If CLI hangs, suspect dockerd API availability vs containerd still running.
3. Inspect container state
   - Use targeted `docker inspect --format` queries for exit codes, mounts, log path, and PID.
4. Check logs and signals
   - Confirm PID 1 behavior and signal handling; suggest `exec` in entrypoint scripts.
   - Address stdout buffering or logs written to files instead of stdout/stderr.
5. Branch by symptom:
   - Connectivity: port bindings, `host.docker.internal`, localhost vs 0.0.0.0, Desktop proxying.
   - Volumes/permissions: UID/GID mismatch, rootless constraints, bind mount performance.
   - Compose: depends_on readiness, env precedence, orphaned services.

## Validation Checklist

- [ ] Verified active context with `docker context ls`
- [ ] Confirmed container state via `docker inspect --format` (exit code, mounts, PID)
- [ ] Checked logs for stdout/stderr buffering issues
- [ ] Verified port bindings and host reachability for the platform
- [ ] Confirmed bind mount performance path (VirtioFS/WSL2 path)

## Findings Template

- Platform/runtime:
- Active context:
- Container state (exit code, PID):
- Networking diagnosis:
- Volume/permissions diagnosis:
- Recommended next command:

Example Output:
- Platform/runtime: macOS, Docker Desktop 4.27
- Active context: default
- Container state (exit code, PID): exit 137, PID 4021
- Networking diagnosis: port bound to 127.0.0.1, not reachable externally
- Volume/permissions diagnosis: VirtioFS enabled, no UID mismatch
- Recommended next command: docker compose logs --tail 50 api

## Core Capabilities

- Explain Docker architecture (CLI, dockerd, containerd, runc, shim) and why it matters for debugging.
- Distinguish Linux-native behavior from macOS/Windows VM and WSL2 boundaries.
- Provide reliable CLI/Compose command recipes for state inspection and debugging.
- Diagnose performance issues tied to file sharing (VirtioFS, 9P) and build context size.
- Apply pragmatic networking guidance for host-to-container and container-to-host access.

## Usage Notes

- Favor deterministic checks over trial-and-error. Explain "why" briefly when it helps avoid repeat mistakes.
- If the user mentions Docker Desktop versions, Rancher Desktop settings, or WSL2 paths, align advice to those specifics.
- When giving commands, prefer minimal, copy-pasteable sequences; avoid long scripts unless necessary.

## When Not to Use

- Do not use for general Kubernetes orchestration guidance unless the issue is specifically Docker Desktop/Rancher Desktop related.
- Do not use for container security hardening beyond local development troubleshooting.

## Reference Material

- Use the split reference set for deep dives and platform-specific behavior:
  - `references/guide-foundations.md`
  - `references/guide-installation-connectivity.md`
  - `references/guide-cli-debugging.md`
  - `references/guide-advanced-debugging.md`
  - `references/guide-networking-compose-ops.md`
- For migration from Docker Desktop to Rancher Desktop:
  - `references/guide-rancher-migration.md`
