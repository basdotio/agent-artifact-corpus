---
name: pre-commit
# prettier-ignore
description: Run before committing code. Runs lint, format, type check, and tests to ensure code quality. Use when preparing to commit changes or when asked to verify code quality.
---

# Pre-Commit Checklist

Run these checks before committing code to ensure quality.

## Quick Commands

```bash
npm run check      # TypeScript type checking
npm run lint       # Prettier + ESLint check
npm run test       # Run all tests
npm run format     # Auto-fix formatting issues
```

## Full Pre-Commit Flow

1. **Format code** (auto-fix):
   ```bash
   npm run format
   ```

2. **Check types**:
   ```bash
   npm run check
   ```

3. **Run linter**:
   ```bash
   npm run lint
   ```

4. **Run tests**:
   ```bash
   npm run test
   ```

5. **Stage and commit** (if all pass):
   ```bash
   git add <files>
   git commit -m "message"
   ```

## One-Liner

Run all checks in sequence (stops on first failure):

```bash
npm run format && npm run check && npm run lint && npm run test
```

## Common Issues

| Issue | Fix |
|-------|-----|
| Prettier errors | Run `npm run format` |
| ESLint errors | Fix manually or check `.eslintrc` |
| Type errors | Fix TypeScript issues in code |
| Test failures | Fix failing tests before commit |

## Notes

- Always run checks before pushing to remote
- Format first to avoid unnecessary lint errors
- Tests should pass in CI - don't skip locally
