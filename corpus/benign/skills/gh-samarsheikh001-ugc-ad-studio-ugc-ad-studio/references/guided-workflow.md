# Guided workflow

This adapts the four-stage Miko workflow. The sequence stays: product research → reference breakdown → editable ad plan → media generation and review. NinjaChat replaces Higgsfield for creation; the selected Claude Opus 5.5 client coordinates the work.

## 1. Product intake and research

Ask for the product/brand website and any available product images, packaging reference, existing ad, audience notes, customer-review evidence or claims document. These extras are optional at intake.

Visit the supplied public pages with the active client’s available browser. Inspect the home, product and useful about/FAQ pages. Record dates, URLs, actual wording, visible product construction and unresolved contradictions. Separate sourced facts from interpretations and creative directions. Do not call a page exhaustive research when pages or login-only sources were inaccessible.

Save a readable brand brief with product facts, voice, visual identity, audience hypotheses, purchase motivations, claim sources, creative angles and gaps. For regulated, health, financial or safety claims, preserve only what authoritative product evidence explicitly supports.

## 2. Reference intake and breakdown

Ask for the video or videos and which concept they want adapted if that is not clear. Prefer user-provided or authorized media files when a platform link does not provide inspectable footage. Record source URL and permissions/provenance.

Inspect the actual footage. Use ffprobe/ffmpeg for technical properties and frame sampling/contact sheets; inspect the frames, visible text, actions, camera, product handling, hook, beat structure, pacing and closing. Use the available audio/player/transcript evidence and label any limits. NinjaChat's image/video generation tools are not reference-analysis tools; do not present generation as video analysis. If audio or dialogue cannot be heard/transcribed reliably, mark that gap.

Write one reference breakdown per clip: structure, measured duration and format, shot/beat map, product visibility, visual/audio details, source dialogue summary where permitted, transferable mechanics, production burdens and confidence. Do not infer conversion performance from a clip alone.

If there are several references and no chosen base, ask which one to adapt. Do not assume every reference should become its own generated ad.

## 3. Editable ad preview

Adapt the selected narrative mechanics to the researched product and target duration. Prepare an original concept, exact dialogue, timed beat/shot plan, detailed master prompt, product-image attachment map and continuity checklist. Mark staging clearly where a fictional creator speaks in first person.

Show the full editable preview. Resolve missing images/claims/format choices before quoting. Then search NinjaChat's live catalog for suitable current media models and capabilities. Report supported durations, aspect ratios, image references, speech/audio and extension only when the selected model's current listing or tool response confirms them.

Quote the specific image/video/speech operations and total batch estimate. Include output count, aspect, duration, references and any extensions. Do not submit anything during preview.

Say: “Tell me any edits. When this version is ready, say ‘generate’.” Update the preview and identifier when edited. Earlier approval does not carry over to a materially changed prompt or batch.

## 4. Generate and review

After the user approves the current preview and says “generate,” use the appropriate NinjaChat media operation with explicit per-call spend caps and stable idempotency keys. Keep image, video and speech as distinct operations when the selected model does not return all requested components. Upload only authorized product images/references, observing exact file sizes and URL expirations.

Persist generation IDs and selected references. Poll the existing job; do not duplicate after timeouts. Download/save assets only after the user-facing result has been shown where required by the client workflow.

Review actual output for dialogue, product label/shape, hands, lighting, wardrobe, framing, pace, visible artifacts, captions/logos, audio and continuity. Check actual duration and decode/playback when available. Make one evidence-led edit/extension within authorized budget, then review again. Do not silently re-roll repeated failures.

If separate UGC clips require assembly, keep assembly as a distinct editing step. Do not call a set of generated clips a finished ad until the actual clips have been assembled and reviewed.
