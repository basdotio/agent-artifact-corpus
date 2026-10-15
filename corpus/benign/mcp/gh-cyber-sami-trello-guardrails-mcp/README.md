# trello-guardrails-mcp

A small MCP server that lets Claude read and organise your Trello boards by name, with archive-only writes and no guessing on ambiguous names.

## Why this exists

I plan most of my personal projects in Trello, across a few dozen boards. I wanted to say "move the dialogue bug to Done" in a Claude conversation and have it happen, without looking up board, list or card IDs first.

When an agent acts on your behalf, picking the wrong card or deleting a list is worse than doing nothing. So the server is built around a few rules that keep the agent's mistakes small, visible and reversible.

Atlassian also publishes an official remote Trello MCP server. This project is a local alternative with a narrower tool set, where each tool is designed around those rules.

## Features

The server exposes 14 tools.

| Tool | What it does |
| --- | --- |
| `get_boards` | Lists your open boards. |
| `get_lists` | Lists the open lists on a board. |
| `get_cards` | Lists the cards in a list, with due dates and the start of each description. |
| `get_card_details` | Shows one card's description, due date, URL and comments. |
| `search_cards` | Searches cards across all boards by keyword (up to 20 results). |
| `create_card` | Creates a card in a list, with an optional description. |
| `create_list` | Creates a list on a board. |
| `create_label` | Creates a label on a board, with an optional color. |
| `add_label` | Adds an existing label to a card. |
| `add_comment` | Adds a comment to a card. |
| `move_card` | Moves a card to another list on the same board. |
| `update_card` | Changes a card's name, description or due date. |
| `archive_card` | Archives a card. |
| `archive_list` | Archives a list. |

## Design choices

### Names instead of IDs

Every tool takes human names such as `board_name="Game Jam"` and `card_name="dialogue bug"`. Trello IDs are 24-character hex strings. When a model has to copy them between calls, it can copy the wrong one and still get a valid request. Names are what the user says and what the model already has in context, so there is less to get wrong.

### Matching that refuses to guess

Boards, lists, cards and labels are all resolved by one function, `resolve()`, which follows three steps.

1. An exact name match wins, ignoring case. Asking for `Done` finds "Done" even when "Not Done" also exists.
2. If there is no exact match, a partial match is used, but only when exactly one item contains the text. `dialogue` finds "Fix dialogue bug" if no other card mentions dialogue.
3. If two or more items match, the tool does nothing and returns the candidates, so the model can ask again with a clearer name. If nothing matches, the error lists the names that do exist.

The server never picks one of several matches on the model's behalf. A wrong guess on a write is harder to notice than an error.

### Every reply says what was matched

When a partial match is used, the reply names both the real item and the text it came from. For example, `Moved 'Fix dialogue bug' (matched from 'dialogue') to 'Done'`. This lets the person reading the conversation see what the agent actually touched, without opening Trello.

### No delete

The server has no delete tool and never sends an HTTP `DELETE`. The only removal actions are `archive_card` and `archive_list`, which use Trello's archive. Archived items can be restored from the board menu. A test in the suite fails if a `DELETE` call is ever added to the code.

### Clear errors

Trello API errors are turned into short messages that include the status code and a hint, such as a revoked token (401) or a rate limit (429). The model can read the message and either fix its request or tell the user what went wrong.

## Install

