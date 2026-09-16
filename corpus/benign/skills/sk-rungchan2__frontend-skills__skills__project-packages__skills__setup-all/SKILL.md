---
name: setup-all
description: 새 프론트엔드 프로젝트 초기 세팅 시 표준 패키지 설치 + 중앙 setup 파일들을 한 번에 적용하는 마스터 스킬. tailwind cn 유틸, dayjs KST, (추후) TanStack Query, Zustand, Supabase 클라이언트, Server Action/Form 패턴까지 묶어 처리. "프로젝트 초기 세팅", "표준 setup 박아줘", "lib 폴더 표준화", "패키지 표준 적용", "새 프로젝트 부트스트랩" 같은 요청에 트리거. shadcn init 직후 또는 새 Next.js 프로젝트 생성 직후 사용.
---

# Project Packages — 마스터 세팅

새 프로젝트(또는 표준화 안 된 기존 프로젝트)에 **본인의 표준 중앙 setup 일괄 적용**.

## 적용 대상 패턴

| # | 스킬 | 설치/생성 |
|---|------|----------|
| 1 | `tailwind-cn` | `clsx`, `tailwind-merge` + `lib/utils.ts` |
| 2 | `dayjs-kst` | `dayjs` + `lib/dayjs.ts` (KST + 한국어 locale + 헬퍼 5종) |
| 3 | `supabase-clients` | `@supabase/ssr` + client/server/service-role/middleware 4종 |
| 4 | `tanstack-query` | `@tanstack/react-query` + query-defaults / query-keys / QueryProvider |
| 5 | `zustand-store` | `zustand` + State/Actions 패턴 + user-store |
| 6 | `form-validation` | `react-hook-form` + `zod` + shadcn form 컴포넌트 + 표준 예시 폼 |
| 7 | `package-map` | (코드 생성 없음) 기능별 패키지 룩업 표만 참고 |

> `package-map`은 lookup 스킬이라 `setup-all`에서 자동 실행하지 않는다. 사용자가 패키지 결정 시점에 따로 호출.

## 워크플로우

### 1. 사전 점검

다음을 확인하고 사용자에게 보고:

```bash
# 프로젝트 루트 / 구조 / 패키지 매니저 식별
ls -la
cat package.json | head -30
ls components.json 2>/dev/null && echo "shadcn already initialized" || echo "shadcn NOT initialized"
```

확인 항목:
- `src/` 구조 vs 루트 직접
- 패키지 매니저 (pnpm / npm / yarn / bun)
- shadcn/ui 초기화 여부 (`components.json` 존재)
- 기존 `lib/utils.ts`, `lib/dayjs.ts` 유무

### 2. 사용자에게 적용 범위 확인

> "다음 항목을 적용합니다. 빼고 싶은 게 있으면 말씀해주세요:
> - [ ] tailwind-cn (lib/utils.ts)
> - [ ] dayjs-kst (lib/dayjs.ts)
> - [ ] supabase-clients (lib/supabase/* + middleware.ts)
> - [ ] tanstack-query (lib/query-* + providers/query-provider.tsx)
> - [ ] zustand-store (stores/user-store.ts)
> - [ ] form-validation (shadcn form + 예시 폼)"

기본은 전부 적용. 사용자가 일부 제외하면 그것만 건너뜀. 의존 관계:
- `zustand-store`의 user-store는 `supabase-clients`의 client를 import → 함께 적용 권장
- `form-validation`은 shadcn 초기화 필요 → `components.json` 없으면 먼저 `npx shadcn@latest init` 실행

### 3. 순서대로 하위 스킬 실행

각 하위 스킬의 SKILL.md를 직접 따라 실행한다. 하위 스킬은 다음 위치에 있다:

```
skills/project-packages/skills/
├── tailwind-cn/SKILL.md
├── dayjs-kst/SKILL.md
├── supabase-clients/SKILL.md
├── tanstack-query/SKILL.md
├── zustand-store/SKILL.md
└── form-validation/SKILL.md
```

권장 실행 순서: `tailwind-cn` → `dayjs-kst` → `supabase-clients` → `tanstack-query` → `zustand-store` → `form-validation`. (인프라 의존 관계 순서)

각 스킬은 자체 워크플로우와 `assets/` 안의 표준 파일을 갖고 있으므로, 이 마스터 스킬에서 내용을 중복 기술하지 않는다. 위치 결정/패키지 설치/파일 복사 단계는 각 SKILL.md를 그대로 따른다.

### 4. 통합 산출물 확인

모든 하위 스킬 적용 후:

```bash
# 생성된 파일 확인
ls -la lib/utils.ts lib/dayjs.ts 2>/dev/null || ls -la src/lib/utils.ts src/lib/dayjs.ts 2>/dev/null

# 설치된 패키지 확인
cat package.json | grep -E '"(clsx|tailwind-merge|dayjs)"'
```

### 5. CLAUDE.md 통합 블록 (선택)

사용자가 원하면 적용한 모든 스킬의 사용 규칙을 CLAUDE.md의 단일 "## 패키지 사용 규칙" 섹션으로 묶어 추가한다. 각 스킬의 규칙을 따로따로 박지 말고 한 섹션으로 정리:

```markdown
## 패키지 사용 규칙

### 스타일 (tailwind)
- className 결합은 `cn()` 사용. 직접 문자열 결합 금지.
- 통화 표시는 `formatCurrency()` 사용.

### 날짜 (dayjs)
- 모든 dayjs 호출은 `@/lib/dayjs`에서 import. 직접 `from "dayjs"` 금지.
- date-only 문자열은 `parseDateOnly()` 사용. `new Date()` 직접 호출 금지.

### Supabase
- 'use client': `@/lib/supabase/client`
- Server Component / Action / Route Handler: `@/lib/supabase/server` (await)
- 관리자/cron/webhook: `createServiceRoleClient()` (RLS 우회. 일반 흐름 금지)

### React Query
- queryKey는 `@/lib/query-keys`만 사용. 인라인 배열 금지.
- staleTime/gcTime은 컴포넌트에서 오버라이드 금지. SHORT_CACHE_CONFIG / REALTIME_CONFIG 사용.

### Zustand
- store는 State / Actions 인터페이스 분리, initialState 상수, reset() 포함.
- 컴포넌트에서는 selector 사용. store 전체 구독 금지.

### 폼
- react-hook-form + zod + shadcn Form 조합 강제. useState 기반 폼 금지.
- 타입은 `z.infer`로 도출. 별도 interface 금지.
- 서버 검증 에러는 `form.setError`로 매핑.
```

## 비-목표

- 이 스킬은 **개별 패턴 세부 결정을 하지 않는다.** 그건 각 하위 스킬의 책임.
- 이 스킬은 **shadcn 초기화(`shadcn init`)나 Next.js 프로젝트 생성을 대신 하지 않는다.** 이미 프로젝트가 있다는 가정.
