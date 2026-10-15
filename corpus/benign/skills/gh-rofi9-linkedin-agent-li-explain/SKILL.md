---
name: li-explain
description: >-
  Explain a medical or healthcare-AI article, study, news item or physician's
  post in plain English for a writer with no medical background, then turn it
  into a Darman.ai post angle. Use when the user pastes a link, abstract, news
  story or LinkedIn post about AI in medicine and asks "what does this mean",
  "explain this", "is this worth posting about", "I don't understand this
  study", or "what should Darman say about this".
---

# li-explain

The person running Darman.ai's page is not a clinician. This skill is the
colleague who reads the medical source first and says, in plain words, what it
means, whether it's solid, and whether Darman has anything worth saying about
it.

## Before you start

1. Read `linkedin/voice.md`. Darman's positions, off-limits topics and
   "claims we can't make" decide what the post angle can be.
2. Read the whole source. If the user gives only a headline or a link you can't
   open, ask them to paste the text or the abstract. Never explain a study from
   its headline.
3. If `linkedin/research/topic-radar.md` exists, check whether the topic is
   already mapped there and reuse its glossary terms.

## Output, in this order

```
IN ONE SENTENCE
  What happened, with no medical words.

PLAIN ENGLISH  (4-6 short lines)
  Who did what, to whom, and what they found. Define every medical or
  statistical term in brackets the first time: "sensitivity (how many real
  cases the test catches)".

HOW SOLID IS IT
  Type:        randomized trial / observational study / survey / opinion /
               press release / vendor claim
  Size:        how many people or patients
  Where:       country, setting
  Weak spots:  1-3 honest caveats a doctor would raise in the comments
  Verdict:     strong / reasonable / early / marketing

WHAT A DOCTOR WOULD THINK
  2-3 lines on how a practicing physician would react, and which specialties
  care.

DARMAN ANGLE
  Which of the five positions in voice.md this connects to, and the one thing
  Darman can say that a news account can't. If there is no honest angle, say
  "skip this one" and why. That is a valid answer.

POST IDEA
  One hook, using a formula from li-post/hooks.json (give its number), and the
  one number or fact from the source it would rest on.

GLOSSARY
  Every term used above that a non-clinician might not know.
```

## Rules

- **Never invent.** Every number in the explanation must be in the source. If
  the source doesn't give a figure, say it doesn't.
- **Separate what the study measured from what people say it means.** A
  press release claiming "AI improves outcomes" about a study that measured
  reading time gets called out.
- **Association is not causation.** Say which one the source shows.
- **No patient cases, no medical advice.** If the source is a clinical case
  about an identifiable patient, or the post idea drifts into telling people
  how to treat something, stop and say so.
- **Flag voice.md conflicts.** If the obvious post would break a "claims we
  can't make" rule, say which rule and suggest the honest version.
- Hand the post idea to `/li-post` if the user wants a full draft.
