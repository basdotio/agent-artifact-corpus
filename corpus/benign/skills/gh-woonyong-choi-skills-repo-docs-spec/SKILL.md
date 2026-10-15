---
name: repo-docs-spec
description: "구현된 protocol·CLI·UI·data·configuration·errors의 형식과 값을 문서화할 때 사용."
---

# Repo Docs Spec

- 우선순위: 사용자 지시 → 저장소 규칙 → 이 스킬. 범위 밖은 명시한 소유 스킬 적용
- 기반: repo-docs 먼저 적용. 이 스킬 범위: 인터페이스 문서 템플릿과 항목 규칙
- 필요할 때만 읽기: 데이터 그림을 만들거나 바꿀 때 → repo-docs-figures; 요구·검증 범위, 생성표 의미, 기능 생략 시 호환 사례 → repo-docs-design 요구사항 절
- 문서 생성 여부: repo-docs 문서 목록 만드는 조건
- 인터페이스 문서: 찾아보는 문서. 형식 이해에 필요한 설명과 항목 포함. 선택 이유는 설계 문서에
- 코드에서 만들 수 있는 내용(명령 도움말, 스키마, 기본값): 코드와 같은 글자. 코드가 바뀌면 같은 PR에서 수정
- 항목 순서: 문서마다 정한 순서. 정하지 않은 곳은 알파벳순

## protocol.md

`protocol.md` 작성·갱신·검토 전 [protocol.md](references/protocol.md) 필수 확인

## cli.md

`cli.md` 작성·갱신·검토 전 [cli.md](references/cli.md) 필수 확인

## ui.md

`ui.md` 작성·갱신·검토 전 [ui.md](references/ui.md) 필수 확인

## data.md

`data.md` 작성·갱신·검토 전 [data.md](references/data.md) 필수 확인

## configuration.md

`configuration.md` 작성·갱신·검토 전 [configuration.md](references/configuration.md) 필수 확인

## errors.md

`errors.md` 작성·갱신·검토 전 [errors.md](references/errors.md) 필수 확인
