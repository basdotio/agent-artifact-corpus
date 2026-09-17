---
name: claude-code
description: Consult Claude Code CLI for AI-assisted coding advice and code generation
license: MIT
compatibility: opencode
---

## What I do
Provide consultation with Anthropic's Claude Code CLI, a powerful coding assistant that can help with code generation, debugging, refactoring, and understanding complex codebases.

## When to use me
Use this skill when you need expert coding assistance from Claude Code, such as:
- Generating code snippets or functions
- Debugging complex issues
- Refactoring code
- Understanding unfamiliar code patterns
- Getting AI-powered coding suggestions

## How to consult Claude Code
1. Ensure Claude Code is installed: Follow installation instructions at https://code.claude.com/docs/en/quickstart
2. Run the CLI with your query: `claude "your coding question or task"`
3. For non-interactive queries: `claude -p "your question"`
4. You can also pipe content: `cat file.txt | claude -p "analyze this code"`

## Examples
- `claude "write a React component for a todo list"`
- `claude -p "explain this Python function"`
- `cat error.log | claude -p "what does this error mean?"`

## Best practices
- Be specific in your queries for better results
- Include relevant code context when possible
- Use the interactive mode (`claude`) for multi-turn conversations
- Use `-p` flag for quick, one-off consultations