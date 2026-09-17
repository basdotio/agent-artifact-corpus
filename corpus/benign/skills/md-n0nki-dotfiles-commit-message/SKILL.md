---
name: commit-message
description: git の staged な変更から適切なコミットメッセージを生成します。コミットメッセージの作成、git diff の確認、変更のレビューが必要なときに使用してください。
---

# Commit Message Helper

git の staged な変更を分析し、適切なコミットメッセージの候補を提案します。

## 前提条件

- コミットサマリは 50 文字前後、命令形・小文字で書き出す（例: `add AGENTS.md`）
- 生成物や個人環境ファイル（`~/.gitconfig.local` 等）はコミット対象にしない

## 実行手順

### 1. staged な変更を確認

```bash
git diff --staged
```

を実行して、ステージされているファイルと変更内容を確認します。

### 2. 変更内容の分析

- どのファイルがステージされているかを整理する
- 影響範囲をグルーピングし、コミットを1つにまとめても問題ないか確認する
- 明らかに別トピックが混ざっていれば分割を提案する

### 3. 差分が空の場合の対応

まず、staged な変更があるかを確認：

```bash
git diff --staged --name-only
```

または

```bash
git status -sb
```

staged な変更が存在しない場合は、以下のように伝える：

「現在ステージされている変更がありません。`git add <ファイル名>` でファイルをステージしてから、再度お試しください。」

### 4. コミットメッセージの生成

#### 返答フォーマット

1. **変更点の要約**（箇条書き、1〜3行）
   - 各項目に対象ファイルやディレクトリ名を含める
   - 例：
     - `src/components/Button.tsx` にクリックイベントハンドラを追加
     - `README.md` のインストール手順を更新

2. **コミットメッセージ候補**（3つ）
   - 各候補は1行で、命令形・短文
   - シンプルな形式を優先（特別な prefix は不要）
   - 候補例：

     ```
     候補1: add click handler to button component
     理由: Button コンポーネントの機能追加に焦点を当てた表現

     候補2: improve button interactivity
     理由: より抽象的で、機能改善の意図を強調

     候補3: add button click handler
     理由: 最もシンプルで明確な表現
     ```

3. **各候補の説明**
   - どの変更点と対応するのか示す
   - なぜそのメッセージが適切かの理由を簡潔に説明

### 5. 追加提案（必要に応じて）

変更内容に応じて、「Next steps」として以下のような提案を行う：

- 追加のテストが必要な場合
- ドキュメント更新が必要な場合
- 環境設定の確認が必要な場合
- コミットの分割を推奨する場合

## ガイドライン

### コミットメッセージの書き方

- 命令形で書く（`added` ではなく `add`）
- 小文字で始める（`Add` ではなく `add`）
- 50文字前後に収める
- 末尾にピリオドを付けない

### スコープの使い方（オプション）

**基本方針**: シンプルな命令形を優先し、特別な prefix（`nvim:`, `feat:` など）は付けない

推奨形式：

```
add button click handler
fix token refresh issue
update installation steps
```

必要に応じて、Conventional Commits 形式でスコープを括弧内に追加することも可能：

```
add (components): button click handler
fix (auth): token refresh issue
update (readme): installation steps
```

ただし、特に指定がない限りはシンプルな命令形のみを使用してください。

### 複数トピックの検出

以下のような場合は、コミットの分割を提案：

- 機能追加とバグ修正が混在
- 複数の独立した機能変更
- ドキュメント更新とコード変更が大量に混在

分割提案の例：
「この変更には2つの独立したトピックが含まれています。以下のように分割することをお勧めします：

1. 機能追加: `add user authentication`
2. バグ修正: `fix login redirect issue`」

## 例

### 例1: シンプルな機能追加

**staged な変更:**

```diff
+++ b/src/utils/validation.ts
+export function validateEmail(email: string): boolean {
+  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
+}
```

**返答:**

変更点の要約：

- `src/utils/validation.ts` にメールアドレス検証関数を追加

コミットメッセージ候補：

候補1: `add email validation function`
理由: シンプルで直接的な表現。何を追加したかが明確。

候補2: `add email validator to utils`
理由: 配置場所（utils）を含めることで、変更箇所がより明確。

候補3: `implement email validation`
理由: より実装に焦点を当てた表現で、技術的なニュアンスを強調。

### 例2: 複数ファイルの変更

**staged な変更:**

```diff
+++ b/src/components/LoginForm.tsx
// フォームコンポーネントの改善

+++ b/src/styles/form.css
// スタイルの追加

+++ b/README.md
// ドキュメント更新
```

**返答:**

変更点の要約：

- `src/components/LoginForm.tsx` のフォーム UI を改善
- `src/styles/form.css` にフォーム用スタイルを追加
- `README.md` のログイン機能セクションを更新

コミットメッセージ候補：

候補1: `improve login form ui and styling`
理由: UI とスタイリングの改善に焦点を当てた表現。

候補2: `enhance login form with new styles`
理由: 改善内容を強調しつつ、新スタイル追加を示唆。

候補3: `update login form and documentation`
理由: フォーム改善とドキュメント更新の両方を含む包括的な表現。

Next steps: ログインフォームの動作確認と、新しいスタイルのブラウザ互換性テストを実施してください。

## 注意事項

- 個人的な設定ファイル（`.gitconfig.local`、`.env.local` など）がステージされている場合は警告する
- 大量の自動生成ファイル（`package-lock.json`、`yarn.lock` など）のみの変更の場合は、その旨を伝える
- binary ファイルの変更がある場合は、その旨を明記する
