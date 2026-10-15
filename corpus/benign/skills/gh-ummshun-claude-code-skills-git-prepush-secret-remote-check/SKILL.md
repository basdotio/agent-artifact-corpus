---
name: git-prepush-secret-remote-check
description: Use immediately before a git push or public release to confirm that the remote points to the intended repository and to scan staged changes for API keys, tokens, credentials, and personally identifiable information.
author: auto
created: 2026-06-16
version: 1.0.0
status: stale
---

## Procedure

### 1. Verify the remote URL

```bash
git remote -v
```

Expected shape:

```text
origin  git@github.com:YOUR_USERNAME/YOUR_REPO.git (fetch)
origin  git@github.com:YOUR_USERNAME/YOUR_REPO.git (push)
```

Confirm that the account and repository are yours. If `origin` still points to an upstream or third-party fork, correct it before continuing:

```bash
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
```

### 2. Scan staged changes for secrets

```bash
git diff --cached | grep -iE \
  "(api_?key|secret|token|password|passwd|auth|credential|access_?key|private_?key)\s*[=:]\s*\S+"
```

No output is the expected result. If a value is found, unstage the file, move the value to an ignored environment file, and stage only the sanitized changes.

### 3. Check recent committed content

```bash
git log --oneline -10
git show HEAD | grep -iE "(api_?key|secret|token|password)\s*[=:]\s*\S+"
```

### 4. Confirm environment files are not tracked

```bash
git ls-files | grep -E "^\.env"
```

If a private environment file appears, remove it from the index and add the appropriate pattern to `.gitignore`.

### 5. Run a basic PII scan

```bash
git diff --cached | grep -iE \
  "(\b[0-9]{3}-[0-9]{4}-[0-9]{4}\b|@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
```

Review every phone-number or email-like match for hardcoded personal data.

## Pitfalls

- A fork can retain its upstream remote, making an otherwise normal push target the wrong repository.
- Framework-generated `.gitignore` files do not cover every custom environment-file name.
- Regular expressions do not detect every encoded or obfuscated secret. Prefer a dedicated scanner such as gitleaks or TruffleHog when available.
- Rewriting Git history does not invalidate a secret that has already been published. Rotate exposed credentials immediately.

## Verification

```bash
git remote -v | grep "YOUR_USERNAME"
git diff --cached | grep -iE "(api_?key|secret|token|password)\s*[=:]\s*\S+" | wc -l
git ls-files | grep -E "^\.env" | wc -l
```

Both counts should be zero, and the remote must point to the intended account and repository.
