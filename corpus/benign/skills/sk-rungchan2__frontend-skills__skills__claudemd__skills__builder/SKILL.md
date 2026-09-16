---
name: builder
description: >
  CLAUDE.md 파일을 블록 단위로 생성, 검사, 정리하는 스킬.
  프로젝트의 기술 스택(Supabase, Next.js 등)을 감지하여 필요한 블록을 판단하고,
  누락된 블록을 알려주거나, 기존 내용을 표준 포맷으로 정리합니다.
  트리거: CLAUDE.md 만들어줘, CLAUDE.md 블록 추가, CLAUDE.md 검사해줘,
  CLAUDE.md 감사(audit), context file 정리, claudemd 빌드, claudemd builder.
  claude-refactoring 스킬과 다른 점: refactoring은 기존 파일 최적화에 집중,
  builder는 블록 정의 기반으로 생성/검사/정리를 수행.
---

# CLAUDE.md Builder

블록 단위로 CLAUDE.md를 생성, 검사, 정리하는 도구.

## Workflow Decision Tree

```
사용자 요청 분석
├─ "CLAUDE.md 만들어줘" / "생성"
│   └─ Mode: BUILD → Step 1 → Step 2 → Step 3
├─ "CLAUDE.md 검사해줘" / "audit"
│   └─ Mode: AUDIT → Step 1 → Step 4
├─ "블록 추가해줘" / "이 부분 정리해줘"
│   └─ Mode: PATCH → Step 1 → Step 5
└─ "CLAUDE.md 포맷 맞춰줘" / "정리"
    └─ Mode: FORMAT → Step 1 → Step 6
```

---

## Step 1: Tech Stack Detection

프로젝트 분석하여 필요한 블록 결정.

**Detect sources:**
- `package.json` — dependencies
- `tsconfig.json` — path aliases
- Directory structure — `/app`, `/lib/services`, `/hooks`, `/stores`, `/spec`
- Existing `CLAUDE.md` — current state

**Block requirement matrix:**

| Condition | Required Blocks |
|-----------|----------------|
| Always | Header, Tech Stack, NOT TO DOs |
| `@supabase/supabase-js` detected | Supabase, MCP & Migration, Database Tables, SSOT |
| `next` detected | Next.js Convention, Routing Convention |
| `@tanstack/react-query` detected | 3-Layer Architecture, Revalidation Strategy |
| `zustand` detected | Auth & User State |
| `/spec` directory exists | Spec Files |
| Korean UI project | Terminology |
| External API integration | API Integration |
| `/constants` or `/lib/constants` exists | Constants Strategy |

**Block definitions:** See [references/block-definitions.md](references/block-definitions.md) for all 18 blocks.

### Supabase CLI Setup (db-schema)

Supabase가 감지되면, `db:schema` CLI 스크립트 셋업 여부를 확인하고 없으면 설치를 제안.

**Check:**
1. `package.json`에 `"db:schema"` script 있는지 확인
2. `scripts/db-schema.ts` (또는 유사 파일) 존재 여부 확인

**Setup (없을 때):**
1. `scripts/db-schema.ts`를 프로젝트에 복사 — bundled script: [scripts/db-schema.ts](scripts/db-schema.ts)
2. `package.json`에 script 추가:
   ```json
   { "scripts": { "db:schema": "tsx scripts/db-schema.ts" } }
   ```
3. `tsx` dev dependency 확인: `pnpm add -D tsx` (없을 때만)

**Script 특성:**
- `types/database.types.ts`를 파싱하여 테이블/enum 정보를 추출
- 전체 파일(4000+ lines)을 context에 로드하지 않고 필요한 부분만 조회
- `DB_TYPES_PATH` 환경변수로 경로 커스터마이징 가능 (기본: `types/database.types.ts`)
- 대체 경로 자동 탐색: `src/types/`, `lib/`, `src/lib/`
- Commands: `tables`, `table <name>`, `enums`, `enum <name>`, `search <keyword>`

**CLAUDE.md Supabase Block에 반드시 포함:**
```markdown
**ALWAYS use the CLI to query database schema instead of reading `types/database.types.ts` directly.**

```bash
npm run db:schema tables              # List all tables
npm run db:schema table students      # Show specific table schema
npm run db:schema enums               # List all enums
npm run db:schema enum user_role      # Show specific enum values
npm run db:schema search center       # Search for tables/enums
```
```

---

## Step 2: BUILD — Generate CLAUDE.md

유저에게 블록별로 정보를 수집하여 CLAUDE.md 생성.

### Process

1. Step 1에서 감지한 Required Blocks 목록을 유저에게 보여줌
2. 각 블록별로 필요한 정보를 질문:

**Block-specific questions:**

| Block | Ask User |
|-------|----------|
| Header | 프로젝트 이름, 한 줄 설명 |
| Supabase | Dev/Prod project ref, CLI script 경로 |
| Auth | 인증 방식 (JWT cookie? Supabase Auth?), 유저 store 경로 |
| Terminology | 주요 비즈니스 용어 (Code↔Korean↔English) |
| 3-Layer | 서비스 경로, 훅 경로, 예외 허용 케이스 |
| Database Tables | 테이블 목록 (CLI로 조회 가능하면 자동 수집) |
| Routing | 라우팅 패턴 (역할 기반? 기능 기반?) |

3. 수집 완료 후 블록 템플릿에 정보 채워서 CLAUDE.md 생성

**Block templates:** See [references/block-templates.md](references/block-templates.md).

### Auto-Detection Shortcuts

