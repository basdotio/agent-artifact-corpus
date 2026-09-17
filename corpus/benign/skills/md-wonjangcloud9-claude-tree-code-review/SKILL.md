---
name: code-review
description: Thorough code review. Use when reviewing PR, checking code quality, or auditing changes.
allowed-tools: Read, Grep, Glob
---

# Code Review

Perform systematic code review with actionable feedback.

## Checklist

### Security
- [ ] No hardcoded secrets or API keys
- [ ] Input validation present
- [ ] SQL injection prevention
- [ ] XSS prevention

### Quality
- [ ] Functions under 30 lines
- [ ] Clear, descriptive naming
- [ ] Single responsibility principle
- [ ] Error handling complete

### Tests
- [ ] Test coverage adequate
- [ ] Edge cases covered
- [ ] Tests are readable

## Output Format

Use severity levels:

- **CRITICAL**: Security issues, data loss risk
- **WARNING**: Code quality, maintainability
- **INFO**: Style, suggestions

## Example Output

```markdown
## Code Review: auth.ts

### CRITICAL
- Line 45: API key hardcoded in source

### WARNING
- Line 12-80: Function too long (68 lines), split into smaller units

### INFO
- Line 5: Consider using `const` instead of `let`
```
