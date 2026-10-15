# agent-speak-readability

An agent skill that makes an agent's natural-language output readable to a
human reader. The skill holds cross-language rules at the top level, Chinese
rules under `lang/zh/`, and English rules under `lang/en/`. The core of the
skill is a pre-send check written as edit steps, not as a quality to aim at.

## The problem this skill fixes

An agent writes for itself. The agent already knows the actor, the object, the
file name and the result, so the agent compresses all of them out of the
sentence. The human reader does not know any of them. The text that comes out
looks confident and carries almost no information.

This repository is not a style preference. This repository is a list of edits
that an agent performs on a draft before the agent sends the draft.

## Directory tree

```
agent-speak-readability/
├── README.md                      this file
├── CHANGELOG.md                   version history
├── LICENSE                        Apache License 2.0
├── SKILL.md                       skill entry point: 9 cross-language rules + the pre-send check
├── AGENTS.md                      repository-wide constraints for agents
├── CLAUDE.md                      symlink to AGENTS.md
├── docs/
│   └── suggested-claude-md-section.md   a replacement section for a user's global CLAUDE.md
└── lang/
    ├── zh/
    │   ├── PRINCIPLES.md          Chinese rules Z1 to Z10
    │   ├── ACCEPTANCE-CASES.md    four hand-written corrections, kept word for word
    │   └── NEGATIVE-SAMPLES.md    real Chinese failure samples from one session
    └── en/
        └── PRINCIPLES.md          English rules E1 to E9
```

## How an agent uses the skill

1. Read `SKILL.md` and take the nine cross-language rules.
2. Read the file for the language you are about to write in. Chinese output
   uses `lang/zh/PRINCIPLES.md`. English output uses `lang/en/PRINCIPLES.md`.
3. Write the draft.
4. Run the ten check steps in section 4 of `SKILL.md` on the draft.
5. Run the extra check steps at the end of the language file.
6. Send the edited draft.

When a user says that a reply was hard to understand, run the check steps
again on that reply. Send the rewritten text. Do not explain and do not
apologise.

## Install

```bash
git clone https://github.com/xinbenlv/agent-speak-readability.git ~/.claude/skills/agent-speak-readability
```

If you already cloned the repository somewhere else, use a symlink instead.

```bash
ln -s <absolute path to this repository> ~/.claude/skills/agent-speak-readability
```

`docs/suggested-claude-md-section.md` holds a replacement for the language
section of a global `~/.claude/CLAUDE.md`. Read that file and paste the
replacement yourself. This repository does not edit a global configuration
file.

## For contributors

The first code block in `lang/zh/ACCEPTANCE-CASES.md` is the acceptance
standard. Check every change to this repository against those four
corrections. Keep that code block exactly as it is, character for character.

The working language of this repository is English. The Chinese examples
inside `lang/zh/` stay in Chinese, because those examples are the subject
matter of the file.

Every sentence in this repository must pass the check in `SKILL.md`. A
readability skill written in unreadable prose refutes itself.

## Where this skill came from

A native Chinese speaker could not understand the Chinese that an agent wrote
during a long working session. That user already had thirteen writing rules in
a global configuration file. The agent read that file. The user then repeated
the requirement inside the prompt. The agent still broke the rules seven times
in the very next reply.

Action constraints from the same file held for hours. One example is the rule
"never commit unless the user asks". The writing rules drifted back to the
default voice of the model within one or two turns.

So this skill states the requirement as "perform these ten steps before you
send". This skill does not state the requirement as "write more clearly".

## Version

The current version is 0.1.0. The version lives in the `version` field of
`SKILL.md`, and `CHANGELOG.md` records what each version changed. The rules
and the check work at 0.1.0, and the interface may still change.

## License

Apache License 2.0. The full text is in the `LICENSE` file.
Copyright 2026 Zainan Victor Zhou.
