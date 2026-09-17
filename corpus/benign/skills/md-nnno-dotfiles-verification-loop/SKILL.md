---
name: verification-loop
description: PR作成前の6段階検証（ビルド、型チェック、リント、テスト、セキュリティ、差分確認）を実行。トリガー: "検証", "PR準備", "/verify", "/verification-loop"
---

# Verification Loop（検証ループ）

コード変更後、PR作成前に実行する6段階の品質検証フレームワーク。

## 使用タイミング

- 機能実装完了後
- 重要なコード変更後
- PR 作成前
- 長時間の開発セッション中（15分ごとの定期チェック推奨）

---

## 6段階検証フェーズ

### Phase 1: ビルド検証

プロジェクトが正常にコンパイルされることを確認。

| 環境 | コマンド |
|------|----------|
| TypeScript | `npm run build` または `pnpm build` |
| Go | `go build ./...` |

```bash
# TypeScript
npm run build

# Go
go build ./...
```

### Phase 2: 型チェック

型安全性を検証。

| 環境 | コマンド |
|------|----------|
| TypeScript | `tsc --noEmit` |
| Go | コンパイル時に自動実行 |

```bash
# TypeScript
npx tsc --noEmit

# Go（vet で追加チェック）
go vet ./...
```

### Phase 3: リントチェック

コードスタイルと潜在的な問題を検出。

| 環境 | コマンド |
|------|----------|
| TypeScript | `eslint .` または `biome check .` |
| Go | `golangci-lint run` |

```bash
# TypeScript（ESLint）
npx eslint . --ext .ts,.tsx

# TypeScript（Biome）
npx biome check .

# Go
golangci-lint run ./...
```

### Phase 4: テスト実行

テストスイートを実行し、カバレッジを確認。
**目標: 80%以上のカバレッジ**

| 環境 | コマンド |
|------|----------|
| TypeScript | `npm test` または `vitest run --coverage` |
| Go | `go test -cover ./...` |

```bash
# TypeScript（Vitest）
npx vitest run --coverage

# TypeScript（Jest）
npm test -- --coverage

# Go
go test -cover -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
```

### Phase 5: セキュリティスキャン

既知の脆弱性とセキュリティ問題を検出。

| 環境 | コマンド |
|------|----------|
| TypeScript | `npm audit` |
| Go | `gosec ./...` または `govulncheck ./...` |

```bash
# TypeScript
npm audit
# 修正可能な脆弱性を自動修正
npm audit fix

# Go（gosec）
gosec ./...

# Go（govulncheck）
govulncheck ./...
```

### Phase 6: 差分確認

意図しない変更がないかを確認。

```bash
# ステージングされていない変更を確認
git diff

# ステージングされた変更を確認
git diff --staged

# 変更されたファイル一覧
git status

# 特定のファイルの詳細差分
git diff -- path/to/file
```

---

## コマンドマトリクス

| フェーズ | TypeScript | Go |
|----------|------------|-----|
| ビルド | `npm run build` | `go build ./...` |
| 型チェック | `tsc --noEmit` | `go vet ./...` |
| リント | `eslint .` / `biome check .` | `golangci-lint run` |
| テスト | `npm test --coverage` | `go test -cover ./...` |
| セキュリティ | `npm audit` | `gosec ./...` / `govulncheck ./...` |
| 差分確認 | `git diff` | `git diff` |

---

## 一括実行スクリプト

### TypeScript プロジェクト用

```bash
#!/bin/bash
set -e

echo "=== Phase 1: Build ==="
npm run build

echo "=== Phase 2: Type Check ==="
npx tsc --noEmit

echo "=== Phase 3: Lint ==="
npx eslint . --ext .ts,.tsx

echo "=== Phase 4: Test ==="
npm test -- --coverage

echo "=== Phase 5: Security ==="
npm audit

echo "=== Phase 6: Diff Review ==="
git status
git diff --stat

echo "=== All Phases Complete ==="
```

### Go プロジェクト用

```bash
#!/bin/bash
set -e

echo "=== Phase 1: Build ==="
go build ./...

echo "=== Phase 2: Vet ==="
go vet ./...

echo "=== Phase 3: Lint ==="
golangci-lint run ./...

echo "=== Phase 4: Test ==="
go test -cover ./...

echo "=== Phase 5: Security ==="
gosec ./...

echo "=== Phase 6: Diff Review ==="
git status
git diff --stat

echo "=== All Phases Complete ==="
```

---

## 検証レポート形式

各フェーズの結果を以下の形式で報告:

```
┌─────────────────────────────────────────┐
│         VERIFICATION REPORT             │
├─────────────────────────────────────────┤
│ Phase 1: Build          ✅ PASS         │
│ Phase 2: Type Check     ✅ PASS         │
│ Phase 3: Lint           ⚠️ 3 warnings   │
│ Phase 4: Test           ✅ 85% coverage │
│ Phase 5: Security       ✅ PASS         │
│ Phase 6: Diff Review    ✅ 5 files      │
├─────────────────────────────────────────┤
│ OVERALL: ✅ READY FOR PR                │
└─────────────────────────────────────────┘
```

### ステータス判定基準

| ステータス | 条件 |
|------------|------|
| ✅ READY | すべてのフェーズが PASS |
| ⚠️ REVIEW NEEDED | 警告あり（重大な問題なし） |
| ❌ NOT READY | いずれかのフェーズが FAIL |

---

## トラブルシューティング

### ビルドエラー

```bash
# TypeScript: 依存関係の再インストール
rm -rf node_modules package-lock.json
npm install

# Go: モジュールキャッシュのクリア
go clean -modcache
go mod download
```

### リントエラーの自動修正

```bash
# TypeScript（ESLint）
npx eslint . --fix

# TypeScript（Biome）
npx biome check --apply .

# Go（gofmt）
gofmt -w .
```

### テスト失敗時のデバッグ

```bash
# TypeScript: 特定のテストのみ実行
npm test -- --grep "test name"

# Go: 特定のテストをverboseで実行
go test -v -run TestFunctionName ./...
```

---

## CI/CD 統合例

### GitHub Actions（TypeScript）

```yaml
name: Verification
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run build
      - run: npx tsc --noEmit
      - run: npx eslint .
      - run: npm test -- --coverage
      - run: npm audit --audit-level=high
```

### GitHub Actions（Go）

```yaml
name: Verification
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: go build ./...
      - run: go vet ./...
      - run: golangci-lint run
      - run: go test -cover ./...
      - run: govulncheck ./...
```

---

## ベストプラクティス

1. **早期・頻繁に検証**: 問題の蓄積を防ぐため、小さな変更ごとに検証
2. **自動化**: pre-commit hook や CI で自動実行
3. **カバレッジ監視**: 80%を下回らないよう維持
4. **セキュリティ優先**: セキュリティ警告は即座に対応
5. **差分レビュー**: 意図しない変更を見逃さない
