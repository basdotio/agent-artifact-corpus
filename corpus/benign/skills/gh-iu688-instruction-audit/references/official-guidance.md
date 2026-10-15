# Official guidance used by this audit

Primary source: [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) (OpenAI Developers, 2026-09-11).

Use this reference to calibrate findings, not as a reason to rewrite files automatically. The article's relevant principles are:

- Keep skill descriptions as short as possible while making the trigger clear; broad descriptions can cause unnecessary skill selection.
- Use progressive disclosure: keep the root skill document a minimal router and load supporting material only when relevant.
- Avoid elaborate itineraries and overly specific recipes when an outcome and decision criteria are enough.
- In `AGENTS.md`, point to documentation contextually instead of requiring a stack of docs before every edit.
- Do not force tests or checks after every change when the model can choose proportionate validation; keep explicit safe workflows where they are genuinely needed.
- Define safe completion and persistence boundaries. A blanket “stop and ask” can be excessive, while a concrete permission or production-risk gate can be meaningful.

These principles support the instruction audit categories but do not replace judgment. A directive is not a finding merely because it is long, cautious, or model-specific; report it only when the quoted text creates unnecessary work or context consumption, an applicable contradiction, or a wait with no meaningful condition.
