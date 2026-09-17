---
name: delegate-claude
description: Delegate tasks to a separate Claude Code instance in its own git worktree. Use this skill when the user says "delegate", "/delegate-claude", asks to run a task in parallel in another worktree, wants to spawn a child Claude session, or needs to offload implementation work to an independent Claude Code instance. Also trigger when the user wants to start work on a different repository without leaving the current session, or when breaking down a large task into parallel sub-tasks each handled by separate Claude instances.
---

# 別の Claude Code インスタンスにタスクを委任する

`a wm new --prompt` を使って、別の worktree で別の Claude Code インスタンスに処理を委任する。

## 最優先ルール

- **ユーザーが明示的に delegate を指示した場合は、必ず delegate する**: タスクの規模・複雑さ・難易度に関わらず、ユーザーが `/delegate-claude` や「delegate して」と指示した場合は、自分の判断で「delegate 不要」と判断してはならない。ユーザーには delegate する意図がある。理由を推測せず、指示に従うこと
- **delegate 不要と判断して自分で作業を始めることは禁止**: このスキルが発動した時点で、タスクの実行方法は delegate に確定している。「これは簡単だから自分でやろう」「PR 不要だから delegate しなくてよい」といった判断は一切してはならない

## 絶対禁止事項

- **ユーザーが指定したリポジトリを勝手に変更しない**: ユーザーが委任先リポジトリを明示した場合、自分の判断で別のリポジトリに変更してはならない。ユーザーはどのリポジトリで修正すべきかを把握している。「こっちのリポジトリの方が適切では」と思っても、ユーザーの指定に従うこと
- **自分で実装作業をしない**: このスキルが発動したら、ファイル編集・コード変更・調査を自分で行ってはならない。唯一の仕事はプロンプトを構成して `a wm new` コマンドを実行すること
- **委任前にファイルを編集しない**: 「先に少し直してから委任しよう」は禁止。未コミットの変更がある状態で worktree を作ると、委任先にその変更が反映されない
- **SendMessage で委任先に追加指示を送らない**: `/delegate-claude` で起動したインスタンスは独立した tmux セッションの別プロセスであり、SendMessage は届かない。追加指示が必要な場合は worktree を消して委任し直すこと

## 使い方

```bash
a wm new <branch-name> --agent --label "<title>" --prompt "<instructions>"
```

- `branch-name`: 新しい環境用に作成するブランチ名
- `--agent`: **必須**. 委任元 Claude Code セッションからの呼び出しであることを示す。プロンプトを `<delegated-task>` XML でラップし、ブランチ名・base ブランチ・ディレクトリ情報を自動注入する
- `--label`: **必須**. セッションのタイトル。`cc watch` の TUI でセッション一覧に表示され、コンテキストスイッチ時に「このセッションで何をやっていたか」を素早く思い出すためのもの。以下のルールで生成すること:
    - 日本語 2-5 語
    - 具体的な識別子 (PR 番号、ファイル名、機能名、エラー名など) を必ず含める
    - 末尾に句読点を付けない
    - 良い例: "PR #40 CI 修正", "セッション一覧 TUI 実装", "Renovate 設定デバッグ", "ラベル生成プロンプト改善"
    - 悪い例: "バグ修正", "機能実装" (何の? がわからない)
- `--prompt`: 新しい Claude Code インスタンスへの指示

### オプション

- `--from <ref>`: ベースとなる ref を指定 (デフォルト: main ブランチ)
    - 例: `a wm new feature-x --agent --label "..." --from origin/develop --prompt "..."`
    - Renovate の PR をテストする場合: `a wm new test-upgrade --agent --label "..." --from origin/renovate/some-branch --prompt "..."`
- `-R <path>` / `--repo <path>`: 対象リポジトリのパスを指定。指定するとカレントディレクトリに関係なく、そのリポジトリ上で worktree を作成する
    - 例: `a wm new fix-api-timeout -R ~/ghq/github.com/fohte/other-repo --agent --label "..." --prompt "..."`

