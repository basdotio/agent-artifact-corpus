# voice.md

Save the filled copy to `~/.claude/virality/voice.md`. The virality skill reads it before every
rewrite. If you already filled `~/.claude/youtube/voice.md` or `~/.claude/linkedin/voice.md` for
Jake's other packs, start from that file.

## How to capture a voice (Claude does this, from 3 to 5 samples)

1. Get 3 to 5 of the creator's OWN pieces: transcripts of their best videos first (spoken words
   matter more than written ones), then captions or posts. Not what they wish they sounded like.
2. Measure, do not guess:
   - pace: `python3 tools/speech.py their_video.srt` prints words per minute. Use it as `--wpm`.
   - sentence length: short and punchy, mixed, or long. Quote two typical sentences.
   - person: mostly "I" (proof), mostly "you" (instruction), or "we".
   - contractions, swearing, emoji, slang. Yes or no, with an example of each yes.
   - signature phrases: any 2 to 4 word phrase that appears in two or more samples.
   - how they open and how they ask (their usual first line and their usual CTA).
3. Write the profile below with real quotes from the samples, then rewrite one line in this voice
   and ask the creator "is that you?" Fix the profile from the answer.

## The profile

- **Name / handle:**
- **Pace:** ___ wpm (measured from: ___)
- **Sounds like (three real lines, verbatim):**
  1.
  2.
  3.
- **Sentence shape:**
- **Person:** I / you / we
- **Signature phrases (keep these):**
- **Words I never use (strip these):**
- **Words the humanizer must leave alone** (pass to `humanize.py`/`detect.py` by editing
  `tools/slop.json`):
- **Swearing / emoji / slang:**
- **How I open:**
- **How I ask (CTA):**

## Proof I can say out loud

Real numbers, results and stories the creator will put their name on. The skill never invents
one. If this list is empty, scripts come back with `{{your number}}` in them.

-
-

## Off limits

- Topics, clients, numbers or claims I cannot use:
