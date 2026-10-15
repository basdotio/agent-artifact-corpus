# Working with the Predis MCP

Every skill in this repo makes media through the Predis MCP connector (`https://mcp.predis.ai/mcp`). This file is the run loop they all share. It is copied into each skill's `references/` folder so every skill installs on its own.

## Before anything

- Look for Predis tools (names end in `get_account`, `list_models`, `generate`). If none are there, stop and say: "Add the Predis connector first: Settings, Connectors, Add custom connector, paste `https://mcp.predis.ai/mcp`, then sign in." Never use another provider.
- Call `get_account` once. If `ready_to_create` is false, tell the user its `tell_user` sentence in your own words, offer its `next_step`, and stop.
- There is no brand kit tool. The brand look comes from what the user gives you: a product page, a logo, an earlier ad, or their words. For files already in Predis (including the brand logo), call `choose_from_uploads`. Never claim you loaded a brand kit.

## The loop

1. `list_models` (filter with `capability` and `family`) once per chat. Starting picks in each skill are defaults, not facts: if a pick is missing from the live list, take the closest live model with the same capability and say so in one line.
2. `describe_model` once per model before first use. Pass only option names it lists, with allowed values.
3. References, numbered in the order the prompt mentions them ("image 1", "video 1"):
   - Public https link to a file: `add_reference(url=...)`
   - File attached in ChatGPT: `add_reference(chatgpt_file=...)`
   - File already in Predis: `choose_from_uploads`, then ask the user to send a message once they have picked
   - Local file: `start_upload`, send the bytes to the link it returns, then `add_reference(upload_id=...)`
   - An earlier output: `add_reference(asset_id=...)` with the asset id from `check_run` or `list_runs`
4. `estimate_cost` before every generation. Tell the user the total credits for the whole job in one line. If the whole job is over 150 credits, ask before spending.
5. `generate` with a fresh `idempotency_key` per take (a new UUID). Reuse a key only to retry a call that errored with no run id. Independent takes go out in one batch.
6. Results:
   - If the result says the app shows a result card, don't wait or poll. The card shows the outputs.
     Exception: when a later step needs this output (as a reference, or to fix it), call `wait_for_run` anyway so you have its asset id.
   - Otherwise call `wait_for_run` until the run finishes, then `check_run` for the output links.
7. A failed run: read the error, fix the obvious cause (option value, reference, refused prompt), retry once with a new key. Fails again: one plain sentence on why, and stop.

## Files and ffmpeg

Some steps (stitching clips, trimming a shot, resizing) need ffmpeg. Check once with `ffmpeg -version`.
- Works: download outputs with `curl -L -o` into `./predis-output/<skill>/<job>/` and do the step.
- No shell, no ffmpeg, or the download is blocked: skip the step, share the output links, and give the user the one exact edit to make in their editor ("put hook B in front of the original from 0:03"). Never pretend a file was edited.

## Talking to the user

- Say what you are making and what it costs, then show the result. No tool names, model ids, run ids, field names or polling updates.
- Look at every image output before showing it. For video, look at one frame if you can extract it.
- Things the MCP cannot do: voiceover or TTS, lip-sync to a script, captions burned in by a tool, publishing or launching ads. Say so and offer the closest thing it can do. Sound comes only from native-audio video models or a file the user gives.
- Real people, other brands' logos or copyrighted characters: steer to an original look before spending.
