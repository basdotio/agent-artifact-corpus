## 1) 가정/전제(필요 최소)

* **가정:** Stage 5 SSOT(AGENTS.md 및 부록)에 **G0~G6 게이트 정의 / R1~R8 Recovery 정의 / Protected Zones / Allowlist / Audit schema**가 이미 존재하며, Stage 6에서는 **재정의하지 않고 ID로 “참조”만** 합니다(불일치 방지).
* **확정(요청 3건):**

  1. Skill 후보 **11개**로 확정(아래 Skill Map)
  2. 공통 Output Envelope: `schema_id=urn:project_baton_v1:skill_output_envelope`, `schema_version=1.0.0`
  3. Tool 분류(Read/Write/External/Costly) + **needsApproval 기본 true**, External IO 기본 **DENY**, OpenClaw는 **제안만**(PR/MERGE/EXEC/External 금지)

---

## 2) Discovery 질문(0개)

(이미 입력이 충분합니다.)

---

## 3) Skill Map(설계)

| skill name            | 1줄 목적                                      | 트리거 키워드(description에 반영)                 | 필요 리소스              | 위험/권한                     |
| --------------------- | ------------------------------------------ | ---------------------------------------- | ------------------- | ------------------------- |
| stop-check            | STOP(킬스위치) 최우선 감지 후 ZERO_STOP 수렴           | STOP, kill switch, ZERO_STOP             | docs/skills/schemas | Read(승인)                  |
| queue-scan            | `.autodev_queue/*` 상태/카운트/작업 목록 스냅샷        | inbox/claimed/work/pr/done/blocked, scan | docs/skills/schemas | Read(승인)                  |
| claim-lock            | 작업 Claim/Lock 및 충돌(LOCK_CONFLICT) 처리       | claim, lock, conflict                    | docs/skills/schemas | Write/Move(승인)            |
| intake-validate       | 필수 파일/스키마/Allowlist/Protected Zone 사전 차단   | validate, protected zone, allowlist      | docs/skills/schemas | Read(승인)                  |
| patch-draft-request   | OpenClaw에 “제안(diff/patch)” 생성 요청/수신        | draft patch, OpenClaw, proposal          | docs/skills/schemas | Write(승인, 제한경로)           |
| diff-risk-scan        | diff 요약 + delete/lockfile/external 등 위험 스캔 | diff, risk, delete, lockfile             | docs/skills/schemas | Read(승인)                  |
| gate-runner           | G1~G6 실행(소유=Cursor) + evidence 수집          | gate, G1~G6, evidence                    | docs/skills/schemas | Exec(승인, Cursor only)     |
| decision-router       | AUTO_MERGE/PR_ONLY/ZERO_STOP 라우팅 결정        | decision, AUTO_MERGE, PR_ONLY            | docs/skills/schemas | Read(승인)                  |
| pr-merge-orchestrator | PR 생성/체크/merge 조건 가시화(실행은 Cursor)          | PR, merge, auto merge                    | docs/skills/schemas | PR/Merge(승인, Cursor only) |
| audit-append          | append-only 감사로그 기록(이벤트 체인)                | audit, append-only, trace                | docs/skills/schemas | Write(승인, append-only)    |
| incident-brief        | S7 수렴: 원인/영향/복구/알림 템플릿                     | incident, S7, recovery                   | docs/skills/schemas | Write(승인, 제한경로)           |

---

## 4) (선택) Subagent Map(권장 최소 1개)

| subagent name | 1줄 목적                            | 트리거 문구              | 권한          | 오버헤드 |
| ------------- | -------------------------------- | ------------------- | ----------- | ---- |
| verifier      | “게이트/결정/감사로그” 결과 독립 검증(완료 주장 방지) | “검증”, “evidence 확인” | readonly 권장 | 중    |

> Subagent는 Stage 6 필수는 아니며, **독립 검증**이 필요할 때만 추가합니다.

---

## 5) 생성 파일 트리

```text
docs/
  skills/
    SKILL_MAP.md
    TOOL_POLICY_CARDS.md
    APPROVAL_MATRIX.md
    RECOVERY_PLAYBOOK.md
    TRACE_EVALS_PLAN.md
    schemas/
      skill_io_envelope.schema.json
      skill_outputs.schema.json

skill-pack/
  stop-check/
    SKILL.md
    references/examples.json
  queue-scan/
    SKILL.md
    references/examples.json
  claim-lock/
    SKILL.md
    references/examples.json
  intake-validate/
    SKILL.md
    references/examples.json
  patch-draft-request/
    SKILL.md
    references/examples.json
  diff-risk-scan/
    SKILL.md
    references/examples.json
  gate-runner/
    SKILL.md
    references/examples.json
  decision-router/
    SKILL.md
    references/examples.json
  pr-merge-orchestrator/
    SKILL.md
    references/examples.json
  audit-append/
    SKILL.md
    references/examples.json
  incident-brief/
    SKILL.md
    references/examples.json
```

---

## 6) 파일별 내용(복사/붙여넣기)

### `docs/skills/SKILL_MAP.md`

