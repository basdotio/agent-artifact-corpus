---
name: nextjs-secure
description: Enforce Next.js Data Security best practices (Data Access Layer, Tainting, Zero Trust).
---

# Next.js Security Skill

This skill codifies the "Zero Trust" data handling patterns for React Server Components (RSC) and Next.js. It forces a separation of concerns between fetching, transforming, and presenting data.

## 1. The Data Access Layer (DAL)

**Rule**: Never call the database directly from a Page/Component. Use a dedicated DAL.

### Pattern: The Cached DAL Method

`lib/data/auth.ts`:

```typescript
import { cache } from 'react'
import { cookies } from 'next/headers'
import 'server-only' // 🛡️ Usage from client triggers build error

export const getCurrentUser = cache(async () => {
  const token = cookies().get('AUTH_TOKEN')
  // Verify/Decrypt token logic...
  return { id: 'user_123', role: 'admin' }
})
```

### Pattern: The DTO (Data Transfer Object)

**Rule**: Never pass raw DB rows to the client. Returns safe, minimal objects.

`lib/data/user-dto.ts`:

```typescript
import 'server-only'
import { getCurrentUser } from './auth'
import { db } from '@/lib/db'

export async function getProfileDTO(slug: string) {
  const user = await getCurrentUser()
  const rawData = await db.query('SELECT * FROM users WHERE slug = ?', [slug])

  // 🛡️ Authorization Filter
  const canSeePhone = user.role === 'admin' || user.id === rawData.id

  // 🛡️ API Minimization (Return ONLY what's needed)
  return {
    username: rawData.username,
    phonenumber: canSeePhone ? rawData.phonenumber : null,
  }
}
```

## 2. Preventing Leaks

### Experimental Taint

Use React Taint APIs to prevent sensitive objects from ever reaching the client props.

`next.config.js`:

```js
module.exports = {
  experimental: { taint: true }
}
```

`lib/data/sensitive.ts`:

```typescript
import { experimental_taintObjectReference } from 'react'

export async function getSecretKeys() {
  const keys = { secret: process.env.SECRET_KEY }
  // 🛡️ If this object is passed to a Client Component, throw error
  experimental_taintObjectReference('Do not pass keys to client', keys)
  return keys
}
```

## 3. Server Actions Security

**Rule**: Treat Server Actions like Public REST Endpoints.

### Validation & Authorization

Always re-verify auth and validate inputs inside the action.

`app/actions.ts`:

```typescript
'use server'

import { z } from 'zod'
import { getCurrentUser } from '@/lib/data/auth'

const schema = z.object({
  api_key: z.string().min(1)
})

export async function updateKey(formData: FormData) {
  // 1. 🛡️ Auth Check
  const user = await getCurrentUser()
  if (!user.role === 'admin') throw new Error('Unauthorized')

  // 2. 🛡️ Input Validation
  const data = schema.parse({
    api_key: formData.get('api_key')
  })

  // 3. Mutation
  await db.updateKey(user.id, data.api_key)
}
```

### Encryption & Closures

Next.js encrypts closed-over variables, but **do not rely on it** for highly sensitive secrets.

- Use `process.env.NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` for consistent keys across multi-server deployments.

## 4. Auditing Checklist

- [ ] **DAL Isolation**: Are DB packages imported *only* in `lib/data/*`?
- [ ] **DTOs**: Do Server Components return minimal objects?
- [ ] **Server-Only**: Do data files import `server-only`?
- [ ] **Tainting**: Are pure secrets tainted?
- [ ] **Action Auth**: Does every `use server` function start with an auth check?
