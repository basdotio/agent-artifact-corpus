# obsidian-guarded-mcp

A local MCP server that lets Claude read, search and edit notes across several Obsidian vaults, with guardrails around every file operation.

## Why this exists

I keep a lot of Obsidian vaults. One is my main notes vault, and most of my projects have their own vault. I wanted Claude Desktop and Claude Code to work in those notes directly, so they could read a spec, update a task list or file meeting notes where they belong.

The existing Obsidian MCP servers I looked at either go through the Obsidian Local REST API plugin, which means Obsidian has to be running, or point at a single vault. I wanted something that works on the plain Markdown files, can switch between vaults by name, and is careful about what an AI agent is allowed to do to notes I care about. This server is about 400 lines of Python and has no dependencies beyond `fastmcp` and `python-frontmatter`.

## Features

The server exposes 12 tools.

**Vault management**

| Tool | What it does |
|---|---|
| `list_vaults()` | Lists every configured vault and marks the active one. |
| `get_active_vault()` | Returns the name and path of the active vault. |
| `switch_vault(name)` | Makes another configured vault active until the server restarts. |

**Notes** (all operate on the active vault)

| Tool | What it does |
|---|---|
| `read_note(path)` | Returns a note's body and its parsed YAML frontmatter. |
| `write_note(path, content, mode, frontmatter_data)` | Writes a note in `overwrite`, `append` or `prepend` mode, creating folders as needed. |
| `patch_note(path, old_string, new_string, replace_all)` | Replaces an exact string in a note without rewriting the rest of it. |
| `list_notes(subfolder)` | Lists all Markdown notes, optionally limited to one folder. |
| `search_notes(query, limit)` | Case-insensitive search over filenames and content, returning path, line number and an excerpt. |
| `get_frontmatter(path)` | Returns only the frontmatter of a note. |
| `update_frontmatter(path, updates, merge)` | Changes frontmatter keys and leaves the body untouched. |
| `delete_note(path, confirm_path)` | Moves a note into the vault's `.trash/` folder. It never deletes a file. |
| `get_vault_stats()` | Returns note count, folder count, total size and the five most recently modified notes. |

Every note tool includes a `"vault"` key in its response, so the model always knows which vault it just acted on.

## Design choices

**Every path is checked against the active vault.** Paths are resolved to their real location, following `..` and symlinks, and anything that ends up outside the vault root is rejected with an error. Listing and search skip symlinked files that point outside the vault, so they cannot be used to get around that check. An agent that builds a bad path, or is tricked into trying `../../.ssh/id_rsa`, gets an error instead of a file.

**Only Markdown, and never the hidden folders.** Tools accept only `.md` and `.markdown` files. Any path with a component starting with a dot (`.obsidian`, `.git`, `.trash`) is excluded from listing and search and refused by the read and write tools. That keeps the agent away from Obsidian's own settings, plugin code and version control.

**Delete moves notes to the trash.** `delete_note` moves the note to `.trash/` inside the vault and keeps its folder structure, which is the same folder Obsidian uses for its own trash. If a note with that name is already in the trash, the new one gets a timestamp suffix, so nothing is overwritten. A wrong delete is a file move to undo, not a restore from backup.

**Deletion asks for the path twice.** `delete_note` requires `path` and `confirm_path` to be identical. This is not real authorization, since the model fills in both. It is a speed bump. It forces the model to state the target explicitly twice, which catches truncated or malformed arguments, and it makes the intent obvious in the tool call the user approves.

**Edits are exact and counted.** `patch_note` fails if the search string is not found, and also fails if it matches more than once unless `replace_all` is set. The agent can't silently edit the wrong paragraph because its string was less specific than it thought. This is the same contract Claude Code's own file editing uses, so models already handle it well.

**Frontmatter has its own tools.** Changing a `status` or `tags` field should not mean rewriting the note body. `update_frontmatter` merges keys by default and leaves the content as it was.

**Vaults are chosen by name.** The model works with short names like `notes` or `side-project` from a config file, not absolute paths. Switching vaults is an explicit tool call, and each response names the vault it used, which makes mistakes visible in the transcript.

## Install

You need Python 3.10 or newer.

### Let Claude Code set it up

This is how I install it on a new machine. Open Claude Code in the folder where you keep your projects and paste this prompt.

```text
Clone https://github.com/cyber-sami/obsidian-guarded-mcp and set it up for me
by following its README. Install the dependencies with uv (or pip if uv is not
available) and run the tests. Then ask me for the names and paths of my Obsidian
vaults and create vaults.json from them. Check that each path exists and
contains a .obsidian folder. Finally, register the server with Claude Code and,
if I use it, Claude Desktop. Back up any config file before you edit it, and keep
the servers that are already in it.
```

