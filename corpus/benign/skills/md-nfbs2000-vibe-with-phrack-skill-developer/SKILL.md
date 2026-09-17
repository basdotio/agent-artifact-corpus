---
name: skill-developer
# prettier-ignore
description: Claude Code 스킬 생성 및 관리. 스킬 구조, 트리거, 훅, skill-rules.json 작업을 다룹니다.
---

# 스킬 개발자 가이드

## 목적

Anthropic의 공식 베스트 프랙티스를 준수하면서, 자동 활성화 시스템을 갖춘 Claude Code 스킬을 만들고 관리하기 위한 종합 가이드입니다. 500줄 규칙과 점진적 공개(Progressive Disclosure) 패턴을 포함합니다.

## 이 스킬을 사용할 때

다음과 같은 내용을 언급하면 자동 활성화됩니다:
- 스킬 생성 또는 추가
- 스킬 트리거나 규칙 수정
- 스킬 활성화 동작 이해
- 스킬 활성화 문제 디버깅
- skill-rules.json 작업
- 훅 시스템 메커니즘
- Claude Code 베스트 프랙티스
- 점진적 공개
- YAML 프론트매터
- 500줄 규칙

---

## 시스템 개요

### 이중 훅 아키텍처

**1. UserPromptSubmit 훅** (선제 제안)
- **파일**: `.claude/hooks/skill-activation-prompt.ts`
- **트리거 시점**: Claude가 사용자 프롬프트를 보기 *전*
- **목적**: 키워드 + 의도 패턴을 기반으로 관련 스킬 제안
- **방법**: 포맷된 알림을 컨텍스트로 주입 (stdout → Claude 입력)
- **사용 사례**: 주제 기반 스킬, 암묵적인 업무 감지

**2. Stop 훅 - 에러 처리 리마인더** (부드러운 알림)
- **파일**: `.claude/hooks/error-handling-reminder.ts`
- **트리거 시점**: Claude가 응답을 *마친 후*
- **목적**: 작성한 코드의 에러 처리를 스스로 점검하도록 부드럽게 상기
- **방법**: 수정된 파일의 위험 패턴을 분석하고 필요 시 알림 표시
- **사용 사례**: 워크플로우를 막지 않고 에러 처리 주의 환기

**방침 변경 (2025-10-27):** Sentry/에러 처리를 위해 PreToolUse에서 블로킹하는 방식은 중단했습니다. 대신 워크플로우를 방해하지 않으면서도 품질 인식을 유지할 수 있도록, 응답 이후에 부드러운 리마인더를 사용합니다.

### 설정 파일

**위치**: `.claude/skills/skill-rules.json`

다음을 정의합니다:
- 모든 스킬과 트리거 조건
- 강제 수준 (block, suggest, warn)
- 파일 경로 패턴 (glob)
- 콘텐츠 감지 패턴 (regex)
- 건너뛰기 조건 (세션 추적, 파일 마커, 환경 변수)

---

## 스킬 유형

### 1. 가드레일 스킬

**목적:** 치명적인 실수를 막기 위한 필수 베스트 프랙티스 강제

**특징:**
- Type: `"guardrail"`
- Enforcement: `"block"`
- Priority: `"critical"` 또는 `"high"`
- 스킬 사용 전까지 파일 편집 차단
- 흔한 실수 방지 (컬럼명, 치명적 오류 등)
- 세션 인지 (같은 세션에서 반복 알림 없음)

**예시:**
- `database-verification` – Prisma 쿼리 전 테이블/컬럼명 확인
- `frontend-dev-guidelines` – React/TypeScript 패턴 강제

**사용 시점:**
- 런타임 오류를 유발하는 실수
- 데이터 무결성 우려
- 치명적인 호환성 이슈

### 2. 도메인 스킬

**목적:** 특정 영역에 대한 종합적인 지침 제공

**특징:**
- Type: `"domain"`
- Enforcement: `"suggest"`
- Priority: `"high"` 또는 `"medium"`
- 권장 사항 위주, 강제 아님
- 주제/도메인에 특화
- 상세 문서 제공

