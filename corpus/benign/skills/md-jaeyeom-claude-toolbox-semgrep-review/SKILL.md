---
name: semgrep-review
description: Analyze semgrep scan findings, triage real vulnerabilities vs false positives, fix real issues using framework-native escaping, and suppress false positives with properly formatted nosemgrep comments.
---

# Semgrep Review Skill

You are an expert at analyzing semgrep static analysis findings. Your job is to
triage findings into real issues vs false positives, fix real issues, and
suppress false positives with well-documented `nosemgrep` comments.

## Workflow

### Step 1: Run Semgrep

If the user hasn't provided semgrep output, run the scan.

First, check if the project has local semgrep rules (a `.semgrep/` directory or
`.semgrep.yaml` file in the project root). If local rules exist, include them
alongside the auto config:

```bash
# With local rules (.semgrep/ directory or .semgrep.yaml exists)
semgrep scan --config auto --config .semgrep <target-directory>

# Without local rules
semgrep scan --config auto <target-directory>
```

Using `--config auto --config .semgrep` ensures local custom rules are applied
on top of the semgrep registry defaults. Omitting the local config when it
exists can cause semgrep to fail.

### Step 2: Triage Each Finding

For every finding, determine whether it is a **real issue** or a **false
positive** by reading the flagged code and tracing the data source.

**Questions to ask for each finding:**

1. Where does the flagged value originate? (user input, database, config, test
   fixture)
2. Is the value sanitized or escaped before use? (framework auto-escaping,
   manual escaping)
3. What is the threat model? (public-facing, admin-only, test-only)

**Common false positive categories:**

| Category | Example | Why It's Safe |
|----------|---------|---------------|
| Test fixtures | Private keys, hashes in test files | Intentionally committed, no real system access |
| Framework-escaped values | Variables inside Hono `html` template literals, React JSX | Framework auto-escapes interpolated values |
| Admin-only internal tools | Values from admin DB displayed in admin panel | Not user-controlled, but still fix for defense-in-depth |

### Step 3: Fix Real Issues

**Prefer framework-native escaping over custom helpers.** Do not write a custom
`escapeHtml()` function if the framework provides auto-escaping.

**Common fix patterns by framework:**

#### Hono (html tagged template literals)

Replace manual string interpolation with `html` template literals:

```typescript
// BAD: Manual string building, no escaping
const items = data.map((d) => `<span>${d.name}</span>`).join('');
return raw(items);

// GOOD: Hono html template auto-escapes interpolated values
const items = data.map((d) => html`<span>${d.name}</span>`);
return items; // No raw() needed; html`` returns HtmlEscapedString
```

When refactoring from `raw()` + string templates to `html` templates:

- Replace backtick strings with `html` tagged template literals
- Remove `.join('')` calls (arrays of `HtmlEscapedString` render correctly)
- Remove `raw()` wrappers (no longer needed when content is already
  `HtmlEscapedString`)
- Watch for extra `)` characters left behind when removing `raw(` wrapper

#### React / JSX

JSX auto-escapes by default. Flag only `dangerouslySetInnerHTML` usage:

```tsx
// BAD
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// GOOD
<div>{userInput}</div>
```

#### Plain HTML / Server-side rendering

Use the framework's escape utility or a well-known library. As a last resort,
write a standard escape function:

```typescript
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
```

### Step 4: Suppress False Positives with nosemgrep

#### Syntax Rules

The `nosemgrep` comment must be:

- On the **same line** as the finding, OR
- **Alone on the line immediately above** the finding

Use the **short rule ID** (e.g., `detected-private-key`), not the full dotted
path (e.g., `generic.secrets.security.detected-private-key.detected-private-key`).

```typescript
// WRONG: Full dotted path (semgrep ignores this)
// nosemgrep: generic.secrets.security.detected-private-key
const key = `-----BEGIN PRIVATE KEY-----...`;

// WRONG: nosemgrep is not immediately above the finding
// nosemgrep: detected-private-key
// This key is used for testing only.
const key = `-----BEGIN PRIVATE KEY-----...`;

// CORRECT: Short rule ID, immediately above the finding
// This key is used for testing only.
// nosemgrep: detected-private-key
const key = `-----BEGIN PRIVATE KEY-----...`;
```

#### Documenting the Rationale

Always add a comment explaining **why** the suppression is safe:

```typescript
// Test-only ES256 private key for unit tests.
// This key is intentionally committed for testing JWT generation.
// It has no access to any real systems and is safe to expose.
// nosemgrep: detected-private-key
const TEST_KEY = `-----BEGIN PRIVATE KEY-----...`;
```

For bcrypt hashes in tests:

```typescript
// Example bcrypt hashes for testing hash format detection.
// Not real credentials - test fixtures to verify needsRehash()
// correctly identifies legacy formats for migration.
// nosemgrep: detected-bcrypt-hash
expect(needsRehash('$2a$10$...')).toBe(true);
```

#### Suppressing Inside Template Literals

JavaScript `//` and `/* */` comments don't work inside template literal text.
Use these techniques instead:

**Inside `${}` expressions** (these are JS expression context):

```typescript
// Use /* */ block comment inside ${}
html`<div>
  ${/* nosemgrep: unknown-value-with-script-tag */ renderItems(data)}
</div>`;

// Use // line comment when the expression continues on the next line
html`<input value=${
  getValue() // nosemgrep: unknown-value-with-script-tag
} />`;
```

**For object properties inside `${}`:**

```typescript
// // comment works because it's inside a JS expression (object literal)
html`${textarea({
  name: 'field',
  value: data.join('\n'), // nosemgrep: unknown-value-with-script-tag
  rows: 2,
})}`;
```

**When no JS expression context is available**, extract the value to a variable
above the template:

```typescript
// nosemgrep: unknown-value-with-script-tag
const safeValue = computeValue();
html`<div>${safeValue}</div>`;
```

Note: The `nosemgrep` comment must be on the **specific line semgrep flags**,
not just anywhere nearby. Run semgrep after adding comments to verify
suppression works.

### Step 5: Verify

After all fixes and suppressions:

1. Re-run semgrep (with `--config auto --config .semgrep` if local rules exist) to confirm 0 findings
2. Run type checking / build to confirm no regressions
3. Run tests if the changes affect runtime behavior

## Output Format

Present findings as a summary table:

| # | File | Rule | Verdict | Action |
|---|------|------|---------|--------|
| 1 | `path/to/file.ts:42` | `rule-id` | Real issue | Fix: use `html` template |
| 2 | `path/to/test.ts:10` | `detected-private-key` | False positive | Suppress: test fixture |

Then proceed with fixes and suppressions.
