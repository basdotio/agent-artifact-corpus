---
name: supabase-clients
description: Next.js 프로젝트에 Supabase 클라이언트 표준 4종 세트를 한 번에 세팅. 브라우저용 client, 서버용 server, RLS 우회 service-role, 그리고 세션 갱신 + 보호 라우트 리다이렉트 middleware를 lib/supabase/ 아래에 박는다. "supabase 클라이언트 세팅", "supabase ssr 셋업", "lib/supabase 만들어줘", "supabase middleware 추가", "service role 클라이언트 추가" 등에 트리거. database.types.ts(Database 제네릭)는 별도 supabase:initial-setting 스킬로 생성하는 것을 가정.
---

# Supabase 클라이언트 4종 세트

`@supabase/ssr` 기반 Next.js 프로젝트의 표준 클라이언트 분리.

## 왜 이 분리가 필요한가

| 환경 | 사용할 클라이언트 | 이유 |
|-----|----------------|-----|
| `'use client'` 컴포넌트 / hooks | `client.ts`의 `createClient()` | 브라우저 cookie에서 세션 읽기 |
| Server Component / Route Handler / Server Action | `server.ts`의 `createClient()` | Next 서버 cookies API 사용 |
| Cron / Webhook / 관리자 작업 | `service-role.ts`의 `createServiceRoleClient()` | RLS 우회 필요 |
| 모든 요청 진입점 (세션 갱신) | `middleware.ts`의 `updateSession()` | 세션 자동 갱신 + 보호 라우트 |

잘못된 클라이언트를 사용하면 세션이 안 잡히거나, RLS가 막거나, 브라우저에 service key가 노출되는 보안 사고로 이어진다.

## 워크플로우

### 1. 패키지 설치

```bash
pnpm add @supabase/ssr @supabase/supabase-js
```

### 2. 위치 결정

| 프로젝트 구조 | 베이스 경로 |
|------------|----------|
| `src/` 구조 | `src/lib/supabase/` |
| 루트 직접 | `lib/supabase/` |

루트 middleware는 항상 프로젝트 루트의 `middleware.ts`.

### 3. 파일 생성

`assets/` 안의 5개 파일을 다음과 같이 배치:

| asset | 대상 위치 |
|-------|---------|
| `client.ts` | `lib/supabase/client.ts` |
| `server.ts` | `lib/supabase/server.ts` |
| `service-role.ts` | `lib/supabase/service-role.ts` |
| `middleware.ts` | `lib/supabase/middleware.ts` |
| `root-middleware.ts` | `middleware.ts` (프로젝트 루트) |

> ⚠️ `Database` 제네릭 타입은 `@/types/database.types`에서 import. 이 파일이 없으면 `supabase:initial-setting` 스킬로 먼저 생성하거나, 임시로 import 라인을 주석 처리하고 나중에 채운다.

### 4. 환경변수 점검

`.env.local`에 다음이 있어야 한다:

```env
NEXT_PUBLIC_SUPABASE_URL=https://...supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...    # 서버 전용. NEXT_PUBLIC_ 절대 금지.
```

없으면 사용자에게 안내하고 추가하도록 함.

### 5. 보호 라우트 커스터마이즈

`assets/middleware.ts`의 보호 정책은 **`/auth`, `/error` 외 모든 경로 인증 필요**가 기본값.
프로젝트마다 공개 페이지(`/`, `/pricing` 등)가 있을 수 있으니 사용자에게:

> "현재 기본은 `/auth`, `/error`를 제외한 모든 경로에서 로그인을 요구합니다. 공개 페이지가 있다면 알려주세요 — 미들웨어에 화이트리스트로 추가하겠습니다."

### 6. CLAUDE.md 사용 규칙 (선택)

```markdown
## Supabase 클라이언트 사용 규칙

- `'use client'` / hooks / store: `import { createClient } from "@/lib/supabase/client"`
- Server Component / Route Handler / Server Action: `import { createClient } from "@/lib/supabase/server"` (await 호출)
- Cron / webhook / 관리자 백그라운드 작업: `createServiceRoleClient()` (RLS 우회. 일반 요청 흐름 금지)
- 새 보호 라우트가 추가되면 `lib/supabase/middleware.ts`의 화이트리스트 검토
```

## 산출물

- `lib/supabase/{client,server,service-role,middleware}.ts`
- 루트 `middleware.ts`
- (선택) CLAUDE.md 사용 규칙 블록

## 비-목표

- 이 스킬은 **`Database` 타입을 생성하지 않는다.** `supabase:initial-setting`이 그 역할.
- 이 스킬은 **RLS 정책이나 마이그레이션을 만들지 않는다.**
- RLS 에러 자동 토스트/Sentry 통합 같은 고급 기능은 의도적으로 제외 (의존성 단순화).
