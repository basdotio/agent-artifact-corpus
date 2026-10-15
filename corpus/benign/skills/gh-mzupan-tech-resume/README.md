# tech-resume

A shared Agent Skill for Claude Code, Codex, IBM Bob, GitHub Copilot, Gemini CLI, and OpenCode that writes tailored resumes and cover letters for tech jobs. It interviews you once to build a career profile, asks a few targeted questions for each job description, and produces DOCX and PDF files that:

- parse cleanly in ATS and AI screeners (Greenhouse, Lever, Ashby, Workday): single column, contact info in the body, no tables or text boxes, embedded fonts, no ligatures
- cover the job description's must-have terms with bullets that prove them, not just a skills list
- don't read as AI-written: a lint pass flags stock AI resume words, dashes, uniform bullets, and -ing riders before anything is built

It never invents numbers, titles, or tools. If a bullet needs a fact you haven't given it, it asks.

## Install

Requires an agent that can read files and run shell commands, Python 3.9+, and git for cloning.

All supported agents use the same `SKILL.md`, scripts, references, and templates. Separate copies of the instructions for each agent are unnecessary; only the discovery location and invocation differ.

| Agent | Personal installation folder | Project installation folder |
|---|---|---|
| [Codex](https://developers.openai.com/codex/skills) | `~/.agents/skills/tech-resume` | `.agents/skills/tech-resume` |
| [IBM Bob](https://bob.ibm.com/docs/ide/features/skills) | `~/.bob/skills/tech-resume` | `.bob/skills/tech-resume` |
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/tech-resume` | `.claude/skills/tech-resume` |
| [GitHub Copilot](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) | `~/.agents/skills/tech-resume` or `~/.copilot/skills/tech-resume` | `.agents/skills/tech-resume` or `.github/skills/tech-resume` |
| [Gemini CLI](https://geminicli.com/docs/cli/skills/) | `~/.agents/skills/tech-resume` or `~/.gemini/skills/tech-resume` | `.agents/skills/tech-resume` or `.gemini/skills/tech-resume` |
| [OpenCode](https://opencode.ai/docs/skills/) | `~/.agents/skills/tech-resume` or `~/.config/opencode/skills/tech-resume` | `.agents/skills/tech-resume` or `.opencode/skills/tech-resume` |

One installation under `~/.agents/skills/tech-resume` serves Codex, Copilot, Gemini CLI, and OpenCode. Bob and Claude Code use their own discovery folders.

1. Choose a folder from the table and clone the skill there. For Codex (and the other agents that support the shared folder):

   ```bash
   SKILL_DIR="$HOME/.agents/skills/tech-resume"
   mkdir -p "$(dirname "$SKILL_DIR")"
   git clone https://github.com/mzupan/tech-resume.git "$SKILL_DIR"
   ```

   For Bob, use `SKILL_DIR="$HOME/.bob/skills/tech-resume"`; for Claude Code, use `SKILL_DIR="$HOME/.claude/skills/tech-resume"`.

   To install the version in an existing checkout instead of cloning, run this from the checkout after setting `SKILL_DIR` to a new installation folder outside it:

   ```bash
   mkdir -p "$SKILL_DIR"
   cp SKILL.md README.md requirements.txt LICENSE "$SKILL_DIR/"
   cp -R scripts references templates "$SKILL_DIR/"
   ```

   For project installation, put the whole skill folder in the chosen project's discovery folder. A `SKILL.md` at the root of an ordinary checkout alone is not a discovery installation.

2. Install the Python packages the build and verify scripts use, in the same Python that runs the scripts:

   ```bash
   python3 -m pip install -r "$SKILL_DIR/requirements.txt"
   ```

3. Install poppler for `pdftotext` and `pdftoppm` (recommended; text extraction falls back to pypdf without it, but PNG previews require poppler or another PDF renderer):

   ```bash
   brew install poppler          # macOS
   sudo apt install poppler-utils  # Debian/Ubuntu
   ```

4. Optional: install the two writing skills the human-voice pass uses beside `tech-resume` in the same discovery folder. Without them, it uses its own writing rules and linter.

   ```bash
   git clone https://github.com/blader/humanizer.git "$(dirname "$SKILL_DIR")/humanizer"
   git clone https://github.com/theclaymethod/unslop.git "$(dirname "$SKILL_DIR")/unslop"
   ```

   - [humanizer](https://github.com/blader/humanizer) rewrites AI writing patterns based on Wikipedia's "Signs of AI writing".
   - [unslop](https://github.com/theclaymethod/unslop) adds a phrase scanner that `scripts/lint.py` merges into its report.

5. Start a new agent session or reload its skills. In Bob, check Settings > Skills; in Gemini CLI, use `/skills list`.

PDFs use Arial when it's installed (macOS has it; on Linux install `ttf-mscorefonts-installer`) and fall back to Helvetica otherwise.

## Use

Run your agent from the folder where you want your career data to live (for example `~/career`). The skill creates `profile/` and `applications/` there.

In Claude Code, invoke `/tech-resume`; in Codex, invoke `$tech-resume`. For Bob, Copilot, Gemini CLI, and OpenCode, ask in plain language, for example: `Use the tech-resume skill to init old-resume.pdf`. The operations below are the same in every agent; `/tech-resume` is shown as Claude Code syntax.

| Command | What it does |
|---|---|
| `/tech-resume init old-resume.pdf` | Seeds your profile from an existing resume or LinkedIn PDF export and reports what would break in an ATS |
| `/tech-resume profile` | Interviews you role by role for scope, numbers, and ownership |
| `/tech-resume target staff` | Sets the level you're aiming for (senior, staff, principal, manager, director, vp, architect) |
| `/tech-resume apply <job URL or text>` | Asks 3-8 gap questions, then writes the resume and cover letter |
| `/tech-resume resume <JD>` / `cover <JD>` | Resume only / cover letter only |
| `/tech-resume review resume.pdf [JD]` | Critiques an existing resume and ranks fixes by impact |
| `/tech-resume base` | Lists base resumes, if you keep more than one version of your history |

Each application gets its own folder:

```
applications/2026-10-11-company-role/
  jd.md  keywords.txt  gaps.md  resume.md  cover-letter.md  report.md
  First-Last-Resume-Company.docx/.pdf
  First-Last-Cover-Letter-Company.docx/.pdf
```

`report.md` lists must-have keyword coverage, what was left out on purpose, and the facts that would most improve that resume.

Your profile and applications hold personal data. Keep that folder out of public repos.

## Is installation needed?

Installation makes the workflow available for automatic discovery and explicit skill invocation across sessions. It is useful if you tailor resumes repeatedly or want the same process across agents.

For a one-off task, an agent with file and shell access can use an ordinary checkout without installing it: ask it to read the checkout's `SKILL.md` and follow it, using the checkout as `SKILL_DIR` and a separate career workspace for your data. The scripts also work directly without an agent. Skill installation supplies reusable instructions; it does not add model capabilities or replace the Python dependencies.

## Scripts

The skill drives these, but they also work on their own:

| Script | Purpose |
|---|---|
| `scripts/extract.py` | Old resume (PDF, DOCX, TXT, MD) to text, with a parse report |
| `scripts/build.py` | Markdown to ATS-safe DOCX and PDF |
| `scripts/verify.py` | Parse test of the built files plus keyword coverage by section |
| `scripts/lint.py` | Flags AI-sounding and generic writing in a resume or letter |

`references/research.md` lists the sources behind the formatting and writing rules.

## License

MIT
