---
name: list-tasks
description: 現在のgit worktree一覧を表示します。アクティブなタスクを確認できます。
disable-model-invocation: true
allowed-tools: Bash(git:*)
---

# Worktree一覧表示

現在のプロジェクトに関連するすべてのworktreeを一覧表示します。

## 実行するコマンド

```bash
echo "📋 Git Worktrees:"
echo ""
git worktree list
```

結果を見やすく整形してユーザーに報告してください。各worktreeについて：
- パス
- ブランチ名
- コミットハッシュ（短縮版）

を表形式で表示すると分かりやすいです。