**예시:**
- `backend-dev-guidelines` – Node.js/Express/TypeScript 패턴
- `frontend-dev-guidelines` – React/TypeScript 베스트 프랙티스
- `error-tracking` – Sentry 통합 가이드

**사용 시점:**
- 깊은 지식이 필요한 복잡한 시스템
- 베스트 프랙티스 문서화
- 아키텍처 패턴
- How-to 가이드

---

## 빠른 시작: 새로운 스킬 만들기

### 1단계: 스킬 파일 생성

**위치:** `.claude/skills/{skill-name}/SKILL.md`

**템플릿:**
```markdown
---
name: my-new-skill
description: Brief description including keywords that trigger this skill. Mention topics, file types, and use cases. Be explicit about trigger terms.
---

# My New Skill

## Purpose
What this skill helps with

## When to Use
Specific scenarios and conditions

## Key Information
The actual guidance, documentation, patterns, examples
```

**베스트 프랙티스:**
- ✅ **Name**: 소문자 + 하이픈, 가능하면 동명사 형태(verb + -ing)
- ✅ **Description**: 모든 트리거 키워드/문구 포함 (최대 1024자)
- ✅ **Content**: 500줄 이하 (세부 내용은 리소스 파일에 분리)
- ✅ **Examples**: 실제 코드 예시 제공
- ✅ **Structure**: 명확한 헤딩, 목록, 코드 블록

### 2단계: skill-rules.json에 추가

[SKILL_RULES_REFERENCE.md](SKILL_RULES_REFERENCE.md)에 전체 스키마가 있습니다.

**기본 템플릿:**
```json
{
  "my-new-skill": {
    "type": "domain",
    "enforcement": "suggest",
    "priority": "medium",
    "promptTriggers": {
      "keywords": ["keyword1", "keyword2"],
      "intentPatterns": ["(create|add).*?something"]
    }
  }
}
```

### 3단계: 트리거 테스트

**UserPromptSubmit 테스트:**
```bash
echo '{"session_id":"test","prompt":"your test prompt"}' | \
  npx tsx .claude/hooks/skill-activation-prompt.ts
```

**PreToolUse 테스트:**
```bash
cat <<'EOF' | npx tsx .claude/hooks/skill-verification-guard.ts
{"session_id":"test","tool_name":"Edit","tool_input":{"file_path":"test.ts"}}
EOF
```

### 4단계: 패턴 다듬기

테스트 결과를 바탕으로:
- 누락된 키워드 추가
- 거짓 양성을 줄이도록 의도 패턴 정교화
- 파일 경로 패턴 조정
- 실제 파일 콘텐츠로 정규식 검증

### 5단계: Anthropic 베스트 프랙티스 준수

✅ SKILL.md를 500줄 이하로 유지  
✅ 리소스 파일을 활용한 점진적 공개 적용  
✅ 100줄 넘는 리소스에는 목차 추가  
✅ 트리거 키워드를 포함한 상세 설명 작성  
✅ 문서화 전 실제 시나리오 3건 이상 테스트  
✅ 실제 사용에 맞춰 지속적으로 개선

---

## 강제 수준

### BLOCK (치명적 가드레일)

- Edit/Write 도구 실행 자체를 막음
- 훅이 종료 코드 2 반환 → stderr 메시지를 Claude가 확인
- Claude는 메시지를 확인하고 스킬을 사용한 뒤 다시 시도
- **용도**: 치명적 실수, 데이터 무결성, 보안 이슈

**예시:** 데이터베이스 컬럼명 검증

### SUGGEST (권장)

- Claude가 프롬프트를 보기 전에 알림 주입
- 관련 스킬 인지 유도
- 강제 아님, 권고용
- **용도**: 도메인 가이드, 베스트 프랙티스, 사용법 안내

**예시:** 프론트엔드 개발 지침

### WARN (선택)