### 例

```bash
# 現在のリポジトリ
a wm new feature-login --agent --label "メール認証ログイン実装" --prompt "メール/パスワード認証によるログイン機能を実装"

# 別のリポジトリ (-R オプション)
a wm new fix-api-timeout -R ~/ghq/github.com/fohte/other-repo --agent --label "API タイムアウト修正" --prompt "API のタイムアウト設定を修正"
```

実行すると:

1. 指定したブランチで新しい git worktree を作成
2. Neovim と Claude Code を含む新しい tmux ウィンドウを開く
3. Claude Code にプロンプトを自動送信

## 委任時の注意事項

- **既存ブランチで作業する場合**: 既存のリモートブランチ (例: follow-up PR のブランチ) にそのまま commit したい場合は、ブランチ名をそのまま `<branch-name>` に指定する
    - 例: `a wm new follow-up-123-terraform/foo --agent --label "..." --prompt "..."`
- **ブランチ名**: 新規ブランチを作る場合、ブランチ名に `/` を含めないこと。代わりにハイフンを使う (例: `fix/login-bug` ではなく `fix-login-bug`)。ブランチには `fohte/` がプレフィックスとして付くため、`fix/...` だと `fohte/fix/...` になり冗長
- 新しいインスタンスは独立した worktree で作業するため、現在の作業と競合しない

### `--from` の判断ルール (重要)

**`--from` はデフォルトで使わない。** 以下の判断フローに従うこと:

1. 委任するタスクは、現在のブランチの変更がないと作業できないか?
    - **いいえ** → `--from` を指定しない (main ブランチベース)
    - **はい** → `--from <現在のブランチ>` を指定する

**`--from` を使ってよいケース** (現在のブランチの変更が前提として必要):

- 現在の PR に対する follow-up 修正
- 現在のブランチで追加したファイル/設定を前提とする追加作業

**`--from` を使ってはいけないケース** (独立した変更):

- CI の汎用的な修正 (trivy の無効化、linter 設定の変更など)
- 別の機能の追加・修正
- リポジトリ全体に影響する設定変更
- main にも存在するファイル (ドキュメント、設定ファイルなど) の修正で、修正内容が現在のブランチの新規コードに依存しない場合
- 自動生成された PR (依存関係更新など) で問題が発見されたが、修正内容自体が main 上でも適用できる場合

**よくある誤判断**:

- 「現在のブランチで同じファイルを編集した」という理由だけで `--from` が必要だと判断してはいけない。判断基準は「そのファイルを編集したかどうか」ではなく、「委任先が main ブランチ上で同じ修正を適用できるかどうか」。main にあるファイルに対する独立した修正であれば、たとえ現在のブランチでも同じファイルを触っていても `--from` は不要
- 「ある PR で問題が見つかった」という理由だけで `--from` にその PR のブランチを指定してはいけない。PR は問題の発見契機にすぎない。修正がその PR の変更内容に依存しない限り main ベースで行う

間違えて `--from` で現在のブランチを指定すると、関係のない変更が混入して別々の PR にできなくなる。

## プロンプト構造 (必須)

委任先の Claude Code インスタンスは**現在の会話の事前知識を持っていない**。以下の構造を使って十分なコンテキストを含めること。

**最重要: 「背景」セクションに最も力を入れて書く。** 委任先が自律的に適切な判断を下せるかどうかは、背景の質で決まる。

```
## 背景

### 目的・モチベーション
[なぜこのタスクが必要か。何を実現したいか。ユーザーにとってどんな価値があるか]

### 問題の詳細 (バグ修正の場合)
[症状、再現手順、期待される動作と実際の動作の差分]

### 調査済みの内容
[すでに分かっていること。調査結果とその根拠 (ログ、コード箇所、ドキュメントなど)]

### 参考リンク
[関連する Issue / PR / ドキュメントの URL。親 Issue や親 PR がある場合は必ず含める]

## 現状
[現在のコードの状態。関連ファイルやアーキテクチャ。すでに決まっている設計判断]

## ゴール
[最終的に何が達成されていればよいか。成功条件]

`/commit` skill で commit し、`/create-pr` skill で PR を作成するところまで完了させること。
```

