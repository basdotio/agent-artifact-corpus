---
name: code-clean
description: Code quality review skill focusing on readability, maintainability, and consistency (non-architectural). Checks for naming conventions, code duplication, type consistency, unused code, and other clean code issues.
license: MIT
metadata:
  author: Transcoder
  version: "1.0.0"
---

# Code Clean Skill

Performs non-architectural code quality review to improve readability, maintainability, and extensibility.

## When to Use

Call this skill when:
- User invokes `/code-clean` command
- User asks to review code for quality issues
- User mentions "code review", "cleanup", "refactoring"
- Before committing significant changes

## Review Scope

### 1. Variable & Naming Consistency
- Check frontend-backend variable name alignment (especially in Tauri apps)
- Verify display text matches backend parameters
- Look for inconsistent naming patterns (camelCase vs snake_case where inappropriate)

### 2. Code Duplication
- Identify repeated logic blocks
- Find duplicate utility functions
- Spot similar patterns that could be extracted

### 3. Type Safety
- Check frontend-backend type definition mismatches
- Verify `any` types are appropriately used
- Look for missing type annotations

### 4. Unused Code
- Find unused variables, imports, functions
- Identify commented-out code
- Spot dead code branches

### 5. Code Smells
- Magic numbers without constants
- Overly complex functions (suggest splitting)
- Missing error handling
- Inconsistent formatting (blank lines, spacing)
- Using array index as React key (anti-pattern)

### 6. String & Display Consistency
- Hardcoded strings that should be constants
- User-facing text not centralized
- Inconsistent terminology in UI

## Review Process

1. **Scan project structure**
   - Use Glob to find relevant source files
   - Focus on recently modified files first if specified

2. **Read key files**
   - Read type definition files (types/index.ts, models.rs, etc.)
   - Read component/implementation files
   - Read backend command/handler files

3. **Analyze and categorize findings**
   - Group issues by category (naming, duplication, types, etc.)
   - Mark severity: [High], [Medium], [Low]
   - Note file locations with line numbers

4. **Present findings**
   - Start with a summary table
   - Provide detailed suggestions per issue
   - Include code examples for fixes
   - Propose specific file:line references

## Output Format

```
## Code Review Report

### Summary
- Total issues found: X
- [High]: Y | [Medium]: Z | [Low]: W

### Issues by Category

#### 1. Category Name
| Issue | File | Severity | Suggestion |
|-------|------|----------|------------|
| description | file.ts:42 | [High] | fix suggestion |

#### 2. Another Category
...

### Detailed Findings

**[High] Issue Description**
- Location: `src/file.ts:42`
- Problem: explanation
- Suggested fix:
  ```typescript
  // code example
  ```
```

## Exclusions

- **DO NOT** critique architectural decisions (unless asked)
- **DO NOT** suggest major refactors that break functionality
- **DO NOT** change external library integrations
- **DO NOT** modify build configurations

## Tips

- Be specific with file paths and line numbers
- Provide executable code examples
- Prioritize issues that impact maintainability
- Consider the project's existing style before suggesting changes
- Ask user before making edits if uncertain
