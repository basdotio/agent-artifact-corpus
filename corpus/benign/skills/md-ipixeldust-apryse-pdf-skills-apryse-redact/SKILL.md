---
name: apryse-redact
description: Permanently remove sensitive content from PDFs using Apryse SDK. Redact by search term or regex pattern (SSN, email, phone). Use when user needs to sanitize documents or remove confidential information.
license: Proprietary. LICENSE.txt has complete terms
compatibility: Requires Node.js 14+ and @pdftron/pdfnet-node. Set PDFTRON_LICENSE_KEY environment variable.
metadata:
  author: apryse
  version: "1.0"
---

# PDF Redaction

Permanently remove sensitive content from PDFs. All scripts are in the `scripts/` directory.

**WARNING:** Redaction is permanent and irreversible. The original content is completely removed from the file.

## Available Scripts

### Redact by Search Term
```bash
node scripts/redact-search.js <input.pdf> <output.pdf> "term1" ["term2"] [--overlay "[REDACTED]"]
```
Finds and redacts all occurrences of the specified terms.

### Redact by Pattern (Regex)
```bash
node scripts/redact-pattern.js <input.pdf> <output.pdf> "<pattern>" [--overlay "[REDACTED]"]
```

## Common Patterns

| Data Type | Pattern | Example Match |
|-----------|---------|---------------|
| SSN | `\d{3}-\d{2}-\d{4}` | 123-45-6789 |
| Email | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | user@example.com |
| Phone (US) | `\(\d{3}\)\s*\d{3}-\d{4}` | (555) 123-4567 |
| Credit Card | `\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}` | 1234-5678-9012-3456 |
| Date | `\d{1,2}/\d{1,2}/\d{2,4}` | 12/31/2024 |

## Examples

Redact all SSN numbers:
```bash
node scripts/redact-pattern.js doc.pdf redacted.pdf "\d{3}-\d{2}-\d{4}"
```

Redact specific words:
```bash
node scripts/redact-search.js doc.pdf redacted.pdf "confidential" "secret" "password"
```

Redact emails with replacement text:
```bash
node scripts/redact-pattern.js doc.pdf redacted.pdf "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" --overlay "[EMAIL REMOVED]"
```

## When to Use

- User asks to "redact", "remove", or "black out" specific text → `redact-search.js`
- User asks to "remove all SSN/email/phone numbers" → `redact-pattern.js` with appropriate pattern
- User asks to "sanitize" or "clean sensitive data" → use patterns for common PII

## Notes

- Redaction is PERMANENT - always work on a copy
- The `--overlay` text appears in place of redacted content
- Patterns use JavaScript regex syntax (escape backslashes in shell)
- Test patterns on a copy first to verify matches
