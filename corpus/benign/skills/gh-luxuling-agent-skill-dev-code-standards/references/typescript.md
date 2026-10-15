# TypeScript, JavaScript, React, Next.js, Node

These rules add to the general ones in `SKILL.md`. They apply to frontend React, full-stack Next.js, and Node backend or API code.

## Functions and exports

Write functions and components as arrow functions assigned to `const`, and export them by name.

```tsx
export const UserCard = ({ user }: Props) => {
  return <div>{user.name}</div>
}

export const formatDate = (d: Date): string =>
  d.toISOString().slice(0, 10)
```

Do not use default exports. Named exports keep one name per thing across the codebase, which makes renames and searches reliable.

The one exception is a file where the framework requires a default export, such as a Next.js `page.tsx`, `layout.tsx`, or a config file. Keep the arrow style and export the constant at the bottom:

```tsx
const UsersPage = async () => {
  const users = await getUsers()
  return <UserList users={users} />
}

export default UsersPage
```

## Components, hooks, and services

Components only render. Each layer keeps to its own job:

- `components/` holds JSX and props. A component reads what it needs from a hook and renders it.
- `hooks/` holds state, effects, and data fetching through TanStack Query, one custom hook per concern.
- `services/` holds API calls, Zod parsing of responses, and business logic. Services do not import React.

```tsx
// components/user-list.tsx
export const UserList = () => {
  const { data: users, status, error } = useUsers()

  if (status === 'pending') return <Spinner />
  if (status === 'error') throw error

  return <ul>{users.map((user) => <UserRow key={user.id} user={user} />)}</ul>
}

// hooks/use-users.ts
export const useUsers = () => useQuery({ queryKey: ['users'], queryFn: getUsers })

// services/users.ts
export const getUsers = async () => {
  const res = await fetch('/api/users')

  return usersSchema.parse(await res.json())
}
```

## Types

- Use `interface` for object shapes. Use `type` for unions, tuples, function signatures, and mapped or utility types.

  ```ts
  interface User {
    id: string
    name: string
  }

  type Status = 'active' | 'banned'
  ```

- No `any`. When a value's type is unknown, type it as `unknown` and narrow it.
- No `as` casts and no non-null `!`. Both tell the compiler to stop checking, so the bug surfaces at runtime instead. Fix the type at its source. `as const` and `satisfies` are fine because they add checking.
- Define each shape once. Derive the rest with `z.infer`, `Pick`, `Omit`, `ReturnType`, or `typeof` instead of writing the same fields a second time.

## Validation

Use Zod where data enters the system: request bodies, query params, environment variables, form input, and responses from external APIs. Parse once at that edge and pass typed data inward. Code past the edge does not validate again.

```ts
const createInvoiceSchema = z.object({
  customerId: z.string(),
  items: z.array(z.object({ price: z.number(), qty: z.number().int() })),
})

type CreateInvoiceInput = z.infer<typeof createInvoiceSchema>
```

## Errors

Services and utils throw. The route handler, server action, or React error boundary is the only place that catches.

```ts
export const getUser = async (id: string) => {
  const user = await db.user.find(id)
  if (!user) throw new NotFoundError('user')
  return user
}
```

## Default libraries

Reach for these first, and do not add another dependency for a job one of them already does:

- **Tailwind CSS** for styling.
- **Zod** for validation.
- **TanStack Query** for client-side server state. Do not fetch inside `useEffect`.

For anything else, including database access, use what the project already has. If the project has nothing for the job, ask before adding a dependency.

## Layout

```
src/
  components/
    login-form.tsx
  hooks/
    use-auth.ts
  services/
    auth.ts
  utils/
  types/
tests/
  hooks/
    use-auth.test.ts
  services/
    auth.test.ts
```

In Next.js, `app/` holds only the routing files the framework needs (`page.tsx`, `layout.tsx`, `route.ts`, and so on). Components, hooks, services, and utils still go in their layer folders.
