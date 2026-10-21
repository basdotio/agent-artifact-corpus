# Questionnaire for a third person

*Loaded when an open question cannot be answered by the user because the knowledge sits with
someone else (a delivery team, a product owner, a data owner, a domain expert) and a structured,
send-ready document beats a chat message. Pattern credit: the "interview the send, not the subject"
framing follows Matt Pocock's to-questionnaire skill (MIT); the rules and template below are this
setup's own.*

## When it applies

- The user says "only X knows that", "I need to ask the team", "we have a meeting with Y", or an
  interview stalls on a fact nobody in the conversation holds.
- Never for a fact you could look up yourself: files, tickets, documentation, the web. Finding facts
  is the agent's job; the questionnaire is for knowledge that lives only in another person's head.
- It does not replace a skill's own short-message rules where those exist (a follow-up message with
  one or two questions per item stays a message). The questionnaire is for a gap wide enough to
  need structure, or a recipient who will fill it in async or during a meeting.

## Interview the SEND, not the subject (two exchanges, then write)

The user cannot answer the subject questions; that is the whole point. Ask only what they can
always answer:

1. **Who is it going to?** Role, expertise, relationship to the user. This fixes the tone and how
   much context the document must carry. Done when you know what the recipient knows that the user
   does not.
2. **What must come back?** The concrete decisions or facts the user cannot settle alone. Done when
   you hold a list of what the user must be able to do or decide once the answers land.

Then write the document. Every item from step 2 must be covered by at least one question.

## Rules for the questions

- Aim every question at the GAP between what the recipient knows and what the user needs.
- Most important first: async means you may get only one pass.
- One idea per question, never compound. An answer stub directly under each question.
- A one-line *why this matters* only where a question could be misread or invite a throwaway answer.
- Never ask what the ticket, the documentation, or your own analysis already answers; a settled
  finding becomes the premise of a sharper question, never the question itself.
- Group the questions under `##` theme headings once there are more than a handful.
- Every link in the document must already contain what the questionnaire says it contains.

## Where it goes and what happens next

- Write `<topic>-<recipient>-questionnaire.md` to the folder the skill names for run artifacts;
  if it names none, the current folder. Announce the path in one chat line and show the body as
  plain text (no blockquote markers), since the user will copy it out.
- Record the open item as "waiting on <recipient> - questionnaire at <path>" in the project's open
  questions (PROJECT.md when the project has one), then CONTINUE the work on labeled assumptions
  rather than parking it until the answers arrive. When the answers land, fold them in and delete
  the open item.
- Drafts only: the agent never sends the document itself.

## Template

```markdown
# <Questionnaire title>

**Purpose:** why this questionnaire exists and the decision riding on it.

**From:** <the user>  **To:** <the recipient>  **How your answers will be used:** <where they go>

## Context

One paragraph orienting a recipient who was not in the user's head. Enough to answer well, not a page.

## How to answer

Deadline and rough effort. Partial answers and "I don't know" are useful: flag anything you are
unsure of rather than skipping it.

## <Theme heading>

### <One question, one idea, most important first>

_Why this matters: <one line, only where the question could be misread>_

>

## Anything else?

Anything we did not ask that we should know?
```
