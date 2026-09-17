---
name: pr-ci-loop
description: "GitHub PR URL을 인자로 받아 현재 브랜치가 PR의 head branch와 일치하는지 검증한 뒤, GitHub Actions CI 실패 원인을 분석/수정하고 commit+push 후 CI 성공을 폴링으로 확인하는 복구 루프를 수행한다. CodeRabbit/Copilot 같은 코드리뷰 체크는 제외하고 GitHub Actions run만 대상으로 한다. PR CI 실패 복구를 요청받으면 사용한다."
argument-hint: "[pr-url]"
disable-model-invocation: true
---

# PR CI Loop

GitHub PR의 GitHub Actions CI 실패를 `분석 -> 최소 수정 -> commit -> push -> 재폴링`으로 반복해서 녹색이 될 때까지 복구한다.

핵심 원칙:

1. 브랜치 일치 검증 우선
- PR head branch와 현재 체크아웃 브랜치가 다르면 즉시 중단한다.

2. Actions만 대상으로
- CodeRabbit/Copilot 등 코드리뷰/봇 체크는 대기/성공 판정에서 제외한다.

3. 최소 수정 + 재현 우선
- 실패한 step의 실행 커맨드를 로컬에서 가능한 한 재현 후 수정한다.
- 불필요한 리팩토링/정리 커밋을 섞지 않는다.

4. 루프 안전장치
- 동일 실패가 2회 반복되면 원인/대안 정리 후 사용자 승인 없이는 방향을 바꾸지 않는다.
- 권한/시크릿/외부 장애 등 자동 수정 불가 사유는 즉시 보고하고 중단한다.

## 사용법

- `/pr-ci-loop https://github.com/{owner}/{repo}/pull/{number}`
- 인자가 없으면 PR URL 입력을 요청하고 중단한다.

## 실행 워크플로우

### 0단계: 입력 검증 및 파싱

1. `$ARGUMENTS`에서 PR URL을 추출한다.
2. 아래 패턴과 일치하는지 확인한다.
- `https://github.com/{owner}/{repo}/pull/{number}`
3. 형식이 맞지 않으면 예시를 보여주고 중단한다.

파싱 예시:

```bash
PR_URL="$ARGUMENTS"
echo "$PR_URL" | grep -Eq '^https://github.com/[^/]+/[^/]+/pull/[0-9]+/?$'

OWNER=$(echo "$PR_URL" | sed -E 's@^https://github.com/([^/]+)/([^/]+)/pull/([0-9]+)/?$@\1@')
REPO=$(echo "$PR_URL" | sed -E 's@^https://github.com/([^/]+)/([^/]+)/pull/([0-9]+)/?$@\2@')
PR_NUMBER=$(echo "$PR_URL" | sed -E 's@^https://github.com/([^/]+)/([^/]+)/pull/([0-9]+)/?$@\3@')
REPO_NWO="$OWNER/$REPO"
```

### 1단계: 현재 브랜치와 PR head branch 일치 확인 (불일치 시 실패)

사전 체크:

```bash
git rev-parse --is-inside-work-tree
gh auth status
CURRENT_BRANCH=$(git branch --show-current)
test -n "$CURRENT_BRANCH"
```

현재 디렉토리의 저장소가 PR 저장소와 같은지 확인(권장):

```bash
LOCAL_REPO_NWO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
test "$LOCAL_REPO_NWO" = "$REPO_NWO"
```

PR의 head branch/sha 확인:

```bash
PR_HEAD_BRANCH=$(gh pr view -R "$REPO_NWO" "$PR_NUMBER" --json headRefName --jq .headRefName)
PR_HEAD_SHA=$(gh pr view -R "$REPO_NWO" "$PR_NUMBER" --json commits --jq '.commits[-1].oid')
echo "$PR_HEAD_BRANCH $PR_HEAD_SHA"
```

판정:

- `$CURRENT_BRANCH` != `$PR_HEAD_BRANCH` 이면 아래를 출력하고 즉시 중단한다.
  - 현재 브랜치
  - PR head branch
  - 올바른 사용 예시
- 일치하면 다음 단계로 진행한다.

push 거부(behind/non-fast-forward)를 예방하려면(권장):

```bash
git fetch origin
git status -sb
```

