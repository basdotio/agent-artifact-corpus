---
name: godot-autonomous-iteration
description: "Autonomously iterate a Cloverhollow Godot 2D level or art slice from spec to implementation to deterministic playtest and captured visual evidence, while stopping safely on unsupported tooling."
compatibility: Godot 4.5.1 and repository CI/scenario scripts
---

# Godot autonomous iteration

Follow a tight loop: inspect spec and existing implementation, make one small
change under `game/` or the explicitly requested asset path, run the relevant
Scenario Runner scenario, inspect trace/log/completion/captures, then keep or
revert the hypothesis. Read captured images with image reading/vision.
Scenario Runner is the required behavioral harness and does not require MCP.
The DEV-only `satellite` MCP is supplementary read-only observation against an
external disposable snapshot. Treat the quarantined legacy MCP and image tools
as unavailable. The configured `godot-lsp-bridge` is only a compatibility
setting because V2 does not start LSP servers from `lsp` configuration; do not
claim active diagnostics.

Before editing, resolve real scene paths, scripts, input actions, scenario IDs,
palette files, and asset dimensions from the repository. Respect the eight
directions in the art docs, 16x16 tile grid, varied sprite sizes, 512x288 base
resolution, pixel-stable camera, and spec.md source-of-truth rule.

## Safety and stop conditions

Fail closed on missing files, unknown APIs, tool errors, no trace, `passed` not
true, errors/noop events, missing expected captures, or visual evidence that
does not support the hypothesis. Do not claim a `check_*` log action is an
assertion. Do not use OS-level window control, blanket quantization, or an
unverified image-generation command. Image generation is opt-in only, never
automatic, and must not require API keys or paid services.

For art, use the locked `uv`/Pillow pipeline in
`docs/art/verified-pipeline.md`: nested `.colors` palettes and repeated palette
unions are supported, transparent RGB is ignored, sizes are explicit, and
quantization requires a separate non-overwriting output. Validate every changed
asset explicitly; `just validate-assets` is only two selected bench samples.
Update spec.md when behavior or a decision changes, and keep every iteration
small and scenario-backed.

For exact dialogue or UI text, do not trust previous visual approvals. Corroborate
trace/diff evidence with OCR and a fresh native-PNG attachment review using
`tools/agents/review-capture.ts`; generic model approval is not acceptance.
Use the current `opencode2 models` catalog, and fail closed if the configured
model is unavailable. The legacy built-in vision helper is disabled.
