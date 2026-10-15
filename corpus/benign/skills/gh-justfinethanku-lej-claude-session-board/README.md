# LEJ Claude Session Board

A Claude Code skill for running a lot of Claude Code sessions in one project without losing track of them.

One session becomes the **manager**. Every other session in the project folder reports to it: when it starts something, when it needs you, before it touches shared code or deploys, and when it's done. The manager keeps one page current, the **LEJ Session Board**. It's a local HTML file in your project folder that reloads itself every minute:

- **An overview up top:** a paragraph on what's happening now and one on what already happened.
- **A collapsed section per open session:** its title and what it needs from you. Urgent sessions come first, then ones with questions, then the rest. Click to open its state, where it stands and its questions.
- **Recommended answers:** each question has two or three options, one marked Recommended, plus **Write your own answer**. Copy puts the session's name and `Re: <question>` above your reply, so the manager knows where it goes. Paste it in the session, or paste a batch back to the manager and it relays each one. **Copy all answers** answers a whole session in one paste.
- **The to-do list:** collapsible groups by who acts. Your-call items come with recommended answers too. Every item Claude can build has a numbered starter prompt (`PRJ5 Short name`) to copy into a new session, title included.
- **Question counts and copy marks:** the header says how many questions need you, and each Copy button turns into "✓ Copied" once used.
- **It stays current on its own:** every answer you copy for a session ends with a line asking it to tell the manager once it's acted. The manager also sweeps every session every 15 minutes, and if nobody has checked in 30 minutes the board says "Out of date" in red.

The manager also keeps the deploy queue (one deploy at a time, best enforced by a lock and queue file in your deploy script so sessions don't wait on manager messages), hands out migration numbers, keeps session titles in the `PRJ5 Short name` pattern, and catches overlaps between sessions.

It uses Claude Desktop's session tools, so it runs in the **Code tab of the Claude desktop app**.

**Local page vs. artifact:** the board is a local file by default (`LEJ Session Board.html` in your project folder). It can also be published as a claude.ai artifact so you can open it on your phone. Artifact publishes have a daily cap per account, which a busy manager hits by mid-afternoon, so the skill publishes only when you ask and never more than every 15–20 minutes.

## Watch it

A three-minute video of the whole loop (install, make a manager, read the board, answer, start new work), plus a step-by-step guided setup: **[limitededitionjonathan.com/session-board](https://limitededitionjonathan.com/session-board)**. The project in the video is made up; its board data is `assets/demo-data.json`.

## Install

```bash
git clone https://github.com/justfinethanku/lej-claude-session-board.git ~/.claude/skills/lej-session-board
```

Then in a Claude Code desktop session in your project folder, say something like "be the manager for this folder and make me a session board", or "which of my sessions are stale?"

## What's inside

| Path | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows: roster, hub setup, building the board, keeping it current. |
| `assets/board-template.html` | The board page, rendered from a JSON block. Example data included. |
| `scripts/build_local.py` | Turns the filled template into a standalone page that auto-reloads (60 s, and not while you're typing). |
| `assets/demo-data.json` | The made-up "Pantry" board from the video, with every feature filled in. |
| `references/data-schema.md` | The JSON fields the page reads. |
| `references/coordination-rule.md` | The `CLAUDE.md` block that makes sessions report to the manager. |
| `references/sweep.md` | The 15-minute sweep the manager schedules to keep the board true. |

## Look

LEJ branding: Bricolage Grotesque, Hanken Grotesk and JetBrains Mono. Terracotta on soft white, with charcoal text and a matching dark mode. Color marks only what needs you and the main actions.

Made by Jonathan Edwards ([Limited Edition Jonathan](https://limitededitionjonathan.com)).

## License

MIT. See [LICENSE](LICENSE).
