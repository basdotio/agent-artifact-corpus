---
name: ugc-ad-studio
description: Guide end-to-end product UGC ad creation with AI-assisted research and NinjaChat MCP media tools. Use when planning, scripting, generating, or revising product UGC ads.
---

# UGC Ad Studio

Run a guided, product-first UGC process inspired by [Miko's video-ad stack](https://github.com/mikoxai/miko-video-ad-stack), adapted for Claude and NinjaChat MCP. Do not invoke Higgsfield or Seedance-specific APIs from the source kit.

Read [the guided workflow](references/guided-workflow.md) first. Load [the NinjaChat tool map](references/ninjachat-tool-map.md) when preparing assets, choosing media operations, quoting cost, or generating. Load [the prompt contract](references/prompt-contract.md) before showing a generation-ready prompt. See [the source-example mapping](references/miko-example-map.md) to keep the adapted process connected to the tutorial, and [client setup](references/client-setup.md) before a Claude production session.

## Start

Use this starter when the user says “start the UGC ad stack”:

> Start UGC Ad Studio. Ask me for the product or brand website first. Research its claims and visual identity, then ask for the reference video or videos. Show me the reference breakdown, an original script, shot plan, image map, and generation prompts. Quote the proposed NinjaChat media calls and wait for my “generate” instruction before creating paid media.

Collect missing inputs progressively. Reuse the product, references, brand assets, style choices, output format and approvals already supplied. Do not make the user repeat them.

## Hard requirements

- Confirm that the active Claude client is using Opus 5.5 and that NinjaChat MCP tools are present in that same client. A NinjaChat connection in another assistant session does not prove Claude is connected.
- Treat Opus as the research, scripting and tool-orchestration model. NinjaChat MCP performs the selected image, video, editing, animation and speech operations.
- The source workflow is guided by default. Do not make paid media calls until the user approves the current prompt/script and says “generate,” unless the current conversation already grants a matching, bounded generation scope.
- Quote the selected operation and planned batch before generation. Use NinjaChat's estimate and per-call spending limit. Never silently exceed the approved batch.
- Keep product facts separate from creative hypotheses. Link every material product claim to a public source or user-supplied evidence.
- A generated actor's testimonial is a staged performance, not evidence of a real customer's experience. Do not invent a review, rating, endorsement, price, discount or performance claim.
- Analyze reference mechanics; create original dialogue and product-specific scenes. Do not reproduce creator identity, copied claims, logos or protected packaging from a reference.
- Do not promise audio/video lip-sync, continuous character identity, exact object control, or an exact requested duration until the selected NinjaChat model supports it and the returned media passes review.
- Do not publish, post, or send assets externally from this workflow.

## Setup boundary

Opus 5.5 is an Anthropic model. NinjaChat MCP exposes media tools, not an alternate way to select Opus inside Claude. Verify model selection in Claude and NinjaChat connection in Claude separately. Do not write API keys into project files or prompts. If the client lacks a required connection, disclose the setup gap and continue with prompt planning only.

## Output and records

Keep project work under the active campaign directory: sourced research, reference notes, approved script/shot plan, generation prompts and product-image map, quoted scope, output manifest, results and review notes. Save job IDs before polling; resume existing jobs rather than duplicating them. Keep credentials, signed upload URLs and private customer materials out of committed files.
