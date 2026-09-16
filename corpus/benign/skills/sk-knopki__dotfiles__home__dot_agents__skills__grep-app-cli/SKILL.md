---
name: grep-app-cli
description: "Search public GitHub code with the grep.app MCP CLI to find real implementation patterns, concrete API usage, regex-based code matches, and repository-scoped examples. Use when a task needs literal code search rather than documentation search, especially to verify how libraries, frameworks, config files, or language features are used in real projects."
license: MIT
compatibility: Requires uv and access to the internet
allowed-tools: Bash(uv run --with fastmcp python ./scripts/grep-app-mcp.py:*) Bash(sh ./scripts/grep-app-mcp.sh:*)
metadata:
  author: knopki <knopki@duck.com>
  version: "1.0.1"
  hermes:
    category: research
    complexity: intermediate
    icon: 🔍
    tags:
      - code-search
      - github
      - mcp
      - grep.app
    requires_toolsets:
      - terminal
---

# grep.app CLI

Use this skill to query `mcp.grep.app` from the terminal and inspect
real code from public repositories.

## Workflow

1. Translate the user's need into a literal code pattern that would
   actually appear in source files.
2. Start with the narrowest useful query.
3. Add filters for `--language`, `--repo`, or `--path` before
   broadening the pattern.
4. Use `--use-regexp` only when a literal string is too restrictive.
5. Summarize the returned pattern and why it is relevant instead of
   dumping raw matches.

## Query Design

- Search for code, not topics.
- Prefer tokens such as `useState(`, `getServerSession`, `CORS(`,
  `server.listen(`, `FROM node:`, or `name: ci`.
- Avoid natural-language queries such as `react auth example` or
  `python cors tutorial`.
- Keep the first pass short and exact; broaden only if the result set is
  empty or obviously too narrow.

## Filter Strategy

- Use `--language` when syntax or framework usage is language-specific.
- Use `--repo` when the user asks about a known project, organization, or ecosystem.
- Use `--path` when the pattern is expected in files like
  `package.json`, `Dockerfile`, `.github/workflows/`, or `/route.ts`.
- Combine filters before switching to regex. Narrowing scope is usually
  cheaper than making the pattern more complex.

## Regex Guidance

- Add `--use-regexp` for flexible patterns, optional spacing, or
  multi-line matches.
- Prefix with `(?s)` when the match may span line breaks.
- Escape regex metacharacters when the intent is literal punctuation.
- Prefer targeted regex such as
  `(?s)useEffect\\(\\(\\) => \\{.*removeEventListener` over overly broad
  `.*` searches with no anchors.

## Commands

Resolve paths from the skill directory when invoking the bundled script.

```bash
cd skills/grep-app-cli
sh ./scripts/grep-app-mcp.sh list-tools
```

```bash
cd skills/grep-app-cli
sh ./scripts/grep-app-mcp.sh call-tool searchGitHub \
  --query "useState(" --language TSX --language TypeScript
```

```bash
cd skills/grep-app-cli
sh ./scripts/grep-app-mcp.sh call-tool searchGitHub \
  --query "(?s)try \\{.*await" --use-regexp --language Python
```

## Supported Operations

- `list-tools`
- `list-resources`
- `read-resource <uri>`
- `list-prompts`
- `get-prompt <name> [key=value ...]`
- `call-tool searchGitHub --query <pattern> [filters...]`

## searchGitHub Flags

- `--query`: required literal code pattern or regex.
- `--match-case`: use for case-sensitive identifiers or formats.
- `--match-whole-words`: use when partial identifier matches create noise.
- `--use-regexp`: enable regex interpretation.
- `--repo`: restrict to a repository or org fragment such as `vercel/`.
- `--path`: restrict to a file path or fragment such as `/route.ts`.
- `--language`: repeatable language filter such as
  `--language TypeScript --language TSX`.

## Output Expectations

- Explain what pattern was searched and why.
- Call out any filters that materially shaped the result.
- Distinguish direct matches from your inference about best practice.
- Mention when results are sparse, noisy, or biased toward a specific
  ecosystem.

## Limits

- Treat grep.app as a source of implementation examples, not as
  authoritative documentation.
- Do not claim a pattern is recommended solely because it appears in public repositories.
- Prefer official docs when the task depends on guarantees, specs, or
  version-specific behavior.
