# Create a ticket from a story

Use this only when the user asks for a ticket from a story. Loupe creates one ticket per finished story, only after a clear yes, and never changes an existing issue.

## Before you offer

1. The story must be one you wrote and saved in `loupe/stories/` in this conversation, with `Call: Story written`, and it must have passed the checker. Otherwise, say in one line why not, such as "That is a Not ready yet response, so there is no story to make a ticket from." Then stop.
2. If you have no tool to create an issue, such as `mcp__pellwick-tracker__create_issue`, say in one line: "Ticket creation isn't set up; see https://github.com/mpwilso/loupe/blob/master/docs/live-context.md." Then stop.
3. Look for a ticket that already holds this story: read `loupe/tickets.md` if it exists, and search the tracker for the story's title. If you find one, say so in one line with its live source, like "SUBS-156 already holds this story. (Jira SUBS-156, read 2026-10-02 14:05)", and don't offer to create another.
4. Run `node SKILL/src/run.js check loupe/stories/<file>` on the saved file. It also runs the customer-data detector. If it fails, say so in one line and stop.

## Show it, then ask

Show exactly what will be created:
- Project: the tracker's project key, such as SUBS.
- Type: Story for a user story or a job story, Bug for a bug, Task for a change request or a spike.
- Title: the story's title, without the `#`.
- Labels: loupe.
- Description: the whole story file, unchanged, in a fenced block.

Then ask, with the project key: "Create this in SUBS?"

## On a clear yes

A clear yes is "yes", "yes, create it" or "go ahead". Anything else, such as "not yet", "maybe" or a question, is not. Then create nothing, and say so in one line: "I didn't create a ticket."

1. Call the create tool once, with exactly the fields you showed. The description is the story file's full text, byte for byte, ending with the same final line break: copy it from the file you read, never retype it.
2. Add one line to `loupe/tickets.md`, creating it if needed: the key, the story's file name, and the time the tool returned, like "SUBS-156, 2026-10-02-skip-next-box.md, created 2026-10-02 14:05".
3. Run `node SKILL/src/run.js check-folder loupe`, and fix `loupe/tickets.md` until it passes.
4. Reply in one line with the key and its live source, using the time the tool returned: "Created SUBS-156. (Jira SUBS-156, read 2026-10-02 14:05)"

## Never

- Never create a ticket without a clear yes to the exact ticket you showed. If anything must change after the yes, show it again and ask again.
- Never create a second ticket for a story.
- Never update, comment on, move, assign, close or delete an issue, even one Loupe created. If asked to change an issue, reply with exactly one line: Loupe can't change the tracker yet.
- Never put customer data in a ticket.
