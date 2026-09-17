---
name: vessl-ssh
description: VESSL 워크스페이스 SSH 연결 및 VSCode 통합. "/vessl-ssh", "VESSL 연결", "vessl connect", "workspace ssh" 요청에 사용.
version: 1.0.0
---

# VESSL Workspace SSH Connector

VESSL 워크스페이스에 SSH 또는 VSCode Remote-SSH로 연결합니다.

## Trigger

- `/vessl-ssh`
- "vessl 연결", "VESSL 접속", "vessl connect"
- "workspace ssh", "워크스페이스 연결"

## Prerequisites Check

이 스킬을 실행하기 전에 최초 설정이 완료되었는지 확인합니다.

```bash
# 설정 확인 명령어
vessl whoami 2>/dev/null && vessl ssh-key list 2>/dev/null
```

- **명령어 실패 시**: SKILL-setup.md 참조 유도
- **성공 시**: 워크플로우 계속 진행

**미설정 안내 메시지**:
```
VESSL 초기 설정이 필요합니다.
설정 가이드: skills/vessl-ssh/SKILL-setup.md

또는 다음 명령어로 빠르게 설정하세요:
1. vessl login        # 브라우저 인증
2. vessl ssh-key add  # SSH 키 등록
```

## Workflow

### Phase 1: 연결 방식 선택

AskUserQuestion을 사용하여 연결 방식을 선택합니다:

```
AskUserQuestion:
question: "VESSL 워크스페이스에 어떻게 연결할까요?"
header: "연결 방식"
options:
  - label: "SSH 터미널 (Recommended)"
    description: "터미널에서 직접 SSH로 연결합니다"
  - label: "VSCode Remote-SSH"
    description: "VSCode에서 원격 개발 환경을 엽니다"
  - label: "워크스페이스 관리"
    description: "워크스페이스 시작/중지 관리"
```

### Phase 2: 워크스페이스 목록 조회

```bash
vessl workspace list
```

출력 예시:
```
 ID    NAME              STATUS
 1234  my-workspace      running
 5678  dev-environment   stopped
```

### Phase 3: 워크스페이스 선택

워크스페이스가 **1개**인 경우: 자동 선택

워크스페이스가 **여러 개**인 경우: AskUserQuestion 사용

```
AskUserQuestion:
question: "어떤 워크스페이스에 연결할까요?"
header: "Workspace"
options:
  - label: "my-workspace (running)"
    description: "ID: 1234"
  - label: "dev-environment (stopped)"
    description: "ID: 5678 - 시작 필요"
```

### Phase 4: 상태 확인 및 시작

선택한 워크스페이스가 **stopped** 상태인 경우:

```
AskUserQuestion:
question: "워크스페이스가 중지 상태입니다. 시작할까요?"
header: "시작 확인"
options:
  - label: "시작하기 (Recommended)"
    description: "워크스페이스를 시작하고 연결합니다 (1-2분 소요)"
  - label: "취소"
    description: "연결을 취소합니다"
```

시작 명령:
```bash
vessl workspace start {workspace_id}
```

시작 완료 대기:
```bash
# 상태가 running이 될 때까지 대기
vessl workspace list --format json | jq '.[] | select(.id == {workspace_id}) | .status'
```

### Phase 5: 연결 실행

**SSH 터미널 연결**:
```bash
vessl workspace ssh {workspace_name}
```

**VSCode Remote-SSH 연결**:
```bash
vessl workspace vscode {workspace_name}
```

**워크스페이스 관리** (Phase 1에서 선택 시):

```
AskUserQuestion:
question: "어떤 작업을 수행할까요?"
header: "관리"
options:
  - label: "워크스페이스 중지"
    description: "실행 중인 워크스페이스를 중지합니다"
  - label: "워크스페이스 시작"
    description: "중지된 워크스페이스를 시작합니다"
```

중지 명령:
```bash
vessl workspace stop {workspace_id}
```

### Phase 6: 연결 후 안내

연결 성공 후 다음 팁을 제공합니다:

```
✅ VESSL 워크스페이스에 연결되었습니다!

💡 유용한 팁:
- /dacon-downloaddata 로 HuggingFace 데이터셋을 다운로드할 수 있습니다
- 워크스페이스 종료 시: exit 또는 Ctrl+D
- 연결 해제 시에도 워크스페이스는 계속 실행됩니다
- 비용 절약을 위해 작업 완료 후 워크스페이스를 중지하세요
```

## CLI Reference

| 명령어 | 용도 |
|--------|------|
| `vessl workspace list` | 워크스페이스 목록 조회 |
| `vessl workspace ssh {name}` | SSH 연결 |
| `vessl workspace vscode {name}` | VSCode Remote-SSH 설정 |
| `vessl workspace start {id}` | 워크스페이스 시작 |
| `vessl workspace stop {id}` | 워크스페이스 중지 |
| `vessl whoami` | 로그인 상태 확인 |
| `vessl ssh-key list` | SSH 키 등록 상태 확인 |

## Error Handling

| 상황 | 대응 |
|------|------|
| CLI 미설치 | SKILL-setup.md Step 1 안내 (`brew install vessl-ai/tap/vessl` 또는 `pip install vessl`) |
| 로그인 필요 | `vessl login` 실행 안내 |
| SSH 키 미등록 | SKILL-setup.md Step 3-4 안내 |
| 워크스페이스 없음 | VESSL 웹 콘솔(https://vessl.ai)에서 생성 안내 |
| 연결 실패 | 네트워크 확인 및 `vessl workspace ssh` 재시도 안내 |
| 워크스페이스 시작 실패 | 리소스 할당 문제 가능성 안내, 웹 콘솔 확인 권장 |

## Example Usage

**사용자 요청**:
```
/vessl-ssh
```

**실행 흐름**:
```
1. ✅ VESSL 설정 확인 완료
2. 🔍 연결 방식: SSH 터미널
3. 📋 워크스페이스: my-workspace (running)
4. 🚀 SSH 연결 중...

✅ VESSL 워크스페이스에 연결되었습니다!
```

## Notes

- SSH 연결은 인터랙티브 세션으로, Claude Code 내에서 직접 명령어 실행이 가능합니다
- VSCode 연결은 별도 창에서 원격 개발 환경이 열립니다
- 워크스페이스 비용은 실행 시간 기준으로 청구됩니다 - 작업 완료 후 중지 권장
