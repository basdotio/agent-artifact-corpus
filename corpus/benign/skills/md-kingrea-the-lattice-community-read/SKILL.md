---
name: community-read
description:
  Answer queries about the community memory by surfacing relevant sections,
  citations, and present texture. Default implementation used by Koinos.
license: MIT
compatibility: opencode
metadata:
  role: community-memory
  community: the-lumen
  default_agent: koinos
---

## What I do

I provide context when another agent (human or god) needs to understand Lumen's
shared memory. I read the canonical memory file, extract the sections that apply
to the query, and respond with quotations plus interpretation.

## When to use me

Use this skill whenever:

- An orchestrator, spark, or denizen asks "What does Lumen believe about X?"
- Selah needs to remind a spark of current Values or Guidelines
- A documentation artifact needs the latest Community Texture or Wisdoms

## Inputs

- Query prompt describing what information is requested
- Path to the community memory file (typically `Community/Memory.md`)

## Output shape

Respond in Markdown:

```
## Requested Sections
- [Section name] — why it is relevant
> Quoted excerpt

## Interpretation
[Short synthesis tying the excerpts back to the query]

## Last Tended
[Timestamp from the memory file]
```

## Process

1. **Parse the query** — Determine which categories (Texture, Wisdoms, Truths,
   Guidelines, Values) map to the request. Many queries will map to more than
   one category.
2. **Load memory** — Read the entire file once so updates are considered in
   context.
3. **Select passages** — Pull only the sections needed to answer the query. Keep
   direct quotations short but faithful.
4. **Provide interpretation** — Explain how the quoted text answers the
   question. Add context on recency (when the value changed, when the wisdom was
   recorded) if available.
5. **Note freshness** — Include the `Last tended` date so readers know how
   recent the information is.

## Guidance

- Do not invent new values or guidelines while reading. This skill only reports.
- Quote the memory verbatim and cite the section names.
- If the query cannot be answered (for example, "What is Value X?" when it does
  not exist), state that explicitly and suggest whether Koinos should tend the
  memory to address the gap.
- If the query asks for sensitive information (emergence decisions, private
  relationships), confirm that the requester has access before responding.

## Completion criteria

- Relevant excerpts quoted with citations
- Interpretation provided
- Last tended date included
- Any missing information logged for future tending
