---
description: L3 フェーズの形式をインライン1ファイル⇔フォルダ構造（_phase.md + F-xxxx_*.md）の間で相互変換する。同梱スクリプトで決定的に往復変換し、チェック状態・frontmatter・検証記録を保持する。変換方向は対象の現在の形式から自動判定する。
when_to_use: フェーズを機能単位のファイルに分けて管理したい・split して・分割して、または分割したフェーズを1ファイルにまとめ直したい・merge して・統合して、と言われたとき。英語では split / merge the phase。フェーズの内容自体の生成・変更は gen-l3 を使う（reshape は形式変換のみで内容は変えない）。
argument-hint: "<PH-ID | パス> - 変換対象（必須）。現在の形式から自動で逆方向へ変換"
allowed-tools: Read, Write, Glob, Grep, Bash
---

# L3 フェーズ形式変換スキル

<tri_ssd_context>
Tri-SSD: L0(任意メモ docs/l0_ideas/) → L1(要件 docs/l1_requirements/vision.md) → L2(構成 docs/l2_foundation/foundation.md) → L3(フェーズ docs/l3_phases/PH-xxxx.md)。
ID形式: PREFIX-nnnn（REQ, PH, F）。番号は再利用しない（永久欠番）。
配置・分割・粒度の判断に迷ったら `${CLAUDE_SKILL_DIR}/../../docs/layer-rules.md` を読むこと。
</tri_ssd_context>

## 概要

L3 フェーズの2つの形式を相互に変換する（split⇔merge の往復対）:

| 方向 | 変換 | 用途 |
|------|------|------|
| **split** | インライン1ファイル → フォルダ構造 | 慎重に進めたいフェーズを機能単位で管理・機能数が多いフェーズの整理 |
| **merge** | フォルダ構造 → インライン1ファイル | 開発完了後のシンプル化・分割の必要がなくなったフェーズ |

変換方向は対象の現在の形式から自動判定する（ファイル → split、フォルダ → merge）。

## 変換時の原則

<avoid_over_engineering>
- 機能が1〜2個しかないフェーズは分割する必要がない（警告は出さない）
- 変換で内容を書き換えない（形式の変換のみ）
</avoid_over_engineering>

変換の保証: チェック状態（`[x]`）・frontmatter・検証記録などの全セクションを保持し、往復可能（split → merge で元に戻る）。phase-template 準拠の書式なら往復 diff ゼロ。逸脱した書式は機能一覧のみテンプレ書式に正規化され、F の並びはファイル名（F-ID）順に揃う。

## 引数

- `$ARGUMENTS`: 変換対象（必須）
  - PH-ID: `PH-0001`
  - ファイルパス: `docs/l3_phases/PH-xxxx_name.md`（→ split）
  - フォルダパス: `docs/l3_phases/PH-xxxx_name/`（→ merge）

### 使用例

```
/reshape-l3 PH-0001                          # 現在の形式から自動判定して変換
/reshape-l3 docs/l3_phases/PH-0001_mvp.md    # インライン → フォルダ（split）
/reshape-l3 docs/l3_phases/PH-0001_mvp/      # フォルダ → インライン（merge）
```

## 前提処理（方向判定）

1. `$ARGUMENTS` で指定された対象を特定
   - パス指定: 直接参照（ファイルなら split、ディレクトリなら merge）
   - PH-ID 指定: Glob で `docs/l3_phases/` 内を検索（`_archive/` は除外）
     - `docs/l3_phases/$ARGUMENTS*.md`（ファイル）に一致 → **split**
     - `docs/l3_phases/$ARGUMENTS*/`（フォルダ）に一致 → **merge**
     - 両方に一致（通常起きない）→ ユーザーに方向を確認
2. ユーザーが明示的に「split して」「merge して」と言っている場合はその方向を優先し、対象の形式と矛盾したらエラー

---

## 実行

同梱スクリプトで決定的に変換する（チェック状態・frontmatter・全セクションを保持、往復可能）:

```bash
# split（インライン → フォルダ）
python3 "${CLAUDE_SKILL_DIR}/scripts/split.py" PH-0001

# merge（フォルダ → インライン）
python3 "${CLAUDE_SKILL_DIR}/scripts/merge.py" PH-0001
```

`python3` が使えない環境（Windows の python3 は Store スタブの場合がある）では `python` / `py`。スクリプトが使えない場合のみ、下記「フォールバック」に従って手作業で変換する。

## 出力フォーマット

### フォルダ構造（split の出力）

```
docs/l3_phases/PH-xxxx_[phase-name]/
├── _phase.md           # frontmatter + 機能一覧（リスト）以外の全セクション（目的・Exit Criteria・検証記録・完了サマリ等）
├── F-xxxx_feature1.md   # 機能1（対応REQ + 受け入れ条件）
└── F-xxxx_feature2.md   # 機能2
```

`_phase.md` の「機能一覧」は `- F-xxxx: [機能名]` のリストになり、各機能の本文は `F-xxxx_*.md` に移る。
それ以外のセクション（検証記録・完了サマリ含む）は元の順序のまま `_phase.md` に残る。

### インライン形式（merge の出力）

`_phase.md` のセクション順序を保ち、「機能一覧」に各 `F-*.md` の内容を `### F-xxxx:` ブロックとして展開した1ファイル。
F ファイルの `## 受け入れ条件` は `**受け入れ条件**:` に戻る。

## フォールバック（スクリプトが使えない場合）

**split**: ①frontmatter とタイトルを控える ②`### F-xxxx` ブロックを抽出し、各 `F-xxxx_[kebab-case名].md` に
`# F-xxxx: 名前` + 本文（`**受け入れ条件**:` → `## 受け入れ条件`）として書き出す
③残りの全セクションを元の順序で `_phase.md` に書き、機能一覧は `- F-xxxx: 名前` のリストにする ④元ファイルを削除
**merge**: 逆の手順。F ファイルをファイル名順に統合し、`## 受け入れ条件` → `**受け入れ条件**:` に戻す。統合後フォルダを削除

---

## 完了後の案内

- 変換方向（split / merge）と入出力パスを報告
- 機能数・チェック状態（merge 時）を報告
- 次のステップ:
  - split 後: 各機能ファイルを個別に編集可能。`/gen-code F-xxxx` で機能単位のコード生成、`/reshape-l3 PH-xxxx` で元に戻せる
  - merge 後: `/gen-code PH-xxxx` でコード生成、実装完了後は `/archive-l3 PH-xxxx`

---

## エラーケース

| ケース | 対応 |
|--------|------|
| 対象が見つからない | エラー: 「指定されたフェーズが見つかりません」 |
| split 対象にフォルダが既に存在 | エラー: 「同名フォルダが存在します。手動で確認してください」 |
| merge 対象に同名ファイルが存在 | エラー: 「同名ファイルが存在します。手動で確認してください」 |
| 機能セクション（### F-xxxx）がない | エラー: 「機能セクションが見つかりません」 |
| `_phase.md` がない（merge 時） | エラー: 「_phase.md が見つかりません」 |
