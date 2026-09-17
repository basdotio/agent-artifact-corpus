---
name: skill-issue-manager
description: GitHub Issueのライフサイクル管理（作成、仕様策定、実装、レビュー、完了）を自動化・支援し、Issue駆動開発（IDD）を推進するスキル。
---

# Skill: GitHub Issue Manager

GitHub Issueのライフサイクル全体（作成、開発開始、実装、レビュー、完了）を管理し、Issue駆動開発（IDD）のプロセスを自動化・支援します。

## 概要
IDD（Issue-Driven Development）プロセスの各フェーズ（Start, Task, Review, End）を適切に遷移させ、GitHub Issue を SSOT として管理する。

## Instructions
1. **ブランチ管理**: 作業開始時に必ず Issue 専用のブランチを作成する。
2. **SSOT 準拠**: GitHub Issue の Body を常に最新の要件（Success Criteria）として扱う。
3. **フェーズ管理**: 
   - **Start**: `design.md` と `tasks.md` を作成しユーザーの承認を得る。
   - **Task**: 承認されたタスクに基づき実装。
   - **Review**: 自己レビューとテスト。
   - **End**: PR 作成。
4. **トレーサビリティ**: セッションログを `development_logs/` に記録する。

## Output Contract
- GitHub Issue の作成・更新・状態遷移
- Issue ワークスペース (`docs/issues/[ID]/`) 内の `design.md` および `tasks.md`
- 開発ブランチおよび PR (Pull Request)
- `development_logs/` への作業記録
