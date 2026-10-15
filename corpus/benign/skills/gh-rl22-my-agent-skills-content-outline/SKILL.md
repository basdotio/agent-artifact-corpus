---
name: content-outline
description: >
  Generate a waterfall-ready content script outline from a YouTube URL,
  article link, raw idea, or markdown file. Produces a structured outline with
  recording cue markers (CLIP START/END, KEY MOMENT, B-ROLL HERE) and saves to
  the content-outlines directory configured via SPRINTZ_CONTENT_DIR (default:
  ~/Sprintz/brands/sprintz/content/content-outlines/). Trigger:
  /content-outline [source]. Auto-activates when user says "outline this
  video/article/idea", "create a content outline", "make an outline for", or
  drops a YouTube URL with content intent.
---

# Content Outline Generator

## Purpose
Transform any content source into a waterfall-ready script outline — one recording session that produces 15+ platform-specific assets. Follows the Un-Scripting Method: scripted hooks + freestyle connective tissue, with embedded cue markers for post-production clip extraction.

---

## Invocation
```
/content-outline [source?]
```
- `source` = YouTube URL, article URL, `/Sprintz/brands/sprintz/content/` file path, or raw idea text (optional — will ask if omitted)
- Args may be passed inline: `/content-outline https://youtube.com/watch?v=abc123`

---

## Step 1 — Gather Inputs

If no source argument was provided, ask:
> "What's your content source? You can paste one source or multiple (YouTube URLs, article links, file paths, or a raw idea). Separate multiple sources with a line break."

Then ask these three questions (always, every run):

> **CTA:** "What's your campaign CTA for this piece?"

> **Creator POV:** "What's your personal take on this topic? Share any relevant experience, client stories, results you've seen, or opinions you hold — even rough notes are fine. This becomes the primary voice of the outline."

> **Angle:** "Is there a specific angle or contrarian take you want to lead with, or should I find the strongest one from the source(s)?"

**Detect source type from each input:**
- Contains `youtube.com` or `youtu.be` → **YouTube**
- Starts with `http` or `https` (not YouTube) → **Article**
- Ends with `.md` or starts with `~/` or `/` → **Markdown file**
- Anything else → **Raw idea / text**

**Multiple sources:** Fetch all sources before generating the outline. Synthesizing across 2–3 sources produces inherently more original content than mirroring any single one.

---

## Step 2 — Fetch Source Content

### YouTube URL
Extract the transcript using `youtube-transcript-api`. Run this in a single Bash call:

```bash
python3 -c "import youtube_transcript_api" 2>/dev/null || pip3 install youtube-transcript-api -q
python3 << 'PYEOF'
import re, sys
url = "REPLACE_WITH_URL"
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    vid_id = re.search(r'(?:v=|youtu\.be/)([^&\n?#]+)', url).group(1)
    transcript = YouTubeTranscriptApi.get_transcript(vid_id)
    text = ' '.join([t['text'] for t in transcript])
    print(text[:10000])
except Exception as e:
    print(f"ERROR: {e}")
PYEOF
```

If transcript fetch fails (private video, no captions), fall back to WebFetch on the YouTube URL to get title + description, and note the limitation.

### Article URL
Use the WebFetch tool to retrieve the full page content. Extract the main body text — skip nav, footer, ads.

### Markdown File
Use the Read tool. If the path starts with `~/`, expand to the full path.

### Raw Idea / Text
Use directly as-is. No fetch needed.

### Multiple Sources
Fetch each source independently, then consolidate into a single source brief before proceeding to Step 2.5.

---

## Step 2.5 — Transform Before Outlining

Before generating a single word of the outline, complete this internal analysis:

**1. Extract the theme, discard the structure.**
Identify what the source is fundamentally *about* (the core insight or tension), then set aside how the source organized it. The outline must follow its own structure derived from the Creator POV — not mirror the source's order, sections, or framing.

