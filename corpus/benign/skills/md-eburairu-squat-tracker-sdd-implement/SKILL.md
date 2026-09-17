---
name: sdd-implement
description: 作成済みのタスクリスト（tasks.md）に従い、厳格なテスト駆動開発（TDD）サイクルを回して実装を進める標準モード。
---

Trigger examples: "実装開始", "コード書いて", "implement feature", "start coding", "タスク消化", "TDD実行", "開発開始"

## ステップ1：前提確認とspec特定
1. `.sdd/target-spec.txt` からspec名を取得し、ディレクトリの存在を確認する。
2. ステアリング情報（product.md, tech.md, structure.md）を読み込む。
3. spec文書一式（requirements.md, design.md, tasks.md）を読み込む。
   - `tasks.md` が存在しない場合は、`/sdd-tasks` または `/sdd-highway` を案内して終了する。

## ステップ2：実装実行ループ
`tasks.md` の未完了タスクを上から順に実行する：

1. **Test (RED)**: 対象タスクのテストコードを作成/修正し、`npm test` で失敗することを確認する。
2. **Implement (GREEN)**: テストを通すための最小限の実装を行う。
3. **Refactor**: 重複の排除や可読性の向上など、コードを整理する。
4. **Update**: `tasks.md` の当該タスクを `[x]` に更新する。

※タスクはスキップせず、必ず順番に消化すること。

## ステップ3：完了後の処理
すべてのタスクが完了したら：
1. 全テスト (`npm test`) が通過することを確認する。
2. `/sdd-archive` を実行して仕様をクローズするよう案内する。
3. 未解決の課題がある場合は、その理由と対処を記録する。