### 2단계: GitHub Actions CI 상태 폴링 (CodeRabbit/Copilot 제외)

환경 변수:

```bash
POLL_INTERVAL_SEC=60
MAX_EMPTY_POLLS=5
IGNORE_WORKFLOW_NAME_REGEX="coderabbit|copilot"
```

최신 head SHA 기준으로 워크플로우 이름별 최신 run 상태만 확인:

```bash
PR_HEAD_SHA=$(gh pr view -R "$REPO_NWO" "$PR_NUMBER" --json commits --jq '.commits[-1].oid')

gh run list -R "$REPO_NWO" --limit 200 \
  --json databaseId,headSha,event,status,conclusion,name,url,createdAt \
  --jq "
    [ .[]
      | select(.headSha == \"$PR_HEAD_SHA\")
      | select(.event == \"pull_request\" or .event == \"pull_request_target\")
      | select((.name | test(\"$IGNORE_WORKFLOW_NAME_REGEX\"; \"i\")) | not)
    ]
    | sort_by([.name, .createdAt])
    | group_by(.name)
    | map(.[-1])
    | sort_by(.createdAt)
    | reverse
    | .[]
    | [.name, (.conclusion // .status // \"PENDING\"), .url, (.databaseId|tostring)]
    | @tsv
  "
```

상태 판정 규칙:

- 결과가 비어있으면 `sleep "$POLL_INTERVAL_SEC"` 후 재조회한다.
  - 비어있는 상태가 `MAX_EMPTY_POLLS`를 초과하면 workflow 미설정/권한 문제 가능성이 있으니 중단하고 원인을 보고한다.
- 한 줄이라도 `queued/in_progress/waiting` 이면 `sleep` 후 재조회한다.
- 모든 줄이 `success/skipped/neutral` 이면 종료한다.
- 하나라도 `failure/error/timed_out/cancelled/action_required/startup_failure` 가 있으면 3단계로 진행한다.

### 3단계: 실패 run 분석

1. 실패 run 식별:
- 위 출력에서 실패 상태인 줄의 `RUN_ID(databaseId)`를 확보한다.
- 여러 개면 가장 최근 실패(출력 상단)를 먼저 처리한다.

2. 실패 로그 수집:

```bash
gh run view -R "$REPO_NWO" "$RUN_ID" --log-failed
```

3. 실패 원인 분류:
- 테스트 실패(단위/통합/e2e)
- lint/format/typecheck
- 빌드 실패
- 의존성/캐시/환경 변수/시크릿
- flaky(비결정적) / 외부 장애

4. 로컬 재현(가능한 한):
- 로그에 나온 실제 커맨드를 로컬에서 동일하게 실행한다.
- repo에 권장 명령이 있으면 그걸 우선한다 (예: `make ci`, `pnpm test`, `npm run lint`).

### 4단계: 수정 반영 -> commit -> push

1. 최소 수정으로 실패 원인을 해결한다.
2. 필요하면 관련 테스트/검증을 로컬에서 재실행한다.
3. 커밋:
- 프로젝트 커밋 컨벤션이 있으면 준수한다.
- 없으면 예: `fix: CI 실패 원인 수정 ({workflow-name})`

```bash
git status --porcelain
git diff
git add -A
git commit -m "fix: CI 실패 원인 수정"
git push
```

push가 거부되면(behind/non-fast-forward):

1. `git fetch` 후 `git pull --rebase`로 동기화하고 재시도한다.
2. 충돌이 크면 원인/대안을 정리해 사용자 승인 후 진행한다.

### 5단계: 루프

2단계로 돌아가서 다시 폴링한다.

반복 중단 조건:

- 동일한 실패 패턴(같은 workflow/같은 에러)이 2회 반복: 원인/가설/대안/추가 정보 요청을 정리하고 사용자 승인 전에는 방향 전환 금지
- 권한/시크릿/외부 장애로 자동 수정 불가: 필요한 수동 조치(예: 시크릿 추가, 권한 부여, workflow 수정 권한)를 명시하고 중단

### 6단계: 결과 요약 출력

- PR URL, 브랜치명, 최종 head SHA
- 폴링 횟수, 최종 상태
- 실패가 있었으면:
  - 실패 workflow/run url, 주요 에러 요약
  - 반영한 커밋 해시/메시지
  - 재검증 결과
