---
name: make-release
description: 저장소 릴리즈 배포 — 남은 수정사항 커밋·푸시, 검증, 버전 올리기(프로젝트의 모든 버전 파일), 태그 푸시, GitHub 릴리즈 노트 작성·공개까지 한 번에. 태그로 도는 Release 워크플로가 있으면 빌드를 기다려 초안을 공개한다. "릴리즈 해줘", "배포해줘", "새 버전 내줘", "/make-release [버전]"에 사용.
argument-hint: "[버전, 예: 1.4.0 | patch | minor | major | 1.5.0-beta.1] (생략 시 변경 내용으로 판단)"
---

# make-release — 릴리즈 배포

인자: `$ARGUMENTS` (비어 있으면 버전을 직접 판단)

사용자가 이 스킬을 호출한 것 자체가 **이번 릴리즈(커밋·푸시·태그·릴리즈 공개)에 대한 승인**이다. 단, 승인 범위는 이 저장소의 git 태그와 GitHub 릴리즈까지다. 패키지 레지스트리 수동 게시(`npm publish`, `cargo publish`, `twine upload` 등)·운영 배포처럼 되돌리기 어려운 외부 작업은 프로젝트 지침에 절차로 적혀 있거나 사용자가 명시했을 때만 한다.

**프로젝트 규칙 우선**: CLAUDE.md·AGENTS.md·README·CONTRIBUTING·RELEASING.md·docs/ 에 릴리즈 절차(버전 파일, 검증 명령, 노트 형식, 허용되는 기존 실패 등)가 있으면 그것을 이 문서보다 우선한다. 먼저 찾아 읽는다(`grep -ril "release\|릴리즈\|릴리스" *.md docs .github 2>/dev/null`).

## 0. 환경 주의
- 커밋 메시지·릴리즈 노트는 **파일(BOM 없는 UTF-8)** 이나 HEREDOC으로 넘긴다(`git commit -F`, `gh release ... --notes-file`). Windows PowerShell 5.1은 네이티브 인자 속 `"`를 깨뜨리므로 특히 파일로 쓴다.
- 대화에서 지정된 attribution 줄(예: `Co-Authored-By: ...`)이 있으면 커밋 메시지 끝에 붙인다.
- `gh`가 없거나 `gh auth status`가 실패하면 태그 푸시까지만 하고 릴리즈 생성은 보고로 넘긴다(GitHub가 아닌 원격도 마찬가지).

## 1. 상태 점검 (병렬로)
```
git status --short
git branch --show-current
git remote show origin | grep 'HEAD branch'      # 기본 브랜치
git log --oneline -1 --decorate
git tag --sort=-v:refname | head -5
gh release list --limit 3
ls .github/workflows/ 2>/dev/null
```
- **직전 릴리즈 태그**: `git describe --tags --abbrev=0`(없으면 첫 릴리즈 — 전체 히스토리가 대상). 태그 형식(`v1.2.3` / `1.2.3` / `pkg@1.2.3`)은 기존 태그를 따른다. 태그가 없으면 `v` 접두사.
- 현재 브랜치가 기본 브랜치(또는 프로젝트가 정한 릴리즈 브랜치)가 아니면 멈추고 알린다.
- 미커밋 변경은 멈추지 말고 **upload-git 스킬과 같은 규칙**으로 처리한다: diff를 읽고 성격별로 나눠 커밋(저장소 관례 접두사), 비밀 값·정체불명 파일은 커밋하지 말고 묻는다. 그다음 `git fetch` → 원격이 앞서 있으면 `git pull --rebase` → 미푸시 커밋을 푸시.
- 직전 태그 이후 커밋이 없으면 릴리즈할 게 없다고 알리고 끝낸다.

## 2. 릴리즈 방식 파악
- **Release 워크플로**: `.github/workflows/*.yml`에서 `on: push: tags:` 또는 `release:` 트리거를 찾는다. 있으면 무엇을 하는지 읽는다(빌드 산출물, 초안 생성 여부, 레지스트리 게시 여부, 필요한 secrets).
  - 태그 푸시 → 워크플로가 릴리즈(초안)를 만드는 방식 → 5·6단계에서 기다렸다가 노트를 채워 공개.
  - `release: published` 트리거 방식 → 릴리즈를 직접 만들면 워크플로가 뒤따른다.
  - 워크플로가 없으면 → 6단계에서 `gh release create`로 직접 만든다.
- **릴리즈 도구**: `release-please`·`changesets`·`semantic-release`·`goreleaser`·`cargo-release` 설정이 있으면 그 도구의 흐름을 따르고, 수동으로 버전·태그를 만들어 도구와 충돌시키지 않는다(예: release-please면 릴리즈 PR을 머지하는 것이 릴리즈다 — 그 사실을 알리고 사용자에게 확인).

## 3. 검증
프로젝트에 정해진 검증 명령을 실행한다(지침 문서 → `package.json` scripts의 `typecheck`/`lint`/`test`/`build` → Makefile → 언어 기본 `cargo test`·`go test ./...`·`pytest` 순으로 찾는다). 패키지 매니저는 lockfile로 고른다(pnpm-lock → pnpm, yarn.lock → yarn, 그 외 npm).
- 실패하면 멈추고 고치거나 보고한다. 단, 프로젝트 문서에 **알려진 기존 실패**로 적혀 있고 그것과 동일한 실패면 진행하고 보고에 적는다. 새 실패면 멈춘다.
- 검증 명령이 없으면 생략하고 그렇게 보고한다.

