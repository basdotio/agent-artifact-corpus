---
name: debugging
description: Debug code errors systematically. Use when analyzing error messages, fixing bugs, resolving build/lint errors, or troubleshooting runtime issues.
---

# Debugging Skill

## When to Use
- Analyzing error messages and stack traces
- Finding root causes of bugs
- Fixing runtime errors
- Resolving build/lint errors

## Debugging Process

### Step 1: Understand the Error
1. Read the **full error message**
2. Identify the **error type** (TypeError, ReferenceError, etc.)
3. Find the **file and line number**
4. Check the **stack trace** for call sequence

### Step 2: Reproduce the Issue
1. Identify the **trigger conditions**
2. Create a **minimal reproduction**
3. Note any **environment factors**

### Step 3: Analyze Root Cause
1. Check **recent changes** (git diff)
2. Verify **assumptions** about data types
3. Trace **data flow** through the code
4. Check for **edge cases**

### Step 4: Fix and Verify
1. Make the **smallest fix** possible
2. Add **defensive checks** if needed
3. Test the **fix** thoroughly
4. Check for **regression**

## Common Error Patterns

### TypeError: Cannot read properties of undefined

**Cause**: Accessing property on undefined/null
```typescript
// Bad
const name = user.profile.name; // user might be undefined

// Fix: Optional chaining
const name = user?.profile?.name;

// Fix: Default value
const name = user?.profile?.name ?? 'Unknown';

// Fix: Early return
if (!user?.profile) return null;
const name = user.profile.name;
```

### TypeError: X is not a function

**Cause**: Calling something that isn't a function
```typescript
// Check 1: Is it imported correctly?
import { myFunction } from './utils'; // Named export?
import myFunction from './utils';      // Default export?

// Check 2: Is it defined?
console.log(typeof myFunction); // Should be 'function'

// Check 3: Is it bound correctly in classes?
class MyClass {
  method = () => {}; // Arrow function preserves 'this'
}
```

### ReferenceError: X is not defined

**Cause**: Using variable before declaration or misspelling
```typescript
// Check 1: Is it imported?
import { useState } from 'react';

// Check 2: Is it in scope?
function outer() {
  const x = 1;
  function inner() {
    console.log(x); // x is in scope
  }
}

// Check 3: Typo?
const userNmae = 'John'; // Typo: userNmae vs userName
```

### Async/Await Errors

```typescript
// Error: await used outside async function
// Fix: Make function async
async function fetchData() {
  const data = await fetch('/api/data');
  return data.json();
}

// Error: Unhandled promise rejection
// Fix: Add try-catch
async function fetchData() {
  try {
    const response = await fetch('/api/data');
    if (!response.ok) throw new Error('Fetch failed');
    return await response.json();
  } catch (error) {
    console.error('Fetch error:', error);
    return null;
  }
}
```

### React Hooks Errors

```typescript
// Error: Hooks can only be called inside function components
// Fix: Move hook to component level
function MyComponent() {
  const [state, setState] = useState(0); // Correct
  
  // Wrong: Hook inside callback
  const handleClick = () => {
    // const [x, setX] = useState(0); // Error!
  };
}

// Error: Rendered more hooks than during the previous render
// Fix: Don't conditionally call hooks
function MyComponent({ show }) {
  // Wrong
  // if (show) {
  //   const [state, setState] = useState(0);
  // }
  
  // Correct
  const [state, setState] = useState(0);
  if (!show) return null;
}
```

### Next.js Specific Errors

```typescript
// Error: "use client" directive required
// Fix: Add directive at top of file
'use client';

import { useState } from 'react';
export function ClientComponent() {
  const [count, setCount] = useState(0);
}

// Error: Cannot use hooks in Server Components
// Fix: Move to Client Component or extract interactive parts
```

### Next.js Build Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `'use client' must be first` | Directive not at line 1 | Move to very first line |
| `Module not found: @/...` | Path alias issue | Check tsconfig paths |
| `Hydration mismatch` | Server/client HTML differs | Ensure same data |
| `await params` | Dynamic route in Next.js 16 | Add `await context.params` |
| `Text content mismatch` | Date/random on server | Use `suppressHydrationWarning` or move to client |

### React Runtime Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Element type is invalid: got undefined` | Wrong import/export | Check export type matches import |
| `mixed up default and named imports` | Import mismatch | Pages: `import X from`, Components: `import { X } from` |

**Import/Export Rules:**
- **Pages (`app/**/page.tsx`)**: Use `export default` → Import with `import X from`
- **Components (`components/*`)**: Use `export function X` → Import with `import { X } from`

```typescript
// WRONG - will cause "Element type is invalid"
import HeroSection from '@/components/HeroSection';  // if HeroSection uses named export

// CORRECT
import { HeroSection } from '@/components/HeroSection';  // named export
```

### Prisma Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `P1001: Can't reach database` | DB not running | Start postgres container |
| `P2002: Unique constraint` | Duplicate entry | Check unique fields |
| `P2025: Record not found` | Delete/update missing | Check ID exists first |
| `PrismaClient not generated` | Missing generate | Run `bunx prisma generate` |
| `P2003: Foreign key constraint` | Referenced record missing | Create parent first |
| `Invalid prisma client` | Schema changed | Run `bunx prisma generate` |

## Debugging Tools

### Console Methods
```typescript
console.log('Value:', value);
console.table(arrayOfObjects);
console.trace('Call stack');
console.time('operation');
// ... code ...
console.timeEnd('operation');
```

### TypeScript Type Checking
```typescript
// Check type at runtime
console.log('Type:', typeof value);
console.log('Is array:', Array.isArray(value));
console.log('Instance:', value instanceof Date);

// Narrow types
if (typeof value === 'string') {
  // value is string here
}
```

### Git for Finding Regressions
```bash
# Find when bug was introduced
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>

# Check recent changes
git diff HEAD~5
git log --oneline -10
```

## Fix Verification Checklist

- [ ] Error no longer occurs
- [ ] Related functionality still works
- [ ] No new TypeScript errors
- [ ] Tests pass (if any)
- [ ] Edge cases handled

## References

- `references/error-handling-patterns.md` - Toast notifications, form errors, error boundaries