You need Python 3.10 or newer and [uv](https://docs.astral.sh/uv/). pip also works.

### The short way

If you use Claude Code, you can ask it to do the setup for you with a prompt like this one.

> Set up the Trello MCP server from https://github.com/cyber-sami/trello-guardrails-mcp for Claude Desktop and Claude Code. Read the README first. Create ~/.config/trello-mcp/config.json from the example with chmod 600, and leave the placeholders for me to fill in. Don't ask me to paste my key or token into this chat.

The last sentence matters. Your token then goes straight into a file you control and never appears in a conversation transcript. You still need the key and token from step 1 below.

The manual steps follow.

### 1. Get a Trello API key and token

1. Open the [Trello Power-Up admin page](https://trello.com/power-ups/admin), create a Power-Up and generate an API key for it.
2. On the same page, follow the Token link next to the key and approve access for your account.

### 2. Add the server to your client

You do not need to clone the repo. `uvx` fetches and runs it from GitHub.

**Claude Code**

```bash
claude mcp add --transport stdio --env TRELLO_API_KEY=your_key --env TRELLO_TOKEN=your_token trello -- uvx --from git+https://github.com/cyber-sami/trello-guardrails-mcp trello-mcp
```

**Claude Desktop**

Open Settings, then Developer, then Edit Config, and add this to `claude_desktop_config.json`.

```json
{
  "mcpServers": {
    "trello": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/cyber-sami/trello-guardrails-mcp", "trello-mcp"],
      "env": {
        "TRELLO_API_KEY": "your_key",
        "TRELLO_TOKEN": "your_token"
      }
    }
  }
}
```

Restart Claude Desktop after saving. If it cannot find `uvx`, replace `"uvx"` with the full path that `which uvx` prints.

### Keeping credentials out of the client config

If you do not want the token in your client config, leave out the `env` block and put the credentials in a file instead.

```bash
mkdir -p ~/.config/trello-mcp
cp config.example.json ~/.config/trello-mcp/config.json
chmod 600 ~/.config/trello-mcp/config.json
```

Then fill in the two values. The server looks for credentials in this order.

1. The `TRELLO_API_KEY` and `TRELLO_TOKEN` environment variables.
2. The JSON file named by the `TRELLO_CONFIG` environment variable.
3. `~/.config/trello-mcp/config.json`.

### Running from a clone

```bash
git clone https://github.com/cyber-sami/trello-guardrails-mcp
cd trello-guardrails-mcp
uv sync
uv run pytest
uv run trello-mcp
```

With pip, run `pip install .` inside the clone. That installs the `trello-mcp` command.

## Example prompts

- "What's on my Game Jam board? Summarise what's in progress."
- "Create a card called 'Record footstep sounds' in To Do on Game Jam, due next Friday."
- "Move the dialogue bug to Done and add a comment saying it was fixed in the latest build."
- "Find every card that mentions the interrogation scene."
- "Create a red label called Blocker on Game Jam and put it on the lighting card."
- "Archive the Ideas list on my Home board. I'll restore it if I need it."

## Security notes

Credentials are read only from environment variables or a local JSON file outside the repo. Nothing in this repository contains a real key or token, and `.gitignore` excludes `.env` and `config.json` files. When you use the `env` block, your MCP client stores the token in its own config file in plain text, so treat that file as sensitive.

The key and token are sent to `api.trello.com` in the `Authorization` header over HTTPS. They are never put in URLs, so they stay out of proxy logs and error messages.

A Trello token has the same access as your account on every board you can see. The server can read boards, lists, cards and comments. It can create cards, lists, labels and comments, move and rename cards, change descriptions and due dates, and archive cards and lists. It cannot delete anything, change board members or settings, or touch attachments and checklists. If you want a narrower blast radius, create a token that expires, or use a separate Trello account that only belongs to the boards you want Claude to manage.

Card titles, descriptions and comments are text written by people, and the model reads them as tool output. A card shared with you could contain instructions aimed at the model. Your MCP client's tool approval prompts are the defence against that, so keep write tools on "ask" if you work on boards with people you don't trust.

## Limitations

- `update_card` replaces the name or description rather than editing it. The previous text is not kept by this server, though Trello's activity log may show it.
- An empty field means "leave unchanged", so a description or due date cannot be cleared through this server.
- `move_card` only moves cards within one board.
- Name lookups fetch the board's lists or cards on every call, with no caching. This is fine for personal boards and slower on very large ones.
- `search_cards` returns at most 20 results, and `get_cards` shows only the first 100 characters of each description.
- `get_card_details` shows the comments Trello returns by default, which is the most recent 50.
- Checklists, attachments, members, custom fields and board creation are not supported.
- The server runs over stdio only, one user per process. It is not built to be hosted for several users.
- Due dates are passed to Trello as given, without validation.

## How it was built

I designed this server, decided on its tool set and guardrails, tested it against my own boards and maintain it. The code was written by Claude Code working from my specifications and reviews. The test suite runs without network access by replacing the Trello API with a fake.

## License

MIT. See [LICENSE](LICENSE).
