---
name: deploy
description: MagicSwitchのビルド・リリース・Homebrew tap更新を一連で実行するデプロイスキル。「デプロイ」「deploy」「リリース」「release」などの依頼時に使用。
allowed-tools: Bash, Read, Edit, Glob, Grep
user-invocable: true
argument-hint: "[--major | --minor | --patch]"
---

# MagicSwitch デプロイスキル (`/deploy`)

フルデプロイ（ブランチ統合 + バージョンバンプ + タグ + ビルド + Release + Homebrew tap更新 + アプリ起動）を一連で実行する。

## 引数: $ARGUMENTS

- `--major` → メジャーバージョンをインクリメント (例: 1.2.3 → 2.0.0)
- `--minor` → マイナーバージョンをインクリメント (例: 1.2.3 → 1.3.0)
- `--patch` → パッチバージョンをインクリメント (例: 1.2.3 → 1.2.4) **[デフォルト]**
- 引数なし → `--patch` と同じ

## 実行手順

以下のステップを順に実行せよ。各ステップでエラーが発生した場合は、エラーハンドリング表に従う。

---

### Step 1: 環境検出

1. `git worktree list` を実行し、最初のエントリからメインリポジトリルートを特定する
2. `git branch --show-current` で現在のブランチ名を取得する
3. 現在のブランチ名を `CURRENT_BRANCH`、メインリポジトリルートを `MAIN_REPO` として記録する

### Step 2: 未コミット変更のコミット＆プッシュ

1. `git status --porcelain` で変更を確認する
2. 変更がある場合:
   - `git add -A` でステージング
   - 変更内容を確認し、適切なコミットメッセージを生成してコミット
   - `git push origin $CURRENT_BRANCH` でプッシュ（上流未設定なら `-u` を付与）
3. 変更がない場合:
   - 未プッシュのコミットがあるか `git log origin/$CURRENT_BRANCH..HEAD` で確認
   - あれば `git push origin $CURRENT_BRANCH` でプッシュ

### Step 3: ブランチ統合

**`CURRENT_BRANCH` が `main` の場合:**
- Step 2 でプッシュ済みなので、このステップはスキップ

**`CURRENT_BRANCH` が `main` 以外の場合:**

#### 3a: PR作成

1. `gh pr view --json number,title,url` で既存PRを確認
2. 既存PRがない場合:
   - `git log main..$CURRENT_BRANCH --oneline` でコミット一覧を取得
   - PRタイトルとbodyを生成（コミット内容を要約）
   - `gh pr create --base main --title "..." --body "..."` でPRを作成
3. 既存PRがある場合:
   - そのPRを使用する

#### 3b: PRマージ

**重要:** `gh pr merge --delete-branch` はマージ後にローカルで `git checkout main` を試みるため、ワークツリーから実行すると失敗する。そのため `--delete-branch` は使わず、リモートブランチ削除は別途行う。

1. `gh pr merge --squash` でマージを試みる
2. **成功した場合** → リモートブランチを削除: `git push origin --delete $CURRENT_BRANCH` → 3c へ進む
3. **失敗した場合（conflict）:**
   - `git fetch origin main` を実行
   - `git rebase origin/main` でリベースを試みる
   - conflictが発生したら、conflictを解消してリベースを完了する
   - `git push --force-with-lease` でプッシュ
   - `gh pr merge --squash` を再試行
   - 成功したら `git push origin --delete $CURRENT_BRANCH` でリモートブランチ削除
   - **2回目も失敗した場合は停止し、エラーを報告する**

#### 3c: メインリポジトリ同期＆ローカルブランチ削除

**ワークツリーから実行した場合:**
1. `MAIN_REPO` ディレクトリに移動する
2. `git pull origin main` でmainを最新化する
3. `git worktree remove <現在のワークツリーパス>` でワークツリーを削除する（ローカルブランチも自動削除される）
4. **以降のすべてのステップは `MAIN_REPO` ディレクトリで実行する**

**通常のブランチから実行した場合（ワークツリーでない）:**
1. `git checkout main` でmainに切り替える
2. `git pull origin main` でmainを最新化する
3. `git branch -d $CURRENT_BRANCH` でローカルブランチを削除する
4. **以降のすべてのステップは現在のディレクトリ（= `MAIN_REPO`）で実行する**

### Step 4: バージョンバンプ

#### 4a: 現在バージョン読み取り

- `Resources/Info.plist` を Read ツールで読み取り、`CFBundleShortVersionString` の値を取得する

#### 4b: バージョン計算

- 引数（`$ARGUMENTS`）に応じてインクリメント:
  - `--major` → X+1.0.0
  - `--minor` → X.Y+1.0
  - `--patch`（デフォルト）→ X.Y.Z+1
- 新バージョンを `NEW_VERSION` として記録する

#### 4c: Info.plist 更新

