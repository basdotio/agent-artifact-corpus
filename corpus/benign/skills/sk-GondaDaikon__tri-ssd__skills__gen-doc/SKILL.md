---
description: 書きたい情報を layer-rules の配置判定で正しい置き場に振り分け、ドキュメント作成をオーケストレーションする。L2 のサブ文書（機能契約 features/・教訓 lessons.md・検証実証ログ validation/・用語集 glossary.md）は自ら生成し、画面設計は gen-interface、データ設計は gen-data、要求は gen-l1、実装計画は gen-l3 へ委譲する。
when_to_use: これどこに書けばいい？・ドキュメント化したい・仕様として残したい・機能契約を書きたい・やらないことを明文化したい・教訓/lesson を残したい・検証ログを整理したい・用語集を作りたい・このメモを docs に入れたい、と言われたとき。英語では where should this go / document this。書き先が明確なら各スキル（gen-interface / gen-data / gen-l1 等）を直接使う。
argument-hint: "[書きたい内容] - 自由記述（省略時は対話で聞く）"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# ドキュメント作成スキル（配置オーケストレーター）

<tri_ssd_context>
Tri-SSD: L0(任意メモ docs/l0_ideas/) → L1(要件 docs/l1_requirements/vision.md) → L2(構成 docs/l2_foundation/foundation.md) → L3(フェーズ docs/l3_phases/PH-xxxx.md)。
ID形式: PREFIX-nnnn（REQ, PH, F）。番号は再利用しない（永久欠番）。
配置・分割・粒度の判断に迷ったら `${CLAUDE_SKILL_DIR}/../../docs/layer-rules.md` を読むこと。
</tri_ssd_context>

## 概要

「この情報をどこに書くか」を layer-rules の配置判定フロー（Q0〜Q4）と配置決定表で決定し、置き場に応じてドキュメントを生成・追記する。
next-tri-ssd が**工程**のオーケストレーターであるのに対し、本スキルは**配置**のオーケストレーター。

## 作成時の原則

<avoid_over_engineering>
- 文書を増やすこと自体を目的にしない。迷ったら foundation 内の既存セクションに書く（分離は layer-rules の規模基準に該当したときだけ）
- 機能契約は適用基準（機能10個超 or 逸脱事故が起きうるリソース・常駐系）に該当する場合のみ。小規模では L3 の AC と L2 設計方針で足りる
- lessons は追記のみ（過去の教訓を書き換えない・消さない）
- 同じ事実を2箇所に書かない（結論と詳細を分ける場合は片方をポインタに）
</avoid_over_engineering>

## 引数

- `$ARGUMENTS`（省略可）: 書きたい内容の自由記述。省略時は「何を残したいですか？」から対話で聞く

### 使用例

```
/gen-doc 検索処理はインデックスを開かないという約束を明文化したい
/gen-doc 今回のリリースで学んだこと残したい
/gen-doc
```

## 実行手順

### Step 1: 配置判定

書きたい情報を layer-rules の判定フロー（Q0〜Q4）と配置決定表に照らして振り分ける:

| 情報の種類 | 置き場 | 処理 |
|---|---|---|
| 画面・UI・導線の設計 | `interface.md` | **`/gen-interface` へ委譲** |
| データモデル・ライフサイクル | `data.md` | **`/gen-data` へ委譲** |
| 機能単位の責務・**やらないこと**・性能予算 | `features/<機能名>.md`（機能契約） | 本スキルで生成（Step 2） |
| 要求でも設計でもない学び・廃止判断 | `lessons.md` | 本スキルで追記（Step 3） |
| 事実確認の実証ログ詳細 | `validation/<topic>.md` | 本スキルで生成（Step 4） |
| ドメイン用語の定義 | foundation §7（肥大時 `glossary.md`） | 本スキルで追記 |
| 上記以外の L2 の関心領域 | foundation 内セクション（②④該当ならサブ文書化） | 本スキルで生成 |
| 「〜できること」（要求） | L1 | **`/gen-l1` へ誘導** |
| フェーズの計画・作業 | L3 | **`/gen-l3` へ誘導** |
| どこでもない生メモ | `docs/l0_ideas/` | そのまま置く |

判定に迷ったら layer-rules の「曖昧ケースの裁定」を読み、それでも曖昧ならユーザーに1問で確認する。

### Step 2: 機能契約（features/<機能名>.md）

**`${CLAUDE_SKILL_DIR}/references/doc-templates.md` の「機能契約」を読み**、7セクション（目的・やること・**やらないこと**・性能予算・副作用・依存・既知の判断）で生成する。
適用基準に該当するか先に確認し、該当しなければ foundation の設計方針＋L3 の AC で足りる旨を伝える。
初回作成時は `features/README.md`（一覧）も作り、以後は一覧に1行追加する。

### Step 3: 教訓（lessons.md）

doc-templates.md の「lessons」形式で `docs/l2_foundation/lessons.md` に**追記**する（無ければ作成）。
出所（PH-xxxx / 日付）を必ず添える。L1 の要求変更・L2 の設計変更に昇格すべき内容が混ざっていたら、該当スキルへの反映を併せて提案する。

### Step 4: 検証実証ログ（`validation/<topic>.md`）

doc-templates.md の「validation」形式で生成し、**結論のみ** foundation「確認済みの前提」に1行で書き、詳細は validation/ 側に置く（相互に参照を張る）。

### 共通

- 生成物の文体・構造化・図は `${CLAUDE_SKILL_DIR}/../../docs/writing-rules.md`（記載規約の SSOT）に従う
- 分離ファイルを新設したら foundation.md（または docs/README.md の在り処マップ）に1行の索引ポインタを追加する

## 完了後の案内

- 作成・追記したファイルのパスと配置判定の根拠（layer-rules のどの行に該当したか）を報告
- 委譲した場合: 委譲先スキル（/gen-interface 等）を案内
- 機能契約を作成した場合: gen-code が実装時に読む旨を伝える

---

## エラーケース

| ケース | 対応 |
|--------|------|
| docs/ が存在しない | エラー: 「`/init-tri-ssd` を先に実行してください」 |
| L2（foundation.md）が存在しない | 警告: 「L2 が未作成です。foundation 系の文書は `/gen-l2` の後に作ることを推奨します」（lessons / L0 メモは作成可） |
| 内容が複数の置き場にまたがる | 分割して各置き場へ（例: 要求部分は L1、具体仕様は L2）。分割案を提示して確認 |
