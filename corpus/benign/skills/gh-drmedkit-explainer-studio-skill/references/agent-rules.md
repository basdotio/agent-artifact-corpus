# Agent rules

- **Headless Chrome always `--mute-audio`**: test runs should never play on the speakers. The kit's `lib/chrome.mjs`
  and the anatomy scripts do it; any ad-hoc puppeteer/Chrome command you write must pass it too.
- **One browser per render worker** (a page that is not in front gets no animation frames). `--workers 3` when other
  topics render on the same machine at the same time.
- **Ports**: each parallel topic gets its own local port (in `topic.config.json`); use only yours.
- **Stay in your folder**: never modify other topics, the anatomy skill, the kit (unless that is your task) or another
  agent's topic. Copy from them. Adding a new music bed or sound effect to your audio library through
  `gen_music --keep` / `gen_sfx` is fine; do not otherwise edit the library.
- **Kit gaps during a round**: write them into `KIT-NOTES.md` in your topic folder (what, why, the exact patch if you
  have one) and work around them locally; the coordinator folds the notes into the kit after the round.
- **Deploy and publish** only when the user approved deploying for the round (`npx wrangler login` first). An artifact
  starts private; say so in STATUS.
- **Git**: a repo per topic, sensible commits, no remote unless asked, never push on your own.
- **ElevenLabs**: check `--dry` before generating; reuse the library (voice cache, `lib:` sfx, `--from-lib` beds); keys
  may have a hard cap.
- **Models**: use the strongest model you have for building a topic (figure craft and film direction need it); a small
  model is fine for mechanical subtasks (renaming, checking ids, batch file edits).

## Rounds of five

The coordinator assigns five topics from approved concept cards, gives each agent its folder, port and card, and the
rules above. Each agent works the skill's workflow to a full gate table. The coordinator reviews stills of each film
(the `--sheet` frames and `out/gate/contrast-*.jpg`), the gate table and STATUS before anything is deployed, and sends
fixes back once ("Fixes after review" in STATUS, `--ranges` re-renders). After the round the KIT-NOTES are folded
into the kit.

The `explainer-round` workflow (`<kit>/.claude/workflows/explainer-round.js`) does exactly this: build -> review ->
one fix round -> optional ship per topic (pipelined, no waiting between topics), then the kit-notes fold.
