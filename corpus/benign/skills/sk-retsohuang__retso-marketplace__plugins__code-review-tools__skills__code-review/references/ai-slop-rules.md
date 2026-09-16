# AI Slop Detection Rules

Identify AI-generated patterns that are inconsistent with the codebase style and best practices.

## Rule 1: Unnecessary Comments

**What to check**: Comments that a human wouldn't add or are inconsistent with file style.

**Patterns to detect**:

### 1.1 Obvious Code Explanations
```tsx
// ❌ AI slop
// Get the user from the database
const user = await db.users.findById(userId);

// ✅ No comment needed - code is self-explanatory
const user = await db.users.findById(userId);
```

### 1.2 Redundant JSDoc
```tsx
// ❌ AI slop - duplicates TypeScript types
/**
 * Process user data
 * @param user - The user object
 * @returns void
 */
function processUser(user: User): void { }

// ✅ Only add JSDoc if it provides additional context
function processUser(user: User): void { }
```

### 1.3 Step-by-Step Comments
```tsx
// ❌ AI slop
// Step 1: Validate input
if (!data) return;
// Step 2: Transform data
const transformed = transform(data);
// Step 3: Save to database
await save(transformed);

// ✅ Extract to named functions if steps need explanation
async function processData(data: Data) {
  if (!data) return;
  const transformed = transform(data);
  await save(transformed);
}
```

**What to flag**: Comments that explain what the code does rather than why.

---

## Rule 2: Defensive Programming

**What to check**: Extra try/catch blocks or checks that are abnormal for the codebase area, especially in trusted/validated codepaths.

**Patterns to detect**:

### 2.1 Unnecessary Try/Catch
```tsx
// ❌ AI slop - function already handles errors internally
try {
  processValidatedData(data);
} catch (error) {
  console.error(error);
}

// ✅ Trust internal error handling
processValidatedData(data);
```

### 2.2 Redundant Null Checks
```tsx
// ❌ AI slop - TypeScript guarantees non-null
function processValidatedUser(user: User) {
  if (!user) {
    throw new Error('User is required');
  }
  return user.email.toLowerCase();
}

// ✅ Trust TypeScript types
function processValidatedUser(user: User) {
  return user.email.toLowerCase();
}
```

### 2.3 Impossible Error Handling
```tsx
// ❌ AI slop - this can't actually fail
try {
  return user.email.toLowerCase();
} catch (error) {
  return '';
}

// ✅ Remove unnecessary try/catch
return user.email.toLowerCase();
```

**What to flag**: Defensive code in trusted/validated codepaths where errors can't occur.

---

## Rule 3: Type Bypasses

**What to check**: `as any` casts used to work around type issues.

**Patterns to detect**:

### 3.1 Any Type Casts
```tsx
// ❌ AI slop
const items = data.items as any;
const count = (items.length as any) || 0;

// ✅ Fix the types properly
const items: Item[] = data.items;
const count = items.length;
```

### 3.2 Excessive Type Assertions
```tsx
// ❌ AI slop
const result = (response.data as ApiResponse).items as Item[];

// ✅ Define proper types
interface ApiResponse {
  items: Item[];
}
const result = response.data.items;
```

**What to flag**: Any usage of `as any` or excessive type assertions to bypass type errors.

---

## Rule 4: Style Inconsistencies

**What to check**: Code style that doesn't match the surrounding file or project conventions.

**Patterns to detect**:

### 4.1 Inconsistent Naming
```tsx
// ❌ AI slop - file uses camelCase, new code uses snake_case
const user_data = getUserData();

// ✅ Match existing style
const userData = getUserData();
```

### 4.2 Inconsistent Error Handling
```tsx
// ❌ AI slop - rest of file throws errors, new code returns null
function findUser(id: string): User | null {
  if (!id) return null;
}

// ✅ Match existing error handling pattern
function findUser(id: string): User {
  if (!id) throw new Error('ID required');
}
```

### 4.3 Inconsistent Import Styles
```tsx
// ❌ AI slop - file uses named imports
import React from 'react';

// ✅ Match existing style
import { useState, useEffect } from 'react';
```

### 4.4 Over-Engineering
```tsx
// ❌ AI slop - simple operation over-engineered
const isValid = useMemo(() => {
  return data.length > 0;
}, [data]);

// ✅ Keep it simple
const isValid = data.length > 0;
```

**What to flag**: Code that doesn't match the conventions and patterns used in the rest of the file.

---

## Comment Format

When flagging AI slop:

```markdown
**Line X-Y:**
```tsx
{/* problematic code */}
```
> **🧹 AI Slop**: [Brief description of the issue]. [Suggestion to fix it].
```

## Examples

### Example 1: Unnecessary Comment

```markdown
**Line 15-17:**
```tsx
// Fetch user data from the API
const userData = await fetchUser(userId);
```
> **🧹 AI Slop**: Remove unnecessary comment. The code is self-explanatory and the file doesn't use inline comments for simple operations.
```

### Example 2: Defensive Try/Catch

```markdown
**Line 72-75:**
```tsx
try {
  processValidatedData(data);
} catch (error) {
  console.error(error);
}
```
> **🧹 AI Slop**: Unnecessary try/catch block. The `processValidatedData` function is called with already-validated data and handles errors internally. This defensive programming is abnormal for this area of the codebase.
```

### Example 3: Type Bypass

```markdown
**Line 120:**
```tsx
const result = response.data as any;
```
> **🧹 AI Slop**: Type bypass using `as any`. Fix the type definition for `response.data` instead of casting to `any`.
```

### Example 4: Style Inconsistency

```markdown
**Line 45-50:**
```tsx
const user_id = getUserId();
const user_name = getUserName();
```
> **🧹 AI Slop**: Inconsistent naming convention. File uses camelCase (`userId`, `userName`), not snake_case.
```

---

## When NOT to Flag

Don't flag as AI slop if:
1. Comments explain complex business logic or non-obvious decisions
2. Error handling is required for external APIs or user input
3. Type assertions are necessary for third-party library types
4. The code follows project conventions (even if different from typical patterns)
5. Defensive checks are intentional for production safety
