# Enforce Data Layer Separation

**CRITICAL ARCHITECTURE RULE**: This project follows strict data layer separation principles based on SOLID and encapsulation.

## Architecture Rules (MUST FOLLOW)

### 1. Service Layer (`/lib/services/`)
- **All Supabase queries MUST be defined here**
- File naming: `{table-name}.ts` or `{feature-name}-service.ts`
- No Supabase client calls outside this layer
- Export pure functions that handle data operations
- **ALL functions MUST have explicit return types defined**
- **ALL async functions MUST return Promise<T> types**

**Type System Rules:**
- **Import types from `/types/models.ts` and `/types/enums.ts`** - NEVER define types inline
- **Reuse existing types whenever possible** - Check `/types/` before creating new types
- If new types are needed, define them in `/types/` directory first
- Use Type Helpers: `StudentRow`, `StudentInsert`, `StudentUpdate` from `/types/models.ts`

**Example structure:**
```typescript
// /lib/services/students.ts
import { createClient } from '@/lib/supabase/client'
import type { StudentRow, StudentInsert } from '@/types/models' // ✅ Import from centralized types

// ✅ CORRECT - Explicit return type with Promise<T>
export async function getStudents(centerId: number): Promise<StudentRow[]> {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('students')
    .select('*')
    .eq('center_id', centerId)

  if (error) throw error
  return data
}

// ✅ CORRECT - Return type defined
export async function createStudent(studentData: StudentInsert): Promise<StudentRow> {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('students')
    .insert(studentData)
    .select()
    .single()

  if (error) throw error
  return data
}

// ❌ WRONG - Missing return type
export async function deleteStudent(id: number) {
  // ...
}

// ❌ WRONG - Inline type definition
export async function updateStudent(id: number, data: { name: string }): Promise<any> {
  // Should import StudentUpdate from /types/models.ts
}
```

### 2. Hook Layer (`/hooks/`)
- **All TanStack Query hooks MUST be defined here**
- Import service functions from `/lib/services/`
- No direct Supabase calls allowed
- File naming: `use-{feature}-query.ts` or `use-{feature}.ts`
- **ALL hooks MUST have explicit return types defined**
- **Import types from `/types/` - NEVER define types inline**

**Type System Rules:**
- Use TanStack Query type helpers: `UseQueryResult<T>`, `UseMutationResult<T>`
- Import data types from `/types/models.ts`
- Define query key types properly with `as const`

**Example structure:**
```typescript
// /hooks/use-students-query.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { getStudents, createStudent } from '@/lib/services/students'
import type { StudentRow, StudentInsert } from '@/types/models' // ✅ Import from centralized types

export const STUDENTS_QUERY_KEYS = {
  all: ['students'] as const,
  list: (centerId: number) => [...STUDENTS_QUERY_KEYS.all, 'list', centerId] as const,
} as const

// ✅ CORRECT - Explicit return type
export function useStudentsQuery(centerId: number): UseQueryResult<StudentRow[], Error> {
  return useQuery({
    queryKey: STUDENTS_QUERY_KEYS.list(centerId),
    queryFn: () => getStudents(centerId),
    enabled: !!centerId,
  })
}

// ✅ CORRECT - Explicit return type for mutation
export function useCreateStudentMutation(): UseMutationResult<StudentRow, Error, StudentInsert> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createStudent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: STUDENTS_QUERY_KEYS.all })
    },
  })
}

// ❌ WRONG - Missing return type
export function useDeleteStudentMutation() {
  // ...
}

// ❌ WRONG - Inline type definition
export function useUpdateStudent(id: number): UseQueryResult<{ name: string }, Error> {
  // Should use StudentRow from /types/models.ts
}
```

### 3. Component Layer
- **Import hooks from `/hooks/` ONLY**
- **NO Supabase client imports**
- **NO TanStack Query hooks defined inline**
- Components should be clean and focused on UI logic

**Example structure:**
```typescript
// /components/students/student-list.tsx
import { useStudentsQuery, useCreateStudentMutation } from '@/hooks/use-students-query'

export function StudentList({ centerId }: { centerId: number }) {
  const { data: students, isLoading } = useStudentsQuery(centerId)
  const createMutation = useCreateStudentMutation()

  // Clean component code focused on UI
}
```

## Violations to Check

### ❌ FORBIDDEN Patterns:

1. **Direct Supabase in components:**
```typescript
// ❌ BAD - Component importing Supabase
import { createClient } from '@/lib/supabase/client'

function MyComponent() {
  const supabase = createClient()
  // ...
}
```

2. **Inline TanStack Query in components:**
```typescript
// ❌ BAD - Query defined in component
function MyComponent() {
  const { data } = useQuery({
    queryKey: ['students'],
    queryFn: async () => {
      const supabase = createClient()
      // ...
    }
  })
}
```

3. **Service functions in hooks:**
```typescript
// ❌ BAD - Service logic in hook file
export function useStudents() {
  return useQuery({
    queryKey: ['students'],
    queryFn: async () => {
      const supabase = createClient() // Should be in service layer!
      // ...
    }
  })
}
```

### ✅ CORRECT Patterns:

1. **Service → Hook → Component:**
```typescript
// ✅ GOOD - /lib/services/students.ts
export async function getStudents() { /* ... */ }

// ✅ GOOD - /hooks/use-students-query.ts
export function useStudentsQuery() {
  return useQuery({
    queryKey: ['students'],
    queryFn: getStudents, // Import from service
  })
}

// ✅ GOOD - Component
import { useStudentsQuery } from '@/hooks/use-students-query'
```

