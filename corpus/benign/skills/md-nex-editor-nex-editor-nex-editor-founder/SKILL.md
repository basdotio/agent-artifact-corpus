---
name: nex-editor-founder
description: Use when working on nex-editor architecture or implementation, especially the Rust editor core, runtime facade, WASM bridge, browser playground, or cross-platform rendering protocol.
---

# Nex Editor Founder

Treat `nex-editor` as a headless editor engine with thin platform shells. Optimize for stable editor boundaries and incremental delivery, not feature breadth.

## Use This Skill For

- Rust editor core work in `model`, `transform`, `state`, `commands`
- Plain-text runtime work in `runtime`
- WASM bridge work in `wasm`
- Browser playground work in `apps/web-playground`
- Cross-platform protocol and rendering-boundary decisions

## Core Direction

- Preserve the dependency direction: `model -> transform -> state -> commands -> runtime -> wasm/shells`.
- The editing truth lives in Rust. Platform shells render snapshots and send commands.
- Prefer a narrow, correct plain-text editor over a broad but stubbed rich-text system.
- Add product-visible capabilities only after the command/snapshot boundary is stable.

## Rules

- Keep platform-agnostic logic out of web-specific code.
- Do not expose internal document structure directly to shells when a plain snapshot is enough.
- Commands mutate state; snapshots are read-only render/input data.
- If a feature is not implemented, return a no-op or explicit failure. Never fake success.
- For browser work, avoid `contenteditable` as the source of truth.
- For end-to-end tests, prefer shared hooks/harness helpers over ad hoc event plumbing inside each spec.

## Working Loop

1. Run `cargo test`.
2. For browser changes, also validate `apps/web-playground`.
3. Fix contract breaks before adding new behaviors.
4. Add tests at the behavior boundary that changed.

## Read As Needed

- For architecture boundaries and layer responsibilities: [references/architecture.md](./references/architecture.md)
- For runtime, WASM, and shell protocol rules: [references/runtime-and-shells.md](./references/runtime-and-shells.md)
- For browser playground workflow and constraints: [references/web-playground.md](./references/web-playground.md)
