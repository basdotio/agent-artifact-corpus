---
name: claudeweaver
description: Local kanban board over Markdown ticket files, plus a dev-mode overlay. The human Shift-clicks (or taps) the running app to drop a sticky note, and the note becomes a ticket for the agent. Use when you set up the board in a project, add the overlay to a dev server, file or update tickets, or watch the board to work tickets as the human files them.
license: MIT
---

# Claudeweaver

Claudeweaver is a feedback loop between a human and a coding agent. The human drops notes on the running app. The agent watches the board, does the work and moves each ticket to review.

A ticket is one Markdown file with YAML frontmatter in a `tickets/` folder. The tickets are committed to git. The board is one Go program in this folder. It uses only the standard library. It serves a kanban page, a JSON API and the overlay script `devnotes.js`. It listens on loopback only and has no auth.

In this file, `<skill-dir>` is the folder that contains this file.

## Run the board

You need Go 1.22 or later. Run these commands from the project root:

```sh
go build -C <skill-dir> -o "$PWD/.claudeweaver" .   # add .claudeweaver and .claudeweaver.log to .gitignore
mkdir -p tickets
./.claudeweaver -addr :8090 -dir tickets 2>&1 | tee -a .claudeweaver.log
```

The flags are:

- `-addr`: the listen address. The default is `:8090`. Any free port works. An empty host binds the loopback addresses only.
- `-dir`: the tickets folder. The default is `tickets`.
- `-areas`: a comma list of areas. The default is `web,server,docs,infra`. The first area is the default for new tickets.
- `-tailnet-host`: the Tailscale name of this machine, for example `box.example.ts.net`. Use it with `tailscale serve`, so that a phone on your tailnet can drop notes.

Open `http://localhost:<port>`. On the board, N opens quick add (`feat: Title p1 #web`, then Enter). J and K move between cards. Enter opens a card. Keys 1 to 6 move it to a column. E edits the title. The panel saves as you type. You can paste or drop images into it.

## The CLI

The same binary is a CLI. All commands take `--dir` and `--areas`.

```sh
./.claudeweaver ls --status inbox,todo
./.claudeweaver show 1003
./.claudeweaver new --title "..." --type bug --area web --status todo --body - < notes.md
./.claudeweaver mv 1003 doing
./.claudeweaver note 1003 "Picked this up." --by claude
```

You can also edit the ticket files directly. A write through the tool changes only the lines it touches. It keeps unknown fields, comments and the body.

## Add the overlay (dev only)

Load `http://localhost:<port>/devnotes.js` in dev builds only. Do not load it in production. The optional `data-area="web"` attribute sets the area of new notes.

Vite (`vite.config.ts`):

```ts
plugins: [{
  name: "claudeweaver",
  apply: "serve", // dev server only
  transformIndexHtml: () => [{ tag: "script", injectTo: "body",
    attrs: { src: "http://localhost:8090/devnotes.js", async: true, onerror: "this.remove()" } }],
}]
```

Plain HTML: add the tag by hand to a dev-only page, or remove it in the build.

```html
<script src="http://localhost:8090/devnotes.js" async onerror="this.remove()"></script>
```

Server template (Go `html/template` is shown, other engines are the same):

```html
{{if .Dev}}<script src="http://localhost:8090/devnotes.js" async onerror="this.remove()"></script>{{end}}
```

The page must come from `http://localhost`, `http://127.0.0.1` or `http://*.localhost`. With `-tailnet-host`, the page can also come from `https://<tailnet-host>`. The API refuses other origins.

To drop a note, the human Shift-clicks an element, types and presses Enter. On a phone or tablet, the human opens the small tab on the right edge, chooses "Drop a note" and taps the element. The ticket goes to `inbox` with the URL, a CSS selector, the element text, the viewport and an optional screenshot. Pins mark the open notes on the page. Each pin shows the status color and icon. The icon of a `doing` ticket turns. Shift+D hides the whole overlay.

### Phones over Tailscale

1. Run `tailscale serve --bg --https=18090 http://localhost:8090`.
2. Serve the app the same way, for example on port 18081.
3. Start the board with `-tailnet-host <name>.ts.net`.
4. In the app, load the overlay from `https://<name>.ts.net:18090/devnotes.js` when the page host ends in `.ts.net`.

iOS Safari cannot capture the screen. On a phone or tablet, the note has a "Choose from Photos" button instead. The overlay makes each image smaller until it is 5 MB or less.

### Screenshots from an iPhone Shortcut

You make an iOS Shortcut one time. Then you share a screenshot to it, type a note, and the board gets an `inbox` ticket with the image. The phone must be on your tailnet, and the board must be served with `tailscale serve` (see Phones over Tailscale). Open `https://<name>.ts.net:18090/phone` on the phone to see these steps with your address filled in.

1. Open the Shortcuts app. Tap + to make a new Shortcut. Name it "Send to board".
2. Tap the info button (i) and turn on "Show in Share Sheet". In the first action, set "Receive Images from Share Sheet". If there is no input, set "Stop and Respond".
3. Add the action "Ask for Input". Set the type to Text and the prompt to "Note". Turn on "Allow Multiple Lines" if you want a body.
4. Add the action "Get Contents of URL". Set the URL to `https://<name>.ts.net:18090/api/notes`. Tap "Show More".
5. Set Method to POST and Request Body to Form.
6. Add a Text field. Set the key to `title` and the value to the "Provided Input" variable.
7. Add a File field. Set the key to `image` and the value to the "Shortcut Input" variable.
8. Add the action "Show Notification". Set its text to the "Contents of URL" variable.

