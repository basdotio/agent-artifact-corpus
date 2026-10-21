---
name: find
description: Finds one of the user's published pages by a few words and hands back its link, so this session can open or update that page instead of making a new one. Use when the user asks where a page is, wants to continue or update an earlier artifact, or says "the pricing page", "that dashboard", "my launch checklist".
---

# Find a page

The user has a list of every page they published: `~/.claude/artifact-hub/pages.json`
(written by the plugin at each publish: `url`, `title`, `folder`, `first`, `last`, `was`
for the earlier titles of a renamed page, and `deleted` or `replacedBy` when that
happened), and a Project Hub whose link is `hubUrl` in `~/.claude/artifact-hub/hub.json`,
with a row per page (`[title, id, description, date]` between `HUB-DATA-START` and
`HUB-DATA-END`; a fifth item may hold `was`, the earlier titles).

1. Take the words the user gave. Look in `pages.json` first (titles, earlier titles in
   `was`, and folders), then in the hub's rows (titles, earlier titles and descriptions)
   if the hub exists. A page found by an earlier title is the same page: answer with its
   current title and say what it used to be called. Match loosely: any of
   the words, any case, partial words. If neither file exists, say the plugin has not
   recorded a page yet and point to the `setup` skill.
2. Skip entries marked `deleted`. For an entry with `replacedBy`, prefer the newer page it
   points to and mention the older link exists.
3. One match: answer in one line with the title, its folder and the full link, and ask
   whether to open it (`Artifact` `action: "open"`) or to read it (`action: "read"`) so
   the next publish goes to the same URL. Never publish without `url` when the user means
   this page: that makes a second page.
4. Several matches: list them (title, folder, date), newest first, at most ten, and ask
   which one. More than ten: say how many and ask for another word.
5. None: say so, and offer a rebuild (`hub` skill) in case the page was never filed.

Do not open or read a page the user did not pick, and do not change the hub here.
