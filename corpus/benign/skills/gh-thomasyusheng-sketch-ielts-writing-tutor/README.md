# ielts-writing-tutor

> An Agent Skill that marks IELTS Academic Writing the way a real examiner would — with a six-step process built specifically to stop AI graders scoring too harshly.

## What & Why

Ask an AI to mark an IELTS essay and it will usually mark it **too low**, in a
predictable way: it treats *noticeable* flaws as *standard-failing* flaws. Over one
marking series that produced this record — every essay first scored Band 5 was
re-examined after pushback, and **every single one was revised up to 5.5**. The
deviation sat entirely in Task Response, Coherence and Lexical Resource at the
5-vs-5.5 boundary; Grammatical Range and Accuracy was never once overturned.

The root cause was the same each time: **mistaking "done poorly" for "not done".**

This skill encodes a six-step process that makes that failure structurally hard. The
centre of it is a single binary test — *do these problems make a reader misunderstand,
or force a re-read?* If not, the criterion starts at 5.5, because that is what the
official descriptors actually say. Alongside it ship a task-type template set and a
ten-topic idea bank, so the same skill can both mark an essay and help write the next one.

Crucially, the calibration only moves **where the band lands**. It never softens
**what gets reported**: every error is still found, quoted and corrected.

## Quick Start

Claude Code (or any agent that reads Agent Skills):

```bash
git clone https://github.com/thomasyusheng-sketch/ielts-writing-tutor.git ~/.claude/skills/ielts-writing-tutor
```

Then paste an essay and ask for a band. The skill triggers on marking requests, band
estimates, Band 7 rewrites, and "which single fix would help most?".

Not using an agent? The `references/` files stand alone — `scoring-process.md` is a
usable marking checklist for a human, and the two template files work as study notes.

## What you get back

Every marking response contains four things, in order:

1. **Per-criterion evaluation** — what was done well (named specifically), then every
   deduction with the original text quoted, then the band justified against descriptor language
2. **Overall band** — arithmetic shown, rounded (`.25` down, `.75` up), Task 1 : Task 2 weighted 1 : 2
3. **A full Band 7 rewrite** — with each change mapped to the deduction it answers
4. **The single highest-leverage fix** — one change, not a list, with an honest estimate
   of its band impact (including "this won't move the rounded band" when that is true)

## Structure

| Path | Purpose |
|---|---|
| `SKILL.md` | The skill itself — workflow, output format, hard rules |
| `references/scoring-process.md` | The six steps in full, with the criterion-ownership table and two worked calibration failures |
| `references/band-descriptors.md` | Working summary of what separates each band, per criterion |
| `references/task1-templates.md` | Task 1 — seven visual types, sentence patterns, pre-writing checks |
| `references/task2-templates.md` | Task 2 — six essay types with opening and closing frames |
| `references/idea-bank.md` | Ten topic modules: arguments on both sides plus topic vocabulary |

## Scope

Writing Task 1 and Task 2 only. **Speaking is deliberately out of scope** — speaking
bands belong to a live human examiner, and this process is not built to produce them.

## Note on the band descriptors

The official IELTS Writing band descriptors are published free by the IELTS partners
and are the only authority for marking. This repository does **not** reproduce them.
`references/band-descriptors.md` is an original working summary intended to be used
*alongside* the official public version, not instead of it.

## 繁體中文摘要

這是一個 IELTS 學術組寫作評分的 Agent Skill。它解決的問題很具體：AI 改雅思作文時
**系統性偏低**，習慣把「寫得不夠好」誤判成「沒有達到標準」。實測紀錄是——初評 Band 5
的作文，經覆核後**無一例外全部上修到 5.5**，偏差全部落在 TR／CC／LR 的 5 與 5.5 邊界。

核心是一個六步驟流程，其中最關鍵的是一道二選一測試：**這些問題有沒有讓讀者看不懂、
誤解、或必須重讀？** 沒有的話，該項就從 5.5 起跳——因為官方描述本來就是這樣寫的。

這套校準只調整**分數落點**，不調整**錯誤清單**：每個錯誤照樣完整列出、引用原句、逐一訂正。

附帶 Task 1 七種圖表類型模板、Task 2 六種題型模板，以及十個主題的正反論點與話題詞彙庫。

## License

MIT
