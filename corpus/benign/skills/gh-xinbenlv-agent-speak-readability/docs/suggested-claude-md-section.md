# A suggested replacement for the language section of a global CLAUDE.md

This file suggests a replacement for the writing rules inside a global
`~/.claude/CLAUDE.md`. This repository does not edit that global file. The
owner's own rule requires explicit manual approval before any change to a
global `AGENTS.md` or `CLAUDE.md`. Read this file and paste the replacement
yourself.

## The English version

```markdown
## Rules for writing to the user
- Read the agent-speak-readability skill before you write any prose a human reads.
- Read lang/en/ for English output. Read lang/zh/ for Chinese output.
- Run the pre-send check in section 4 of that skill before you send the text.
  Perform the check as edits, not as a judgement.
- When the user says the text was hard to understand, run the check again and
  send the rewritten text. Do not explain and do not apologise.
```

## The Chinese version, for a global file written in Chinese

```markdown
## 与用户交流的语言的原则
- 我写任何给人读的自然语言之前，我先加载 agent-speak-readability 这一个技能。
- 我写中文的时候，我再加载该技能的 lang/zh/；我写英文的时候，我再加载该技能的 lang/en/。
- 我发出这一段文字之前，我先执行该技能第 4 节的发送前检查，我把检查当成编辑动作做完。
- 用户说「看不懂」的时候，我重新执行上述发送前检查，我直接发出改写后的文字，我不解释也不道歉。
```

## Why the replacement is shorter

### 1. The old section was long, and the length bought nothing

The old section held thirteen rules. An agent read the whole section into the
context of every session without any condition. In one real session the agent
read the section, the user repeated the requirement inside the prompt, and the
agent still broke the rules seven times in the very next reply.

The count of the rules was never the problem. The form of the rules was the
problem.

### 2. Action constraints survive. Style constraints drift

Action constraints from the same file held for hours. One example is the rule
"never commit unless the user asks". The writing rules in the same file
drifted back to the default voice of the model within one or two turns.

So the new section lists the actions to perform. The new section does not ask
for clear writing. An agent can check an action. An agent cannot check a
quality.

### 3. A global file holds the trigger. A skill holds the rules

The owner's own principle says that `AGENTS.md` holds only the constraints
that change agent behaviour in any session. "Load the skill" and "run the
check" both meet that test. The detail of the thirteen rules is conditional
material, so the detail belongs inside the skill.

## Where each old rule went

| Old rule | New location |
| --- | --- |
| The ASD-STE100 items for English | `lang/en/PRINCIPLES.md`, E1 to E5 |
| Active voice | `SKILL.md`, R7 |
| Write the subject of every sentence | `lang/zh/PRINCIPLES.md`, Z1 |
| No pronoun pointing at earlier text | `SKILL.md` R3, and Z4 for Chinese |
| Do not drop any element | `SKILL.md` R1, promoted to the master rule |
| One thing, one name | `SKILL.md`, R5 |
| No invented words and no metaphors | `SKILL.md`, R6 |
| Length caps | `SKILL.md` R9, with the numbers in Z8 and E3 |
| Use the Chinese word when one exists | `lang/zh/PRINCIPLES.md`, Z6 |
| Tense markers | `lang/zh/PRINCIPLES.md`, Z7 |

## What the replacement adds

| New rule | Location | Source |
| --- | --- | --- |
| Announce your next action as a full sentence | R2, and Z2 for Chinese | the short-fragment failures in a real session |
| Add a category word after an identifier | R4 | correction 3 from the user |
| Do not use compressed colloquial speech | R8, with Chinese examples in Z5 | correction 3 from the user |
| Never drop the numeral and the measure word | Z3 | correction 1 from the user |
| Use 「上述」 to point at earlier text | Z4 | correction 2 from the user |
| The pre-send check | `SKILL.md`, section 4 | the finding that style constraints drift |
