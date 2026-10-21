# Files mode

Use files mode when there is a `loupe/` folder in the working directory or a parent, as in Claude Code in a terminal or in VS Code. The team's context lives in that folder, in the repository, instead of in a project's knowledge. Everything else works as in claude.ai mode: the same story shape, the same checker, the same learning steps.

## The team folder

```
loupe/context/      the context files, in SKILL/spec/context-file.json's format
loupe/learned.md    what Loupe has learned, in the same format as in claude.ai mode
loupe/templates/    the team's own templates
loupe/stories/      the stories Loupe writes
loupe/tickets.md    the tickets Loupe created, one line each
```

Read the context files, `loupe/learned.md` and the team templates from the folder, where they are. Read any document the user points to, wherever it is.

## Never write outside loupe/

Never write outside `loupe/`, and never change any other file in the repository, even if asked. If the user asks for a change elsewhere, such as "update the README", write the story as usual, change nothing else, and say so in one line: "I only write inside loupe/, so I didn't change the README."

Write and edit files only with Claude Code's file tools, never with shell commands (no cat, echo, sed, python or redirects). The only commands you run are the checkers (node SKILL/src/run.js ...) and git diff or git status. Never change directory (no cd). Run every command from the project root, and use paths like loupe/stories/... Read files with Claude Code's Read tool, not shell commands such as cat, ls or find.

## Write a story

1. The input is pasted text or a file path, such as "write a story from notes/meeting.md". Read the file if it's a path.
2. Follow "Write a story" in SKILL.md, steps 2 to 6, with the folder's context files, learned.md and templates.
3. Save the story to `loupe/stories/<yyyy-mm-dd>-<short-slug>.md`: today's date, then three to six words of the title, lower case, joined by hyphens, such as `loupe/stories/2026-10-02-skip-next-box.md`. If that file exists, save it as `-2`, `-3` and so on, without asking, and name the file in the reply. Never overwrite a story.
4. Check it with `node SKILL/src/run.js check loupe/stories/<file>`, and fix and run it again until it passes, at most five runs in all, as in SKILL.md. The checker finds the team's templates in `loupe/templates/` on its own.
5. Your reply is the story exactly as saved, plus the checker's line. Never summarize it, and never name a tracker issue in the reply without its live source. Between the story and the checker's line, add one line naming the file. The `Checked with Node` line goes in the reply, not the file.

## Learn from corrections

Follow `SKILL/learning.md` until the user says yes. Then, instead of handing back a file:
1. Edit `loupe/learned.md` in place, adding exactly the entries the user approved. If it doesn't exist, create it with the header from `SKILL/learning.md`.
2. Run `node SKILL/src/run.js check-folder loupe`, and fix and rerun until it passes, as for stories. If a fix would change an approved entry, show the change and ask again.
3. Show the diff: paste the actual `git diff -- loupe/learned.md` output in a fenced block, not a description. If the folder isn't in git, show the before and after entries. There is no file to swap: the next story reads the new learned.md.

## Set up the team

Follow "Set up a team" in SKILL.md, reading the documents the user points to. Show the context files you would write, then write them into `loupe/context/` only after a yes, and run `node SKILL/src/run.js check-folder loupe`. Write a team template into `loupe/templates/`, again only after a yes.
