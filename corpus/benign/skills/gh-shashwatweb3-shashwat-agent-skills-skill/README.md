# Skill template

A starting point for a new skill. Copy it, then replace every placeholder.

```bash
cp -r templates/skill skills/my-new-skill
```

Then edit `skills/my-new-skill/SKILL.md`.

## Before you start

A skill should represent one recognisable user goal. If you cannot describe the
problem the skill solves in a sentence, split it into two skills instead of
building a "do everything" skill.

Good names: `website-launch-safety`, `seo-audit`, `pr-review`.

Bad names: `ultimate-web-development`, `all-in-one-helper`.

## Steps

1. **Rename the directory** to the skill's `name`. The specification requires
   the frontmatter `name` and the directory name to match.

2. **Write the frontmatter.**

   ```yaml
   ---
   name: my-new-skill
   description: What the skill does, and when an agent should reach for it.
   ---
   ```

   `name` and `description` are the only required fields. Keep `description`
   under 1024 characters, and lead with the key use case so it still matches
   when a host truncates it.

   `license`, `compatibility`, `metadata` and `allowed-tools` are optional. Do
   not add any other key: platform-specific frontmatter breaks packaging for
   claude.ai uploads and the Skills API.

3. **Fill in each section of the body.** Keep `Purpose`, `When to use`, `Inputs`,
   `Workflow`, `Rules`, `Output` and `Edge cases`. Delete sections that genuinely
   do not apply rather than leaving them as filler.

4. **Add supporting files only if you need them.**

   | Directory     | Use it for                                                     |
   | ------------- | -------------------------------------------------------------- |
   | `references/` | Detail the agent reads on demand, kept out of the main file     |
   | `scripts/`    | Deterministic, repeatable operations the agent runs             |
   | `assets/`     | Templates, fixtures, or files the agent copies or fills in     |

   Do not create these directories to fill them. A small skill is one file.

5. **Write behaviour test cases** under `tests/<skill-name>/`. See
   `tests/website-launch-safety/` for a worked example covering positive,
   indirect, non-trigger and edge cases.

6. **Validate.**

   ```bash
   ./scripts/validate-skills
   ./scripts/list-skills
   ```

## Adding a skill never requires a registry

`skills/` is the source of truth. `scripts/list-skills` and
`scripts/validate-skills` discover skills by scanning the directory, so a new
skill is picked up the moment it lands. The only files you edit are inside
`skills/<skill-name>/` and `tests/<skill-name>/`.

Platform packaging (`.claude-plugin/`, `.agents/plugins/`) points at the whole
`skills/` directory, so it stays correct as the collection grows.

## Before you open a pull request

Every skill should answer these questions:

- **Trigger** — can an agent tell when to use it?
- **Scope** — does it solve one recognisable workflow?
- **Inputs** — is it clear what information it needs?
- **Procedure** — are the steps explicit without being bloated?
- **Evidence** — does it separate observed facts from assumptions?
- **Output** — is the result predictable?
- **Failure mode** — does it say what to do when something cannot be verified?
- **Safety** — no destructive actions, credential exposure, or data exfiltration.
- **Portability** — the same file works in any Agent Skills client.