- Edit ツールで `Resources/Info.plist` の以下を更新:
  - `CFBundleVersion` → `NEW_VERSION`
  - `CFBundleShortVersionString` → `NEW_VERSION`

#### 4d: ローカル Cask 更新（version のみ）

- Edit ツールで `homebrew/magic-switch.rb` の `version "..."` 行を `version "NEW_VERSION"` に更新する

#### 4e: コミット＆プッシュ

```bash
git add Resources/Info.plist homebrew/magic-switch.rb
git commit -m "Bump version to $NEW_VERSION"
git push origin main
```

### Step 5: Git タグ

```bash
git tag v$NEW_VERSION
git push origin v$NEW_VERSION
```

- **タグが既に存在する場合は停止し、エラーを報告する**

### Step 6: ビルド＆Release

#### 6a: ビルド

```bash
make bundle
```

- **ビルド失敗時は停止する**

#### 6b: ZIP作成

```bash
cd .build/release && zip -r MagicSwitch-$NEW_VERSION.zip MagicSwitch.app
```

#### 6c: SHA256計算

```bash
shasum -a 256 .build/release/MagicSwitch-$NEW_VERSION.zip
```

- ハッシュ値を `SHA256` として記録する

#### 6d: ローカル Cask 更新（sha256）

- Edit ツールで `homebrew/magic-switch.rb` の `sha256` 行を `sha256 "$SHA256"` に更新する
  - **注意:** `sha256 :no_check` （Ruby symbol）の場合も `sha256 .*` でマッチさせて置換する
- コミット＆プッシュ:

```bash
git add homebrew/magic-switch.rb
git commit -m "Update sha256 for v$NEW_VERSION"
git push origin main
```

#### 6e: リリースノート生成

- `git log` から前バージョンのタグ以降のコミットを取得（バージョンバンプcommit `"Bump version to ..."` と sha256更新commit `"Update sha256 ..."` は除外）
- 以下の形式でリリースノートを生成:

```
## v{NEW_VERSION}
### Changes
- 変更内容の箇条書き（各コミットを要約）
### Install / Update
brew tap byteflare-co/tap && brew install --cask magic-switch
```

#### 6f: GitHub Release 作成

```bash
gh release create v$NEW_VERSION .build/release/MagicSwitch-$NEW_VERSION.zip \
  --title "v$NEW_VERSION" \
  --notes "リリースノート内容"
```

### Step 7: Homebrew tap 更新

GitHub API を使用して `byteflare-co/homebrew-tap` リポジトリの `Casks/magic-switch.rb` を更新する。

```bash
# 1. 現在のファイルSHA取得
FILE_SHA=$(gh api repos/byteflare-co/homebrew-tap/contents/Casks/magic-switch.rb --jq '.sha')

# 2. リモートの内容を取得 → version と sha256 を置換 → base64エンコード
REMOTE_CONTENT=$(gh api repos/byteflare-co/homebrew-tap/contents/Casks/magic-switch.rb --jq '.content' | base64 -d)
UPDATED=$(echo "$REMOTE_CONTENT" | sed -E "s/version \"[^\"]+\"/version \"$NEW_VERSION\"/" | sed -E "s/sha256 .*/sha256 \"$SHA256\"/")
ENCODED=$(echo "$UPDATED" | base64 -b 0)

# 3. PUT で更新
gh api repos/byteflare-co/homebrew-tap/contents/Casks/magic-switch.rb \
  --method PUT \
  --field message="Update magic-switch to v$NEW_VERSION" \
  --field content="$ENCODED" \
  --field sha="$FILE_SHA"
```

- **API失敗時は報告するが続行する**（Releaseは既に公開済みのため）

### Step 8: アプリ起動

```bash
pkill -x MagicSwitch || true
sleep 1
open .build/release/MagicSwitch.app
```

- **起動失敗時は警告のみ出力して続行する**

### Step 9: 完了報告

以下の情報をサマリーとして出力する:

```
═══════════════════════════════════════════
  MagicSwitch Deploy Complete
═══════════════════════════════════════════
  Version:    v{NEW_VERSION}
  Tag:        v{NEW_VERSION}
  Release:    https://github.com/byteflare-co/magic-switch/releases/tag/v{NEW_VERSION}
  Tap:        ✓ updated / ✗ failed
  App:        ✓ launched / ✗ failed
═══════════════════════════════════════════
```

---

## エラーハンドリング

| ステップ | エラー | 対処 |
|----------|--------|------|
| Step 3b | PRマージ失敗（conflict） | rebase → force-with-lease push → リトライ。2回目失敗で**停止** |
| Step 5 | タグ既存 | **停止** |
| Step 6a | ビルド失敗 | **停止** |
| Step 7 | tap API失敗 | 報告するが**続行**（Releaseは公開済み） |
| Step 8 | 起動失敗 | **警告のみ** |
