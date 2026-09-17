---
allowed-tools: [Read, Write, Bash, Glob, TodoWrite, Task, AskUserQuestion]
argument-hint: "[주제/제목]" [--category 카테고리] [--analyze] [--skip-review]
description: 저자의 스타일을 학습하여 한국어 블로그 글을 자동 작성하는 4-에이전트 파이프라인. 스타일 분석, 초안 작성, 검토 루프(80점 기준), 사용자 승인까지 자동 수행. "글 써줘", "블로그 작성", "포스트 생성", "write a blog post", "새 글 쓰기" 등의 요청에 사용하세요. 번역이 아닌 원본 한국어 글을 쓸 때 /translate-writer 대신 이 스킬을 사용합니다.
---

## 블로그 글쓰기 에이전트 시스템

4개의 전문 에이전트가 협업하여 저자의 스타일에 맞는 블로그 글을 작성합니다.

```
사용자 요청 [주제/제목] [--category 카테고리]
  → Phase 0: 스타일 가이드 확인 (없으면 style-analyzer 호출)
  → Phase 1: 글 작성 (content-writer, 스타일 가이드 참조)
  → Phase 2: 검토 루프 (content-reviewer, 80점 기준, 최대 3회)
      80점 미만 → content-writer에 수정 지시 → 재검토
      80점 이상 → 사용자 승인 요청
  → Phase 3: 사용자 최종 결정
      ✅ 승인 → Phase 4 | 📝 수정 → Phase 1 | ❌ 거절 → 종료
  → Phase 4: 저장 및 학습 (style-learner)
```

---

## 현재 스타일 가이드 상태

@.claude/skills/blog-writer/data/style-guide.md

## 최근 피드백

!`tail -30 .claude/skills/blog-writer/data/feedback-log.md 2>/dev/null || echo "피드백 로그 없음"`

## 샘플 글 목록

!`ls -la .claude/skills/blog-writer/data/samples/ 2>/dev/null || echo "샘플 없음 - 초기 분석 필요"`

---

## 작업

**"$ARGUMENTS"** 주제로 블로그 글을 작성하세요.

### 실행 단계

#### Phase 0: 스타일 가이드 확인

1. `.claude/skills/blog-writer/data/style-guide.md` 읽기
2. `[분석 필요]` 문자열이 많으면 → style-analyzer 에이전트 먼저 호출
3. 스타일 가이드가 준비되면 Phase 1로 진행

**style-analyzer 호출 조건**:
- style-guide.md에 `[분석 필요]`가 3개 이상
- `--analyze` 옵션 사용 시
- samples/ 폴더에 새 파일 추가 후

#### Phase 1: 글 작성 (content-writer)

Task 도구로 content-writer 에이전트 호출:
```
- 주제: [사용자 입력]
- 카테고리: [--category 또는 자동 추론]
- 스타일 가이드 참조
- 초안 작성 및 반환
```

#### Phase 2: 검토 루프 (content-reviewer)

**루프 조건**: 점수 80점 이상 또는 3회 수정 완료

```
반복 (최대 3회):
  1. content-reviewer 에이전트로 평가
  2. 점수 < 80:
     - 수정 지시를 content-writer에게 전달
     - 수정된 글 받기
  3. 점수 >= 80:
     - 루프 종료
     - 사용자 승인 요청
```

**3회 수정 후에도 80점 미만**:
- 사용자에게 상황 보고
- 현재 점수와 주요 문제점 안내
- 계속 진행할지 사용자 결정

#### Phase 3: 사용자 최종 결정

AskUserQuestion으로 사용자에게 질문:

```
## 작성된 글 검토

**점수**: XX/100
**제목**: [제목]
**카테고리**: [카테고리]

[글 미리보기 또는 전체 내용]

---

이 글을 어떻게 처리할까요?

1. ✅ 승인 - 이대로 저장
2. 📝 수정 요청 - 피드백 입력 후 수정
3. ❌ 거절 - 폐기
```

**사용자 선택에 따른 처리**:

| 선택 | 처리 |
|------|------|
| ✅ 승인 | style-learner 호출 (긍정) → 파일 저장 → 완료 |
| 📝 수정 | 피드백 받기 → style-learner 호출 → Phase 1로 |
| ❌ 거절 | style-learner 호출 (부정) → 종료 |

