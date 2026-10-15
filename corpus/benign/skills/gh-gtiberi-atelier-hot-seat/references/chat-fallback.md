# Chat fallback (no Lavish)

Use when preflight reports no usable Lavish (`lavish.runner` is null) or the first `lavish-axi <page>` fails, or the user asks for chat. Say so in one line: "Lavish is not available, so this is a chat session."

The contract in SKILL.md is unchanged. What changes is transport: the round is chat text and the answers are the user's next message. This is the upstream `grilling` round format (mattpocock/skills, MIT):

```
❓ **Q1** - **<question title>**: <question body, may be several paragraphs, including choices>

➡️ <your recommended answer, and why>

---

❓ **Q2** - **<question title>**: <body>

➡️ <your recommended answer>
```

- One round is the whole frontier; number questions continuously across rounds (Q4, Q5, ...).
- Every question has its recommendation. Tell the user they can answer with just numbers ("1 agree, 2 b, 3 don't know") and that "needs a prototype" and pushback are valid answers.
- After each reply, summarise in 3 lines what you settled and what you changed because of their pushback, then ask the next frontier. Keep the design tree as an indented list you re-print when it changes shape.
- The helper still keeps the ledger. Start with `HS init --chat --topic "<what they want grilled>" [--mode me|docs] [--context "<extra>"]` (no page round: the intake happened in chat). After each reply, put their answers in the next patch as `"answers": {"Q4": {"choice": "a", "text": "their exact words"}, ...}` (same fields the page would send) along with your tree updates, and run `HS next`: it validates the round exactly as it does for the page and updates the ledger. Ignore the page it builds. Export with `HS ledger` at the end.
- Codebase mode: the paper trail (CONTEXT.md, ADRs) is exactly as in `paper-trail.md`. Say what you wrote after each round.
- Ending, confirmation and the ledger export are as in SKILL.md.
