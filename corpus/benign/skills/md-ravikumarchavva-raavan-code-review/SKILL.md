---
name: code-review
description: Structured code review skill for evaluating code quality, identifying issues, and suggesting improvements.
version: "1.0"
license: MIT
allowed-tools: code_interpreter file_manager
category: development/project
tags: [review, quality, lint, refactor, best-practice, clean, code, assess]
aliases: [review-code, code-quality, pr-review]
metadata:
  author: agent-framework
---

# Code Review Skill

Use this skill when the user asks you to review code, assess quality, or suggest improvements.

## Review Procedure

### Step 1 — Understand Context
- What does this code do? What is its purpose in the larger system?
- What language/framework is it written in?
- Is this a new feature, bug fix, or refactor?

### Step 2 — Correctness Check
- Does the code do what it claims to do?
- Are there edge cases that aren't handled?
- Are error paths covered (try/catch, null checks, validation)?
- Are return types and values correct?

### Step 3 — Security Review
- Input validation: is user input sanitized?
- Injection risks: SQL, XSS, command injection?
- Secrets: are API keys, passwords, or tokens hardcoded?
- Access control: are authorization checks in place?

### Step 4 — Readability & Maintainability
- Are names descriptive? (variables, functions, classes)
- Is the code DRY (Don't Repeat Yourself)?
- Are there comments where logic is non-obvious?
- Is the function/method length reasonable (<30 lines)?
- Is the nesting depth manageable (<3 levels)?

### Step 5 — Performance
- Are there obvious O(n²) or worse algorithms that could be O(n)?
- Are there unnecessary allocations, copies, or re-computations?
- Database queries: N+1 problem? Missing indexes?

### Step 6 — Testing
- Are there tests for the changed code?
- Do tests cover happy path AND error cases?
- Are tests readable and well-named?

### Step 7 — Deliver Feedback
Format your review as:
```
## Summary
One-paragraph overview of the code and overall assessment.

## Issues (must fix)
- [severity] description → suggested fix

## Suggestions (nice to have)
- description → improvement

## Positives
- What the code does well
```

## Severity Levels
- **Critical** — Security vulnerability, data loss risk, crash
- **Major** — Bug, incorrect behaviour, missing error handling
- **Minor** — Style, naming, minor inefficiency
- **Nit** — Cosmetic, formatting, personal preference
