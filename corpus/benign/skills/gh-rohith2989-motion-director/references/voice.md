# Voice — casting, takes, and a film clocked by its narrator

Narrate onboarding, tutorials and explainers. Launch films usually don't need a voice (titles carry them);
add one only if the user asks or the audience needs hand-holding.

## Writing the script (`voice/script.txt`, one line per beat)
- Plain words a non-technical person uses; one idea per line; ≤ 2.6 words per second of screen time.
- Say what is on screen *as it appears* ("press Allow" exactly when Allow is pressed). Don't read the UI aloud
  except the one phrase that matters.
- Lead with the verb: "First, tell Acme about your company." "Then connect the tools you already use."
- Name real products and buttons exactly; spell proper nouns for the TTS in `voice/hints.txt` too.
- Promises must be true to the product (read its copy: "Your password never reaches Acme.").
- Close with the outcome, not a slogan: "That's it. Your new teammate is ready."
- Delivery note in `voice/style.txt` (one paragraph): warm, unhurried, gently smiling, natural pauses,
  not salesy, not an announcer.

## Providers (keys only as env vars)
| Provider / model | Direction | Notes |
|---|---|---|
| Gemini `gemini-3.8-flash-tts` | `speech_metadata.style` (Interactions API) | 300+ English voices via `voice/tts.py voices`; reads ANY text aloud — never put direction in the text; system instructions are rejected |
| Gemini `gemini-2.5-pro-preview-tts`, `gemini-3.1-flash-tts-preview` | "style paragraph + Read only this script:" | 30 prebuilt voices (Achird, Kore, Charon, Sulafat…) |
| OpenAI `gpt-4o-mini-tts` | `instructions` | cheap, instruction-following |
| ElevenLabs `eleven_v3` | audio tags in text, voice settings | most expressive; huge library; cloning |
Fish Audio S2 led a 2026 blind-preference benchmark; any provider works if it returns 24 kHz+ PCM — add an
adapter to `tts.py`. Whatever the provider, **cast by duels**, never by reputation.

## Casting (the procedure that found a voice everyone liked)
```bash
python voice/tts.py voices warm                     # browse; shortlist 20–50 (accent, age, persona fit)
python voice/tts.py audition v1,v2,v3,...           # the first two lines in each voice → voice/audition/
python voice/cast.py score voice/audition           # Whisper WER (exactness), pace, pitch range
python voice/cast.py duel voice/audition/*.wav      # the clean top ~12: round robin, both orders
python voice/cast.py screen leader1.wav,leader2.wav voice/audition/new*.wav   # newcomers vs the leaders
```
Why duels: an LLM listener's 1–10 scores swing wildly with order (the same take scored 3 and 9); forced A/B
choices heard both ways and tallied (Bradley–Terry) are stable. The first "best voice" by ratings lost every
duel. Prefer natural regional-neutral accents for broad audiences; check pace 2.6–3.1 words/s.

## Takes → the best reading of every line
```bash
python voice/tts.py takes <voice> 6                 # six full takes (each is different)
python voice/cast.py lines voice/takes/*.wav        # cut every line from every take, duel per line
```
`lines` writes `voice/vo_plan.json` with the winning reading per line. Before trusting a winner, re-check the
isolated line: Whisper (and people) can hear "Need it" as "Needed" — pick the clearer reading when close.

## The VO-clocked timeline
Fill `start` for every line in `voice/vo_plan.json` (and `duration`) from the plan: after each line leave the
time the picture still needs (a page loading, a click, a DM arriving — 0.8–2.8 s). Then
```bash
python voice/vo_build.py      # → comp/data/vo.json (every word's time), audio/out/vo.wav, audio/out/captions.srt
```
Set `"narrated": true` in `comp/config.json` and key events to words in scenes: `w(1, "company")` (typing ends
on the word), `w(2, "allow") + 0.04` (the click), `w(3, "anything") … wEnd(3, "first")` (a highlight sweep).
Sanity: no two lines overlap; nothing important happens in a voice gap you didn't plan.

## Captions
`captionsScene({ phrases })` with phrases cut by hand (≤ 42 characters, break at commas/dashes), words firming
as they're spoken, on a soft pill in the bottom band (inside the platform's safe zone). Skip a caption the
picture already writes (an end title). Ship `captions.srt` too — LinkedIn is mostly watched muted.
