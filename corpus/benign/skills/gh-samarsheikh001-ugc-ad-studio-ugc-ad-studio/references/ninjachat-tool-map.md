# NinjaChat MCP operation map

Use live tool schemas and current catalog responses. The current MCP tool family exposes the operations below. Do not assume a model or feature remains available just because a previous run used it.

Official documentation: [NinjaChat MCP overview](https://docs.ninjachat.ai/mcp/overview.md), [MCP quickstart](https://docs.ninjachat.ai/mcp/quickstart.md), [client setup](https://docs.ninjachat.ai/mcp/clients.md), [UGC recipes](https://docs.ninjachat.ai/mcp/recipes.md), [tool reference](https://docs.ninjachat.ai/mcp/tools.md), and [billing/limits](https://docs.ninjachat.ai/mcp/billing.md).

| Workflow need | NinjaChat operation | Notes |
|---|---|---|
| Confirm available media models/capabilities | `search_models` | Free. Filter image/video/audio and reference-image support; select from returned models. |
| Quote a generation | `estimate_cost` | Free. Quote the corresponding image, video, image-to-video, edit, extension or speech operation with its actual prompt/input, model, duration, references and count. |
| Create or route an image/video | `create_media` | Default general operation for new media, edits, animation or options. Use `quality` and a hard `max_spend_cents`; provide aspect, duration, references and a stable idempotency key as appropriate. |
| Fine-control image generation/edit | `generate_image` / `edit_image` | Use when the source/reference or output controls require the specialist operation. |
| Generate a video with optional native audio | `generate_video` | Verify current model/audio and reference support first. Do not promise spoken dialogue or lip-sync unless supported and reviewed. |
| Animate a product/person still | `image_to_video` | Requires a suitable image reference and model; reference support and generated audio vary by model. |
| Continue or revise a video | `extend_video` / `edit_video` | Extensions add 3–10 seconds and may grow a clip up to 40 seconds per current tool description; quote against the existing source and verify each returned continuation. |
| Make a standalone voice track | `generate_speech` | Use exact script, quote it first, and return as AI-generated audio. Audio is a separate track unless an authorized edit actually mixes it. |
| Send a local authorized asset | `upload_asset` | Provide exact byte size and content type. Never save short-lived signed upload URLs in project records. |
| Resume/check result | `get_generation_status` / `get_creation` | Save and reuse generation IDs. Do not submit a new billable request just because polling failed. |
| Help inspect a NinjaChat video | `prepare_scrub_video` | Use only for the inspection output it actually returns; it is not a semantic/audio analyzer by default. |
| Save a keeper for later reuse | `save_creation_as` / `list_creative_entities` | Save only when useful and user-approved/named. Do not persist a real person's identity as a reusable character without consent. |

## Spend rules

1. Use a live catalog search when quality, budget, reference support or a specific visual is important.
2. Quote the exact request with `estimate_cost`; preserve tool-returned pricing rather than estimating from a different model.
3. Show scope and total, then wait for approval. When the user has approved a precise batch already, keep each request inside it.
4. Pass a hard per-call maximum and a unique idempotency key. Reuse the same key after a timeout or uncertain response.
5. Poll the same job to a terminal state. Track failure/refund evidence; do not automatically reroll.

## Key provider differences

- The original kit specifies Higgsfield's analyzer and Seedance-specific operation modes. NinjaChat routes through its own media tools and catalog, so those identifiers and behaviors must not be copied into a NinjaChat call.
- Opus 5.5 remains the active reasoning model in Claude; NinjaChat should supply media capabilities, not replace Claude's selected model.
- Check selected model constraints before giving an output-length plan. The original three-part 30+30+8s proposal was provider-specific, not a universal NinjaChat recipe.