코드베이스에서 자동으로 수집 가능한 정보:
- `package.json` → Tech Stack block
- `tsconfig.json` paths → Path Aliases
- `npm run db:schema tables` → Database Tables block (Supabase CLI 있을 때)
- `/app` directory scan → Routing Convention block
- `/lib/services` scan → Service layer file list
- `/types/enums.ts` → Enum list

---

## Step 3: Assemble & Output

수집한 블록을 아래 순서로 조합:

```
1.  Header
2.  Terminology (있으면)
3.  Tech Stack
4.  Supabase Config (있으면)
5.  Auth & User State (있으면)
6.  SSOT & Type System (있으면)
7.  3-Layer Architecture (있으면)
8.  Next.js Convention (있으면)
9.  Routing Convention (있으면)
10. Database Tables (있으면)
11. Constants Strategy (있으면)
12. Revalidation Strategy (있으면)
13. API Integration (있으면)
14. MCP & Migration (있으면)
15. Spec Files (있으면)
16. Project Structure (있으면)
17. NOT TO DOs
18. Reference Docs (있으면)
```

---

## Step 4: AUDIT — Inspect Existing CLAUDE.md

기존 CLAUDE.md를 블록 단위로 검사.

### Process

1. 기존 CLAUDE.md 읽기
2. Step 1의 tech stack detection 실행
3. 각 블록 존재 여부 + 품질 검사:

**Audit criteria per block:**

| Check | Description |
|-------|-------------|
| **EXISTS** | 블록이 존재하는가? |
| **COMPLETE** | 필수 항목이 모두 있는가? |
| **FORMAT** | 표준 포맷(코드 예시, 테이블)을 따르는가? |
| **EFFICIENT** | 불필요한 산문 없이 압축적인가? |
| **ACCURATE** | 실제 코드베이스와 일치하는가? |

4. Report 형식으로 출력:

```markdown
# CLAUDE.md Audit Report

## Summary
- Detected: Supabase, Next.js, TanStack Query, Zustand
- Required blocks: 14 / Found: 9 / Missing: 5

## Missing Blocks
1. **Revalidation Strategy** — TanStack Query 사용 중이나 revalidation 패턴 미정의
2. **Constants Strategy** — /lib/constants 디렉토리 존재하나 블록 없음

## Improvement Needed
1. **Supabase Block** — Dev project ref 누락
2. **3-Layer Block** — Forbidden patterns 코드 예시 없음

## Redundancies
1. Environment Configuration 섹션이 2회 중복
```

**Detailed checklist:** See [references/audit-checklist.md](references/audit-checklist.md).

---

## Step 5: PATCH — Add/Update Specific Blocks

특정 블록만 추가하거나 업데이트.

### Process

1. 유저가 원하는 블록 확인
2. 해당 블록의 template 로드 ([references/block-templates.md](references/block-templates.md))
3. 필요한 정보 수집 (질문 또는 코드베이스 스캔)
4. 블록 생성 후 기존 CLAUDE.md의 올바른 위치에 삽입

**Insertion order rule:** Step 3의 순서를 따름. 이미 있는 블록 사이에 올바른 위치에 삽입.

---

## Step 6: FORMAT — Reformat Existing Content

기존 내용의 정보는 유지하면서 표준 포맷으로 변환.

### Formatting Rules

| Pattern | Before | After |
|---------|--------|-------|
| Prose → Code | 장황한 설명 | `// CORRECT` / `// WRONG` 예시 |
| Prose → Table | 나열형 텍스트 | `\| Mistake \| Correct \|` 테이블 |
| Duplicate → Single | 같은 정보 2회 | 한 곳에 통합 |
| Vague → Specific | "타입 폴더에서 import" | `import { X } from '@/types/models'` |
| Verbose → Compressed | 72 token 설명 | 28 token 코드 예시 |

### Section Order

기존 섹션을 Step 3의 블록 순서로 재배열. 블록 이름과 정확히 일치하지 않아도 내용 기반으로 매핑.

---

## Real Examples

실제 프로덕션 프로젝트의 CLAUDE.md에서 추출한 best practice 모음.

**See:** [references/real-examples.md](references/real-examples.md) — 블록별 실제 사용 예시와 key patterns.

---

## Quick Reference: Block Summary

| # | Block | Required | Key Content |
|---|-------|----------|-------------|
| 1 | Header | Always | 프로젝트명 + 1줄 설명 |
| 2 | Terminology | Korean UI | Code↔Korean↔English 매핑 |
| 3 | Tech Stack | Always | Framework, UI, State, Path Aliases |
| 4 | Supabase | Supabase | CLI 명령어, Dev/Prod ref |
| 5 | Auth | Auth system | NEVER/CORRECT 패턴, 유저 store |
| 6 | SSOT | Types exist | Type sources, enum workflow, field mistakes |
| 7 | 3-Layer | TanStack Query | Layer diagram, forbidden patterns |
| 8 | Next.js | Next.js | Server Action 우선, API Route 예외 |
| 9 | Routing | App Router | Route 패턴, dynamic routes |
| 10 | Database Tables | Supabase | 카테고리별 테이블 목록 |
| 11 | Constants | Constants dir | 상수 파일 구조 |
| 12 | Revalidation | TanStack Query | Optimistic update, invalidation |
| 13 | API Integration | External APIs | Research first, quick start |
| 14 | MCP & Migration | Supabase | NEVER MCP, ALWAYS CLI |
| 15 | Spec Files | Spec dir | 기획 문서 목록 |
| 16 | Project Structure | Large project | 디렉토리 트리 |
| 17 | NOT TO DOs | Always | Anti-patterns with alternatives |
| 18 | Reference Docs | Docs exist | 상세 문서 링크 |
