---
name: ebpf-go
description: eBPF development in Go using github.com/cilium/ebpf (and bpf2go) for tracing and networking (kprobes/uprobes, tracepoints, XDP, TC). Use when writing/reviewing/debugging Go + eBPF code, setting up CO-RE/BTF toolchains, integrating maps and ringbuf/perf events, or diagnosing verifier/load/attach failures on Linux.
---

# Ebpf Go

## Overview

Build, debug, and ship eBPF programs written in C and loaded/controlled from Go.

Assume Linux. If working from macOS/Windows, run and test eBPF in a Linux VM/container with a recent kernel.

## Workflow Decision Tree

1. Identify the goal:
	- **Observability / tracing**: syscalls, kernel functions, user-space functions → tracepoint/kprobe/uprobe
	- **Networking**: packets / sockets, filtering/redirect/shaping → XDP/TC/cgroup/socket

2. Decide portability:
	- **Need “build once, run many kernels”** → use **CO-RE** with BTF + `vmlinux.h`
	- **Single known kernel** → non-CO-RE builds may be acceptable (still prefer CO-RE)

3. Decide data path from BPF → Go:
	- **High-rate events** → ringbuf (preferred) or perf event
	- **State / counters** → maps (hash/LRU/percpu/array) polled from Go
	- **Configuration** → maps updated from Go

If you need details for a decision point, load the relevant reference file from `references/`.

## Track-Specific Guidance

After you pick a goal, load exactly one of these first:

- **Observability / tracing**: `references/tracing.md`
- **Networking (XDP / TC)**: `references/networking-xdp-tc.md`

## Standard Workflow (C + bpf2go + Go)

Follow this shape unless there’s a strong reason not to:

1. Create a minimal project layout
	- Put BPF C sources under `bpf/` (e.g., `bpf/prog.bpf.c`)
	- Generate Go bindings via `//go:generate` + `bpf2go`
	- Keep runtime code under `cmd/<tool>/` or `internal/`
	- For a concrete layout, read `references/project-layout.md`

2. Implement the BPF program
	- Keep it verifier-friendly: bounded loops, simple control flow, careful pointer arithmetic
	- Prefer CO-RE (`vmlinux.h`, `BPF_CORE_READ`, `bpf_core_read*`) when touching kernel structs
	- Choose maps and event mechanism early (ringbuf/perf/maps)
	- For toolchain and CO-RE specifics, read `references/toolchain-and-core.md`

3. Generate Go bindings
	- Use `bpf2go` to compile the C to BPF bytecode and generate Go types/loaders
	- Keep compilation flags consistent across environments

4. Load and verify
	- Raise memlock/rlimits (commonly via `rlimit.RemoveMemlock()`)
	- Load the `CollectionSpec`, apply any rewrites, then `NewCollection()`
	- When load fails, capture verifier logs and consult `references/troubleshooting.md`

5. Attach
	- Use `github.com/cilium/ebpf/link` to attach to the chosen hook
	- Pin if needed; always close links on shutdown
	- For hook-specific guidance, read `references/program-types-and-attach.md`

6. Read events / interact with maps
	- ringbuf: decode event structs and handle backpressure
	- perf: handle lost samples; tune buffer sizes
	- maps: prefer per-cpu for hot counters; avoid frequent full scans
	- For Go-side patterns, read `references/go-integration-patterns.md`

7. Harden & ship
	- Use capabilities carefully (often `CAP_BPF`/`CAP_PERFMON`/`CAP_SYS_ADMIN` depending on kernel)
	- Include a fallback path or clear error messages for kernels lacking features
	- Provide “dry run”/self-check output (kernel + feature probe)

## Debugging Checklist (Fast)

- Confirm environment: Linux kernel, BTF present at `/sys/kernel/btf/vmlinux`, correct arch.
- Confirm toolchain: `clang` can target BPF, `bpftool` present for diagnostics.
- For load errors:
  - Turn on verifier logs (cilium/ebpf supports `ebpf.CollectionOptions{Programs: ebpf.ProgramOptions{LogLevel, LogSize}}` patterns).
  - Inspect `dmesg` for verifier output.
- For attach errors:
  - Confirm the attach point exists (interface, tracepoint name, symbol present).
  - Verify permissions/capabilities and mount settings.
- For “it loads but does nothing”:
  - Add minimal counters in a map to prove execution.
  - Validate event struct layout/alignment between C and Go.

## References (Load On Demand)

- `references/toolchain-and-core.md`: clang/bpf2go, CO-RE/BTF, `vmlinux.h` generation.
- `references/program-types-and-attach.md`: which hook to choose + how to attach from Go.
- `references/go-integration-patterns.md`: maps/events patterns, lifecycle, performance.
- `references/troubleshooting.md`: common errors, verifier failures, kernel feature probes.
- `references/project-layout.md`: recommended repo layout and `go:generate` conventions.
- `references/tracing.md`: tracing/observability patterns and practical heuristics.
- `references/networking-xdp-tc.md`: XDP/TC decision guidance, map patterns, debugging cues.
