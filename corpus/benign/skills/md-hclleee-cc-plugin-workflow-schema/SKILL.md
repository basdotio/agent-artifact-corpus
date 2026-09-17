---
name: workflow-schema
description: Claude Code 워크플로우 스키마 정의 - 10가지 노드 타입과 연결 규칙을 포함한 워크플로우 구조 명세
---

# Workflow Schema Skill

이 스킬은 Claude Code 워크플로우의 JSON 스키마 정의를 제공합니다.

## 워크플로우 구조

워크플로우는 다음 최상위 필드를 포함합니다:

- `id`: 고유 식별자 (필수)
- `name`: 워크플로우 이름 (최대 100자, 필수)
- `description`: 설명 (선택)
- `version`: 시맨틱 버전 (예: "1.0.0", 필수)
- `nodes`: 노드 배열 (필수, 최대 50개)
- `connections`: 연결 배열 (필수)
- `subAgentFlows`: 서브에이전트 플로우 배열 (선택)
- `createdAt`, `updatedAt`: ISO8601 타임스탬프

## 지원 노드 타입 (10종)

### 1. start (시작점)
- 워크플로우 진입점. 정확히 1개 필수
- 입력: 0개 / 출력: 1개
- 필드: `label` (선택, 기본값: "Start")

### 2. end (종료점)
- 워크플로우 종료점. 최소 1개 필수
- 입력: 무제한 / 출력: 0개
- 필드: `label` (선택, 기본값: "End")

### 3. prompt (메시지/지시)
- 사용자에게 메시지나 지시를 표시
- 입력: 1개 / 출력: 1개
- 필드:
  - `prompt`: 표시할 텍스트 (필수, 최대 10000자)
  - `label`: 노드 라벨 (선택)
  - `variables`: 변수 객체 (선택)

### 4. subAgent (AI 서브에이전트)
- AI 서브에이전트가 주어진 프롬프트로 태스크 실행
- 입력: 1개 / 출력: 1개
- 필드:
  - `description`: 간단한 설명 (필수, 최대 200자)
  - `prompt`: 실행할 프롬프트 (필수, 최대 10000자)
  - `tools`: 사용할 도구들 (선택)
  - `model`: "sonnet" | "opus" | "haiku" | "inherit" (기본값: "sonnet")
  - `color`: 시각적 표시 색상 (선택)

### 5. askUserQuestion (사용자 질문)
- 사용자에게 객관식 질문 제시
- 입력: 1개 / 출력: 2-4개 (옵션 수)
- 필드:
  - `questionText`: 질문 텍스트 (필수, 최대 500자)
  - `options`: 선택지 배열 (필수, 2-4개)
    - `label`: 선택지 라벨 (최대 50자)
    - `description`: 선택지 설명 (최대 200자)
  - `multiSelect`: 다중 선택 허용 (기본값: false)

### 6. ifElse (2방향 조건 분기)
- true/false 2방향 분기 전용
- 입력: 1개 / 출력: 2개 (고정)
- 필드:
  - `evaluationTarget`: 평가 대상 설명 (선택)
  - `branches`: 분기 조건 배열 (필수, 정확히 2개)
    - `label`: 분기 라벨 (최대 50자)
    - `condition`: 조건 설명 (최대 500자)

### 7. switch (다방향 조건 분기)
- 3개 이상 다방향 분기용
- 입력: 1개 / 출력: 2-10개
- 필드:
  - `evaluationTarget`: 평가 대상 설명 (선택)
  - `branches`: 분기 조건 배열 (필수, 2-10개)
    - `label`: 분기 라벨 (최대 50자)
    - `condition`: 조건 설명 (최대 500자)
    - `isDefault`: 기본 분기 여부 (마지막에 true 필수)

### 8. skill (Claude Code 스킬 호출)
- SKILL.md로 정의된 스킬 참조
- 입력: 1개 / 출력: 1개 (고정)
- 필드:
  - `name`: 스킬 이름 (필수, 소문자/숫자/하이픈)
  - `description`: 스킬 설명 (필수)
  - `scope`: "user" | "project" | "local"
  - `validationStatus`: "valid" | "missing" | "invalid"

### 9. mcp (MCP 도구 호출)
- MCP 외부 서버 도구 실행
- 입력: 1개 / 출력: 1개 (고정)
- 필드:
  - `serverId`: MCP 서버 식별자 (필수)
  - `toolName`: 도구 함수명 (필수)
  - `parameters`: 파라미터 스키마 배열 (선택)
  - `parameterValues`: 파라미터 값 객체 (선택)
  - `mode`: "manualParameterConfig" (AI 생성시 필수)

### 10. subAgentFlow (중첩 워크플로우)
- 서브에이전트 플로우 실행
- 입력: 1개 / 출력: 1개 (고정)
- 필드:
  - `subAgentFlowId`: 참조할 플로우 ID (필수)
  - `label`: 표시 라벨 (필수)
- 제약: 내부에서 subAgent, subAgentFlow, askUserQuestion 사용 불가

## 연결 규칙

### 금지
- Start는 입력 연결 불가
- End는 출력 연결 불가
- 순환(cycle) 금지
- 자기 자신 연결 금지
- 출력 포트당 하나의 연결만

### 필수
- 정확히 1개의 Start 노드
- 최소 1개의 End 노드
- Start 제외 모든 노드는 입력 연결 필수
- End 제외 모든 노드는 출력 연결 필수

## 노드/연결 구조

```json
// 노드
{
  "id": "unique-id",
  "type": "subAgent",
  "name": "node-name",
  "position": { "x": 100, "y": 200 },
  "data": { /* 타입별 데이터 */ }
}

// 연결
{
  "id": "conn-id",
  "from": "source-node-id",
  "to": "target-node-id",
  "fromPort": "output",  // 분기: "branch-0", "branch-1"
  "toPort": "input"
}
```

## 참조

상세 스키마: `references/workflow-schema.json`