- 낮은 우선순위의 제안
- 권고용, 강제 거의 없음
- **용도**: 있으면 좋은 정보, 참고용 알림

**드물게 사용** – 대부분 BLOCK 또는 SUGGEST로 충분합니다.

---

## 건너뛰기 조건 및 사용자 제어

### 1. 세션 추적

**목적:** 같은 세션에서 반복 알림 방지

**동작 방식:**
- 첫 번째 편집 → 훅이 블록하고 세션 상태 기록
- 같은 세션 두 번째 편집 → 훅이 허용
- 다른 세션 → 다시 블록

**상태 파일:** `.claude/hooks/state/skills-used-{session_id}.json`

### 2. 파일 마커

**목적:** 검증 완료 파일을 영구적으로 건너뛰기

**마커:** `// @skip-validation`

**사용 예:**
```typescript
// @skip-validation
import { PrismaService } from './prisma';
// This file has been manually verified
```

**주의:** 남용 시 가드레일 목적이 무력화됩니다.

### 3. 환경 변수

**목적:** 긴급 비활성화, 임시 우회

**전역 비활성화:**
```bash
export SKIP_SKILL_GUARDRAILS=true  # Disables ALL PreToolUse blocks
```

**스킬별 비활성화:**
```bash
export SKIP_DB_VERIFICATION=true
export SKIP_ERROR_REMINDER=true
```

---

## 테스트 체크리스트

새 스킬을 만들 때 다음을 확인하세요:

- [ ] `.claude/skills/{name}/SKILL.md` 파일 생성
- [ ] 이름과 설명이 포함된 올바른 프론트매터
- [ ] `skill-rules.json`에 항목 추가
- [ ] 실제 프롬프트로 키워드 테스트
- [ ] 다양한 문장으로 의도 패턴 테스트
- [ ] 실제 파일 경로로 glob 패턴 검증
- [ ] 파일 콘텐츠로 정규식 검증
- [ ] (가드레일인 경우) 블록 메시지가 명확하고 실행 가능한가?
- [ ] 건너뛰기 조건이 적절히 설정되었는가?
- [ ] 우선순위가 중요도와 일치하는가?
- [ ] 테스트에서 거짓 양성 없음
- [ ] 테스트에서 거짓 음성 없음
- [ ] 성능 허용 범위 내 (<100ms 또는 <200ms)
- [ ] JSON 문법 검증: `jq . skill-rules.json`
- [ ] **SKILL.md가 500줄 이하인지** ⭐
- [ ] 필요 시 리소스 파일 생성
- [ ] 100줄 초과 리소스에 목차 추가

---

## 참고 파일

주제별 세부 정보는 다음을 참조하세요:

### [TRIGGER_TYPES.md](TRIGGER_TYPES.md)
모든 트리거 유형 완전 가이드:
- 키워드 트리거 (명시적 주제 매칭)
- 의도 패턴 (암시적 행동 감지)
- 파일 경로 트리거 (glob 패턴)
- 콘텐츠 패턴 (파일 내 regex)
- 각 유형별 베스트 프랙티스와 예시
- 흔한 실수와 테스트 전략

### [SKILL_RULES_REFERENCE.md](SKILL_RULES_REFERENCE.md)
skill-rules.json 완전 스키마:
- 전체 TypeScript 인터페이스 정의
- 필드별 설명
- 가드레일 스킬 전체 예제
- 도메인 스킬 전체 예제
- 검증 가이드 및 흔한 오류

### [HOOK_MECHANISMS.md](HOOK_MECHANISMS.md)
훅 내부 동작 심층 분석:
- UserPromptSubmit 플로우 (상세)
- PreToolUse 플로우 (상세)
- 종료 코드 동작 표 (중요)
- 세션 상태 관리
- 성능 고려사항

### [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
종합 디버깅 가이드:
- 스킬이 트리거되지 않을 때 (UserPromptSubmit)
- PreToolUse가 블로킹하지 않을 때
- 거짓 양성 (과도한 트리거)
- 훅이 전혀 실행되지 않을 때
- 성능 문제