Claude Code will ask for approval before running commands and editing files, so you can follow each step. If you'd rather do it by hand, the steps are below.

### Manual install

With [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/cyber-sami/obsidian-guarded-mcp.git
cd obsidian-guarded-mcp
uv sync
```

With pip:

```bash
git clone https://github.com/cyber-sami/obsidian-guarded-mcp.git
cd obsidian-guarded-mcp
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Run the tests to check the install. They create temporary vaults and never touch your real ones.

```bash
uv run test_server.py
```

With pip, run `venv/bin/python test_server.py` instead. You should see `56/56 passed`.

## Configuration

Copy the example config and add your vaults.

```bash
cp vaults.example.json vaults.json
```

```json
{
  "default": "notes",
  "vaults": {
    "notes": "/Users/you/Documents/Obsidian Vault",
    "side-project": "~/Projects/side-project/vault"
  }
}
```

Names are what Claude will use to switch vaults. Paths may contain spaces and may start with `~`. The `default` vault is active whenever the server starts.

`vaults.json` is gitignored. To keep the config somewhere else, set `OBSIDIAN_MCP_CONFIG` to the full path of your config file.

### Claude Desktop

Edit `claude_desktop_config.json`. On macOS it is in `~/Library/Application Support/Claude/`, and on Windows it is in `%APPDATA%\Claude\`. Use absolute paths.

With uv:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/obsidian-guarded-mcp", "run", "server.py"]
    }
  }
}
```

With pip:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "/absolute/path/to/obsidian-guarded-mcp/venv/bin/python",
      "args": ["/absolute/path/to/obsidian-guarded-mcp/server.py"]
    }
  }
}
```

To use a config file outside the repo, add `"env": {"OBSIDIAN_MCP_CONFIG": "/path/to/vaults.json"}` to the entry. Fully quit and reopen Claude Desktop after any change to this file or to `vaults.json`.

### Claude Code

```bash
claude mcp add obsidian --scope user -- uv --directory /absolute/path/to/obsidian-guarded-mcp run server.py
```

Or add it to a project's `.mcp.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/obsidian-guarded-mcp", "run", "server.py"]
    }
  }
}
```

Then check that it connected with `claude mcp list`, or with `/mcp` inside a session.

## Example prompts

- "Which vaults do you have access to? Switch to side-project and summarize the notes in the Research folder."
- "Search my notes for everything about the onboarding flow and list the open questions."
- "Append today's standup notes to Meetings/2026-09.md under a new heading."
- "In Tasks.md, mark 'draft launch checklist' as done."
- "Set status to archived in the frontmatter of every note in Ideas/Old."
- "Find notes that haven't got a tags field and suggest tags for them. Don't change anything yet."
- "Delete Drafts/untitled 3.md." (The note ends up in the vault's `.trash/` folder.)

## Security notes

The server holds no credentials and makes no network requests. It runs locally over stdio, as the user who started it, with that user's file permissions.

The only configuration is `vaults.json` (or the file named by `OBSIDIAN_MCP_CONFIG`). It holds vault names and paths, and it is gitignored.

What the server can touch is Markdown files inside the configured vault folders, excluding any dot-prefixed folder. What it cannot touch is anything outside those folders, any non-Markdown file, and Obsidian's `.obsidian` config. There are no shell calls and no `eval` anywhere in the code.

Keep two things in mind. `list_vaults` and `get_active_vault` return the absolute paths of your vaults, so the model and the conversation will contain them. And `write_note` in `overwrite` mode can replace a note's entire content. Only deletion goes through the trash, so keep your vault under version control or sync if that matters to you.

## Limitations

- The active vault is global to the server process. Two conversations sharing one server process share one active vault, and it resets to the default on restart.
- Search is a plain substring scan. It returns the first matching line per note, reads every file on every query, and has no regex, tag, link or ranking support beyond putting filename matches first. It is fine for vaults with a few thousand notes and would be slow for very large ones.
- There is no tool for renaming or moving notes, and nothing updates `[[wikilinks]]` when a note changes.
- Attachments, canvases and other non-Markdown files are not accessible.
- `update_frontmatter` re-serializes the YAML, which can change quoting, key order or comments in the frontmatter block.
- There is no file locking. If you edit a note in Obsidian while Claude writes to it, the last write wins.
- Nothing empties `.trash/`. Clean it up yourself or through Obsidian.
- The test suite is a single script, not a pytest suite. It has been run on Linux and macOS. Windows is untested.

## How it was built

I designed the tool set, the safety rules and the config format, and I tested and maintain the server. The code was written by Claude Code from those specifications, and each change was reviewed against the test suite before I used it on my own vaults. I use it most days with Claude Desktop and Claude Code.

## License

[MIT](LICENSE)
