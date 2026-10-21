---
name: garmin-browser-tools
description: Read an authorized Garmin Connect workout and prepare a bounded connectivity-test delivery using an agent's supported browser. Use for direct Garmin browser reads or testing workout/calendar delivery; this package does not manage a complete coaching plan.
---

# Garmin browser tools

Use the agent's own supported browser and command runtime. Browser sessions stay
with that platform. This Skill does not grant access to Garmin, a phone, another
agent, or ChatGPT Health.

Read [the browser entry contract](references/entry.md) for installation,
capability checks, read handoff, and delivery. It owns commands and evidence
boundaries. The supported read result is a selected workout, not a complete
training or recovery history.

For interpreting training evidence, load the shared reference with
`python -m garmin_agent_tools.browser training-guidance`. It returns the exact
text, source revision and SHA256. The reference owns training judgment; this
Skill owns the connection workflow. The command loads no athlete context or
current plan. Fields such as `plan.*`, `training_breaks` and `training_history`
belong to the source coach schema; their absence here is unknown, not a confirmed
training condition. Do not report a proposed plan as persisted by this tool: its state
contains connectivity evidence and delivery journals, not a coaching PlanState.

Report observed fields and their observation time, with absent evidence unknown.
Use the SDK's actual instructions and result rather than assuming a browser
operation succeeded. For example, a login page is unavailable data, not a rest
day; a queued delivery is not a created workout. The entry contract names the
checks and readback states that establish completion.