```md
# SKILL_MAP — PROJECT_BATON_v1 (Folder Queue / Option A)

## 목적
Stage 5(Agents)에서 고정된 “Folder Queue 기반 안전 자동개발 오케스트레이션”을 Stage 6에서 재사용 가능한 Skill 모듈로 분해한다.
- OpenClaw = diff/patch **제안만**
- Cursor = APPLY/TEST/COMMIT/PR/MERGE **소유**
- 안전흐름: DRY_RUN → Diff → Gate → Decision(AUTO_MERGE/PR_ONLY/ZERO_STOP) → APPLY

## Folder Queue SSOT(고정)
.autodev_queue/
- inbox/ claimed/ work/ pr/ done/ blocked/ audit/

## 호출 시퀀스(Entry → S1..S7)
Entry
  0) stop-check (G0)
     - STOP 감지 시: decision=ZERO_STOP, state=blocked 수렴
     - 이후 incident-brief + audit-append로 기록

  1) queue-scan (S1)
     - inbox/claimed/work/pr/done/blocked 카운트 + 후보 task 목록 생성

  2) claim-lock (Claim)
     - 선택 task를 claimed로 이동/락 생성
     - LOCK_CONFLICT면 incident-brief + audit-append 후 종료(재시도 금지)

  3) intake-validate (S2)
     - 필수 파일/스키마/Protected Zone/Allowlist 위반 검사
     - FAIL이면 decision=ZERO_STOP 또는 PR_ONLY(SSOT 규칙)로 수렴

  4) patch-draft-request (S3)
     - OpenClaw에 draft patch + rationale 생성 요청
     - 산출물은 work/<TASK_ID>/ 하위 “제안 아티팩트”로만 저장

  5) diff-risk-scan (S4)
     - diff lines/deletes/lockfile/protected/external-io 스캔 → risk_level 산출
     - HIGH/CRITICAL이면 decision-router에서 PR_ONLY 또는 ZERO_STOP로 제한

  6) gate-runner (G1~G6)
     - 실행/테스트/게이트는 Cursor만 수행, evidence를 지정 경로에 기록

  7) decision-router (Decision)
     - SSOT Decision Rules에 따라 AUTO_MERGE / PR_ONLY / ZERO_STOP 결정

  8) pr-merge-orchestrator (PR/Merge)
     - PR 생성/체크/merge 조건 가시화(실행은 Cursor)
     - AUTO_MERGE는 “조건 충족 시만” 수행 가능

  9) audit-append (항상)
     - 각 단계 결과를 append-only로 기록(이벤트 체인 유지)

S7(사고 수렴)
  - incident-brief: 원인/영향/복구(R1~R8 참조)/알림 템플릿 작성 → blocked 수렴
```

---

### `docs/skills/TOOL_POLICY_CARDS.md`

```md
# TOOL_POLICY_CARDS — Tool Classifications & Guards (Approval-by-default)

## 공통 원칙(불변)
- needsApproval 기본값: **true** (Read/Write/External/Costly 모두)
- External IO(업로드/메신저/웹전송): **기본 DENY**
- OpenClaw는 “제안만”: EXEC/PR/MERGE/External IO 금지
- Allowlist 밖 경로 접근/수정 시도 → 즉시 ZERO_STOP
- Delete/파괴 명령 시도 → 즉시 ZERO_STOP
- Denied는 **재시도 금지**

---

## TOOL_CLASS: READ
- 예: 파일/디렉토리 목록, 내용 읽기, diff 읽기
- needsApproval: true
- DENY 조건:
  - Protected Zones 접근
  - Allowlist 밖 경로
- Audit fields(최소):
  - actor, tool_class=READ, paths[], result, event_id

## TOOL_CLASS: WRITE
- 예: draft patch/rationale 저장, 보고서/로그 작성
- needsApproval: true
- 허용 경로(원칙):
  - .autodev_queue/work/<TASK_ID>/** (제안 아티팩트)
  - .autodev_queue/audit/** (append-only)
  - .autodev_queue/blocked/<TASK_ID>/** (incident 산출물)
- DENY 조건:
  - 기존 파일 “수정(덮어쓰기)” (append-only 위반)
  - Protected Zones
  - Allowlist 밖
- Audit fields:
  - actor, tool_class=WRITE, path, append_only(true/false), event_id

## TOOL_CLASS: MOVE
- 예: inbox→claimed→work→pr→done/blocked 상태 전이(폴더 이동/rename)
- needsApproval: true
- DENY 조건:
  - 상태 전이 규칙 위반
  - 대상 task에 락/충돌 존재(LOCK_CONFLICT)
- Audit fields:
  - from_state, to_state, task_id, lock_path, event_id

## TOOL_CLASS: EXEC
- 예: 테스트/린트/게이트 실행
- needsApproval: true
- Cursor only: true
- timeout: 900s(권장) / retry: 0(기본)
- DENY 조건:
  - OpenClaw 실행
  - 네트워크/외부 전송 포함 커맨드
- Audit fields:
  - command_fingerprint, exit_code, evidence_paths[], event_id

## TOOL_CLASS: PR / MERGE
- needsApproval: true
- Cursor only: true
- DENY 조건:
  - OpenClaw 실행
  - Gate fail / risk=HIGH+핵심게이트 FAIL / STOP 감지
- Audit fields:
  - pr_url, checks_status, merge_status, event_id

## TOOL_CLASS: EXTERNAL
- 기본: DENY(차단)
- 예외 허용은 Stage 5 SSOT에 “명시”된 경우만(없으면 항상 DENY)

## TOOL_CLASS: COSTLY
- 예: 장시간 리서치/대규모 스캔
- needsApproval: true
- retry: 0(기본)
- Audit fields:
  - duration_ms, scope_hint, event_id
```

---

### `docs/skills/APPROVAL_MATRIX.md`

```md
# APPROVAL_MATRIX — Skills × Tool Classes (Default: needsApproval=true)

## 역할 경계(불변)
- OpenClaw: diff/patch “제안만” (EXEC/PR/MERGE/External IO 금지)
- Cursor: APPLY/TEST/COMMIT/PR/MERGE 소유

| Tool Class | OpenClaw | Cursor | 기본 승인 | 비고 |
|---|---:|---:|---|---|
| READ | 허용 | 허용 | 필요 | Allowlist/Protected 검사 필수 |
| WRITE | 제한 허용 | 허용 | 필요 | OpenClaw는 work/<TASK_ID> “제안 아티팩트”만 |
| MOVE | 금지(원칙) | 허용 | 필요 | 상태 전이는 Cursor만 권장 |
| EXEC | 금지 | 허용 | 필요 | Gate/Tests |
| PR | 금지 | 허용 | 필요 | PR 생성 |
| MERGE | 금지 | 허용 | 필요 | AUTO_MERGE도 조건 충족 시만 |
| EXTERNAL | 금지 | 금지(기본) | N/A | 기본 차단(SSOT 예외만) |
| COSTLY | 제한 | 제한 | 필요 | 범위/시간 상한 명시 |

## Denied 재시도 금지(불변)
- approval state=DENIED 인 경우 동일 입력으로 재시도하지 않는다.
```

---

### `docs/skills/RECOVERY_PLAYBOOK.md`