**2. Identify what's original vs. borrowed.**
Classify each key idea from the source into one of three buckets:
- `[REFERENCE]` — a specific fact, story, or framework from the source that should be cited if used
- `[INSPIRED]` — a theme or concept you're building on with your own angle
- `[ORIGINAL]` — comes entirely from the Creator POV provided in Step 1

The outline must contain a meaningful amount of `[ORIGINAL]` material. If the Creator POV is thin, flag this before generating and ask for more before proceeding.

**3. Find the Creator's unique angle.**
Based on the Creator POV and the source themes, identify the single strongest angle that is distinctly theirs. This angle — not the source's angle — becomes the spine of the outline.

**4. Multi-source synthesis check.**
If multiple sources were provided, identify where they agree, where they conflict, and what gap exists between them. That gap is often the most original territory.

**5. Score re-hook candidates against the Virality Framework.**
Before selecting which insights become KEY POINT #1–3, evaluate every candidate moment from the source and Creator POV against these 8 dimensions. The top 3 scoring candidates become the re-hooks. Document the primary dimension that makes each one clip-worthy — this becomes the `Why This Works` annotation in the outline.

| Dimension | What to Look For |
|-----------|-----------------|
| **Hook moment** | Strong opening line that stops the scroll on its own |
| **Emotional peak** | Laughter, vulnerability, anger, awe — visceral reaction |
| **Opinion bomb** | Contrarian, spicy, or debate-bait take |
| **Revelation moment** | "Wait, what?" reframe — changes how viewer sees something |
| **Conflict** | Tension, disagreement, callout, stakes |
| **Quotable line** | Tight, screenshot-worthy phrasing — built to be shared |
| **Story peak** | Climax of a narrative arc — satisfying resolution |
| **Practical value** | Actionable insight a viewer will save or screenshot |

A strong re-hook scores high on 2–3 dimensions simultaneously. A moment that only scores on one dimension is a weak clip — skip it or combine with another moment.

---

## Step 3 — Generate the Outline

**Act as the Content Strategist.** Your job: generate an outline rooted in the creator's voice and POV, informed by the source(s) — not derived from them.

Use the frameworks below when writing hooks, re-hooks, and the CTA. Pick the best fit for each section — don't default to the same formula every time.

---

### Hook Formulas
Apply to PRIMARY HOOK and all Re-Hook scripts. Pick one named formula per hook — label it in a comment so the creator knows what they're executing.

| Formula | Template | Example |
|---------|----------|---------|
| **Correction** | "Stop doing [X]. Do this instead." | "Stop pitching your offer first. Do this instead." |
| **Insider Secret** | "No one talks about this in [industry]..." | "No one talks about this in the creator economy..." |
| **Quick Fix** | "Here's how to fix [problem] in [time]" | "Here's how to fix your content strategy in 30 minutes" |
| **Curiosity Loop** | "Watch what happens when I..." | "Watch what happens when I remove this one thing from my funnel" |
| **Transformation** | "I can't believe [X] actually..." | "I can't believe this one reframe actually doubled my close rate" |
| **Call-Out** | "If you're a [person], this is for you" | "If you're a founder posting content with zero results, this is for you" |
| **Personal Mistake** | "This mistake cost me [result]" | "This mistake cost me 6 months of wasted content" |

### Hook Stacking
For the PRIMARY HOOK, layer multiple hook types for maximum retention. Call out each layer in the Visual Direction note:
- **Visual hook** — motion, expression, text overlay, unexpected prop
- **Auditory hook** — tone shift, silence, snappy open line
- **Content hook** — bold statement, question, strong opinion
- **Emotional hook** — taps into stress, ambition, frustration, or relief

### CTA Tiers
Match CTA intensity to audience temperature. Use the tier that fits the platform and where this audience sits in the funnel:

| Tier | Use When | Templates |
|------|----------|-----------|
| **Soft** | Cold audience, discovery content | "Link in bio if you want to check it out" · "I'll drop the link if you're curious" |
| **Medium** | Warm audience, returning viewers | "Use the link below to grab it" · "Check out the details in the description" |
| **Strong** | Hot audience, high-intent content | "Book it now — spots fill fast" · "Click the link before [date/limit]" |

