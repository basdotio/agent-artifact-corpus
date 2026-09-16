# Check Data Layer Violations

Scan the codebase for violations of the data layer separation architecture and report them.

## What to Check

### 1. Component violations:
   - Search for `import.*createClient.*from.*@/lib/supabase/client` in component files
   - Search for `useQuery` or `useMutation` defined directly in component files (not imported)

### 2. Hook violations:
   - Search for `createClient()` calls in `/hooks/` files
   - Hooks should only import service functions, not call Supabase directly

### 3. Service organization:
   - Check if service functions are properly organized in `/lib/services/`
   - Verify proper file naming: `{table-name}.ts` or `{feature-name}-service.ts`

### 4. TypeScript violations:
   - Functions without explicit return types
   - Async functions without `Promise<T>` return types
   - Inline type definitions (not imported from `/types/`)
   - Usage of `any` type
   - Duplicate type definitions that already exist in `/types/`

## Search Patterns

Use Grep to find violations:

```bash
# === Architecture Violations ===

# Find components importing Supabase client
grep -r "import.*createClient.*from.*@/lib/supabase/client" app/ components/ --include="*.tsx" --include="*.ts"

# Find inline queries in components (check for useQuery not from import)
grep -r "useQuery({" app/ components/ --include="*.tsx" -A 3

# Find createClient in hooks (should be in services only)
grep -r "createClient()" hooks/ --include="*.ts" --include="*.tsx"

# Find service functions not in /lib/services/
grep -r "from('.*')" app/ components/ hooks/ --include="*.tsx" --include="*.ts"

# === TypeScript Violations ===

# Find functions without return types (async functions)
grep -rE "export async function [a-zA-Z]+\([^)]*\)\s*{" lib/services/ hooks/ --include="*.ts" --include="*.tsx"

# Find functions without return types (regular functions)
grep -rE "export function [a-zA-Z]+\([^)]*\)\s*{" lib/services/ hooks/ --include="*.ts" --include="*.tsx"

# Find usage of 'any' type
grep -r ": any" lib/services/ hooks/ --include="*.ts" --include="*.tsx"

# Find inline type definitions (type/interface not in /types/)
grep -r "^type [A-Z]" app/ components/ lib/services/ hooks/ --include="*.ts" --include="*.tsx"
grep -r "^interface [A-Z]" app/ components/ lib/services/ hooks/ --include="*.ts" --include="*.tsx"
```

## Report Format

For each violation found, report:

1. **File path and line number**
2. **Violation type** (component with Supabase, inline query, etc.)
3. **Current code snippet**
4. **Recommended fix** (which service file to create/use, which hook to create/use)

## Example Report

```
❌ VIOLATION FOUND: Direct Supabase in Component
File: app/students/page.tsx:15
Current:
  import { createClient } from '@/lib/supabase/client'
  const supabase = createClient()

Recommended Fix:
  1. Create service: /lib/services/students.ts with getStudents()
  2. Create hook: /hooks/use-students-query.ts with useStudentsQuery()
  3. Import hook in component: import { useStudentsQuery } from '@/hooks/use-students-query'

---

❌ VIOLATION FOUND: Inline Query in Component
File: components/class-list.tsx:23
Current:
  const { data } = useQuery({
    queryKey: ['classes'],
    queryFn: async () => { /* ... */ }
  })

Recommended Fix:
  1. Move query to: /hooks/use-classes-query.ts
  2. Import hook: import { useClassesQuery } from '@/hooks/use-classes-query'

---

❌ VIOLATION FOUND: Missing Return Type
File: lib/services/students.ts:45
Current:
  export async function getStudents(centerId: number) {
    // ...
  }

Recommended Fix:
  export async function getStudents(centerId: number): Promise<StudentRow[]> {
    // ...
  }

---

❌ VIOLATION FOUND: Inline Type Definition
File: hooks/use-students-query.ts:12
Current:
  type Student = {
    id: number
    full_name: string
    // ...
  }

Recommended Fix:
  1. Check if StudentRow exists in /types/models.ts
  2. If yes, import it: import type { StudentRow } from '@/types/models'
  3. If no, create it in /types/models.ts first, then import

---

❌ VIOLATION FOUND: Usage of 'any' Type
File: lib/services/reports.ts:78
Current:
  export async function getReport(id: number): Promise<any> {
    // ...
  }

Recommended Fix:
  1. Check /types/models.ts for ReportRow type
  2. Replace 'any' with proper type: Promise<ReportRow>
```

## Actions

After reporting violations:

1. Ask user if they want to fix all violations automatically
2. If yes, proceed with refactoring following the enforce-data-layer.md patterns
3. Create necessary service files in `/lib/services/`
4. Create necessary hook files in `/hooks/`
5. Update components to use the new hooks
6. Run type check to verify no errors

**Note**: This command only CHECKS and REPORTS. Use `/enforce-data-layer` to actually fix violations.