To use it, take a screenshot, tap the thumbnail, tap the share button and choose "Send to board". The first line of the note becomes the title, and the other lines become the body. The notification shows the reply, for example `Ticket #1340 created: Button overlaps`.

Each image must be 5 MB or less, and one request takes 10 images at most. If a photo is too large, add the action "Convert Image" (format JPEG) before "Get Contents of URL".

## Ticket format

The file name is `tickets/<id>-<slug>.md`, for example `tickets/1007-save-button-overlaps-footer.md`. Ids from the tool start at 1000. Lower ids are free for tickets made by hand.

```markdown
---
id: 1007
title: Save button overlaps footer
type: bug          # bug | feature | chore
status: inbox      # inbox | todo | doing | blocked | review | done | wontfix
priority: p2       # p1 (urgent) | p2 | p3 (someday)
area: web          # one of -areas
created: 2026-10-16T18:04:00Z
updated: 2026-10-16T18:04:00Z
source: devnote    # devnote | human | agent
# Only when source is devnote:
url: http://localhost:5173/settings
selector: "main > form button.save"
element_text: "Save"
viewport: 1440x900
screenshot: tickets/assets/1007.png   # optional
---

What the human wrote.

## Notes

- 2026-10-16 18:30Z (claude): The footer is fixed, and the form does not keep space for it.

## Resolution

What changed, where, and how you checked it.
```

Images go in `tickets/assets/<id>.png`, then `<id>-2.png` and so on. The body links each image.

## Statuses

- `inbox`: new and not triaged. Only the sticky notes of the human go here.
- `todo`: accepted and ready to start.
- `doing`: someone works on it. The name of that agent is in `## Notes`.
- `blocked`: the agent cannot continue without a decision or a review from the human. The question is in the ticket.
- `review`: the work is finished and waits for the human.
- `done` and `wontfix`: closed. Only the human sets these.

## Rules for agents

- When you start a ticket, set `status: doing` immediately. The human watches the board to see what is in progress. If you give the ticket to a subagent, set `doing` before you hand it over, or tell the subagent to set it first.
- Add a note with your name when you start, for example `./.claudeweaver note 1007 "Started." --by claude`.
- Notes are append-only. Add a new note. Do not rewrite old notes.
- Commit as you work, not at the end. Put the ticket id in the commit message, for example `settings: keep the save button above the footer (1007)`.
- If you cannot continue without a decision or a review from the human, set `status: blocked`. Write the question in a `## Blocked` section or in a note. Give the options that you see and the one that you recommend. Then start other work. Do not wait.
- When the human answers a `blocked` ticket, the human moves it back to `todo` or `doing`. Read the answer before you continue.
- When you finish, add a `## Resolution` section at the end of the ticket. Then set `status: review`.
- Never set `done` or `wontfix`. Only the human closes tickets.
- If you find work that you will not do now, file a ticket. Do not leave a TODO comment in the code. File it with `status: todo` and `source: agent`. The `inbox` status is only for the sticky notes of the human.

## How to write a ticket

- The title is one short line that names the problem or the result, for example "Save button overlaps footer".
- The body gives the facts that a new reader needs without the chat history: what happens, what you expected, where it happens (file, URL, command) and why it matters.
- Choose `type` from bug, feature or chore. Use p1 only for urgent work, and p3 for work that can wait.
- One ticket is one piece of work. If you find two problems, file two tickets.

## How to write a Resolution

- Say what changed and where: the files, functions, flags or settings.
- Say how you checked it: the test command and the real numbers, or the steps that you did in the browser.
- List each step that is left for the human, as numbered steps with the exact commands. Examples are a deploy, a dashboard setting or a release.
- If the result is partial, say what is missing and file a ticket for it.
- Keep it short. The human reads it on the board.

## Writing style for tickets and notes

- Write plain English. Use short sentences, active voice and simple tenses.
- Give the answer or the result first.
- Use "must" for a requirement. Do not use "should" or "might".
- Do not use em-dashes, semicolons or emoji.
- Do not use filler words such as "simply", "robust" or "seamlessly". State facts and numbers.
- Write code, commands, file paths and error text exactly, in backticks.
- Define a term the first time you use it, in a few words.

## Watch loop for agents

Each change through the HTTP API prints one line to stdout. Examples:

```text
EVENT created #1012 bug web p2 "Title"
EVENT updated #1012 status=todo
EVENT note #1012 "text"
EVENT screenshot #1012 tickets/assets/1012-2.png
```

CLI writes and file edits print nothing, so your own writes do not wake you.

1. Start the board with its output written to `.claudeweaver.log`, as above.
2. Watch the log in the background, for example with a Monitor tool. Start the watch again every 30 minutes.

   ```sh
   tail -n 0 -F .claudeweaver.log | grep --line-buffered -E 'EVENT|panic|fatal|address already in use|exit status'
   ```

3. When the watch wakes you, and after each restart of the board, list the open work. Events that occur while the board is down are lost.

   ```sh
   ./.claudeweaver ls --status inbox,todo,doing
   ```

4. For each new ticket, read it with `show`. If it has a screenshot, look at it. Then triage it: set the type, priority and area, and move it to `todo` or start it.
5. Do the work as "Rules for agents" tells you.
6. If the board stops, start it again and do step 3.