Note: Affiliates who test CTAs see ~49% improvement in conversion. Always write the CTA as a natural continuation of the last key point — never tacked on.

### Hormozi's Value Equation
Use when writing the PRIMARY HOOK framing and the CTA section:
```
Value = (Dream Outcome × Perceived Likelihood) / (Time Delay × Effort Required)
```
To maximize perceived value: amplify the dream outcome, build confidence it will work, minimize how long it takes, minimize how hard it seems.

---

Generate the outline using **exactly this structure** — fill every section, do not skip:

---

```markdown
# [Compelling Content Title — Not the Source Title]
**Created**: [YYYY-MM-DD]
**Source**: [URL, file path, or "Original Idea"]
**Campaign CTA**: [User-provided CTA]
**Target Platforms**: YouTube Long-Form, IG Reels, TikTok, YT Shorts, LinkedIn, X

---

## SOURCE ATTRIBUTION
**Inspired by**: [Source title / URL]
**What was borrowed**: [List any specific facts, named frameworks, stories, or examples taken from the source — these must be verbally credited during recording or cited in descriptions]
**What is original**: [The creator's angle, personal examples, reframing, and conclusions]
**Credit language (use during recording if referencing source directly)**:
> "I came across this idea from [Creator/Author name]..."
> "There's a concept from [Source] that I want to build on..."

---

## PRIMARY HOOK / OPENING (60–90 seconds)
**Cue**: `CLIP START` *(extract as standalone teaser short)*
**Visual Direction**: Camera direct to lens
**Platform Targets**: YouTube intro + IG/TikTok teaser

### Script to Record (verbatim — memorize this):
*(Formula used: [name the hook formula] + hook stacking: [visual / auditory / content / emotional layers applied])*

| Beat | Timing | Purpose |
|------|--------|---------|
| Stop the scroll | 0–15s | Hook formula fires — pattern interrupt or bold claim |
| Build stakes | 15–45s | Agitate the problem — make the cost of ignoring this real |
| Promise the payoff | 45–75s | Preview what they'll walk away with |
| Bridge | 75–90s | Transition into credibility section |

[Write each beat as 1–2 sentences in the creator's voice. Apply Hormozi's value equation — lead with dream outcome, signal it's achievable, imply low effort/time. Zero borrowed phrasing from the source. Must stand completely alone as a short-form clip.]

**Cue**: `CLIP END`

---

## CREDIBILITY (30–45 seconds)
**Cue**: `KEY MOMENT`
**Visual**: `B-ROLL HERE` — [specific suggestion: portfolio shots, metrics, testimonials]

### Talking Points (freestyle):
- [Years/results/clients — specific number]
- [Relevant case study or personal journey beat]
- [Bridge to audience pain: "I've been exactly where you are with X"]

---

## KEY POINT #1: [Punchy Headline]
**Cue**: `CLIP START` *(Re-Hook Short #1)*
**Target Platforms**: IG Reel, TikTok
**Duration**: 15–30 seconds

### Script to Record (verbatim):
*(Formula used: [name the hook formula])*
**Why This Works**: [one-liner — primary virality dimension(s) + psychological mechanism, e.g. "Opinion bomb + Quotable line: contrarian reframe delivered as a tight, shareable sentence creates cognitive dissonance"]

| Beat | Timing | Purpose |
|------|--------|---------|
| Pattern interrupt | 0–5s | Hook formula fires — different formula from PRIMARY HOOK |
| Core insight | 5–30s | Single idea delivered fully — one beat only |
| Open loop / micro-CTA | 30–40s | Tease the deeper dive or soft directional nudge |

[Write each beat as 1–2 sentences. Different formula from the PRIMARY HOOK. Completely standalone — no context from the long-form needed.]

**Cue**: `CLIP END`

### Extended Talking Points (freestyle):
- Core idea in one sentence *(creator's framing, not source's)*
- **[PERSONAL]** Story, client example, or result from the Creator POV — use the material provided in Step 1
- Common mistake to avoid
- One actionable step
- *(If referencing source material directly, flag it: "I came across this from...")*

**Visual**: `B-ROLL HERE` — [specific demo, screenshot, or example]

---

## KEY POINT #2: [Punchy Headline]
**Cue**: `CLIP START` *(Re-Hook Short #2)*
**Target Platforms**: YT Shorts, LinkedIn
**Duration**: 20–40 seconds

### Script to Record (verbatim):
*(Formula used: [name the hook formula])*
**Why This Works**: [one-liner — primary virality dimension(s) + psychological mechanism]

| Beat | Timing | Purpose |
|------|--------|---------|
| Pattern interrupt | 0–5s | Hook formula fires — different formula from Re-Hook #1 |
| Core insight | 5–30s | Single idea delivered fully — one beat only |
| Open loop / micro-CTA | 30–40s | Tease the deeper dive or soft directional nudge |

[Write each beat as 1–2 sentences. Different formula from Re-Hook #1. Completely standalone.]

**Cue**: `CLIP END`

### Extended Talking Points (freestyle):
- Core idea *(creator's angle)*
- **[PERSONAL]** Quote, data point, or result the creator has seen firsthand
- Contrarian take or reframe *(where does the creator disagree with or extend the source?)*
- Tactical example from their own work or clients

**Visual**: `B-ROLL HERE` — [relevant visual]

---

## KEY POINT #3: [Punchy Headline]
**Cue**: `CLIP START` *(Re-Hook Short #3)*
**Target Platforms**: TikTok, IG Reel
**Duration**: 15–25 seconds

### Script to Record (verbatim):
*(Formula used: [name the hook formula])*
**Why This Works**: [one-liner — primary virality dimension(s) + psychological mechanism]

| Beat | Timing | Purpose |
|------|--------|---------|
| Pattern interrupt | 0–5s | Hook formula fires — different formula from Re-Hooks #1 and #2 |
| Core insight | 5–25s | Single idea delivered fully — one beat only |
| Open loop / micro-CTA | 25–35s | Tease the deeper dive or soft directional nudge |

[Write each beat as 1–2 sentences. Different formula from Re-Hooks #1 and #2. Completely standalone.]

**Cue**: `CLIP END`

### Extended Talking Points (freestyle):
- Core idea *(creator's framing)*
- **[PERSONAL]** Real-world case study from creator's experience or client work
- Step-by-step breakdown
- Before/after *(from their direct observation)*

**Visual**: `B-ROLL HERE` — [visual proof or example]

---

## CALL TO ACTION (30–45 seconds)
**Cue**: `KEY MOMENT`
**Visual**: [CTA graphic overlay or product demo]
**CTA Tier**: [Soft / Medium / Strong — based on platform and audience temperature]

### Script to Record:
*(Apply Hormozi value equation: amplify dream outcome → confirm it's achievable → minimize perceived effort/time → clear ask)*
[Transition from last key point → dream outcome statement → why this CTA is the next logical step → specific ask using the tier template above → benefit reminder]

**CTA Copy for Captions/Descriptions**:
[Exact copy to paste across platforms]

---

## OUTRO (15–30 seconds)
### Script to Record:
[Recap main transformation → encouragement → standard sign-off]

---

## WATERFALL MAP

| Asset | Source Section | Duration | Platforms |
|-------|---------------|----------|-----------|
| Long-Form Video | Full recording (minus `CUT THIS`) | 8–15 min | YouTube, Podcast |
| Short #1 (Primary Hook) | Opening `CLIP START/END` | 30s | IG Reel, TikTok |
| Short #2 (Key Point #1) | Re-Hook #1 | 15–30s | IG Reel, TikTok |
| Short #3 (Key Point #2) | Re-Hook #2 | 20–40s | YT Shorts, LinkedIn |
| Short #4 (Key Point #3) | Re-Hook #3 | 15–25s | TikTok, IG Reel |
| Short #5 (Credibility) | `KEY MOMENT` #1 | 30–45s | LinkedIn |
| Short #6 (CTA) | `KEY MOMENT` #2 | 30–45s | IG Story, X |
| LinkedIn Post | Expanded Key Point #1 | N/A | LinkedIn |
| X Thread | Key Points 1–3 | N/A | X |
| Newsletter Section | Deep dive Key Point #2 | N/A | ConvertKit |
| IG Carousel | Key points as slides | N/A | Instagram |

---

## RECORDING DAY CHECKLIST
- [ ] Read outline aloud — adjust any phrasing that sounds unnatural
- [ ] Memorize PRIMARY HOOK word-for-word
- [ ] Memorize each Re-Hook script (CLIP START/END sections)
- [ ] Internalize Key Point talking points (don't memorize, understand the flow)
- [ ] Practice voice memos 24–48 hours before recording
- [ ] Riverside Studio: 1920×1080, record all hooks first, then freestyle key points
```

