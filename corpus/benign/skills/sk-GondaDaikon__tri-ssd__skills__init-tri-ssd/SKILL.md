---
description: Tri-SSD の docs/ ディレクトリ構造（L0-L3）と情報の在り処マップ（docs/README.md）を初期化する。プロジェクトで Tri-SSD 仕様駆動開発を始めるときに最初の1回だけ実行する。同梱スクリプトで冪等に作成し、既存ファイルは上書きしない。
when_to_use: Tri-SSD を始めたい・セットアップして・初期化したい・仕様駆動開発を導入したい・スペック駆動で開発したい・docs のレイヤー構造を作って、と言われたとき。または gen-l1 等の実行時に docs/l1_requirements 等のレイヤーディレクトリがまだ存在しないとき。英語では init Tri-SSD / set up spec-driven docs。既に構造があるプロジェクトで要件を書くのは gen-l1 を使う。
allowed-tools: Read, Write, Bash
---

# Tri-SSD 初期化スキル

<tri_ssd_context>
Tri-SSD: L0(任意メモ docs/l0_ideas/) → L1(要件 docs/l1_requirements/vision.md) → L2(構成 docs/l2_foundation/foundation.md) → L3(フェーズ docs/l3_phases/PH-xxxx.md)。
ID形式: PREFIX-nnnn（REQ, PH, F）。番号は再利用しない（永久欠番）。
配置・分割・粒度の判断に迷ったら `${CLAUDE_SKILL_DIR}/../../docs/layer-rules.md` を読むこと。
</tri_ssd_context>

## 概要

Tri-SSD 用のディレクトリ構造と、情報の在り処マップ（docs/README.md）を初期化する。
プロジェクト開始時に1回のみ実行。

## 初期化時の原則

<avoid_over_engineering>
- 既存ファイルは上書きしない
- l0_ideas/ はワークフロー外（自由なメモ置き場）
- 生成するのはディレクトリと docs/README.md（在り処マップ）のみ。レイヤードキュメントの雛形は作らない
</avoid_over_engineering>

## 引数

- 引数なし

## 作成するもの

```
docs/
├── README.md           # 情報の在り処マップ（何をするときどこを見るか）
├── l0_ideas/           # アイディア・ラフメモ（任意）
│   └── .gitkeep
├── l1_requirements/    # 要件定義
│   └── .gitkeep
├── l2_foundation/      # システム構成
│   └── .gitkeep
└── l3_phases/          # フェーズ（機能+受け入れ条件）
    └── .gitkeep
```

## 実行

同梱スクリプトで決定的に作成する（冪等・既存は上書きしない）:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/init.py"
```

`python3` が使えない環境（Windows の python3 は Store スタブの場合がある）では `python` / `py` で実行する。スクリプトが使えない場合のみ、下記「手順（フォールバック）」に従って手作業で同じ構造を作る。

## 手順（フォールバック）

1. **既存確認**: `docs/` が存在するか確認
2. **ディレクトリ作成**: 存在しない場合のみ作成
3. **docs/README.md 作成**: 存在しない場合のみ、init.py 内の README 定数と同じ内容で作成
4. **完了報告**: 作成したディレクトリ構造を報告

## 完了後の案内

- 作成したディレクトリ・ファイル一覧を報告
- `/gen-l1` で L1 要件を生成できることを案内（対話または既存ドキュメント変換）

---

## エラーケース

| ケース | 対応 |
|--------|------|
| docs/ が既に存在 | 警告: 「docs/ は既に存在します」→ 既存を維持し欠落ディレクトリのみ作成 |