```md
# RECOVERY_PLAYBOOK — R1~R8 Skill-level Mapping (Reference-only)

## 원칙
- R1~R8 “정의/절차”는 Stage 5 SSOT(AGENTS.md)에 있음.
- 본 문서는 “어떤 상황에서 어떤 R#을 호출(참조)하는지”만 매핑한다.
- (가정) 아래 매핑은 보수적 추천안이며, SSOT와 다르면 SSOT가 우선.

| Scenario | Trigger | Recommended Recovery Ref | Called by Skill | Notes |
|---|---|---|---|---|
| Lock 충돌 | LOCK_CONFLICT | R1 | claim-lock | 재시도 금지, blocked 수렴 권장 |
| Intake 실패 | missing/invalid/protected | R2 | intake-validate | allowlist/Protected 위반 시 ZERO_STOP |
| Diff 위험 높음 | delete/lockfile/high risk | R3 | diff-risk-scan | PR_ONLY 또는 ZERO_STOP로 다운그레이드 |
| Gate 실패 | G1~G6 FAIL | R4 | gate-runner | evidence 필수 |
| PR checks 실패 | CI/checks fail | R5 | pr-merge-orchestrator | AUTO_MERGE 금지 |
| Apply 롤백 | apply 후 문제 | R6 | pr-merge-orchestrator | Cursor 소유 |
| Audit append 실패 | append-only 실패 | R7 | audit-append | 기록 불가 자체가 incident |
| Incident 에스컬레이션 | SEV1/정책 위반 | R8 | incident-brief | 알림 템플릿 필수 |
```

---

### `docs/skills/TRACE_EVALS_PLAN.md`

```md
# TRACE_EVALS_PLAN — Success/Deny/Fail, Latency, Drift Watch

## 1) 측정 지표(최소)
- success_rate = OK / total
- deny_rate = DENY / total
- fail_rate = (FAIL + ZERO_STOP) / total
- gate_fail_top = 가장 많이 실패한 gate_id Top N
- latency_ms(단계별): stop-check, queue-scan, diff-risk-scan, gate-runner 등
- drift_watch:
  - 정책/규정/SSOT 변경 감지(AGENTS.md, allowlist, audit schema 변경 시)

## 2) 감사로그(append-only) 요구 필드(최소)
- timestamp, event_id, prev_event_id
- actor(OpenClaw/Cursor/Human)
- skill, status, decision
- task_id, from_state, to_state
- tool_class, needsApproval, approval_state
- artifacts(paths)
- findings(severity/code)

## 3) Evals 샘플(권장)
- 정상 10건: inbox→done까지
- 실패 10건: gate fail, lock conflict, intake fail
- 거절 10건: approval missing, external denied
- 목표(권장):
  - Gate evidence 누락 0건
  - Denied 재시도 0건
  - AUTO_MERGE 후 롤백 0건
```

---

