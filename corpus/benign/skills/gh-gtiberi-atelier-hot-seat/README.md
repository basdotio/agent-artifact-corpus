# hot-seat

The [grill-me](https://www.aihero.dev/skills-grill-me) interview with a UI. Every round is a [Lavish](https://github.com/kunchenguid/lavish-axi) page: one card per question with a recommended answer, a free-text box, "I don't know" and "needs a prototype"; a live design tree, the decisions ledger, the resolved terms and ADR candidates on the side. The agent reads your answers back with `lavish-axi poll`, recomputes the frontier and re-renders the same page.

- **No codebase** (not a git repo, no source files, no CONTEXT.md): stateless, like grill-me. The session files live in a temp directory; nothing is written to your folder.
- **In a codebase**: also the [grill-with-docs](https://www.aihero.dev/skills-grill-with-docs) paper trail. Resolved terms go into `CONTEXT.md` as they resolve, ADRs into `docs/adr/` only when all three gates hold (hard to reverse, surprising without context, real trade-off). The page shows a diff of what was written after each round.
- The first page asks what to grill and confirms the mode (it recommends one, you can override).
- Ends with a confirm round, then a markdown decisions ledger you hand to whatever comes next (a spec, tickets, a plan).

## Install

```sh
# project scope (Claude Code reads .claude/skills, Copilot CLI reads .agents/skills and .claude/skills)
npx skills add GTiberi/atelier --skill=hot-seat -a claude-code -a github-copilot

# user scope (Copilot CLI does NOT read ~/.claude/skills; the CLI writes ~/.agents/skills and links ~/.claude/skills)
npx skills add GTiberi/atelier --skill=hot-seat -g -a claude-code -a github-copilot
```

Prerequisites: Node 18+ and `lavish-axi` on PATH (`npm i -g lavish-axi`; `npx -y lavish-axi` also works with network). Without Lavish the skill says so and runs the same interview in chat (`references/chat-fallback.md`).

Optional: Matt Pocock's originals, if you also want plain `/grill-me` and `/grill-with-docs`. hot-seat does not need them; its whole contract is inline in SKILL.md.

```sh
npx skills add mattpocock/skills --skill grilling domain-modeling grill-me grill-with-docs
```

Use the space-separated form: repeating `--skill=a --skill=b` installs the whole repository (skills CLI 1.7.0).

## Use

`/hot-seat <what to grill>` (or just `/hot-seat`; the first page asks). Start it in a fresh conversation, leave plan mode off, use your best model. Answer, push back, say "I don't know", flag what needs a prototype. Then hand the same conversation and the ledger to your spec step.

## What is in the folder

| path | what |
|---|---|
| `SKILL.md` | the contract (interview, steering, paper trail, ledger) and the run-book |
| `scripts/hot-seat.mjs` | zero-dependency helper: `preflight`, `init`, `record`, `next`, `ledger`, `build`. Detects the mode, validates every round (refuses questions without a recommendation, off-frontier questions, unsupported ADR or glossary claims), diffs CONTEXT.md and ADRs, builds the page |
| `assets/hot-seat.html` | the page template (inline SVG tree, no Mermaid, phone-safe, no horizontal overflow) |
| `references/` | patch format, paper-trail formats, chat fallback, upstream NOTICE (MIT) |

The helper only runs `git`, `lavish-axi` and `node`; it never touches the network and writes only inside `.lavish/` (codebase mode), a temp directory (stateless mode), and, when you ask for them, `--out` files.

Derived from mattpocock/skills (MIT), see `references/NOTICE.md`.