### 書き方のルール

- **背景を最も厚く書く**: プロンプト全体の半分以上を背景に充てる。委任先が「なぜこの作業をするのか」を深く理解できるようにする
- **ゴールだけ伝え、手順は指示しない**: 「何を達成してほしいか」を書き、「どうやるか」は委任先に任せる。具体的な実装ステップや中間手順を指示しない
- **テンプレートの完了条件を勝手に変えない**: ゴールセクション末尾の「`/commit` skill で commit し、`/create-pr` skill で PR を作成するところまで完了させること。」は固定テンプレートであり、省略・変更してはならない。「commit 不要」「PR 不要」「commit だけでよい」などの独自判断を加えることは禁止。ユーザーが明示的に指示した場合のみ変更してよい
- **commit/PR 作成の指示は必ず含める**: ゴールセクションの末尾にテンプレートの一文 (「`/commit` skill で commit し、`/create-pr` skill で PR を作成するところまで完了させること。」) を必ず含めること。これは「手順の指示」ではなく「完了条件の定義」であり省略してはならない
- **根拠を含める**: 調査結果や判断には、その根拠 (ログ、コード箇所、エラーメッセージ、ドキュメント URL など) を添える
- **リンクを貼る**: Issue / PR / ドキュメントなど、参考にしたものは URL を貼る。特に親 Issue や関連 PR は必須
- **パスは実在を確認する**: プロンプトにファイルパスやディレクトリパスを含める場合、そのパスが委任先から実際にアクセスできることを事前に確認する。特に worktree 内で作業している場合、本体リポジトリのパスと worktree のパスは異なるため注意する。テンプレートやスキルの指示にあるパスをそのまま使わず、実際の cwd やファイルの所在を確認すること

### 良い例

```bash
a wm new fix-auth-timeout --agent --label "セッション TTL 設定反映修正" --prompt "## 背景

### 目的・モチベーション
セッションタイムアウトが短すぎてユーザーが頻繁に再ログインを強いられている。本来 30 分のはずが 5 分で切れる。

### 問題の詳細
- 症状: ログイン後、5 分間操作しないとセッションが切れて再ログインが必要になる
- 期待される動作: 30 分間操作がなくてもセッションが維持される
- 再現: ログイン後 5 分待つと 401 が返る

### 調査済みの内容
- src/auth/session.ts の SessionManager クラスで TTL を設定しているが、config/auth.json の timeout 値 (1800秒) が反映されていない
- Redis の TTL を確認したところ実際に 300 秒で設定されている (根拠: redis-cli TTL session:xxx の結果)
- 最近の JWT からセッション認証への移行 (PR #142) でデフォルト値のフォールバックが追加され、config の値を上書きしている可能性が高い

### 参考リンク
- Issue: https://github.com/example/repo/issues/210
- 関連 PR (認証移行): https://github.com/example/repo/pull/142

## 現状
- 認証は src/auth/session.ts の SessionManager クラスで処理
- セッション設定は config/auth.json に定義
- Redis をセッションストレージとして使用

## ゴール
セッションタイムアウトが config/auth.json の設定値 (30 分) どおりに動作する。"
```

### 悪い例

```bash
# NG: コンテキスト不足 - 新しいインスタンスは「そのバグ」が何か分からない
a wm new fix-bug --agent --label "バグ修正" --prompt "さっき話したバグを直して"

# NG: 手順を指示しすぎ - 委任先の自律性を奪う
a wm new fix-auth --agent --label "session.ts TTL 修正" --prompt "## タスク
1. src/auth/session.ts を開く
2. 42 行目の TTL を 300 から 1800 に変更
3. テストを追加
4. commit はしないこと"
```