---

## Step 4 — Save to Vault

Generate a URL-friendly slug from the content title:
- Lowercase, hyphens instead of spaces
- Max 40 characters
- Remove stop words (the, a, an, in, for, etc.)

Save the outline to the content-outlines directory configured via
`SPRINTZ_CONTENT_DIR` (default: `~/Sprintz/brands/sprintz/content/content-outlines/`):
```
${SPRINTZ_CONTENT_DIR:-~/Sprintz/brands/sprintz/content/content-outlines}/YYYY-MM-DD-[slug].md
```

Use the Write tool with the full absolute path (expand `~` and the env var to their resolved values first).

Create the directory if it doesn't exist:
```bash
mkdir -p "${SPRINTZ_CONTENT_DIR:-$HOME/Sprintz/brands/sprintz/content/content-outlines}"
```

---

## Step 5 — Confirm

After saving, respond with:
```
✓ Outline saved: ${SPRINTZ_CONTENT_DIR:-~/Sprintz/brands/sprintz/content/content-outlines}/[filename].md

PRIMARY HOOK PREVIEW:
─────────────────────
[First 2–3 sentences of the hook script]
─────────────────────

6 short-form clips + 5 text derivatives mapped.
Ready to record. Estimated session: 12–15 min.
```

---

## Quality Rules

