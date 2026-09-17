---
name: pr-scope-guard
description: PRの範囲を制御し、1PRが「意味のある最小単位」から逸脱しないようにするスキル。PR作成前のスコープ宣言、実装中の範囲確認に使用。
---

# Skill: PR Scope Guard (REQ内サブタスク分割・1PR完結ルール)

## Purpose

このスキルは、REQをサブタスクに分割し、1つのPRが「意味のある最小単位」から逸脱しないように実装範囲を制御する。

**狙い:**
- 「REQは1つでも、PRは分ける」を強制
- "ついで実装" を禁止
- 変更範囲が膨らんだら **止まって提案に切り替える** ルールを入れる

## Inputs

| 項目 | 例 |
|------|-----|
| target_req_id | REQ-0000002 |
| target_pr_id | PR-1 |
| pr_goal | Phase2-A 最小 auto-suggest を導入する |
| allowed_tasks | ["T-2A-01", "T-2A-02"] |
| forbidden_tasks | ["T-2A-03", "T-2B-01", "T-UX-01", "T-OPS-01"] |
| done_definition | PRが完了したと判断する条件（チェックリスト） |

## Hard Rules (Must)

1. **実装対象は allowed_tasks のみに限定する。**
2. **forbidden_tasks に該当する変更は一切行わない**（関連ファイルの追加・修正含む）。
3. **"ついでに"改善は禁止**（リファクタ/命名統一/設定外出し/UI導線追加）。
4. **範囲外の必要性を感じた場合は「実装せず」提案として TODO に残し、PR外に切り出す。**
5. **既存挙動を変える可能性がある変更は、PR内に含めない**（含めるなら提案に切り替える）。

## Soft Rules (Should)

- 変更箇所は最小限にし、差分を読みやすくする。
- PR説明文に「含めたもの/含めないもの」を明記する。
- テストは PRの機能境界に一致する範囲だけ追加する。

## Output Format (Always)

```markdown
### Scope Declaration

- **target_req_id**:
- **target_pr_id**:
- **pr_goal**:
- **included (allowed_tasks)**:
- **excluded (forbidden_tasks)**:

### Implementation Plan (bullet)

- 手順を5〜10項目で提示（PRの範囲内のみ）

### DoD Checklist

- [ ] allowed_tasks のみ変更した
- [ ] forbidden_tasks に触れていない
- [ ] 既存挙動を変更していない（対象PRに含まれていない限り）
- [ ] PRの説明文に「含めない」を書いた
- [ ] 最小テストが通る
```

## Stop Conditions (Switch to proposal)

以下が **1つでも発生したら**、実装を止めて「次PR提案」を出す：

| 条件 | アクション |
|------|-----------|
| forbidden_tasks に触れそう | 実装停止 → 次PR提案 |
| 仕様追加が必要（判断できない） | 実装停止 → 確認待ち |
| 既存挙動の変更が避けられない | 実装停止 → 影響範囲提示 |

## 運用ルール

1. **PR開始前**に必ず Scope Declaration を出力する
2. **実装中**に範囲外に触れそうになったら Stop Conditions を確認
3. **PR完了時**に DoD Checklist をすべてチェック

## 適用例

```markdown
### Scope Declaration

- **target_req_id**: REQ-0000002
- **target_pr_id**: PR-1
- **pr_goal**: Phase 1 ルールベース auto-suggest を導入
- **included**: suggest_categories()実装, Close Dialog統合, テスト追加
- **excluded**: 設定外出し, git diff連携, confidence表示

### Implementation Plan

1. SuggestRule 構造体を追加
2. suggest_categories() 関数を実装
3. start_worklog_close() で呼び出し
4. テスト追加
5. 動作確認

### DoD Checklist

- [x] allowed_tasks のみ変更した
- [x] forbidden_tasks に触れていない
- [x] 既存挙動を変更していない
- [x] PRの説明文に「含めない」を書いた
- [x] 最小テストが通る
```
