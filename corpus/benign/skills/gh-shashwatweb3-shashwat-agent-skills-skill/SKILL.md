---
name: example-skill
description: Short description of what this skill does and when it should be used.
---

# Purpose

State the user problem in one or two sentences. What goes wrong today, and what
"done" looks like once this skill has been used.

If you cannot describe the problem in a sentence, the skill is probably too
broad. Split it.

# When to use

Describe the requests that should trigger this skill, and the neighbouring
requests that should not. Concrete phrasings help more than abstract rules.

Use when:

- the user asks for ...
- the user is about to ...

Do not use when:

- the user only wants ...
- a different skill already covers ...

# Inputs

What the workflow expects to have available. Separate what is required from what
improves the result.

Required:

- ...

Helpful but optional:

- ...

If the agent is working from a local repository, name the paths to read. If it
is working from a deployed URL, say what can and cannot be observed.

# Workflow

Numbered, imperative steps. Each step should be something an agent can actually
do, and the order should be the order that produces correct results.

1. Establish scope. Identify the target and confirm what is reachable.
2. Gather evidence. Read the relevant files or observable behaviour.
3. Check the remaining areas.
4. Produce the report.

# Rules

- Distinguish observed facts from assumptions, and label both.
- Never claim something was verified when it was inferred.
- Never print secrets, tokens, passwords, or environment variable values.
  Report `Potential secret exposure detected.` with the location only.
- Do not send project data, files, or credentials to external services.
- Do not run destructive commands unless the task requires it, and say what you
  are about to change before changing it.
- Use `Could not verify from the available code/environment.` when a check cannot
  be completed, rather than passing it silently.

# Output

Define the exact shape of the result so the same skill produces comparable
reports every time.

```markdown
# <Report title>

## Overall status
<one of the defined statuses>

## Summary
...

## Findings
### <SEVERITY>
#### <Finding title>
Category:
Evidence:
Why it matters:
Recommended fix:
```

State the allowed values for every enumerated field, such as severity levels or
status values. A reader must be able to parse the output without guessing.

# Edge cases

Cover the cases that will actually happen.

- **No source code available.** Say what you can observe and what you cannot.
- **Target is not reachable.** Report it plainly and stop rather than guessing.
- **User pushes back on a finding.** Explain the evidence, or withdraw the
  finding if it was wrong.
- **Scope is ambiguous.** Ask one clarifying question instead of guessing.
