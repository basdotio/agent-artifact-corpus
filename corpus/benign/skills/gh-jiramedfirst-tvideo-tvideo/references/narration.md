# Narration (optional)

Captions + click sounds already make a complete tutorial; narration is an upgrade
that costs TTS quota and review time. Offer it, don't assume it.

## Writing the lines

Put `narration` on `plan.intro`, each step, and `plan.outro` in plan.json. One or
two plain sentences per step, describing *why/what to look for*, not repeating the
caption word for word. Polite particles and tone follow the voice (e.g. Thai male
voice → "ครับ").

**Mixed-language terms.** Multilingual voices pronounce English terms best in
Latin script ("Dashboard", "PO", "PDF"). Brand names with a local
pronunciation are the exception — write them as locals say them (e.g. a Thai
brand read in Thai script). Generate one test line and listen before generating
all of them.

## Generating (HeyGen via Hyperframes media-use)

1. Sign in: `npx hyperframes auth login` (in a real terminal; device/browser flow).
   Check with `npx hyperframes auth status`.
2. Pick a voice. `heygen-tts.mjs --list` shows only the first page (50 voices,
   mostly English). Native voices for other languages are further down — page
   through the catalog (`/voices?engine=starfish&type=public&limit=100&token=<next_token>`)
   and filter by `language`, or try a "Multilingual" voice. Play 2–3 samples to the
   user and let them choose.
3. `node <skill>/scripts/voice.mjs --voice <id> --lang <code>` in the clip project.
   It writes `assets/voice/*.mp3` + `voices.json` and only regenerates changed
   lines. Then `node build.mjs` — steps stretch to fit the voice.

## Quota

Free plans allow only a couple of minutes of TTS per month. Budget ≈ (number of
clips × 70–90 s). If the quota runs out mid-project, stop and tell the user —
options: upgrade the plan, wait for the reset, use captions only, or record a
human voice per line (drop files into `assets/voice/` and write `voices.json`
with each line's `path` and `duration`).

## Keep the files

Never delete `assets/voice/` to "switch to captions only" — set aside
`voices.json` instead (rename it). Regenerating later costs quota again.
