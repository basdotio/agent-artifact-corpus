# Real-World CLAUDE.md Examples

실제 프로덕션 프로젝트에서 사용된 CLAUDE.md 패턴. 블록별 best practice 추출.

---

## Table of Contents

1. [Supabase CLI Block Example](#supabase-cli-block)
2. [Environment Config Example](#environment-config)
3. [3-Layer Architecture Example](#3-layer-architecture)
4. [Auth System Example](#auth-system)
5. [SSOT & Type System Example](#ssot--type-system)
6. [Terminology Guide Example](#terminology-guide)
7. [Database Tables Example](#database-tables)
8. [Migration Policy Example](#migration-policy)
9. [API Integration Example](#api-integration)
10. [NOT TO DOs Example](#not-to-dos)
11. [Revalidation Example](#revalidation-strategy)

---

## Supabase CLI Block

```markdown
## Database Schema CLI Tool

**ALWAYS use the CLI to query database schema instead of reading the entire `types/database.types.ts` file (4600+ lines).**

npm run db:schema tables              # List all tables (47)
npm run db:schema table students      # Show specific table schema
npm run db:schema enums               # List all enums (31)
npm run db:schema enum user_role      # Show specific enum values
npm run db:schema search center       # Search for tables/enums

**See:** `scripts/README.md` for detailed usage guide.
```

**Key pattern**: 파일 크기(4600+ lines)를 명시하여 "왜 직접 읽으면 안 되는지" 이유를 설명. 테이블/enum 개수도 명시하여 규모감 제공.

---

## Environment Config

```markdown
### Supabase Environment Configuration

**Development Database:**
- Project ID: `gcrrmqifnhumylocvzhy`
- Project Name: `place-development`
- Region: `ap-southeast-1`

**Production Database:**
- Project ID: `gwvnuqhuujydtguczijd`
- Project Name: `place-production`
- Region: `ap-southeast-1`

**Environment Switching:**
- Use `supabase link --project-ref gcrrmqifnhumylocvzhy` to connect to DEV
- Use `supabase link --project-ref gwvnuqhuujydtguczijd` to connect to PROD
- Check current linked project with `supabase status`
```

**Key pattern**: Dev/Prod를 병렬 구조로 정리. 전환 명령어 바로 복사 가능.

---

## 3-Layer Architecture

```markdown
### Data Layer Architecture - SOLID Principles (MANDATORY)

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

#### Forbidden Patterns

// FORBIDDEN - Direct Supabase in components
import { createClient } from '@/lib/supabase/client'
function MyComponent() { const supabase = createClient() }

// FORBIDDEN - Inline TanStack Query in components
function MyComponent() {
  const { data } = useQuery({
    queryKey: ['students'],
    queryFn: async () => { const supabase = createClient() }
  })
}
```

**Key pattern**: ASCII art로 레이어 시각화. 각 레이어에 "허용/금지" 명시. FORBIDDEN 패턴 코드 예시.

---

## Auth System

```markdown
### Authentication - JWT Cookie System

**NEVER** use direct `supabase.auth.getUser()` or `supabase.auth.getSession()`.

**Quick Reference:**
// Client-side (React)
import { useUserStore } from '@/stores/user-store'
const user = useUserStore((state) => state.user)

// API Routes (recommended)
import { withCenter, withCenterAdmin } from '@/lib/auth/api-middleware'
export const GET = withCenter(async (request, auth) => {
  const centerId = auth.centerId!  // guaranteed non-null
})

// Server Components
import { getServerAuth } from '@/lib/auth/server'
const auth = await getServerAuth()

**Core Files:** `/lib/auth/README.md`, `/lib/auth/permission-utils.tsx`
```

**Key pattern**: "NEVER use X" 먼저 → 바로 올바른 패턴 제시. Client/API/Server 세 가지 컨텍스트 모두 커버.

---

## SSOT & Type System

```markdown
### Type System - ALWAYS Import Types

**NEVER** manually define database types. Always import from centralized type system.

// CORRECT
import { User, Class, Student } from '@/types/models'
import { UserRole, ClassStatus } from '@/types/enums'

// WRONG
interface User { id: string; ... }
type UserRole = 'headquarter' | 'branch'

**Type Sources:**
- `/types/database.types.ts` - Auto-generated from Supabase (source of truth)
- `/types/models.ts` - All table types (Row, Insert, Update)
- `/types/enums.ts` - All database enums

### Common Field Name Mistakes

| Mistake | Correct |
|---------|---------|
| `users.center_id` | Use `center_users` junction table |
| `students.name` | `students.full_name` |
| `payment_date` | `paid_at` |
| `max_students` | `student_limit` |
| `centers.address` | REMOVED - Use `centers.address_id` (JOIN `addresses`) |
```

**Key pattern**: CORRECT/WRONG 코드 예시. Type Sources 3-line 정리. Common Mistakes 테이블로 자주 틀리는 필드 매핑.

---

## Terminology Guide

```markdown
## Terminology Guide

| Code/DB | Korean | English | Description |
|---------|--------|---------|-------------|
| **center** | 가맹점 | Franchise Center | 개별 영어 학원 |
| **center admin** | 가맹점주 | Center Owner | 가맹점 관리자 |
| **branch** | 지사 | Regional Branch | 지역 지사 |
| **headquarter** | 본사 | Headquarters | 본사 |

**Key Points:**
- **Code/Database**: English terms (`center`, `branch`, `headquarter`)
- **UI/Messages**: Korean terms (가맹점, 지사, 본사)
- **Never** use "센터" in UI - always "가맹점"
```

**Key pattern**: Code↔Korean↔English 3열 매핑. "Never use" 규칙으로 금지 용어 명시.

---

## Database Tables

```markdown
### Core Tables (34 tables)

**User & Organization Management**
- **users**: User accounts with role-based permissions (UUID pk), **address_id references addresses**
- **centers**: Individual academy locations, **address_id references addresses**
- **center_users**: Center staff membership with is_admin and is_approved flags

**Academic Operations**
- **classes**: Template role - days_of_week[] for schedule, student_limit (not max_students)
- **class_sessions**: Individual session instances, status ('scheduled', 'in_progress', 'completed', 'canceled')

**Financial**
- **tuition_bills**: Monthly billing records linked to payments
```

**Key pattern**: 카테고리별 그룹핑. Junction table 관계 설명. 자주 틀리는 필드명 인라인 교정 (`student_limit (not max_students)`).

---

## Migration Policy

```markdown
### Database Migration Policy

**ALL database schema changes MUST be applied via Supabase CLI migrations.**

**NEVER:**
- Use Supabase MCP for schema changes
- Make manual changes in Supabase Dashboard
- Use SQL Editor in Dashboard for DDL operations

**ALWAYS:**
- `supabase migration new <description>` to create migration files
- Write SQL in `supabase/migrations/` directory
- `supabase db push` to apply
- Commit migration files to Git
```

**Key pattern**: NEVER/ALWAYS 대비 구조로 명확한 규칙. 워크플로우 step-by-step.

---

## API Integration

```markdown
## Alimtalk Integration (카카오 알림톡)

**Path**: `/lib/alimtalk` | **Docs**: `/lib/alimtalk/README.md`

### Quick Start (3 Steps)

**1. Server Action (Backend)**
'use server'
import { sendAlimtalkAction } from '@/lib/actions/alimtalk-actions'
const result = await sendAlimtalkAction('1-4', variables, recipient, { centerId })

**2. UI Components (Client)**
import { AlimtalkSendButton } from '@/lib/alimtalk'
<AlimtalkSendButton templateCode="1-4" variables={...} recipient={...} />

### CRITICAL Rules
- CORRECT: `tuitionUrl: '/tuition/123'` (path only)
- WRONG: `tuitionUrl: 'https://placekey.kr/tuition/123'` (full URL)
```

**Key pattern**: Path + Docs 링크 먼저. 3-step quick start. CRITICAL Rules로 자주 틀리는 부분 강조.

---

## NOT TO DOs

```markdown
## NOT TO DOs

- Don't run `npm run dev` on your own (user will execute)
- Don't run `npm run build` unless instructed
- Never manually define database types - always import
- Never use direct Supabase auth calls - use JWT cookie system
- Never assume field names - always check `/spec/database-schema.md`
- Never import Supabase client in components - use hooks from `/hooks/`
- Never define TanStack Query hooks inline in components - extract to `/hooks/`
- Never call Supabase directly in hooks - import service functions from `/lib/services/`
- **NEVER use Supabase MCP or Dashboard for schema changes - ONLY use Supabase CLI migrations**
- **NEVER pass full URLs to alimtalk variables - ONLY use paths**
```

**Key pattern**: 일관된 prefix ("Don't" / "Never"). 올바른 대안 포함. 가장 critical한 항목 bold 처리.

---

## Revalidation Strategy

```markdown
## Data Revalidation

### Principle: All UI updates are immediate

**Modal submit flow:**
const mutation = useMutation({
  mutationFn: updateStudent,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['students', centerId] })
    toast.success('저장되었습니다')
    onClose()  // modal closes immediately
  }
})

**Server Action revalidation:**
'use server'
export async function updateAction(data) {
  // ... mutation
  revalidatePath('/students')
}
```

**Key pattern**: 원칙 한 줄 명시. Modal + Server Action 두 가지 패턴.
