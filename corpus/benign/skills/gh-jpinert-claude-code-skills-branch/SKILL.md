---
name: branch
description: Split a side topic out of this chat into its own NEW chat and open it automatically - write it a capped handoff, lift the reusable procedure into skills, cross-link both directions, then launch the new chat in its own kitty tab (branch-launch.sh) seeded to continue the work. Use when the user says /branch, "I'll use a new chat for that", "fork that off", "spin that off", "split that off", "separate chat for X", "new chat for that", "what handoff can I point it at", "so it can pick that up", AND on your own initiative whenever this chat diverges into a second distinct project that no longer shares state with the first.
---
<!-- needs: the handoff skill (its triage table), kitty with remote control enabled (allow_remote_control yes), bash. -->
<!-- no accounts or hardware. Without kitty, do steps 1-5 and give the user the opening line to paste. -->

# Branch a side topic into its own chat

`/handoff` **replaces** this session when context fills: same work, next chat.
`/branch` **splits** it: a subset leaves, this chat keeps going.
Use the triage table and the four durable homes from the **`handoff` skill**; this file only
covers what is different.

## Why not just fork the chat

A fork inherits the whole transcript, so the new chat opens already carrying this one's context.
That is the opposite of the point, and it is what the context rollover rule exists to avoid.
A branch inherits the **conclusions** and none of the scrollback. If the user asks for a fork,
say so and offer this instead.

## Only branch what is genuinely separable

Ask before writing anything: **do the two topics still share live state?**

- Shares a service, a file being edited, a device mid-change: **do not branch.** Two chats
  editing one thing is how state drifts. Finish or `/handoff` instead.
- Different box, different repo, different problem, only a technique in common: **branch.**
  The technique becomes a skill, which is what makes the split cheap.

## Steps

1. **Name the scope in one line** and say what stays here. If that sentence needs an "and also",
   the scope is wrong.

2. **Harvest to the durable homes first**: triage exactly as `handoff` does. The test is
   sharper here: anything BOTH chats will need is a **skill or memory**, never text copied into
   two handoffs. Copied text is the failure mode; it drifts and then nobody knows which is true.
   *Example: splitting a Raspberry Pi rebuild off a remote-support chat, the no-card-reader
   netboot method went to the `pinetboot` skill, the router and switch access went to its own
   skill, and the new handoff kept only what was different about that one box.*

3. **Write `HANDOFF-<topic>.md`**, capped like any state file. It opens by naming the skills that
   now load on their own, and points at the existing `-history.md` for evidence rather than
   repeating it. It carries **only** what is different about this topic, plus its open items.

4. **Cross-link BOTH directions. This is the step that earns the skill.**
   - Child: name the parent handoff and the history file its evidence lives in.
   - **Parent: remove the branched work from its open items** and leave one line saying where it
     went. If the parent keeps carrying it, the two files drift and both go stale.
   - `MEMORY.md`: one index line for the new handoff, and for any new skill.

5. **Verify what the new chat will actually load.** `ls ~/.claude/skills/` and confirm the
   new skill's `description` contains the words the user would really type. A skill that does
   not trigger is a file nobody reads.

6. **Launch the new chat; don't hand the user a line to paste.** Write the opening prompt to a
   file and run:

   ```bash
   ~/.claude/skills/branch/branch-launch.sh <name> <prompt-file>
   ```

   It opens a kitty tab titled `<name>`, runs `claude` through your shell (so the `handoff`
   wrapper and your usual flags apply), and takes focus. `<name>` = topic + next number, no
   spaces. The prompt tells the new chat to **continue**, not to ask:

   ```
   Continuing the <topic> work, branched from <parent chat name>: read HANDOFF-<topic>.md
   (short, capped). The /<skill> skills carry the procedure. Carry on with its plan; stop only
   where it says the user's word is needed.
   ```

   Then check it took: `kitty @ ls` shows a window titled `<name>` whose foreground process is
   `claude`. Only if the launch fails, fall back to giving the user the line.
   **Auto-trigger, but say so:** when you branch on your own initiative, the final message names
   the new tab and what moved, so a split never happens silently.

7. **Say what the branched chat CANNOT do.** Anything this chat holds that it will not: a stopped
   service, a device only reachable from here, a power cycle it cannot perform. Put it in the
   child handoff too, not only in chat.

## Do not

- Do not close, `/clear` or `/handoff` this chat. It keeps working.
- Do not copy procedure text into the child handoff; lift it to a skill and reference it.
- Do not branch a topic whose work is already half-done in this chat's working tree.
