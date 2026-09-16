# Documentation Audit Skill

A Claude Code skill for systematic manual documentation validation against actual code behavior.

## Overview

This skill performs manual documentation audits to ensure:
- **Accuracy**: Every claim in documentation matches actual code behavior (90-95% of effort)
- **Completeness**: All features, protocols, and behaviors in code are documented
- **Quality**: Basic formatting/link/spelling checks (5% of effort)

## Philosophy

**No automation, no reports, just validation.**

This skill is about reading documentation, reading code, and verifying they match. It uses simple tools (Read, Grep, Glob) to validate every factual claim in documentation against actual code behavior.

## Quick Start

### With Claude Code

From anywhere in your project, ask Claude:

```
"Run a documentation audit"
"Check if our docs are up to date"
"Validate documentation against code"
```

Claude will:
1. List all documentation files and create TODOs for each section
2. Validate each section by reading docs → reading code → verifying claims
3. Fix documentation directly when inaccuracies are found
4. Check code for undocumented features
5. Summarize findings conversationally

## How It Works

### Forward Pass: Documentation → Code (70% of work)

1. Create TODO for each documentation section that makes factual claims
2. Read documentation section carefully
3. Extract every factual claim (what does the doc SAY?)
4. Use Read/Grep/Glob to find relevant code
5. Verify each claim is accurate
6. Update documentation immediately if wrong

**Example:**
```
Doc claims: "Manager.CreateUserSession() returns error if WebSocket is nil"
→ Read pkg/relay/session/manager.go
→ Find CreateUserSession() method
→ Verify error handling
→ Update doc if behavior differs
```

### Reverse Pass: Code → Documentation (25% of work)

1. Create TODO for each Go package/major file
2. Read the code to understand what it does
3. Identify key features, protocols, state machines, error handling
4. Check if these behaviors are documented anywhere
5. Add documentation for undocumented features

**Example:**
```
Read: pkg/relay/session/manager.go
Find: Clock interface for time dependency injection
Check: Is this pattern documented in docs/TESTING.md?
→ If no, add section explaining the pattern
```

### Quick Quality Checks (5% of work)

Optional automated checks for obvious issues:
- markdownlint for formatting
- Link checker for broken links
- codespell for spelling

These are the LEAST important part of the audit.

## What Gets Validated

### Types of Claims to Check

1. **Existence Claims**
   - "The Manager type provides session lifecycle management"
   - "Use OUROCODUS_ACP_BINARY environment variable"
   - → Verify type/variable exists in code

2. **Behavior Claims**
   - "SpawnAgent() returns error if role already exists"
   - "UserSession progresses through ACTIVE → TERMINATED"
   - → Read code to verify actual behavior

3. **Configuration Claims**
   - "Default port is 8080"
   - "ANTHROPIC_API_KEY is required"
   - → Check default values and validation in code

4. **API/Protocol Claims**
   - "Error messages include 'code', 'message', 'recoverable' fields"
   - "WebSocket endpoint is ws://localhost:8080/ws"
   - → Verify message formats and endpoints

5. **Example Claims**
   - "Run `make build` to compile"
   - Code examples in documentation
   - → Test that commands/examples actually work

## What to Document

**Always Document:**
- Exported APIs (types, functions, methods)
- CLI flags and commands
- Environment variables
- Configuration options
- State machines and transitions
- Error handling patterns
- Non-obvious behavior
- Security considerations

**Skip:**
- Trivial getters/setters
- Self-explanatory private code
- Implementation details
- Internal data structures

## Tools You Use

No special tools needed. Use normal Claude Code capabilities:

- **Read**: Read documentation and code files
- **Grep**: Search for functions, types, patterns
- **Glob**: Find files matching patterns
- **Edit/Write**: Update documentation directly
- **Bash**: Run commands to verify examples

## Output

**DO NOT generate reports.** Instead:
- Update documentation files directly as you find issues
- Keep TODO list updated with progress
- Summarize findings conversationally at the end

## Anti-Patterns

❌ **Don't generate reports** - Update docs directly instead
❌ **Don't build automation** - Just read and validate manually
❌ **Don't focus on linting** - That's only 5% of the work
❌ **Don't batch updates** - Fix docs as you find issues
❌ **Don't skip code reading** - Every claim must be verified

## Configuration

Edit `config.yaml` to customize exclusion patterns:

```yaml
exclusions:
  - "vendor/**"
  - "**/*.pb.go"
  - ".git/**"
  - "node_modules/**"
```

## Example Workflow

```
User: Run documentation audit

Claude:
1. Lists all .md files and creates TODOs for major sections
2. For each section:
   - Reads doc section
   - Extracts factual claims
   - Reads relevant code with Read/Grep/Glob
   - Edits documentation if claims are inaccurate
3. Lists all Go packages and creates TODOs
4. For each package:
   - Reads code files
   - Identifies features/behaviors
   - Checks if documented
   - Adds missing documentation
5. Optionally runs quick automated checks (markdownlint, etc.)
6. Summarizes findings: "Fixed 3 inaccuracies, added 2 missing docs"
```

## Integration

### Pre-commit Hook (Optional)

Add to `.pre-commit-config.yaml` to run linting checks:

```yaml
- repo: https://github.com/markdownlint/markdownlint
  rev: v0.12.0
  hooks:
    - id: markdownlint
      args: ['--config', '.markdownlintrc']
```

Note: This only runs formatting checks, not claim validation. Manual validation must be done by Claude.

## Summary

This skill is intentionally simple:
1. Read documentation → Read code → Verify match → Fix docs
2. Read code → Check if documented → Add missing docs
3. Quick automated checks (least important)

**90-95% of effort is manual reading and validating, not automation.**

## References

- [SKILL.md](SKILL.md) - Complete skill documentation
- [config.yaml](config.yaml) - Configuration reference
