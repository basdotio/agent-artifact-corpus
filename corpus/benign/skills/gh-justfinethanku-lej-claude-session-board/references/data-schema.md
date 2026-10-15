# Board data schema

The board page renders from the JSON in `<script type="application/json" id="board-data">`. Edit this block and rebuild the local page; the markup doesn't change.

```json
{
  "updated": "Monday, Oct 5, 2026, 4:30 pm ET (from `date`, never estimated)",
  "updatedISO": "2026-10-05T20:30:00Z (from `date -u +%Y-%m-%dT%H:%M:%SZ`; set on every rebuild)",
  "reportBack": "Optional. The line added to every answer copied for a session. Leave it out for the default.",
  "projectFolder": "~/code/my-project",
  "manager": "Project Manager",
  "overview": "One or two short paragraphs, split by a blank line: what's happening now, then what already happened.",
  "todoIntro": "One or two sentences above the to-do list.",
  "sessions": [ Session, ... ],
  "groups": [ Group, ... ]
}
```

`updatedISO` drives the red "Out of date" line: the page shows it once the stamp is 30 minutes old, and keeps it current without a reload. Set it on every rebuild, even when nothing else changed, because a sweep that found nothing new still counts as a check.

`reportBack` is added, after a blank line, to the end of every **Copy** and **Copy all answers** for a session's question. The default is "When you've acted on this, send the <manager> session a one-line update with SendMessage: what you did and what's next." Answers whose header is the manager (the manager's own questions and to-do questions) don't get it, and neither do pastes or starter prompts.

## Session

| Field | Meaning |
|---|---|
| `id` | Short stable id, such as `prj2`. |
| `name` | The session's title, exactly as it appears in the sidebar (`<PREFIX><n> <short name>`). Copy headers use it, so update it whenever a session is renamed. |
| `need` | The subtitle the collapsed section shows: what the session needs from the user, in a few words ("Your go typed in PRJ4"). Leave it out and the page says how many questions need the user, or "Nothing needed from you". |
| `urgent` | Optional `true`. Puts the section first and prefixes the subtitle with "Urgent:". Use it for what blocks other work or what the user is waiting on today. |
| `isManager` | Optional `true` on the manager's own entry. The `overview` replaces its where-it-stands lines, so the page shows the entry only when it holds questions or pastes. |
| `state` | One line inside the section: what it's doing, or what it needs. |
| `tone` | `"needs"` (terracotta, waiting on the user), `"done"` (green), or `""`. |
| `where` | Two to four plain lines on where it stands. Plain text, escaped on render. |
| `questions` | Zero or more `Question`s. The page counts them itself: a total in the header, and a count at the top of each open section. |
| `actions` | Optional. Steps only the user can do (a key, a setting, a click, SQL): `[{ "id", "title", "why"?, "link"?, "linkText"?, "steps": [..], "text"?, "textTo"? }]`. Each renders inside the section with its link, numbered steps, any text to copy, and a **Copy "done"** for the manager. Put everything needed to do it here, so the user never goes to another section. |
| `backlog` | Optional. The workstream's open to-do items (trusted HTML strings), shown as a collapsed "Backlog (n)" list in the section. Use it in place of a separate to-do group per workstream. |
| `reminders` | Optional. Things the user asked to be reminded of: `[{ "text", "when"? }]`. They render as a Reminders list inside the section, with no options and no Copy, because a reminder isn't a question. The manager's entry shows when it holds reminders, even with no questions. |
| `pastes` | Optional. Ready-made text the user pastes somewhere else, such as a prompt for another machine: `{ "id", "title", "to", "note"?, "text" }`. It shows as an editable block, and Copy puts the text alone, with no header. |

Sections start collapsed to the title and `need` line, and open on click. The page orders them: `urgent` first, then sessions with questions, pastes or `tone: "needs"`, then the rest, keeping the data's order within each group. A section the viewer opens stays open across reloads.

## Question

| Field | Meaning |
|---|---|
| `id` | Unique and stable. The page keys the user's pick, edits and copied state on it. Change it when the question changes. |
| `to` | Where the reply gets pasted, such as `"PRJ2"` or `"PRJ2 (type the go there yourself)"`. |
| `title` | The question. Copy puts the session's `name`, then `Re: <title>`, then the reply. When a session has two or more questions, a **Copy all answers** button under the last one copies the `name` once, then `Re: <title>` and the reply for each question, separated by blank lines. |
| `note` | Optional context. Keep it under three lines. |
| `options` | Two or three `{ "label", "text", "rec" }`. `label` is what the user reads, `text` is the full reply the session gets, and `rec: true` marks the recommended option, which is selected by default. The page adds a last option, **Write your own answer**, which empties the reply box for the user's own words and keeps them. |

## Group

| Field | Meaning |
|---|---|
| `title` | For example "Your call", "Other people", "Claude builds", "Later". |
| `items` | `{ "text", "question"?, "starter"? }`. `text` may hold `<b>` and `<code>` and is trusted HTML, so write it yourself. Give every item in the user's-call group a `question` (same shape as above, `to` the manager): the page renders it under the item with options, Write your own answer and Copy, and Copy's first line is the manager's name. |

Each group starts collapsed to its title and item count (plus how many starter prompts it holds), and remembers being opened.

`starter` is `{ "title": "PRJ5 Short name", "prompt": "<context>…</context>\n\n<instructions>…</instructions>\n\n<output>…</output>" }`. The page shows the title above an editable prompt. Copy puts the title, a blank line, then the prompt.

## What the viewer's browser keeps

The option picks, edited replies, edited prompts and "✓ Copied" marks stay in the viewer's browser (localStorage, keyed by id), so a rebuild doesn't wipe them. Open sections and groups are remembered the same way. Give a question a new `id` when its wording changes, so an old edit doesn't stick to it.
