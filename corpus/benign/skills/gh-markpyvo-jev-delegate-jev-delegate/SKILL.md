---
name: jev-delegate
description: Sends each delegated task to the cheapest Claude model that can handle it, using TypeSafe's Jev decision model to pick the tier (Haiku, Sonnet, or Opus). Use this whenever the user says Claude Code is burning through tokens or hitting usage limits, asks which model should do a task, wants to save money or tokens on agent work, mentions Jev or model routing, or whenever you are about to spawn two or more subagents or split a large job into parallel pieces. Use it even if the user never mentions Jev or cost, because picking the model per subagent is where most of the savings are.
---

# jev-delegate

Claude Code sessions get expensive because every subtask runs on the strongest model, including renames, typo fixes, and "run the tests and tell me what failed". This skill asks Jev, a fast decision model, how demanding each subtask is, then runs it on Haiku, Sonnet, or Opus accordingly.

Jev only makes a decision. It cannot write or reason about code. You (the main model) split the work, ask Jev where each piece should run, and spawn subagents on the models it picks.

## Setup (once)

The script needs a TypeSafe API key in the environment:

```bash
export TYPESAFE_API_KEY=...   # JEV_API_KEY also works
```

Jev is in early access. If the user has no key, they can join the waitlist at typesafe.ai. Without a key the script does not fail; it returns `"tier": "inherit"` and you carry on with your normal model, so the skill is safe to leave installed.

## Workflow

1. **Split the job** into subtasks that can be handed off. Skip this skill for anything you will just do inline in a few seconds; the routing call is not free (about a quarter to three quarters of a second).

2. **Route them in one call.** Describe each subtask in a sentence or two: what needs doing, roughly where, and any unknowns. Describe the work, not the model. Leave out secrets, credentials, and large code pastes, because the text is sent to api.typesafe.ai.

   ```bash
   python scripts/route.py "rename getUser to fetchUser across src/api" \
                           "find why the checkout total is off by one cent intermittently" \
                           "add unit tests for the date parser"
   ```

   For long lists, put a JSON array of strings in a file and pass `--file tasks.json`.

3. **Read the result.** You get a JSON list in the same order as your tasks:

   ```json
   {"tier": "fast", "model": "haiku", "effort_hint": "low", "confidence": 0.91,
    "risky": 0.02, "reason": "mechanical at 0.91, effort 0.3"}
   ```

   - `model` is `haiku`, `sonnet`, or `opus`. Pass it as the model of the subagent you spawn for that task.
   - `model: null` (tier `inherit`) means Jev was unavailable or no key is set. Spawn the subagent without overriding the model.
   - `effort_hint` is advisory. If it says `low`, tell the subagent to keep reasoning brief and not explore beyond the task.
   - `risky` above about 0.7 has already pushed the task to `opus`. Treat those tasks with care: confirm with the user before anything that touches production, money, or unrecoverable data.

4. **Spawn subagents** using the subagent tool's `model` parameter (or `model:` in the agent definition). Give each one a self-contained prompt with the files, the goal, and how to verify it, since subagents do not see your conversation.

5. **Escalate one tier on failure.** If a subagent's result is wrong, incomplete, or fails its check (tests still red, it says it is stuck), retry once on the next tier up: haiku, then sonnet, then opus. Do not retry on the same tier. Retrying on the same model mostly repeats the same mistake and costs the same again.

## Rules that keep it cheap

- **Never change the model of the main conversation.** Prompt caches are per model, so switching mid-session forces the whole context to be re-read uncached, which usually costs more than the switch saves. Route the subagents, which start with small fresh contexts.
- **Pin the tier for the life of a task.** Do not re-route the same subtask every turn.
- **Trust the asymmetry.** The script moves a task up on modest confidence and down only on high confidence, and only when several signals agree. If it says `balanced` on something that looks easy, that is intended. Do not override it toward cheaper.
- **Do not send Jev your whole conversation.** It sees only the task text you pass. A short, specific description gets better answers than a long one.

## Measuring savings

Every routing call is appended to `~/.jev-delegate/decisions.jsonl` (task text is never stored, only an id, length, and the decision). To see the spread:

```bash
python scripts/report.py
```

The cost estimate uses assumed relative prices. Present it to the user as an estimate, and suggest checking real usage in their plan dashboard before quoting a number. Set `JEV_DELEGATE_LOG=0` to turn logging off.

## Limits worth telling the user about

- Jev reads text only and has a small input window, which is why tasks are passed as short descriptions.
- Accuracy is vendor-reported and the questions and thresholds here are unproven defaults. Misroutes cost a retry, not a wrong answer, because you verify subagent output and escalate.
- Details of the questions, thresholds, environment variables, and how to tune them against real tasks are in `references/tuning.md`. Read it if the user wants to change model names, thresholds, or the effort cap.
