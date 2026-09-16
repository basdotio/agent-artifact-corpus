# Mermaid 다이어그램 템플릿

## 의존성 그래프 (Dependency Graph)

### 기본 템플릿

```mermaid
graph LR
    subgraph M1["M1: Alpha"]
        T001[프로젝트 설정]
        F001[회원가입/로그인]
        F002[프로필 관리]
    end

    subgraph M2["M2: Beta"]
        F003[핵심 기능 A]
        F004[핵심 기능 B]
        F005[검색/필터]
    end

    subgraph M3["M3: Release"]
        F006[알림]
        F007[결제]
        T002[모니터링]
    end

    T001 --> F001
    F001 --> F002
    F001 --> F003
    F003 --> F004
    F004 --> F005
    F003 --> F006
    F005 --> F007
    F006 --> T002
```

### 복잡한 의존성 템플릿

```mermaid
graph TD
    subgraph Infrastructure["인프라"]
        T001[프로젝트 설정]
        T002[CI/CD]
        T003[모니터링]
    end

    subgraph Auth["인증"]
        F001[회원가입]
        F002[소셜 로그인]
        F003[비밀번호 찾기]
    end

    subgraph Core["핵심 기능"]
        F004[게시글 CRUD]
        F005[댓글]
        F006[좋아요]
    end

    subgraph Advanced["고급 기능"]
        F007[검색]
        F008[알림]
        F009[결제]
    end

    T001 --> T002
    T001 --> F001
    F001 --> F002
    F001 --> F003
    F001 --> F004
    F004 --> F005
    F004 --> F006
    F004 --> F007
    F005 --> F008
    F006 --> F008
    F007 --> F009
    T002 --> T003
```

---

## 타임라인 (Gantt Chart)

### 스프린트 타임라인

```mermaid
gantt
    title MVP 개발 로드맵
    dateFormat  YYYY-MM-DD

    section M1: Alpha
    프로젝트 설정     :t001, 2024-01-01, 3d
    회원가입/로그인   :f001, after t001, 5d
    프로필 관리       :f002, after f001, 3d

    section M2: Beta
    핵심 기능 A       :f003, after f002, 7d
    핵심 기능 B       :f004, after f003, 5d
    검색/필터         :f005, after f004, 5d

    section M3: Release
    알림              :f006, after f005, 4d
    버그 수정         :fix, after f006, 5d
    출시 준비         :release, after fix, 3d
```

### 병렬 작업 타임라인

```mermaid
gantt
    title 병렬 개발 로드맵
    dateFormat  YYYY-MM-DD

    section 백엔드
    API 설계          :be1, 2024-01-01, 3d
    인증 API          :be2, after be1, 5d
    핵심 API          :be3, after be2, 7d

    section 프론트엔드
    UI 설계           :fe1, 2024-01-01, 3d
    컴포넌트 개발     :fe2, after fe1, 5d
    페이지 개발       :fe3, after fe2, 7d

    section 통합
    API 연동          :int1, after be2, 3d
    E2E 테스트        :int2, after be3, 5d
```

---

## 플로우차트 (Flowchart)

### 기능 분해 플로우

```mermaid
flowchart TD
    PRD[PRD 기능 목록] --> Categorize{카테고리 분류}

    Categorize --> Auth[인증/사용자]
    Categorize --> Core[핵심 비즈니스]
    Categorize --> Support[지원 기능]

    Auth --> A1[회원가입]
    Auth --> A2[로그인]
    Auth --> A3[프로필]

    Core --> C1[기능 A]
    Core --> C2[기능 B]
    Core --> C3[기능 C]

    Support --> S1[알림]
    Support --> S2[설정]

    A1 --> Priority{우선순위}
    C1 --> Priority
    S1 --> Priority

    Priority --> P0[P0: Must Have]
    Priority --> P1[P1: Should Have]
    Priority --> P2[P2: Could Have]
```

### 스프린트 결정 플로우

```mermaid
flowchart TD
    Start[기능 목록] --> Check{의존성 확인}

    Check -->|의존성 없음| Ready[개발 가능]
    Check -->|의존성 있음| Deps[선행 기능 확인]

    Deps --> DepsComplete{선행 기능 완료?}
    DepsComplete -->|Yes| Ready
    DepsComplete -->|No| Wait[대기]

    Ready --> Estimate[복잡도 추정]
    Estimate --> Assign[스프린트 배정]

    Assign --> Capacity{용량 확인}
    Capacity -->|여유 있음| Add[스프린트에 추가]
    Capacity -->|초과| NextSprint[다음 스프린트로]
```

---

## 상태 다이어그램 (State Diagram)

### 기능 개발 상태

```mermaid
stateDiagram-v2
    [*] --> Backlog
    Backlog --> Planned: 스프린트 배정
    Planned --> InProgress: 개발 시작
    InProgress --> Review: PR 생성
    Review --> InProgress: 수정 요청
    Review --> Testing: 승인
    Testing --> InProgress: 버그 발견
    Testing --> Done: 테스트 통과
    Done --> [*]
```

### 스프린트 상태

```mermaid
stateDiagram-v2
    [*] --> Planning
    Planning --> Active: 스프린트 시작
    Active --> Review: 스프린트 종료
    Review --> Retrospective: 리뷰 완료
    Retrospective --> Planning: 다음 스프린트 준비
    Retrospective --> [*]: 마일스톤 완료
```

---

## 사용 가이드

### 생성 방법

1. PRD의 기능 목록 확인
2. 의존성 관계 파악
3. 마일스톤별 그룹화
4. 템플릿 선택 및 커스터마이즈

### 다이어그램 타입 선택

| 목적 | 추천 다이어그램 |
|------|----------------|
| 기능 간 의존성 | graph (LR/TD) |
| 일정 계획 | gantt |
| 프로세스 흐름 | flowchart |
| 상태 변화 | stateDiagram |

### 마크다운에서 렌더링

대부분의 마크다운 뷰어에서 Mermaid 지원:
- GitHub
- GitLab
- Notion
- Obsidian
- VS Code (확장 프로그램)

지원하지 않는 경우:
- [Mermaid Live Editor](https://mermaid.live) 에서 이미지로 내보내기