**Originality**
- **Theme, not structure.** Extract the core insight from the source. Never mirror its section order, argument flow, or framing.
- **No borrowed phrasing.** Verbatim scripts (hooks, re-hooks, CTA) must be written entirely in the creator's voice. If a phrase came from the source transcript, rewrite it completely.
- **Personal material is primary.** Every key point must include at least one `[PERSONAL]` element from the Creator POV. If none was provided, stop and ask before proceeding.
- **Attribution is mandatory.** If any named framework, specific story, statistic, or example comes from the source, it must appear in the Source Attribution block and be flagged for verbal credit during recording.
- **Multi-source = more original.** When multiple sources are provided, find the synthesis across them — that intersection is inherently original territory no single source owns.

**Craft**
- **One beat per re-hook.** Each CLIP START/END section covers exactly one insight. If a draft section contains two distinct ideas, split into two re-hooks. Overloading a short-form clip degrades its clarity and shareability.
- **Hook must stand alone.** The CLIP START/END sections should work with zero context from the rest of the video.
- **Talking points, not paragraphs.** Freestyle sections use bullet points — never write a full script for these.
- **Specificity beats generality.** "3 clients who 3×'d revenue" beats "many successful clients."
- **B-ROLL HERE must be specific.** "Screen recording of Notion dashboard" beats "show a screenshot."
- **CTA is woven in, not tacked on.** The CTA section should feel like a natural continuation of the last key point.
- **Title is editorial.** The outline title should be a compelling content title, not the source title.
