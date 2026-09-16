---
name: codex
description: **Use this in every interaction** for validating implementation plans and todos, brainstorming before coding, creating TodoWrite todos for checklists, and reviewing work for completeness, clarity, and alignment with design goals - describes Codex cli usage including non-interactive exec mode, prompting guardrails, and operational checklists for reliable Codex sessions
---

# OpenAI Codex

OpenAI Codex CLI is an open-source command-line coding agent that runs locally, providing AI-powered code generation, debugging, and task automation directly in the terminal. It uses advanced reasoning models (GPT-5-Codex by default) to read, modify, and execute code in the local environment.

## Critical Operating Requirements

**Always use these five requirements together:**

1. **Information gathering** - Codex should be used to understanding how things work, the root cause for why things are happening in specific ways, validating feedback to the user as a peer/second pair of eyes to confirm assumptions
2. Include at the end of any prompt: "Do not make any modification to the codebase"
3. **Non-interactive exec mode** - Use `codex --yolo exec --skip-git-repo-check -o ./specs/logs/codex-$(date +%Y-%m-%d-%H%M)-<spec-slug>.md "<task>"` for automation, logging and session resumption

## Best Practices

### Prompting Techniques

1. Be specific: Include programming language, constraints, or optimization goals

- Good: “Create a Python REST API with FastAPI, include rate limiting”
- Poor: “Make an API”

2. Provide context: Reference specific files, functions, or requirements

- Good: “Add authentication middleware to routes.js using JWT”
- Poor: “Add auth”

3. Use constraints: Specify frameworks, style guides, or performance requirements

- Good: “Refactor using functional programming, optimize for speed”
- Poor: “Make it better”

## Exec Mode (Non-Interactive)

Use codex exec for invocations. This mode runs without interactive prompts and streams results to stdout.

## Availability

Install via Homebrew:

```bash
brew update && brew upgrade codex
```

## Permission Errors

Network Access

Ensure one of:

- Proper configuration in ~/.codex/config.toml

Git Repository Requirement

```bash
codex --yolo exec --skip-git-repo-check "task"
```

## Summary

Every Codex operation should: 1. Use codex exec (not interactive mode) 2. Log output to file 3. Support session resumption with resume --last