#### Phase 4: 저장 및 학습 (style-learner)

승인된 경우:
1. `contents/blog/[category]/[slug]/index.md` 저장
2. `approved-posts/`에 백업 저장
3. `samples/`에 심링크 추가 (`ln -s ../approved-posts/<파일명> .`) — style-analyzer가 승인된 스타일을 학습
4. style-guide.md 업데이트 (승인 패턴 강화)
5. feedback-log.md 기록

거절된 경우:
1. 거절 이유 파악
2. feedback-log.md 기록
3. 필요시 style-guide.md에 "피해야 할 패턴" 추가

---

## 옵션 처리

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--category` | 카테고리 지정 | 자동 추론 |
| `--analyze` | 강제 스타일 재분석 | false |
| `--skip-review` | 검토 루프 스킵 (테스트용) | false |

---

## 카테고리 목록

| 카테고리 | 용도 | 예시 주제 |
|----------|------|----------|
| ai | AI, Claude Code, LLM | Claude Code 활용법 |
| technical | 기술 글, 튜토리얼 | 브라우저 렌더링 과정 |
| retrospect | 회고, 후기 | 2024년 회고 |
| career | 면접, 커리어 | 토스 면접 후기 |
| algorithm | 알고리즘, 코테 | Fisher-Yates 셔플 |
| project | 프로젝트 | 포트폴리오 사이트 개발 |
| tools | 개발 도구 | VSCode 설정 |

---

## 에이전트 호출 방법

### style-analyzer 호출
```
Task 도구 사용:
- subagent_type: "general-purpose"
- prompt: "style-analyzer 에이전트를 실행하여 .claude/skills/blog-writer/data/samples/ 폴더의 글들을 분석하고 style-guide.md를 업데이트하세요."
```

### content-writer 호출
```
Task 도구 사용:
- subagent_type: "general-purpose"
- prompt: "content-writer 에이전트를 실행하여 '[주제]' 주제로 블로그 글을 작성하세요. 스타일 가이드 참조 필수."
```

### content-reviewer 호출
```
Task 도구 사용:
- subagent_type: "general-purpose"
- prompt: "content-reviewer 에이전트를 실행하여 작성된 글을 검토하고 점수를 부여하세요."
```

### style-learner 호출
```
Task 도구 사용:
- subagent_type: "general-purpose"
- prompt: "style-learner 에이전트를 실행하여 '[피드백 내용]' 피드백을 학습하고 스타일 가이드를 업데이트하세요."
```

---

## 완료 출력

```
📝 블로그 글쓰기 완료
─────────────────────────────────────

✅ 제목: [제목]
✅ 카테고리: [카테고리]
✅ 파일: contents/blog/[category]/[slug]/index.md
✅ 점수: XX/100
✅ 상태: draft: true

📊 검토 히스토리:
- 1차: XX점 → 수정
- 2차: XX점 → 통과
- 사용자 승인: ✅

📚 학습된 내용:
- [피드백 요약]

─────────────────────────────────────
💡 발행하려면: frontmatter의 draft: false로 변경
```

---

## 주의사항

1. **draft: true**: 모든 글은 초안으로 생성. 발행은 사용자가 직접.
2. **루프 제한**: Writer↔Reviewer 루프는 최대 3회.
3. **피드백 축적**: 모든 피드백은 feedback-log.md에 기록.
4. **백업**: style-guide.md 변경 전 항상 style-history/에 백업.
5. **한국어**: 모든 출력과 글은 한국어로.

---

## 승인된 글 통계

| 지표 | 수치 | 비고 |
|------|------|------|
| 총 승인된 글 | 2편 | - |
| 총 거절된 글 | 0편 | - |
| 평균 점수 | 92점 | 최종 승인 기준 |
| 승인률 | 100% | 2/2 |
| 평균 수정 회수 | 0.5회 | (1회 + 0회) / 2 |

### 승인된 글 목록

| 날짜 | 제목 | 카테고리 | 최종 점수 | 특수사항 |
|------|------|----------|-----------|---------|
| 2026-01-03 | AI와 Playwright로 강의 슬라이드 자동 생성 시스템 구축하기 | ai | 92점 | 1차 승인 |
| 2026-02-11 | AI에게 번역을 시키면서 깨달은 오케스트레이션의 힘 | ai | 92점 | evan-moon 스타일 (일회성) |