### [PATTERNS_LIBRARY.md](PATTERNS_LIBRARY.md)
즉시 사용 가능한 패턴 모음:
- 의도 패턴 라이브러리 (정규식)
- 파일 경로 패턴 라이브러리 (glob)
- 콘텐츠 패턴 라이브러리 (정규식)
- 용도별 정리
- 복사하여 바로 사용 가능

### [ADVANCED.md](ADVANCED.md)
향후 개선 아이디어:
- 동적 규칙 업데이트
- 스킬 의존성
- 조건부 강제
- 스킬 분석
- 스킬 버전 관리

---

## 빠른 참고 요약

### 새 스킬 만들기 (5단계)

1. `.claude/skills/{name}/SKILL.md` 생성 및 프론트매터 작성
2. `.claude/skills/skill-rules.json`에 항목 추가
3. `npx tsx` 명령으로 훅 테스트
4. 테스트 결과에 따라 패턴 다듬기
5. SKILL.md를 500줄 이하로 유지

### 트리거 유형

- **Keywords**: 명시적 주제 언급
- **Intent**: 암시적 행동 감지
- **File Paths**: 위치 기반 활성화
- **Content**: 기술 특정 감지

자세한 내용은 [TRIGGER_TYPES.md](TRIGGER_TYPES.md)를 참고하세요.

### 강제 수준

- **BLOCK**: 종료 코드 2, 치명적 상황에만 사용
- **SUGGEST**: 컨텍스트 주입, 가장 일반적
- **WARN**: 안내용, 드물게 사용

### 건너뛰기 조건

- **Session tracking**: 자동 (반복 알림 방지)
- **File markers**: `// @skip-validation` (영구 건너뛰기)
- **Env vars**: `SKIP_SKILL_GUARDRAILS` (긴급 비활성화)

### Anthropic 베스트 프랙티스

✅ **500줄 규칙**: SKILL.md는 500줄 이하 유지  
✅ **점진적 공개**: 세부 내용은 리소스 파일로 분리  
✅ **목차 추가**: 100줄 초과 리소스 파일에 TOC 제공  
✅ **한 단계만 참조**: 리소스 중첩 참조 지양  
✅ **풍부한 설명**: 모든 트리거 키워드 포함 (1024자 이내)  
✅ **선테스트 후문서화**: 문서 작성 전 최소 3회 이상 평가  
✅ **동명사 네이밍**: 가능하면 -ing 형태 사용 (예: `processing-pdfs`)

### 문제 해결

훅을 수동으로 테스트하세요:
```bash
# UserPromptSubmit
echo '{"prompt":"test"}' | npx tsx .claude/hooks/skill-activation-prompt.ts

# PreToolUse
cat <<'EOF' | npx tsx .claude/hooks/skill-verification-guard.ts
{"tool_name":"Edit","tool_input":{"file_path":"test.ts"}}
EOF
```

[TROUBLESHOOTING.md](TROUBLESHOOTING.md)에서 전체 디버깅 가이드를 확인할 수 있습니다.

---

## 관련 파일

**설정:**
- `.claude/skills/skill-rules.json` – 마스터 설정
- `.claude/hooks/state/` – 세션 추적
- `.claude/settings.json` – 훅 등록

**훅:**
- `.claude/hooks/skill-activation-prompt.ts` – UserPromptSubmit
- `.claude/hooks/error-handling-reminder.ts` – Stop 이벤트(부드러운 알림)

**전체 스킬:**
- `.claude/skills/*/SKILL.md` – 스킬 콘텐츠 파일

---

**스킬 상태**: 완료 – Anthropic 베스트 프랙티스를 따르도록 재구성 ✅  
**줄 수**: 500줄 미만 (500줄 규칙 준수) ✅  
**점진적 공개**: 세부 정보는 리소스 파일로 분리 ✅

**Next**: 새로운 스킬을 추가하고, 사용 경험을 바탕으로 패턴을 개선하세요.
