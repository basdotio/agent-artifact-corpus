---
name: commit
description: Simplify review then commit changes
user_invocable: true
---

# Commit Skill

변경사항을 커밋하기 전에 /simplify를 실행하여 코드 품질을 점검한 후 커밋한다.

## Workflow

1. `/simplify` 스킬을 실행한다 (코드 재사용성, 품질, 효율성 점검)
2. 발견된 이슈를 수정한다
3. 수정 사항을 포함하여 새 커밋을 생성한다
4. 커밋 메시지는 conventional commits 스타일로 작성한다

## Rules

- simplify에서 발견된 이슈 중 실제로 수정할 가치가 있는 것만 수정한다. 과도한 리팩토링은 하지 않는다.
- "마무리해"라는 요청이 오면 이 스킬을 실행한다.
- simplify를 이미 실행하고 반영까지 완료한 상태라면 다시 실행하지 않고 바로 커밋한다.
