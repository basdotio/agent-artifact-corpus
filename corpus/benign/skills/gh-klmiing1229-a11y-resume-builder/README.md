# Resume Builder

![Resume Builder](banner.png)

Paste one prompt into any AI tool. It reads your resume, asks you a few questions, rebuilds it in a clean one page layout, and tells you what changed.

Works in Claude, ChatGPT, Gemini, Perplexity and any other chat AI, because the whole skill is one plain Markdown file: [`PROMPT.md`](PROMPT.md).

## What it does
1. **Scan.** You paste your current resume (or say "none"). It lists what is there, what is missing and what is weak.
2. **Ask.** At most 6 follow-up questions, in one message, only about gaps.
3. **Build.** A refined resume in plain Markdown that pastes into Word or Google Docs.
4. **Report.** What changed and why, what you must confirm, and one next step.

## Quick start

**Any chat AI (works everywhere)**
1. Open [`PROMPT.md`](PROMPT.md) and copy all of it.
2. Paste it as your first message.
3. Answer its questions. Paste your resume when asked.

**Claude (skill)**: put this folder in `~/.claude/skills/resume_builder/` (clone this repo into that path) and start a message with `resume`.

**ChatGPT**: create a custom GPT or a Project and paste `PROMPT.md` into the instructions. Then say "start".

**Gemini**: create a Gem and paste `PROMPT.md` as its instructions. Then say "start".

**Perplexity**: create a Space and paste `PROMPT.md` into its instructions, or paste it as your first message.

## The method
Method adapted from an Instagram reel on resume building. In six bullets:
- **Header:** name, location, contact details, LinkedIn.
- **Education first:** degree, school, GPA or honours, relevant coursework, two bullets.
- **Experience bullets** show what you achieved and its impact, not just what you did.
- **Numbers** go in only when you supply them, such as a sales target or a team size.
- **Unrelated jobs** are reframed around transferable skills you really used.
- **Skills and interests last,** with licences and certifications. Tailor the wording to the job.

## See it work
[`examples/before.md`](examples/before.md) is a weak fictional resume. [`examples/after.md`](examples/after.md) is the result.

## Privacy
Your resume goes to whichever AI tool you paste it into, under that tool's own privacy terms. This repo collects nothing. Remove your ID number, home address and anything you would not email to a stranger before you paste.

## Limits
- It never invents facts. Missing figures appear as `[add number]` for you to fill in.
- It does not promise interviews, jobs or applicant tracking system results.
- It produces Markdown text, not a formatted PDF. Paste it into your own template.
- It is a coach for layout and wording. It does not check whether your claims are true.

MIT licence.