## Task Instructions

When this command is invoked:

1. **Scan the codebase for violations:**
   - Find components importing `@/lib/supabase/client`
   - Find components with inline `useQuery`/`useMutation` definitions
   - Find hooks with direct Supabase calls

2. **Refactor violations:**
   - Extract Supabase queries to `/lib/services/{table-name}.ts`
   - Extract TanStack Query hooks to `/hooks/use-{feature}-query.ts`
   - Update components to use the extracted hooks
   - Ensure proper query key management

3. **Report results:**
   - List all violations found
   - Show before/after code for each fix
   - Confirm all files follow the architecture

## Benefits of This Architecture

- **Separation of Concerns**: Data logic separated from UI logic
- **Reusability**: Service functions and hooks can be reused across components
- **Testability**: Easy to mock service functions in tests
- **Maintainability**: Changes to data layer don't affect components
- **Type Safety**: Centralized types and error handling
- **Cache Management**: Consistent query key patterns

## Quick Reference

```
┌─────────────────────────────────────────────┐
│ Component Layer (UI Logic)                  │
│ - Import hooks from /hooks/                 │
│ - NO Supabase, NO inline queries            │
└─────────────────┬───────────────────────────┘
                  │ imports
┌─────────────────▼───────────────────────────┐
│ Hook Layer (Query Management)               │
│ - TanStack Query hooks                      │
│ - Import service functions                  │
│ - NO Supabase client                        │
└─────────────────┬───────────────────────────┘
                  │ imports
┌─────────────────▼───────────────────────────┐
│ Service Layer (Data Access)                 │
│ - Pure functions with Supabase queries      │
│ - File: /lib/services/{table}.ts            │
│ - ONLY place for Supabase client            │
└─────────────────────────────────────────────┘
```

**This is a MANDATORY architecture pattern. All code MUST follow this structure.**

---

## TypeScript & Type System Rules (MANDATORY)

### 1. Return Type Annotations

**ALL functions and hooks MUST have explicit return types.**

```typescript
// ✅ CORRECT - Explicit return types
export async function getStudent(id: number): Promise<StudentRow | null> { }
export function useStudentsQuery(centerId: number): UseQueryResult<StudentRow[], Error> { }
export function calculateTotal(items: number[]): number { }

// ❌ WRONG - Missing return types
export async function getStudent(id: number) { }
export function useStudentsQuery(centerId: number) { }
export function calculateTotal(items: number[]) { }
```

### 2. Promise Types for Async Functions

**ALL async functions MUST return Promise<T> types explicitly.**

```typescript
// ✅ CORRECT
export async function fetchData(): Promise<StudentRow[]> {
  // ...
}

export async function deleteItem(id: number): Promise<void> {
  // ...
}

// ❌ WRONG - Implicit return type
export async function fetchData() {
  // ...
}
```

### 3. Centralized Type Definitions

**ALL types MUST be defined in `/types/` directory. NEVER define types inline.**

**Type Sources:**
- `/types/database.types.ts` - Auto-generated from Supabase (source of truth)
- `/types/models.ts` - All table types (Row, Insert, Update)
- `/types/enums.ts` - All database enums
- `/types/` - Custom application types

```typescript
// ✅ CORRECT - Import from centralized types
import type { StudentRow, StudentInsert, StudentUpdate } from '@/types/models'
import type { UserRole, ClassStatus } from '@/types/enums'

export async function createStudent(data: StudentInsert): Promise<StudentRow> {
  // ...
}

// ❌ WRONG - Inline type definition
export async function createStudent(data: {
  full_name: string
  center_id: number
  // ...
}): Promise<any> {
  // ...
}

// ❌ WRONG - Any type
export async function getData(): Promise<any> {
  // ...
}
```

### 4. Type Reuse Policy

**ALWAYS check existing types before creating new ones.**

**Before creating a new type:**
1. Check `/types/models.ts` for table types
2. Check `/types/enums.ts` for enum types
3. Search for similar types in `/types/` directory
4. Only create new types if absolutely necessary

```typescript
// ✅ CORRECT - Reuse existing types
import type { StudentRow } from '@/types/models'

type StudentWithContacts = StudentRow & {
  contacts: ContactRow[]
}

// ❌ WRONG - Duplicating existing type
type Student = {
  id: number
  full_name: string
  center_id: number
  // ... duplicating StudentRow
}
```

### 5. ESLint Rules (Recommended)

Add these rules to `eslintrc.json` to enforce type annotations:

```json
{
  "rules": {
    "@typescript-eslint/explicit-function-return-type": ["error", {
      "allowExpressions": true,
      "allowTypedFunctionExpressions": true
    }],
    "@typescript-eslint/explicit-module-boundary-types": "error",
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/consistent-type-imports": ["error", {
      "prefer": "type-imports"
    }]
  }
}
```

**What these rules enforce:**
- `explicit-function-return-type` - Requires return types on functions
- `explicit-module-boundary-types` - Requires return types on exported functions
- `no-explicit-any` - Prevents use of `any` type
- `consistent-type-imports` - Enforces `import type` for type-only imports

### 6. Quick Checklist

Before committing code, verify:

- [ ] All functions have explicit return types
- [ ] All async functions return `Promise<T>`
- [ ] All hooks have `UseQueryResult<T>` or `UseMutationResult<T>` types
- [ ] All types are imported from `/types/` directory
- [ ] No inline type definitions
- [ ] No `any` types used
- [ ] Types are reused when possible
- [ ] New types (if needed) are defined in `/types/` first
