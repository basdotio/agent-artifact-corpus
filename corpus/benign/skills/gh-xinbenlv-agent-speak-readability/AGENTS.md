# AGENTS.md

These rules come from the repository owner's global agent configuration. The
rules are copied here and trimmed to what this repository actually needs. The
working language of this repository is English, so the rules are translated.

## Working language

- The working language of this repository is English. Write every file, every
  commit message and every issue in English.
- The Chinese examples inside `lang/zh/` stay in Chinese. Those examples are
  the subject matter of the file, not prose about the subject matter.
- The Chinese trigger phrases inside the `description` field of `SKILL.md`
  stay in Chinese. Those phrases are match data for the skill loader.

## How to write anything a human reads

- `SKILL.md` in this repository is the full version of this section, so this
  file does not repeat the rules.
- Read `SKILL.md` before you write any prose that a human will read.
- Read `lang/en/PRINCIPLES.md` when you write English. Read
  `lang/zh/PRINCIPLES.md` when you write Chinese.
- Run the pre-send check in section 4 of `SKILL.md` before you send the text.
- Every sentence in this repository must pass that check. A readability skill
  written in unreadable prose refutes itself.

## Rules for AGENTS.md itself

1. What belongs in this file: the main agent harnesses read `AGENTS.md` into
   the context of every session without any condition. So this file holds only
   the constraints that change agent behaviour in any session. Conditional
   rules, explanations and reference material belong beside the files they
   describe, where an agent reads them at the moment of need.
2. Changes need the user's approval. Never change a global `AGENTS.md` or
   `CLAUDE.md`, and never change this file, without explicit manual approval
   from the user.

## Rules for README files

- Naming: follow the naming habit of the directory or of the parent directory.
- Reading: read the README of a directory before you read anything else in
  that directory.
- Readability: keep a README under two pages. Use plain human language. Add a
  directory tree, and add an ASCII or Mermaid diagram when a diagram helps.
  Write for both the users and the developers of the directory.
- Updating: consider a README once a directory holds more than about five
  files. When you change any file in a directory, review the README of that
  directory and of every parent directory. When the code and the README
  disagree, correct the README.

## Loading skills

Use a skill when the user names the skill. Otherwise load only the skill that
the current action needs. Do not chain skills because of a keyword, a
repository name or a link in a document.

## Constraints specific to this repository

- The first code block in `lang/zh/ACCEPTANCE-CASES.md` holds four corrections
  that the user wrote by hand. Keep that block exactly as it is, character for
  character.
- Do not install this repository into `~/.claude/skills/` or
  `~/.agents/skills/`. The user runs the install command.