## 4. 버전 결정·반영
- 인자가 버전이면 그대로. `patch`/`minor`/`major`면 직전 태그에서 올린다. 프리릴리즈(`-beta.1`, `-rc.1`)는 인자로 받았을 때만.
- 인자가 없으면 직전 태그 이후 커밋으로 판단(SemVer):
  - `BREAKING CHANGE`/`!:` 가 있으면 major (단 `0.x`에서는 minor)
  - 기능 커밋(`feat:`, `improve:`, `add`, 새 스킬·명령·화면 등)이 있으면 minor
  - 수정·문서·잡무만이면 patch
- **버전이 적힌 곳을 모두 찾는다**: 현재 버전 문자열로 `git grep -nF "<현재 버전>"`(lockfile·CHANGELOG 과거 항목·의존성 버전은 제외)과 아래 후보를 확인해 함께 바꾼다.
  - `package.json`(모노레포면 배포 대상 패키지 전부), `Cargo.toml`, `pyproject.toml`/`setup.cfg`/`__version__`, `pom.xml`/`build.gradle(.kts)`의 `version`, Android `versionName`과 `versionCode`(**+1**), iOS `MARKETING_VERSION`/`CURRENT_PROJECT_VERSION`, `.claude-plugin/plugin.json`, `manifest.json`, `tauri.conf.json`, `Chart.yaml`의 `version`/`appVersion` (Go 모듈은 태그가 곧 버전)
  - lockfile에 자기 버전이 박히는 경우(`Cargo.lock`, `package-lock.json`의 루트)는 도구로 갱신한다(`cargo update -p <crate>`, `npm install --package-lock-only`).
- `CHANGELOG.md`가 있으면 기존 형식(Keep a Changelog 등)대로 새 버전 항목을 추가한다(`Unreleased` 섹션이 있으면 그 내용을 새 버전으로 옮긴다).
- 커밋: 저장소 관례대로, 없으면 `chore: release v<버전>` (본문에 주요 변경을 짧게).

## 5. 푸시·태그
```
git push origin <브랜치>
git tag -a <태그> -m <태그>
git push origin <태그>
```
- 태그 푸시는 공개 배포의 시작이다. 사용자가 **이번 요청에서** 릴리즈를 시켰을 때만 실행한다.
- 워크플로가 있으면 `gh run list --workflow <파일> --limit 1`로 실행을 찾고 `gh run watch <runId> --exit-status --interval 30`을 **백그라운드**로 실행해 기다린다.
- 빌드 실패 시 `gh run view <runId> --log-failed | tail -80`으로 원인을 보고 고친다. 고친 뒤 태그를 새 커밋으로 옮긴다: `git tag -d <태그> && git push origin :refs/tags/<태그>` → 남은 초안 릴리즈가 있으면 `gh release delete <태그> --yes` → 고친 커밋 푸시 → 5단계 다시. **이미 공개(non-draft)된 릴리즈나 레지스트리에 게시된 버전은 지우지 말고** 다음 patch 버전으로 다시 낸다.

## 6. 릴리즈 노트 작성·공개
- 재료: `git log --format='%h %s%n%b' <직전 태그>..<태그>`, 머지된 PR(`gh pr list --state merged --search "merged:>=<직전 태그 날짜>"`), CHANGELOG·결정 기록 문서.
- 형식: 직전 릴리즈 노트(`gh release view <직전 태그> --json body -q .body`)를 따른다. 이전 릴리즈가 없으면 기본 형식:
  - 언어는 이전 노트 → 저장소 문서 → 사용자 언어 순으로 따른다.
  - `## 새 기능` / `## 개선` / `## 버그 수정` / `## 호환성 주의`(Breaking·필수 동반 업데이트) — 커밋 나열이 아니라 **사용자 관점**에서 무엇이 가능해졌는지. 내부 리팩터·CI 변경은 생략하거나 한 줄로.
  - 빌드 산출물이 있으면 `## 설치 파일` 표(실제 자산 이름 ↔ 플랫폼). 자산은 `gh release view <태그> --json assets`로 확인하고, 기대한 플랫폼 자산이 빠졌으면 보고한다.
  - `**Full Changelog**: https://github.com/<owner>/<repo>/compare/<직전 태그>...<태그>` (첫 릴리즈면 생략)
- 노트를 임시 파일로 쓰고:
  - 워크플로가 만든 초안이 있으면: `gh release edit <태그> --notes-file <파일> --draft=false --latest`
  - 없으면: `gh release create <태그> --title <태그> --notes-file <파일> --verify-tag` (프리릴리즈면 `--prerelease`, `--latest` 대신)
- `gh release view <태그> --json isDraft,isPrerelease,url`로 공개됐는지 확인한다.

## 7. 보고
사용자 언어로 짧게: 버전(직전 → 새), 바꾼 버전 파일, 포함된 변경 요약, 검증 결과(남은 기존 실패 포함), 워크플로 결과와 산출물, 릴리즈 URL, 서명·공증 여부처럼 워크플로 로그에서 드러난 주의점, 하지 않은 외부 작업(레지스트리 게시 등)이 있으면 그 이유.

## 멈출 때
- 기본(릴리즈) 브랜치가 아님, 비밀 값·정체불명 파일, 새 검증 실패, rebase 충돌
- 직전 태그 이후 변경 없음
- 같은 이름의 태그·릴리즈가 이미 존재(덮어쓰지 않는다 — 다음 버전을 제안)
- 릴리즈 도구(release-please 등)의 흐름과 수동 릴리즈가 충돌할 때