### `docs/skills/schemas/skill_io_envelope.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:project_baton_v1:skill_output_envelope:1.0.0",
  "title": "PROJECT_BATON_v1 Skill Output Envelope",
  "type": "object",
  "required": [
    "schema_id",
    "schema_version",
    "skill",
    "skill_version",
    "status",
    "summary",
    "task",
    "approvals",
    "audit",
    "data"
  ],
  "properties": {
    "schema_id": { "const": "urn:project_baton_v1:skill_output_envelope" },
    "schema_version": { "const": "1.0.0" },
    "skill": {
      "type": "string",
      "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"
    },
    "skill_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    },
    "status": {
      "type": "string",
      "enum": ["OK", "FAIL", "DENY", "ZERO_STOP", "PARTIAL"]
    },
    "decision": {
      "type": "string",
      "enum": ["AUTO_MERGE", "PR_ONLY", "ZERO_STOP", "NA"],
      "default": "NA"
    },
    "summary": { "type": "string", "minLength": 1 },
    "task": {
      "type": "object",
      "required": ["task_id", "queue_root", "state_before", "state_after"],
      "properties": {
        "task_id": { "type": "string", "minLength": 1 },
        "queue_root": { "const": ".autodev_queue" },
        "state_before": {
          "type": "string",
          "enum": ["inbox", "claimed", "work", "pr", "done", "blocked", "unknown"]
        },
        "state_after": {
          "type": "string",
          "enum": ["inbox", "claimed", "work", "pr", "done", "blocked", "unknown"]
        }
      },
      "additionalProperties": false
    },
    "signals": {
      "type": "object",
      "required": ["stop_detected", "allowlist_violation", "external_io_attempt", "delete_detected"],
      "properties": {
        "stop_detected": { "type": "boolean" },
        "allowlist_violation": { "type": "boolean" },
        "external_io_attempt": { "type": "boolean" },
        "delete_detected": { "type": "boolean" },
        "lockfile_touched": { "type": "boolean" },
        "protected_zone_touched": { "type": "boolean" }
      },
      "additionalProperties": false
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "code", "message"],
        "properties": {
          "severity": { "type": "string", "enum": ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] },
          "code": { "type": "string", "minLength": 1 },
          "message": { "type": "string", "minLength": 1 },
          "evidence_paths": {
            "type": "array",
            "items": { "type": "string", "minLength": 1 }
          }
        },
        "additionalProperties": false
      }
    },
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["kind", "path"],
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "QUEUE_SNAPSHOT",
              "LOCK_FILE",
              "DRAFT_PATCH",
              "DIFF_SUMMARY",
              "GATE_EVIDENCE",
              "PR_LINK",
              "AUDIT_LOG",
              "INCIDENT_REPORT",
              "OTHER"
            ]
          },
          "path": { "type": "string", "minLength": 1 },
          "note": { "type": "string" }
        },
        "additionalProperties": false
      }
    },
    "approvals": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["tool_class", "needs_approval", "state"],
        "properties": {
          "tool_class": {
            "type": "string",
            "enum": ["READ", "WRITE", "MOVE", "EXEC", "PR", "MERGE", "EXTERNAL", "COSTLY"]
          },
          "needs_approval": { "type": "boolean" },
          "state": { "type": "string", "enum": ["PENDING", "APPROVED", "DENIED", "NOT_REQUIRED"] },
          "approved_by": { "type": "string" },
          "approved_at": { "type": "string", "format": "date-time" },
          "note": { "type": "string" }
        },
        "additionalProperties": false
      }
    },
    "audit": {
      "type": "object",
      "required": ["event_id", "append_only_path"],
      "properties": {
        "event_id": { "type": "string", "minLength": 1 },
        "append_only_path": { "type": "string", "minLength": 1 },
        "prev_event_id": { "type": "string" }
      },
      "additionalProperties": false
    },
    "data": { "type": "object" }
  },
  "unevaluatedProperties": false
}
```

---

### `docs/skills/schemas/skill_outputs.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:project_baton_v1:skill_outputs:1.0.0",
  "title": "PROJECT_BATON_v1 Skill Outputs (union)",
  "oneOf": [
    {
      "title": "stop-check output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "stop-check" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["stop_detected", "stop_paths", "action"],
              "properties": {
                "stop_detected": { "type": "boolean" },
                "stop_paths": { "type": "array", "items": { "type": "string", "minLength": 1 } },
                "action": { "type": "string", "enum": ["CONTINUE", "ZERO_STOP", "MOVE_TO_BLOCKED"] }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "queue-scan output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "queue-scan" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["counts", "tasks"],
              "properties": {
                "counts": {
                  "type": "object",
                  "required": ["inbox", "claimed", "work", "pr", "done", "blocked"],
                  "properties": {
                    "inbox": { "type": "integer", "minimum": 0 },
                    "claimed": { "type": "integer", "minimum": 0 },
                    "work": { "type": "integer", "minimum": 0 },
                    "pr": { "type": "integer", "minimum": 0 },
                    "done": { "type": "integer", "minimum": 0 },
                    "blocked": { "type": "integer", "minimum": 0 }
                  },
                  "additionalProperties": false
                },
                "tasks": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["task_id", "state", "path"],
                    "properties": {
                      "task_id": { "type": "string", "minLength": 1 },
                      "state": { "type": "string", "enum": ["inbox", "claimed", "work", "pr", "done", "blocked"] },
                      "path": { "type": "string", "minLength": 1 },
                      "updated_at": { "type": "string", "format": "date-time" }
                    },
                    "additionalProperties": false
                  }
                }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "claim-lock output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "claim-lock" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["result", "lock_path"],
              "properties": {
                "result": { "type": "string", "enum": ["CLAIMED", "LOCK_CONFLICT", "NOT_FOUND", "DENIED"] },
                "lock_path": { "type": "string", "minLength": 1 },
                "conflict_owner_hint": { "type": "string" }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "intake-validate output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "intake-validate" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["is_valid", "checks"],
              "properties": {
                "is_valid": { "type": "boolean" },
                "checks": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["check_id", "status"],
                    "properties": {
                      "check_id": { "type": "string", "minLength": 1 },
                      "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
                      "note": { "type": "string" }
                    },
                    "additionalProperties": false
                  }
                },
                "blocked_reason_codes": { "type": "array", "items": { "type": "string", "minLength": 1 } }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "patch-draft-request output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "patch-draft-request" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["request_id", "draft_patch_path", "rationale_path", "producer"],
              "properties": {
                "request_id": { "type": "string", "minLength": 1 },
                "producer": { "type": "string", "enum": ["OPENCLAW", "HUMAN"] },
                "draft_patch_path": { "type": "string", "minLength": 1 },
                "rationale_path": { "type": "string", "minLength": 1 },
                "notes": { "type": "string" }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "diff-risk-scan output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "diff-risk-scan" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["risk_level", "diff_stats", "policy_flags"],
              "properties": {
                "risk_level": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
                "diff_stats": {
                  "type": "object",
                  "required": ["files_changed", "insertions", "deletions"],
                  "properties": {
                    "files_changed": { "type": "integer", "minimum": 0 },
                    "insertions": { "type": "integer", "minimum": 0 },
                    "deletions": { "type": "integer", "minimum": 0 }
                  },
                  "additionalProperties": false
                },
                "policy_flags": {
                  "type": "object",
                  "required": ["delete_detected", "lockfile_touched", "protected_zone_touched", "allowlist_violation", "external_io_attempt"],
                  "properties": {
                    "delete_detected": { "type": "boolean" },
                    "lockfile_touched": { "type": "boolean" },
                    "protected_zone_touched": { "type": "boolean" },
                    "allowlist_violation": { "type": "boolean" },
                    "external_io_attempt": { "type": "boolean" }
                  },
                  "additionalProperties": false
                },
                "reasons": { "type": "array", "items": { "type": "string", "minLength": 1 } },
                "diff_summary_path": { "type": "string" }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "gate-runner output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "gate-runner" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["gates", "all_pass"],
              "properties": {
                "all_pass": { "type": "boolean" },
                "gates": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["gate_id", "status"],
                    "properties": {
                      "gate_id": { "type": "string", "pattern": "^G[0-9]+$" },
                      "status": { "type": "string", "enum": ["PASS", "FAIL", "SKIP"] },
                      "evidence_paths": { "type": "array", "items": { "type": "string", "minLength": 1 } },
                      "note": { "type": "string" }
                    },
                    "additionalProperties": false
                  }
                }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "decision-router output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "decision-router" },
            "skill_version": { "const": "1.0.0" },
            "decision": { "enum": ["AUTO_MERGE", "PR_ONLY", "ZERO_STOP"] },
            "data": {
              "type": "object",
              "required": ["decision", "next"],
              "properties": {
                "decision": { "type": "string", "enum": ["AUTO_MERGE", "PR_ONLY", "ZERO_STOP"] },
                "next": {
                  "type": "object",
                  "required": ["skill"],
                  "properties": { "skill": { "type": "string", "minLength": 1 }, "note": { "type": "string" } },
                  "additionalProperties": false
                },
                "reasoning": { "type": "array", "items": { "type": "string", "minLength": 1 } }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "pr-merge-orchestrator output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "pr-merge-orchestrator" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["mode", "plan"],
              "properties": {
                "mode": { "type": "string", "enum": ["AUTO_MERGE", "PR_ONLY"] },
                "plan": { "type": "array", "items": { "type": "string", "minLength": 1 } },
                "pr_url": { "type": "string" }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "audit-append output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "audit-append" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["appended", "audit_path"],
              "properties": {
                "appended": { "type": "boolean" },
                "audit_path": { "type": "string", "minLength": 1 },
                "record_digest": { "type": "string" }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    },
    {
      "title": "incident-brief output",
      "allOf": [
        { "$ref": "./skill_io_envelope.schema.json" },
        {
          "properties": {
            "skill": { "const": "incident-brief" },
            "skill_version": { "const": "1.0.0" },
            "data": {
              "type": "object",
              "required": ["incident_id", "severity", "headline", "actions", "recovery_refs"],
              "properties": {
                "incident_id": { "type": "string", "minLength": 1 },
                "severity": { "type": "string", "enum": ["SEV1", "SEV2", "SEV3"] },
                "headline": { "type": "string", "minLength": 1 },
                "impact": { "type": "string" },
                "actions": { "type": "array", "items": { "type": "string", "minLength": 1 } },
                "recovery_refs": { "type": "array", "items": { "type": "string", "pattern": "^R[0-9]+$" } },
                "notify_template": { "type": "string" }
              },
              "additionalProperties": false
            }
          }
        }
      ]
    }
  ]
}
```

---

## Skill Packages (`skill-pack/*`)

> 모든 Skill은 **출력(JSON)**을 `docs/skills/schemas/skill_outputs.schema.json`에 맞춰 1개 객체로 반환하도록 지시합니다.

---

### `skill-pack/stop-check/SKILL.md`

```md
---
name: stop-check
description: STOP(킬스위치) 감지 후 즉시 ZERO_STOP 수렴. STOP/kill switch/blocked/중단 키워드가 나오면 사용.
---

# stop-check

## Role
STOP(킬스위치) 신호를 최우선으로 탐지하고, 발견 시 즉시 ZERO_STOP으로 수렴한다.

## In-Scope
- `.autodev_queue/**` 및 SSOT가 지정한 STOP sentinel 검사
- STOP 발견 시 blocked 격리(계획만) + incident/audit 트리거

## Out-of-Scope
- 임의의 경로에서 STOP 의미 추정(SSOT 외)
- External IO/업로드/알림 전송

## Inputs
- queue_root: `.autodev_queue`
- (선택) task_id

## Steps
1) needsApproval=true로 READ 범위 승인 확보
2) SSOT 지정 STOP sentinel을 검사(없으면 `.autodev_queue/STOP`만 기본 검사)
3) STOP 발견 시:
   - status=ZERO_STOP, decision=ZERO_STOP
   - 다음 단계: `incident-brief`, `audit-append`, state=blocked 수렴

## Outputs
- JSON 1개(스키마): `docs/skills/schemas/skill_outputs.schema.json`의 stop-check branch

## Safety
- Read도 승인 필요
- STOP 발견 시 다른 작업 금지(즉시 종료)
```

### `skill-pack/stop-check/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "stop-check",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "STOP 신호 없음. 진행 가능.",
    "task": { "task_id": "NA", "queue_root": ".autodev_queue", "state_before": "unknown", "state_after": "unknown" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-STOP", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "stop_detected": false, "stop_paths": [], "action": "CONTINUE" }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "stop-check",
    "skill_version": "1.0.0",
    "status": "ZERO_STOP",
    "decision": "ZERO_STOP",
    "summary": "STOP 감지. blocked 격리 필요.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "inbox", "state_after": "blocked" },
    "approvals": [{ "tool_class": "MOVE", "needs_approval": true, "state": "PENDING" }],
    "audit": { "event_id": "EVT-FAIL-STOP", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "stop_detected": true, "stop_paths": [".autodev_queue/STOP"], "action": "MOVE_TO_BLOCKED" }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "stop-check",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "READ 승인 미확보로 STOP 검사 거절.",
    "task": { "task_id": "NA", "queue_root": ".autodev_queue", "state_before": "unknown", "state_after": "unknown" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-STOP", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "stop_detected": false, "stop_paths": [], "action": "ZERO_STOP" }
  }
}
```

---

### `skill-pack/queue-scan/SKILL.md`

```md
---
name: queue-scan
description: `.autodev_queue` inbox/claimed/work/pr/done/blocked 카운트와 task 목록 스냅샷 생성. queue scan/state count 키워드면 사용.
---

# queue-scan

## Role
Folder Queue 전체 상태를 “읽기 전용”으로 스캔해 가시화한다.

## Steps
1) READ 승인 확보
2) 각 상태 폴더의 task 목록/카운트 수집
3) 결과를 JSON으로 반환(상태/경로 포함)

## Outputs
- `docs/skills/schemas/skill_outputs.schema.json`의 queue-scan branch
```

### `skill-pack/queue-scan/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "queue-scan",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "Queue 스캔 완료.",
    "task": { "task_id": "NA", "queue_root": ".autodev_queue", "state_before": "unknown", "state_after": "unknown" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-SCAN", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "counts": { "inbox": 1, "claimed": 0, "work": 0, "pr": 0, "done": 0, "blocked": 0 },
      "tasks": [{ "task_id": "TASK-0001", "state": "inbox", "path": ".autodev_queue/inbox/TASK-0001" }]
    }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "queue-scan",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "Queue 스캔 실패(경로 접근 오류).",
    "task": { "task_id": "NA", "queue_root": ".autodev_queue", "state_before": "unknown", "state_after": "unknown" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-SCAN", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "counts": { "inbox": 0, "claimed": 0, "work": 0, "pr": 0, "done": 0, "blocked": 0 }, "tasks": [] }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "queue-scan",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "READ 승인 미확보로 스캔 거절.",
    "task": { "task_id": "NA", "queue_root": ".autodev_queue", "state_before": "unknown", "state_after": "unknown" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-SCAN", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "counts": { "inbox": 0, "claimed": 0, "work": 0, "pr": 0, "done": 0, "blocked": 0 }, "tasks": [] }
  }
}
```

---

### `skill-pack/claim-lock/SKILL.md`

```md
---
name: claim-lock
description: inbox→claimed Claim/Lock 수행 및 LOCK_CONFLICT 처리. claim/lock/conflict 키워드면 사용.
---

# claim-lock

## Role
작업을 단일 소유로 만들기 위해 Claim + Lock을 수행한다.

## Safety
- MOVE/WRITE는 needsApproval=true
- LOCK_CONFLICT 발생 시 재시도 금지(incident로 수렴)

## Steps
1) STOP 재확인(stop-check) 결과가 OK인지 확인
2) 대상 task_id를 inbox에서 claimed로 이동(SSOT 상태 전이 준수)
3) lock 파일 생성(SSOT 경로/포맷 준수)
4) 충돌이면 result=LOCK_CONFLICT로 반환 후 incident-brief로 넘김

## Outputs
- claim-lock branch
```

### `skill-pack/claim-lock/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "claim-lock",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "Claim/Lock 완료.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "inbox", "state_after": "claimed" },
    "approvals": [{ "tool_class": "MOVE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-CLAIM", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "result": "CLAIMED", "lock_path": ".autodev_queue/claimed/TASK-0001/.lock" }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "claim-lock",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "LOCK_CONFLICT 발생.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "inbox", "state_after": "inbox" },
    "approvals": [{ "tool_class": "MOVE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-CLAIM", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "result": "LOCK_CONFLICT", "lock_path": ".autodev_queue/inbox/TASK-0001/.lock", "conflict_owner_hint": "UNKNOWN" }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "claim-lock",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "MOVE 승인 미확보로 Claim 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "inbox", "state_after": "inbox" },
    "approvals": [{ "tool_class": "MOVE", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-CLAIM", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "result": "DENIED", "lock_path": "" }
  }
}
```

---

### `skill-pack/intake-validate/SKILL.md`

```md
---
name: intake-validate
description: 필수 파일/스키마/Allowlist/Protected Zone 사전 검증. validate/allowlist/protected zone 키워드면 사용.
---

# intake-validate

## Role
작업 착수 전 “불변 규칙” 위반을 조기 차단한다.

## Steps
1) READ 승인 확보
2) 필수 파일 존재/포맷 확인(SSOT 목록 기준)
3) Allowlist/Protected Zone 위반 검사(SSOT 기준)
4) FAIL이면 blocked_reason_codes를 채우고 decision-router로 넘김(또는 ZERO_STOP)

## Outputs
- intake-validate branch
```

### `skill-pack/intake-validate/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "intake-validate",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "Intake 검증 PASS.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "claimed", "state_after": "work" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-INTAKE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "is_valid": true,
      "checks": [{ "check_id": "REQUIRED_FILES", "status": "PASS" }, { "check_id": "ALLOWLIST", "status": "PASS" }],
      "blocked_reason_codes": []
    }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "intake-validate",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "Intake 검증 FAIL(Protected Zone).",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "claimed", "state_after": "blocked" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-INTAKE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "is_valid": false,
      "checks": [{ "check_id": "PROTECTED_ZONE", "status": "FAIL", "note": "SSOT protected hit" }],
      "blocked_reason_codes": ["PROTECTED_ZONE_TOUCHED"]
    }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "intake-validate",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "READ 승인 미확보로 Intake 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "claimed", "state_after": "claimed" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-INTAKE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "is_valid": false, "checks": [], "blocked_reason_codes": ["APPROVAL_REQUIRED"] }
  }
}
```

---

### `skill-pack/patch-draft-request/SKILL.md`

```md
---
name: patch-draft-request
description: OpenClaw에 draft patch(제안) 생성 요청/수신. draft patch/OpenClaw/proposal 키워드면 사용.
---

# patch-draft-request

## Role
OpenClaw로부터 “제안(diff/patch)”만 생성·수신한다. 적용/커밋/머지는 절대 수행하지 않는다.

## Safety
- OpenClaw: EXEC/PR/MERGE/External 금지
- WRITE는 work/<TASK_ID> 하위 “제안 아티팩트”만 허용

## Steps
1) task_id 확인(상태: claimed 또는 work)
2) OpenClaw에 생성 요청(요청 텍스트에는 PII/토큰/키 금지)
3) 산출물 저장 경로 지정:
   - .autodev_queue/work/<TASK_ID>/draft.patch
   - .autodev_queue/work/<TASK_ID>/rationale.md

## Outputs
- patch-draft-request branch
```

### `skill-pack/patch-draft-request/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "patch-draft-request",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "OpenClaw draft patch 수신 완료.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-DRAFT", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "request_id": "REQ-0001",
      "producer": "OPENCLAW",
      "draft_patch_path": ".autodev_queue/work/TASK-0001/draft.patch",
      "rationale_path": ".autodev_queue/work/TASK-0001/rationale.md"
    }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "patch-draft-request",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "Draft patch 생성 실패(빈 결과).",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-DRAFT", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "request_id": "REQ-0001",
      "producer": "OPENCLAW",
      "draft_patch_path": "",
      "rationale_path": "",
      "notes": "empty output"
    }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "patch-draft-request",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "WRITE 승인 미확보로 draft 저장 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-DRAFT", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "request_id": "REQ-0001", "producer": "OPENCLAW", "draft_patch_path": "", "rationale_path": "" }
  }
}
```

---

### `skill-pack/diff-risk-scan/SKILL.md`

```md
---
name: diff-risk-scan
description: diff 요약 + delete/lockfile/protected/external 스캔으로 risk_level 산출. diff/risk/delete/lockfile 키워드면 사용.
---

# diff-risk-scan

## Role
Draft patch/diff를 요약하고 정책 위반 신호를 탐지해 위험도를 산출한다.

## Steps
1) READ 승인 확보(대상: draft.patch, diff)
2) 파일 변경 수/삽입/삭제 집계
3) 정책 플래그 탐지:
   - delete_detected / lockfile_touched / protected_zone_touched / allowlist_violation / external_io_attempt
4) risk_level 결정(보수적으로):
   - delete_detected 또는 allowlist_violation 또는 external_io_attempt → CRITICAL
   - protected_zone_touched 또는 lockfile_touched → HIGH
   - 그 외 → LOW/MEDIUM(SSOT 규칙 우선)

## Outputs
- diff-risk-scan branch
```

### `skill-pack/diff-risk-scan/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "diff-risk-scan",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "Diff risk LOW.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-RISK", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "risk_level": "LOW",
      "diff_stats": { "files_changed": 1, "insertions": 10, "deletions": 0 },
      "policy_flags": {
        "delete_detected": false,
        "lockfile_touched": false,
        "protected_zone_touched": false,
        "allowlist_violation": false,
        "external_io_attempt": false
      },
      "reasons": ["no delete/no protected/no external"]
    }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "diff-risk-scan",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "Diff risk CRITICAL(delete detected).",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-RISK", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "risk_level": "CRITICAL",
      "diff_stats": { "files_changed": 1, "insertions": 0, "deletions": 12 },
      "policy_flags": {
        "delete_detected": true,
        "lockfile_touched": false,
        "protected_zone_touched": false,
        "allowlist_violation": false,
        "external_io_attempt": false
      },
      "reasons": ["delete detected => ZERO_STOP candidate"]
    }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "diff-risk-scan",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "READ 승인 미확보로 diff 스캔 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-RISK", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": {
      "risk_level": "HIGH",
      "diff_stats": { "files_changed": 0, "insertions": 0, "deletions": 0 },
      "policy_flags": {
        "delete_detected": false,
        "lockfile_touched": false,
        "protected_zone_touched": false,
        "allowlist_violation": false,
        "external_io_attempt": false
      },
      "reasons": ["approval required"]
    }
  }
}
```

---

### `skill-pack/gate-runner/SKILL.md`

```md
---
name: gate-runner
description: G1~G6 게이트 실행(소유=Cursor) 및 evidence 수집. gate/G1/G6/evidence 키워드면 사용.
---

# gate-runner

## Role
Stage 5 SSOT의 Gate Pipeline(G1~G6)을 실행하고 증거(evidence)를 남긴다.

## Safety
- EXEC는 needsApproval=true
- Cursor only(OpenClaw 금지)
- Gate fail 시 AUTO_MERGE 금지(DecisionRouter로 전달)

## Steps
1) EXEC 승인 확보
2) SSOT에 정의된 G1~G6를 순서대로 실행
3) 각 gate별 PASS/FAIL/SKIP 및 evidence_paths 기록
4) all_pass 산출 후 JSON 반환

## Outputs
- gate-runner branch
```

### `skill-pack/gate-runner/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "gate-runner",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "G1~G6 all PASS.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "EXEC", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-GATE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "all_pass": true, "gates": [{ "gate_id": "G1", "status": "PASS", "evidence_paths": [".autodev_queue/work/TASK-0001/evidence/G1.log"] }] }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "gate-runner",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "Gate FAIL 감지.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "EXEC", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-GATE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "all_pass": false, "gates": [{ "gate_id": "G3", "status": "FAIL", "evidence_paths": [".autodev_queue/work/TASK-0001/evidence/G3.log"] }] }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "gate-runner",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "EXEC 승인 미확보로 gate 실행 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "EXEC", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-GATE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "all_pass": false, "gates": [] }
  }
}
```

---

### `skill-pack/decision-router/SKILL.md`

```md
---
name: decision-router
description: Gate/Risk/STOP 결과로 AUTO_MERGE/PR_ONLY/ZERO_STOP 결정. decision/AUTO_MERGE/PR_ONLY/ZERO_STOP 키워드면 사용.
---

# decision-router

## Role
SSOT Decision Rules를 적용해 다음 행동을 결정한다.

## 최소 결정 규칙(보수적)
- STOP 감지 → ZERO_STOP
- allowlist 위반 / delete / external 시도 → ZERO_STOP
- gate fail 또는 risk HIGH/CRITICAL → PR_ONLY (또는 SSOT가 ZERO_STOP이면 그에 따름)
- 그 외 → AUTO_MERGE 후보(단, pr-merge-orchestrator에서 조건 재확인)

## Outputs
- decision-router branch
```

### `skill-pack/decision-router/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "decision-router",
    "skill_version": "1.0.0",
    "status": "OK",
    "decision": "PR_ONLY",
    "summary": "Gate PASS이나 risk=MEDIUM → PR_ONLY.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "pr" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-DECIDE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "decision": "PR_ONLY", "next": { "skill": "pr-merge-orchestrator", "note": "PR 생성 경로" }, "reasoning": ["risk not LOW"] }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "decision-router",
    "skill_version": "1.0.0",
    "status": "OK",
    "decision": "ZERO_STOP",
    "summary": "정책 위반 신호로 ZERO_STOP.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "blocked" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-DECIDE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "decision": "ZERO_STOP", "next": { "skill": "incident-brief", "note": "S7 수렴" }, "reasoning": ["allowlist/delete/external detected"] }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "decision-router",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "READ 승인 미확보로 결정 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "READ", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-DECIDE", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "decision": "PR_ONLY", "next": { "skill": "incident-brief", "note": "승인 필요" }, "reasoning": ["approval required"] }
  }
}
```

---

### `skill-pack/pr-merge-orchestrator/SKILL.md`

```md
---
name: pr-merge-orchestrator
description: PR 생성/체크/merge 조건을 계획으로 정리(실행은 Cursor). PR/merge/AUTO_MERGE/PR_ONLY 키워드면 사용.
---

# pr-merge-orchestrator

## Role
결정(AUTO_MERGE/PR_ONLY)에 따라 “다음 실행 단계(계획)”를 산출한다.
- 실제 PR 생성/merge는 Cursor 소유 + 승인 필요

## Steps
- mode=PR_ONLY:
  1) PR 생성
  2) checks 통과 확인
  3) 리뷰/승인 후 merge 가능
- mode=AUTO_MERGE:
  1) 마지막 위험 재확인(삭제/Protected/External/lockfile 금지)
  2) Gate all PASS
  3) 조건 충족 시만 merge 가능

## Outputs
- pr-merge-orchestrator branch
```

### `skill-pack/pr-merge-orchestrator/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "pr-merge-orchestrator",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "PR_ONLY 실행 계획 산출.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "pr" },
    "approvals": [{ "tool_class": "PR", "needs_approval": true, "state": "PENDING" }],
    "audit": { "event_id": "EVT-OK-PRPLAN", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "mode": "PR_ONLY", "plan": ["Create PR", "Run checks", "Request review", "Merge after approval"] }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "pr-merge-orchestrator",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "AUTO_MERGE 조건 미충족으로 계획 중단.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "MERGE", "needs_approval": true, "state": "PENDING" }],
    "audit": { "event_id": "EVT-FAIL-PRPLAN", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "mode": "AUTO_MERGE", "plan": ["AUTO_MERGE blocked: risk/gate condition not met"] }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "pr-merge-orchestrator",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "PR 승인 미확보로 실행 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "PR", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-PRPLAN", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "mode": "PR_ONLY", "plan": ["Approval required"] }
  }
}
```

---

### `skill-pack/audit-append/SKILL.md`

```md
---
name: audit-append
description: append-only 감사로그 기록(이벤트 체인). audit/append-only/trace 키워드면 사용.
---

# audit-append

## Role
각 단계 결과를 append-only 로그로 남긴다(수정/삭제 금지).

## Steps
1) WRITE 승인 확보
2) append_only_path에 JSONL로 1줄 append
3) event_id/prev_event_id 체인 유지

## Outputs
- audit-append branch
```

### `skill-pack/audit-append/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "audit-append",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "감사로그 append 완료.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-AUDIT", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "appended": true, "audit_path": ".autodev_queue/audit/2026-02-13.jsonl", "record_digest": "sha256:placeholder" }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "audit-append",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "append-only 위반(덮어쓰기 시도)으로 실패.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "blocked" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-AUDIT", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "appended": false, "audit_path": ".autodev_queue/audit/2026-02-13.jsonl", "record_digest": "" }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "audit-append",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "WRITE 승인 미확보로 감사로그 기록 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "work" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-AUDIT", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "appended": false, "audit_path": ".autodev_queue/audit/2026-02-13.jsonl", "record_digest": "" }
  }
}
```

---

### `skill-pack/incident-brief/SKILL.md`

```md
---
name: incident-brief
description: S7 수렴 사고 리포트(원인/영향/복구 R1~R8 참조/알림 템플릿). incident/S7/recovery 키워드면 사용.
---

# incident-brief

## Role
ZERO_STOP/FAIL/DENY 상황을 “사고 텍스트”로 구조화하고 blocked로 수렴한다.

## Steps
1) WRITE 승인 확보
2) incident_id 생성(세션 내 유니크)
3) headline/impact/actions/recovery_refs(R#) 작성
4) notify_template 포함(외부 전송은 금지, 텍스트만)

## Outputs
- incident-brief branch
```

### `skill-pack/incident-brief/references/examples.json`

```json
{
  "ok": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "incident-brief",
    "skill_version": "1.0.0",
    "status": "OK",
    "summary": "Incident brief 생성 완료.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "blocked" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-OK-INC", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "incident_id": "INC-0001", "severity": "SEV2", "headline": "Gate FAIL", "actions": ["Block task", "Collect evidence"], "recovery_refs": ["R4"] }
  },
  "fail": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "incident-brief",
    "skill_version": "1.0.0",
    "status": "FAIL",
    "summary": "Incident brief 작성 실패(경로 오류).",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "blocked" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "APPROVED" }],
    "audit": { "event_id": "EVT-FAIL-INC", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "incident_id": "INC-0001", "severity": "SEV1", "headline": "Policy violation", "actions": ["ZERO_STOP"], "recovery_refs": ["R8"] }
  },
  "deny": {
    "schema_id": "urn:project_baton_v1:skill_output_envelope",
    "schema_version": "1.0.0",
    "skill": "incident-brief",
    "skill_version": "1.0.0",
    "status": "DENY",
    "summary": "WRITE 승인 미확보로 incident 작성 거절.",
    "task": { "task_id": "TASK-0001", "queue_root": ".autodev_queue", "state_before": "work", "state_after": "blocked" },
    "approvals": [{ "tool_class": "WRITE", "needs_approval": true, "state": "DENIED" }],
    "audit": { "event_id": "EVT-DENY-INC", "append_only_path": ".autodev_queue/audit/2026-02-13.jsonl" },
    "data": { "incident_id": "INC-0001", "severity": "SEV3", "headline": "Approval required", "actions": ["Request approval"], "recovery_refs": ["R7"] }
  }
}
```

---

## 7) 플랫폼별 설치 안내(Project/User 경로)

### OpenAI Codex

* Repo(스캔 우선순위): `$CWD/.agents/skills`, `$CWD/../.agents/skills`, `$REPO_ROOT/.agents/skills`
* User: `$HOME/.agents/skills` ([developers.openai.com][1])
  **설치:** `skill-pack/*`를 위 경로 중 하나로 복사(또는 symlink).
  **비활성화:** `~/.codex/config.toml`에서 `[[skills.config]] path=... enabled=false` ([developers.openai.com][1])

### Cursor

* Project: `.cursor/skills/`, (호환) `.claude/skills/`, `.codex/skills/`
* User: `~/.cursor/skills/` ([Cursor][2])
  **설치:** `skill-pack/*`를 `.cursor/skills/`로 복사 권장.

### GitHub Copilot

* Project: `.github/skills/` 또는 `.claude/skills/`
* Personal: `~/.copilot/skills/` 또는 `~/.claude/skills/` ([GitHub Docs][3])

### Claude Code

* (Copilot 문서에도 동일 경로로 언급) Project: `.claude/skills/`, Personal: `~/.claude/skills/` ([GitHub Docs][3])

---

## 8) 검증 체크리스트(최소) + 예시 커맨드

* [ ] 각 폴더명 = frontmatter `name` 일치(예: `skill-pack/stop-check` ↔ `name: stop-check`)
* [ ] 모든 SKILL.md에 `description`이 “무엇을/언제(트리거)”를 포함
* [ ] Output JSON이 `docs/skills/schemas/skill_outputs.schema.json`의 해당 branch에 부합
* [ ] needsApproval 기본 true / External 기본 DENY / OpenClaw 제안만(EXEC/PR/MERGE 금지) 문구 포함
* [ ] Denied 재시도 금지 명시
* [ ] SKILL.md가 과도하게 길지 않음(권장 500줄 이하)

**로컬 검증 예시(선택):**

```bash
# JSON 문법 체크
python -m json.tool docs/skills/schemas/skill_io_envelope.schema.json > /dev/null
python -m json.tool docs/skills/schemas/skill_outputs.schema.json > /dev/null
```

---

## 9) 근거/참고(확인 날짜: 2026-02-13, Asia/Dubai)

* OpenAI Codex Skills 저장 경로/스캔/disable 설정: ([developers.openai.com][1])
* Cursor Skills 디렉토리(프로젝트/유저): ([Cursor][2])
* GitHub Copilot Skills 디렉토리(.github/skills, ~/.copilot/skills, .claude/skills): ([GitHub Docs][3])

[1]: https://developers.openai.com/codex/skills/ "Agent Skills"
[2]: https://cursor.com/cn/docs/context/skills?utm_source=chatgpt.com "Agent Skills | Cursor Docs"
[3]: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills "About Agent Skills - GitHub Docs"
