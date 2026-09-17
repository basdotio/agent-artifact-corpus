---
name: code-review
description: Comprehensive code review following industry standards and best practices. Use when reviewing code for quality, security, performance, maintainability, or architectural issues. Covers all programming languages (Python, JavaScript/TypeScript, C#, Java, Rust, Go, C/C++, etc.), frontend frameworks (React, Vue, Angular, Vite), backend frameworks (FastAPI, Flask, Express, Spring, ASP.NET), SOLID principles, microservices architecture, security vulnerabilities (OWASP), and performance optimization. Invoke with `/skill:code-review` or when user asks to review code, PR, diff, or wants feedback on implementation.
---

# Code Review

Perform thorough code reviews following industry standards. This skill provides a structured approach to reviewing code across all languages and frameworks.

## PR Review Scope (CRITICAL)

**IMPORTANT**: When reviewing a Pull Request (PR), focus ONLY on the changes introduced in that PR.

### The Golden Rule: Diff Only

**DO NOT read entire files.** Only analyze the git diff output. The diff contains everything you need:
- `+` lines = additions (review these for correctness)
- `-` lines = deletions (verify safe to remove)
- Context lines = for understanding only (do NOT review these for issues)

### PR Review Workflow

1. **Get the diff ONCE**: Run `git diff base...HEAD` or `git diff main...HEAD`
2. **Parse the diff output**: Identify changed files and changed lines
3. **Review ONLY the diff**: Do not use ReadFile to read entire files
4. **If you need more context**: Read only the specific function/class from the diff, not the whole file

### What to Analyze

| Type | Review Scope |
|------|--------------|
| New file added | Review entire file (it's all new code) |
| Existing file modified | Review ONLY `+` and `-` lines, use context lines for understanding |
| File deleted | Verify no breaking dependencies |
| Renamed/moved file | Verify imports updated, no logic changes unless shown in diff |

### What NOT to Do

- **Do NOT read entire files** to "understand the codebase"
- **Do NOT search for usages** across the codebase
- **Do NOT flag issues in unchanged code** (context lines)
- **Do NOT suggest refactoring** unrelated code
- **Do NOT explore related files** not in the diff
- **Do NOT make assumptions** about code you haven't seen in the diff

### Handling Limited Context

If the diff doesn't provide enough context to determine if code is correct:
1. **Ask the author** rather than guessing
2. **Flag as "needs clarification"** rather than a definite issue
3. **Trust the existing code** - if it worked before and wasn't changed, don't assume it's broken

### Example: Correct PR Review Behavior

```
# CORRECT: Use git diff only
git diff main...HEAD --stat           # List changed files
git diff main...HEAD -- path/to/file  # Get diff for specific file

# Review the + lines in the diff output
# Do NOT run: cat path/to/file or ReadFile(path/to/file)
```

## Review Process

### 1. Understand Context First

Before reviewing:
- Identify the programming language(s) and framework(s) used
- Understand the purpose of the change (bug fix, feature, refactor)
- Check if there are existing project conventions (AGENTS.md, .editorconfig, linters)
- Note the scope: single file, module, or cross-cutting change
- **For PRs**: Read the PR title and description to understand intent

### 2. Review Checklist (Priority Order)

Review in this order - stop and report critical issues immediately:

#### Critical (Blocking)
1. **Security vulnerabilities** - See [references/security.md](references/security.md)
2. **Data integrity risks** - Race conditions, data loss, corruption
3. **Breaking changes** - API contracts, backward compatibility

#### High Priority
4. **Logic errors** - Off-by-one, null handling, edge cases
5. **Error handling** - Exceptions, error propagation, recovery
6. **Resource management** - Memory leaks, connection pools, file handles

#### Standard
7. **Architecture & Design** - See [references/architecture.md](references/architecture.md)
8. **Performance** - See [references/performance.md](references/performance.md)
9. **Code quality** - Readability, naming, duplication
10. **Testing** - Coverage, edge cases, test quality

### 3. Language-Specific Review

Load the appropriate reference based on the language:
- **Python**: See [references/python.md](references/python.md)
- **JavaScript/TypeScript**: See [references/javascript.md](references/javascript.md)
- **C#/.NET**: See [references/csharp.md](references/csharp.md)
- **Java**: See [references/java.md](references/java.md)
- **Rust**: See [references/rust.md](references/rust.md)
- **Go**: See [references/go.md](references/go.md)
- **C/C++**: See [references/cpp.md](references/cpp.md)

### 4. Framework-Specific Review

Load based on the framework:
- **Frontend (React, Vue, Angular, Vite)**: See [references/frontend.md](references/frontend.md)
- **Backend (FastAPI, Flask, Express, Spring, ASP.NET)**: See [references/backend.md](references/backend.md)

## Review Output Format

Structure feedback with **specific file locations and actionable solutions**:

```markdown
## Code Review Summary

**PR/Change Description**: [Brief description of what this PR does]
**Files Changed**: [Count of files]
**Overall Assessment**: [APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]

### Files Reviewed

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `src/Controllers/UserController.cs` | Modified | +45, -12 |
| `src/Services/UserService.cs` | Added | +120 |
| `tests/UserTests.cs` | Modified | +30, -5 |

---

### Critical Issues (Blocking)

#### 1. [Issue Title]
- **File**: `src/Controllers/UserController.cs:45-52`
- **Problem**: [Clear description of what's wrong]
- **Impact**: [What could go wrong - security breach, data loss, crash, etc.]
- **Solution**:
  ```csharp
  // Replace this:
  var result = user.Value.Property;  // Null dereference risk

  // With this:
  if (user?.Value != null)
  {
      var result = user.Value.Property;
  }
  ```

---

### High Priority

#### 1. [Issue Title]
- **File**: `src/Services/NotificationService.cs:123`
- **Problem**: [Description]
- **Impact**: [Consequence]
- **Solution**: [Specific fix with code example if helpful]

---

### Suggestions

#### 1. [Suggestion Title]
- **File**: `src/Models/User.cs:15`
- **Current**: [What exists now]
- **Suggested**: [What would be better and why]

---

### Questions / Needs Clarification

#### 1. [Topic]
- **File**: `src/Services/SomeService.cs:45`
- **Change**: [What was changed]
- **Concern**: [Why you're unsure]
- **To confirm**: [What information would resolve this]

---

### Positive Notes

- **Good pattern in `src/Services/AuthService.cs`**: [What was done well]
- **Clean implementation of X**: [Reinforce good practices]
```

### When to Use "Questions" vs "Issues"

| Use "Issues" when... | Use "Questions" when... |
|---------------------|------------------------|
| The diff clearly shows a bug | You suspect an issue but can't confirm from diff |
| The problem is in the `+` lines | The concern relates to unchanged context |
| You can provide a concrete fix | You need more information to suggest a fix |
| Impact is clear from the code | Impact depends on runtime behavior you can't see |

### Issue Format Requirements

Each issue MUST include:
1. **Exact file path and line number(s)**: `file.cs:42` or `file.cs:42-50` (from the diff output)
2. **The actual changed code**: Quote the `+` line from the diff
3. **Problem statement**: What is wrong with THIS change
4. **Impact/Risk**: Why it matters (crash, security, data loss, perf)
5. **Concrete solution**: Code snippet showing the fix

**BAD Example** (vague, no code reference):
```
Null dereference risk in readiness queries
- ReadinessController: nextInvoiceDate.Value.Year/Month is used even when BillingDay is null
```

**GOOD Example** (specific, actionable):
```
#### 1. Null Dereference in nextInvoiceDate Access

- **File**: `ReadinessController.cs:87` (line added in this PR)
- **Changed Code**:
  ```csharp
  + let nextInvoiceYear = nextInvoiceDate.Value.Year,
  ```
- **Problem**: `nextInvoiceDate` is null when `BillingDay` is null, but `.Value` is accessed unconditionally
- **Impact**: `NullReferenceException` crashes the endpoint for buildings without billing config
- **Solution**: Guard the access:
  ```csharp
  let nextInvoiceYear = nextInvoiceDate.HasValue ? nextInvoiceDate.Value.Year : (int?)null,
  ```
```

### Line Numbers Must Come From The Diff

- The line number should be the one shown in the diff hunk header (`@@ -old,count +new,count @@`)
- Do NOT read the full file to find the "real" line number
- If the diff shows `@@ -80,10 +85,15 @@`, the new lines start at 85

## Quick Reference: Universal Code Smells

Always flag these regardless of language:

### Complexity
- Functions > 50 lines or cyclomatic complexity > 10
- Deeply nested conditionals (> 3 levels)
- God classes/functions doing too many things
- Circular dependencies

### Naming
- Single-letter variables (except loop indices)
- Misleading names (e.g., `data`, `temp`, `result` without context)
- Inconsistent naming conventions
- Abbreviations that aren't universally understood

### Duplication
- Copy-pasted code blocks
- Similar logic that could be abstracted
- Magic numbers/strings repeated

### Comments
- Commented-out code (should be deleted)
- Comments explaining "what" instead of "why"
- Outdated comments that don't match code
- Missing comments for complex algorithms

### Error Handling
- Empty catch blocks
- Swallowing exceptions without logging
- Generic error messages hiding root cause
- Missing validation at system boundaries

## Quick Reference: SOLID Violations

| Principle | Violation Signs |
|-----------|-----------------|
| **S**ingle Responsibility | Class/function has multiple reasons to change |
| **O**pen/Closed | Modifying existing code to add features instead of extending |
| **L**iskov Substitution | Subclass breaks parent's contract or throws unexpected exceptions |
| **I**nterface Segregation | Implementing empty methods to satisfy large interface |
| **D**ependency Inversion | High-level modules importing low-level concrete implementations |

## Quick Reference: Security Red Flags

Immediately flag these patterns:

| Category | Red Flags |
|----------|-----------|
| **Injection** | String concatenation in SQL/commands, unsanitized user input |
| **Auth** | Hardcoded credentials, weak password rules, missing auth checks |
| **Crypto** | MD5/SHA1 for passwords, hardcoded keys, custom crypto |
| **Data Exposure** | Logging sensitive data, verbose error messages, missing encryption |
| **Access Control** | Missing authorization checks, IDOR vulnerabilities |

For detailed security review, see [references/security.md](references/security.md).

## PR Review Best Practices

### What to Review (In Scope)
- New code added in this PR
- Modified lines and their immediate context
- New files created
- Deleted code (verify safe removal)
- Changes to tests that correspond to code changes
- Configuration/dependency changes

### What NOT to Review (Out of Scope)
- Pre-existing code that wasn't modified
- Style issues in untouched code
- Technical debt that existed before this PR
- Refactoring suggestions for unchanged code
- Issues that should be separate PRs

### Common PR Review Mistakes to Avoid
1. **Reading entire files** instead of just the diff output
2. **Exploring the codebase** beyond files changed in the PR
3. **Suggesting unrelated refactoring** - create a separate issue instead
4. **Flagging pre-existing bugs** as PR issues (unless this PR should fix them)
5. **Missing file:line references** - always point to exact locations
6. **Vague solutions** - provide concrete code examples
7. **Making assumptions** about code behavior without seeing it in the diff
8. **Over-investigating** - if context is missing, ask rather than explore

### Efficiency Guidelines

A good PR review should be **fast and focused**:

1. **One pass through the diff** - don't re-read files multiple times
2. **Flag uncertainties as questions** - don't deep-dive to find answers
3. **Trust existing code** - if it wasn't changed, it's out of scope
4. **Limit scope creep** - resist the urge to "also check" related code
5. **Time box yourself** - a PR review should take minutes, not hours

### When You Lack Context

If the diff alone doesn't tell you if something is correct:

```markdown
#### Question: [Topic]
- **File**: `path/to/file.cs:123`
- **Change**: [What was changed]
- **Concern**: [What might be wrong]
- **Needs clarification**: [What you'd need to know to confirm]
```

This is better than:
- Spending 30 minutes exploring the codebase
- Making incorrect assumptions
- Flagging false positives

## Review Etiquette

- **Be specific**: Point to exact file:line, show code examples for fixes
- **Be constructive**: Explain why something is an issue and how to fix it
- **Stay in scope**: Only review what changed in this PR
- **Acknowledge good code**: Positive reinforcement matters
- **Prioritize**: Clearly distinguish blocking issues from nice-to-haves
- **Ask questions**: If intent is unclear, ask rather than assume
- **Offer alternatives**: Don't just say "this is wrong" - show the right way
