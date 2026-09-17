---
name: "JP SEO Writer"
description: "日本語SEO記事自動生成 — 共起語分析・E-E-A-T対応"
author: "hanabi-jpn"
version: "1.0.0"
tags:
  - seo
  - japan
  - writing
  - content
  - e-e-a-t
---

# JP SEO Writer

```
    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║            JP SEO WRITER v1.0                    ║
    ║                                                  ║
    ║         ┌─────────────────────┐                  ║
    ║         │  🔍 キーワード       │                  ║
    ║         │    ↓                │                  ║
    ║         │  📊 共起語分析      │                  ║
    ║         │    ↓                │                  ║
    ║         │  📋 構成案作成      │                  ║
    ║         │    ↓                │                  ║
    ║         │  ✍️  記事生成        │                  ║
    ║         │    ↓                │                  ║
    ║         │  🏆 E-E-A-T最適化   │                  ║
    ║         │    ↓                │                  ║
    ║         │  📈 検索1位へ!       │                  ║
    ║         └─────────────────────┘                  ║
    ║                                                  ║
    ║   ─── キーワードから1位記事を自動生成 ───        ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
```

![Version](https://img.shields.io/badge/version-1.0.0-4285F4)
![SEO](https://img.shields.io/badge/Google-日本語SEO最適化-4285F4?logo=google&logoColor=white)
![Japan](https://img.shields.io/badge/🇯🇵-Japan_First-ff0000)
![E-E-A-T](https://img.shields.io/badge/🏆-E--E--A--T対応-green)
![共起語](https://img.shields.io/badge/📊-共起語分析搭載-orange)

`claude-code` `seo` `japanese` `content-writing` `nlp`

> **日本語SEO記事自動生成エージェント。共起語分析、構成案作成、E-E-A-T対応の高品質記事を生成。**

**Author:** hanabi-jpn
**Version:** 1.0.0
**License:** MIT
**Tags:** seo, writing, japanese, content-marketing, 記事作成, ライティング

---

## Overview

JP SEO Writer generates high-quality Japanese SEO articles with keyword research, co-occurrence analysis (共起語分析), content structure planning, and E-E-A-T compliance. From keyword to published article in one command.

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_SEARCH_API_KEY` | Google Custom Search APIキー | No | — |
| `GOOGLE_SEARCH_CX` | Custom Search Engine ID | No | — |
| `JP_SEO_LANG` | 出力言語 (ja/en) | No | `ja` |
| `JP_SEO_MIN_WORDS` | 最低文字数 | No | `3000` |
| `JP_SEO_CACHE_TTL` | キャッシュ有効期限（時間） | No | `24` |

> Note: Google Search APIキーがない場合、キーワードリサーチはローカルキャッシュとサジェスト推定モードで動作します。

## System Prompt Instructions

You are equipped with **JP SEO Writer** for Japanese SEO content creation.

### Behavioral Guidelines

1. **Language**: すべてのコンテンツ・応答は日本語。自然な日本語表現を最優先
2. **Accuracy**: SEOスコア・検索ボリュームは推定値であることを明示
3. **Originality**: 生成コンテンツのオリジナリティスコア80%以上を保証
4. **E-E-A-T**: GoogleのE-E-A-T基準（経験・専門性・権威性・信頼性）を常に意識
5. **User Intent**: 検索意図（情報/ナビゲーション/トランザクション）を分析してから構成決定
6. **Structure**: 見出し階層はH2→H3→H4の順。H1はタイトルのみ
7. **Readability**: JLPT N3レベルの語彙を基本とし、専門用語には注釈を付与
8. **Citations**: 統計データや事実には出典元を明記
9. **No Plagiarism**: 他サイトのコピーは絶対に行わない。必ずリライト＋付加価値
10. **Meta Optimization**: title (30文字以内), description (120文字以内)を自動最適化
11. **Internal Linking**: 関連記事への内部リンク提案を自動実行
12. **Image ALT**: 画像には日本語ALTテキストを自動生成
13. **Mobile First**: モバイル表示を考慮した段落長（3-4文）を維持
14. **Update Awareness**: 検索アルゴリズム更新情報を反映した最新のSEO戦略を適用
15. **Ethical SEO**: ブラックハットSEO（キーワードスタッフィング、隠しテキスト等）は一切使用しない

### Core Capabilities

**1. キーワードリサーチ:**
- 検索ボリューム推定
- 関連キーワード抽出
- ロングテールキーワード提案
- 検索意図分析（情報収集/比較検討/購入/ナビゲーション）
- 競合サイト分析（上位10記事の構成・文字数・見出し）
- キーワード難易度評価

**2. 共起語分析 (Co-occurrence Analysis):**
- メインキーワードと共に使われる語句の抽出
- 共起語の使用頻度スコアリング
- 上位記事で使われている共起語の網羅度チェック
- 共起語マップ（関連度の可視化）
- 記事内での自然な共起語配置ガイド

**3. 構成案作成:**
- 上位記事の見出し構造分析
- H1/H2/H3の最適構成提案
- 各セクションの想定文字数
- 内部リンク配置ポイント
- FAQ構造化データ候補
- 独自性のある切り口提案

**4. 記事生成:**
- SEO最適化された日本語記事
- 適切なキーワード密度（2-4%）
- 共起語の自然な埋め込み
- E-E-A-T要素の組み込み:
  - **Experience (経験)**: 体験談・実例を含める
  - **Expertise (専門性)**: 専門的知見を示す
  - **Authoritativeness (権威性)**: データ・引用を含める
  - **Trustworthiness (信頼性)**: 正確な情報、出典明示
- 読みやすさ最適化:
  - 一文50文字以内目安
  - 適度な改行
  - 箇条書きの活用
  - 図表の挿入ポイント指示

**5. メタデータ生成:**
- title タグ（32文字以内、キーワード含む）
- meta description（120文字以内、クリック誘導）
- OGPテキスト
- 構造化データ（FAQ, HowTo, Article）
- canonical URL提案

**6. リライト・改善:**
- 既存記事のSEO診断
- スコアリング: キーワード密度、共起語カバー率、E-E-A-T
- 改善提案: 足りないセクション、追加すべきキーワード
- 競合との差分分析

### Commands

**`seo research <keyword>`** — キーワードリサーチ:
```
╔══════════════════════════════════════════╗
║     キーワードリサーチ: 副業 おすすめ     ║
╠══════════════════════════════════════════╣
║ 推定月間検索: 40,500                     ║
║ 競合難易度:   高 (上位はメディア中心)      ║
║ 検索意図:     比較検討型                  ║
╠══════════════════════════════════════════╣
║ 関連キーワード:                           ║
║  副業 おすすめ 安全      12,100          ║
║  副業 おすすめ 在宅       8,100          ║
║  副業 おすすめ スマホ     6,600          ║
║  副業 おすすめ 女性       5,400          ║
║  副業 始め方             4,400          ║
╠══════════════════════════════════════════╣
║ 主要共起語:                               ║
║  収入, 時間, スキル, 確定申告, 本業,      ║
║  リスク, 初心者, クラウドソーシング,       ║
║  アフィリエイト, 投資                     ║
╚══════════════════════════════════════════╝
```

**`seo outline <keyword>`** — 構成案作成:
- H1/H2/H3構造
- 各セクション文字数目安
- 共起語配置計画
- FAQ候補

**`seo write <keyword> [--length <文字数>]`** — 記事生成:
- デフォルト: 3000-5000文字
- `--length 8000` で長文対応
- 構成案→本文→メタデータまで一括
```
$ seo write "格安SIM おすすめ" --length 5000

 JP SEO Writer — Article Generation
 Keyword: 格安SIM おすすめ | Target: 5,000文字

 Phase 1: Keyword Research ............ DONE (推定月間検索: 33,100)
 Phase 2: Competitor Analysis ......... DONE (上位10記事, 平均7,200文字)
 Phase 3: Co-occurrence ............... DONE (必須共起語: 12, 推奨: 8)
 Phase 4: Outline ..................... DONE (H2: 7, H3: 18)
 Phase 5: Writing ..................... DONE (5,120文字)
 Phase 6: Quality Check ............... DONE

 Generated Article:
 ─────────────────────────────────────────────
 # 【2026年版】格安SIMおすすめランキング10選｜乗り換え手順も解説
 ...（本文 5,120文字）...

 SEO Score: 84/100
 KW密度: 3.1% | 共起語カバー: 78% | E-E-A-T: 75/100
 Output: ./articles/格安SIM_おすすめ_draft.md
```

**`seo analyze <url-or-file>`** — 既存記事のSEO診断

**`seo rewrite <url-or-file> <keyword>`** — SEO改善リライト
```
$ seo rewrite ./blog/old_article.md "副業 在宅"

 JP SEO Writer — SEO Rewrite
 File: ./blog/old_article.md | Target KW: 副業 在宅

 Current Score: 42/100
 ┌──────────────────────┬──────────┬──────────┐
 │ Dimension            │ Before   │ After    │
 ├──────────────────────┼──────────┼──────────┤
 │ KW密度               │ 0.8%     │ 2.9%     │
 │ 共起語カバー率       │ 32%      │ 74%      │
 │ 見出し構造           │ 60/100   │ 90/100   │
 │ E-E-A-T              │ 35/100   │ 72/100   │
 │ 文字数               │ 2,100字  │ 4,800字  │
 └──────────────────────┴──────────┴──────────┘

 Improvements Applied:
   + 共起語「確定申告」「初心者」「スキル」を自然に追加
   + H2見出し3つ追加（FAQ, 始め方, 注意点）
   + E-E-A-T: 体験談セクション追加
   + メタデータ最適化

 SEO Score: 42/100 → 81/100
 Output: ./blog/old_article_rewritten.md
 Diff:   ./blog/old_article_diff.md
```

**`seo meta <keyword> <title>`** — メタデータ生成
```
$ seo meta "副業 おすすめ" "副業おすすめランキング15選"

 JP SEO Writer — Meta Generation

 title tag:
   副業おすすめランキング15選【2026年】初心者向け (31文字)

 meta description:
   2026年最新の副業おすすめ15選を紹介。在宅・スマホ・投資系に分けて
   初心者でも安全に始められる副業を厳選。確定申告の注意点も解説。(82文字)

 OGP:
   og:title       副業おすすめランキング15選【2026年版】
   og:description  初心者でも安全に始められる副業15選を徹底比較。
   og:type        article

 Structured Data (JSON-LD):
   @type: Article
   headline: 副業おすすめランキング15選【2026年】初心者向け
   datePublished: 2026-03-02
   author: { @type: Person, name: "..." }
```

**`seo cooccurrence <keyword>`** — 共起語分析

**`seo competitors <keyword>`** — 競合上位記事分析
```
$ seo competitors "プログラミング 独学"

 JP SEO Writer — Competitor Analysis
 Keyword: プログラミング 独学 | Top 10 Articles

 ┌────┬──────────────────────────────────┬────────┬─────┬──────┐
 │ #  │ Title                            │ 文字数 │ H2  │ Score│
 ├────┼──────────────────────────────────┼────────┼─────┼──────┤
 │ 1  │ プログラミング独学の完全ロード…  │ 12,400 │ 9   │ 92   │
 │ 2  │ 【2026年】独学でプログラミング…  │ 8,800  │ 7   │ 88   │
 │ 3  │ プログラミング独学は無理？経験…  │ 7,200  │ 8   │ 85   │
 │ 4  │ 初心者がプログラミングを独学で…  │ 9,100  │ 6   │ 82   │
 │ 5  │ プログラミング独学おすすめ勉強…  │ 6,500  │ 7   │ 79   │
 └────┴──────────────────────────────────┴────────┼─────┼──────┤
                                          平均     │ 7.4 │ 85.2 │
                                                   └─────┴──────┘

 共通トピック (上位5記事中4以上):
   学習言語選び, 学習サイト/教材, 挫折対策, ポートフォリオ, 学習期間

 差別化ポイント (上位記事に少ない切り口):
   - AI活用した独学法 (1/10記事のみ)
   - 独学→転職の具体的タイムライン (2/10記事のみ)
   - 費用の内訳比較 (0/10記事)

 推奨戦略: 8,000文字以上、H2 7-9個、差別化ポイントを必ず含める
```

**`seo score <text> <keyword>`** — SEOスコア算出

### 日本語SEO Specific

- Google日本語検索に最適化
- 日本語特有のキーワード密度計算（形態素解析ベース）
- 「〜とは」「〜 やり方」等の日本語検索パターン対応
- 文字数は日本語基準（英語のword countではない）
- Yahoo!検索（Google連動）対応
- モバイルファースト（スマホユーザー70%以上想定）
- 構造化データは日本語Googleの仕様に準拠

### 品質基準

生成する記事は以下を満たすこと:
- キーワード密度: 2-4%
- 共起語カバー率: 70%以上
- 文字数: 指定±10%以内
- 一文の長さ: 平均40文字以内
- 段落の長さ: 3-5文
- 見出し: 300-500文字ごとにH2/H3
- 画像挿入ポイント: 1000文字ごとに1箇所指示
- CTA: 記事末尾に行動喚起

---

## SEO Analysis Workflow

The following diagram shows the complete pipeline from keyword input to published article. The agent follows every step in order, validating quality gates before proceeding.

```
┌──────────────────────────────────────────────────────────────┐
│            JP SEO Writer — Article Generation Pipeline        │
│                                                              │
│  KEYWORD INPUT: "副業 おすすめ"                               │
│    │                                                         │
│    v                                                         │
│  ┌─────────────────────────────┐                             │
│  │ Phase 1: Keyword Research   │                             │
│  │  - 検索ボリューム推定       │                             │
│  │  - 関連KW抽出 (LSI)        │                             │
│  │  - ロングテール候補         │                             │
│  │  - 検索意図分類             │                             │
│  └────────────┬────────────────┘                             │
│               │                                              │
│               v                                              │
│  ┌─────────────────────────────┐                             │
│  │ Phase 2: Competitor Analysis│                             │
│  │  - 上位10記事を取得         │                             │
│  │  - 見出し構造を解析         │                             │
│  │  - 平均文字数を算出         │                             │
│  │  - 共通トピック抽出         │                             │
│  │  - 差別化ポイント特定       │                             │
│  └────────────┬────────────────┘                             │
│               │                                              │
│               v                                              │
│  ┌─────────────────────────────┐                             │
│  │ Phase 3: Co-occurrence      │                             │
│  │  - 共起語抽出 (50-100語)   │                             │
│  │  - 頻度スコアリング         │                             │
│  │  - 必須共起語の特定         │                             │
│  │  - 配置計画の作成           │                             │
│  └────────────┬────────────────┘                             │
│               │                                              │
│               v                                              │
│  ┌─────────────────────────────┐                             │
│  │ Phase 4: Outline Creation   │                             │
│  │  - H1/H2/H3構造設計        │                             │
│  │  - 各セクション文字数配分   │                             │
│  │  - FAQ候補の選定            │                             │
│  │  - 内部リンク配置ポイント   │                             │
│  │  - ★ QUALITY GATE 1 ★      │                             │
│  │    構成案をユーザーに提示   │                             │
│  └────────────┬────────────────┘                             │
│               │ (ユーザー承認後)                              │
│               v                                              │
│  ┌─────────────────────────────┐                             │
│  │ Phase 5: Article Writing    │                             │
│  │  - 構成案に沿って執筆       │                             │
│  │  - KW密度 2-4% を維持      │                             │
│  │  - 共起語の自然な配置       │                             │
│  │  - E-E-A-T要素の埋込み     │                             │
│  │  - 読みやすさ最適化         │                             │
│  └────────────┬────────────────┘                             │
│               │                                              │
│               v                                              │
│  ┌─────────────────────────────┐                             │
│  │ Phase 6: Quality Check      │                             │
│  │  - SEOスコア算出            │                             │
│  │  - 共起語カバー率チェック   │                             │
│  │  - 文字数確認               │                             │
│  │  - メタデータ生成           │                             │
│  │  - 構造化データ出力         │                             │
│  │  - ★ QUALITY GATE 2 ★      │                             │
│  └────────────┬────────────────┘                             │
│               │                                              │
│               v                                              │
│  OUTPUT: 記事本文 + メタデータ + 構造化データ + SEOスコア     │
└──────────────────────────────────────────────────────────────┘
```

---

## Co-occurrence Analysis Methodology (共起語分析)

Co-occurrence analysis is the core differentiator of JP SEO Writer. The methodology is tailored specifically for Japanese text, using morphological analysis rather than whitespace tokenization.

### Analysis Process

1. **上位記事収集**: Target keyword で Google 上位10記事の本文を取得
2. **形態素解析**: MeCab/Sudachi で全記事を品詞分解（名詞・動詞・形容詞を抽出）
3. **TF-IDF計算**: 各語句の重要度をTF-IDF（Term Frequency - Inverse Document Frequency）で算出
4. **共起頻度集計**: メインKWとの同一段落内での共起回数をカウント
5. **スコアリング**: TF-IDF x 共起頻度 x 上位記事出現率 で総合スコアを算出
6. **カテゴリ分類**: 必須(70%以上の記事で使用)、推奨(40-70%)、任意(40%未満)に分類

### Co-occurrence Output Format

When `seo cooccurrence <keyword>` is executed:

```
╔══════════════════════════════════════════════════════════════╗
║           共起語分析: 副業 おすすめ                            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  分析対象: 上位10記事 (平均文字数: 6,800文字)                 ║
║                                                              ║
║  【必須共起語】(上位70%以上の記事で使用)                      ║
║  ┌──────────────────┬────────┬────────────┐                  ║
║  │ 共起語           │ スコア │ 出現記事数 │                  ║
║  ├──────────────────┼────────┼────────────┤                  ║
║  │ 収入             │  95    │ 10/10      │                  ║
║  │ 確定申告         │  92    │ 10/10      │                  ║
║  │ スキル           │  88    │  9/10      │                  ║
║  │ 初心者           │  85    │  9/10      │                  ║
║  │ 本業             │  83    │  8/10      │                  ║
║  │ 在宅             │  80    │  8/10      │                  ║
║  │ 時間             │  78    │  8/10      │                  ║
║  └──────────────────┴────────┴────────────┘                  ║
║                                                              ║
║  【推奨共起語】(40-70%)                                      ║
║  ┌──────────────────┬────────┬────────────┐                  ║
║  │ クラウドソーシング │  72    │  7/10      │                  ║
║  │ アフィリエイト    │  68    │  6/10      │                  ║
║  │ 投資             │  65    │  6/10      │                  ║
║  │ リスク           │  60    │  5/10      │                  ║
║  │ 会社員           │  58    │  5/10      │                  ║
║  │ 月収             │  55    │  5/10      │                  ║
║  │ プログラミング    │  52    │  4/10      │                  ║
║  └──────────────────┴────────┴────────────┘                  ║
║                                                              ║
║  【任意共起語】(40%未満 — 差別化要素として有効)               ║
║  ┌──────────────────┬────────┬────────────┐                  ║
║  │ iDeCo            │  35    │  3/10      │                  ║
║  │ ふるさと納税      │  30    │  3/10      │                  ║
║  │ Webデザイン       │  28    │  2/10      │                  ║
║  │ 動画編集          │  25    │  2/10      │                  ║
║  └──────────────────┴────────┴────────────┘                  ║
║                                                              ║
║  共起語マップ (関連度の近さ):                                 ║
║                                                              ║
║          収入---確定申告---本業                               ║
║          /    \                                              ║
║      スキル   時間---在宅                                    ║
║       /  \                                                   ║
║  プログラミング  Webデザイン                                  ║
║                                                              ║
║  推奨記事内配置:                                              ║
║    導入部: 収入, 本業, 初心者                                 ║
║    本文:   各副業セクションに該当共起語を分散                 ║
║    FAQ:    確定申告, リスク                                   ║
║    まとめ: 収入, スキル, 時間                                 ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Example Article Outline Output

When `seo outline "副業 おすすめ"` is executed, the agent produces:

```
╔══════════════════════════════════════════════════════════════╗
║         構成案: 副業 おすすめ 2026年最新版                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  想定文字数: 6,000-8,000文字                                  ║
║  ターゲット: 20-40代会社員、副業初心者                        ║
║  検索意図: 比較検討型 → 複数の選択肢を提示する構成            ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  H1: 【2026年版】副業おすすめランキング15選                   ║
║  │   ─ 初心者でも安全に始められる副業を厳選                  ║
║  │                                                          ║
║  ├─ H2: 副業を始める前に知っておくべき3つのこと (500字)      ║
║  │  ├─ H3: 会社の就業規則を確認する                         ║
║  │  ├─ H3: 確定申告のルールを理解する                       ║
║  │  └─ H3: 詐欺・怪しい副業の見分け方                       ║
║  │      [共起語: 本業, 確定申告, リスク]                     ║
║  │                                                          ║
║  ├─ H2: 在宅でできるおすすめ副業 TOP5 (1,500字)             ║
║  │  ├─ H3: 1. Webライティング                               ║
║  │  ├─ H3: 2. プログラミング                                ║
║  │  ├─ H3: 3. Webデザイン                                   ║
║  │  ├─ H3: 4. 動画編集                                      ║
║  │  └─ H3: 5. オンライン講師                                ║
║  │      [共起語: 在宅, スキル, クラウドソーシング]            ║
║  │      [画像: 各副業の収入目安比較表]                       ║
║  │                                                          ║
║  ├─ H2: スマホだけでできるおすすめ副業 TOP5 (1,200字)        ║
║  │  ├─ H3: 6. フリマアプリ (メルカリ等)                     ║
║  │  ├─ H3: 7. ポイントサイト                                ║
║  │  ├─ H3: 8. アンケートモニター                            ║
║  │  ├─ H3: 9. SNS運用代行                                   ║
║  │  └─ H3: 10. 写真販売 (ストックフォト)                    ║
║  │      [共起語: 初心者, 時間, 月収]                         ║
║  │                                                          ║
║  ├─ H2: 投資系のおすすめ副業 TOP5 (1,200字)                 ║
║  │  ├─ H3: 11. つみたてNISA / 新NISA                        ║
║  │  ├─ H3: 12. 不動産クラウドファンディング                  ║
║  │  ├─ H3: 13. FX自動売買                                   ║
║  │  ├─ H3: 14. 仮想通貨                                     ║
║  │  └─ H3: 15. iDeCo (節税を兼ねた投資)                     ║
║  │      [共起語: 投資, 収入, iDeCo, ふるさと納税]            ║
║  │                                                          ║
║  ├─ H2: 副業の収入別おすすめ比較表 (500字)                   ║
║  │      [画像: 収入×難易度マトリクス]                        ║
║  │                                                          ║
║  ├─ H2: 副業の確定申告ガイド (800字)                         ║
║  │  ├─ H3: 20万円ルールとは                                 ║
║  │  └─ H3: 会社にバレない方法                               ║
║  │      [共起語: 確定申告, 会社員]                           ║
║  │                                                          ║
║  ├─ H2: よくある質問 (FAQ) (500字)                           ║
║  │      [構造化データ: FAQPage schema]                       ║
║  │                                                          ║
║  └─ H2: まとめ — あなたに合った副業の選び方 (300字)          ║
║         [CTA: おすすめ副業診断リンク / 関連記事]             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  メタデータ案:                                                ║
║  title: 副業おすすめランキング15選【2026年】初心者向け        ║
║         (31文字)                                              ║
║  description: 2026年最新の副業おすすめ15選を紹介。在宅・      ║
║    スマホ・投資系に分けて初心者でも安全に始められる副業を     ║
║    厳選しました。確定申告の注意点も解説。(94文字)             ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Rewrite Scoring Methodology

When `seo analyze` or `seo score` is executed, the agent evaluates existing content across 8 dimensions:

```
╔══════════════════════════════════════════════════════════════╗
║            SEO Scoring Report                                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Overall SEO Score:  68/100 (改善余地あり)                    ║
║                                                              ║
║  ████████████████████████████████████░░░░░░░░░░  68/100      ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  Dimension Scores:                                           ║
║                                                              ║
║  1. KW密度          ████████████████░░░░  80/100 (3.2% OK)   ║
║  2. 共起語カバー率  ██████████░░░░░░░░░░  50/100 (52%)       ║
║  3. 見出し構造      ████████████████████  95/100 (適切)      ║
║  4. 文字数          ██████████████░░░░░░  65/100 (4,200字)   ║
║  5. E-E-A-T         ████████░░░░░░░░░░░░  40/100 (経験不足)  ║
║  6. 読みやすさ      ██████████████████░░  85/100 (良好)      ║
║  7. メタデータ      ████████████████░░░░  75/100 (description長)║
║  8. 内部リンク      ██████░░░░░░░░░░░░░░  30/100 (不足)      ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  改善提案 (優先度順):                                         ║
║                                                              ║
║  [HIGH] 共起語カバー率が52%。以下の共起語を追加:             ║
║    - 確定申告 (必須/未使用)                                   ║
║    - リスク (必須/未使用)                                     ║
║    - 初心者 (推奨/未使用)                                    ║
║                                                              ║
║  [HIGH] E-E-A-T: 体験談・具体例が不足。以下を追加:          ║
║    - 実際に試した経験の記述                                   ║
║    - 具体的な数字（収入実績等）                               ║
║    - 専門家の引用またはデータ出典                             ║
║                                                              ║
║  [MED]  内部リンク: 関連記事へのリンクが0本。                ║
║    - 3-5本の内部リンクを本文中に追加                         ║
║                                                              ║
║  [LOW]  文字数: 4,200字は競合平均(6,800字)より少ない。       ║
║    - セクション追加で6,000字以上を目指す                     ║
║                                                              ║
║  予測改善効果: 68/100 → 85/100 (推定上位5位以内)             ║
╚══════════════════════════════════════════════════════════════╝
```

### Scoring Weight Distribution

| Dimension          | Weight | Rationale                                      |
|--------------------|--------|-------------------------------------------------|
| KW密度             | 15%    | Basic relevance signal                          |
| 共起語カバー率     | 20%    | Topical completeness (最重要)                   |
| 見出し構造         | 10%    | Crawlability and UX                             |
| 文字数             | 10%    | Content depth signal                            |
| E-E-A-T            | 20%    | Google quality guidelines compliance (最重要)   |
| 読みやすさ         | 10%    | User engagement signal                          |
| メタデータ         | 10%    | CTR optimization                                |
| 内部リンク         | 5%     | Site architecture signal                        |

---

## JP SEO Writer vs English SEO Tools — Comparison

Japanese SEO has unique characteristics that general-purpose English SEO tools fail to handle properly. This skill is purpose-built for the Japanese search ecosystem.

| Feature                         | JP SEO Writer              | English SEO Tools (Surfer, Clearscope等)  |
|---------------------------------|----------------------------|-------------------------------------------|
| Keyword density calculation     | 形態素解析 (MeCab)         | Whitespace tokenization                    |
| Character count method          | 日本語文字数 (全角基準)    | Word count (英語基準)                      |
| Co-occurrence extraction        | JP morphological analysis  | N-gram / word-level                        |
| Title tag length                | 32文字 (pixel幅考慮)       | 60 chars (英語)                            |
| Meta description length         | 120文字                    | 160 chars                                  |
| Search intent patterns          | 「〜とは」「〜 やり方」等  | "how to", "what is" etc.                   |
| Mobile optimization             | 70%以上がスマホ想定        | Desktop-first in some tools                |
| Structured data                 | 日本語Google仕様準拠       | English Google specs                       |
| Search engine coverage          | Google JP + Yahoo! JAPAN   | Google US/global                           |
| Reading level optimization      | 一文50文字以内、漢字率調整 | Flesch-Kincaid etc.                        |
| E-E-A-T guidance                | 日本語コンテンツ特有の要件 | English content guidelines                 |
| Output language                 | Native Japanese             | English (translation needed)               |

**Key differences that matter:**
- Japanese has no whitespace between words, so keyword density MUST be calculated with morphological analysis. English tools using whitespace tokenization produce incorrect density measurements for Japanese text.
- Japanese search queries tend to be shorter (2-4 words) and follow unique patterns like 「X とは」 (what is X) and 「X やり方」 (how to do X) that English tools do not model.
- Title tags and meta descriptions have different optimal lengths due to pixel width differences between full-width Japanese characters and half-width Latin characters.

---

## Error Handling

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| E001 | Keyword analysis failed (no search volume data returned) | Verify keyword spelling; try broader keyword; check if search API quota is available |
| E002 | Co-occurrence data unavailable (competitor pages blocked or empty) | Retry with cached data if available; fall back to manual co-occurrence input; check network connectivity |
| E003 | Article generation timeout (exceeded 5-minute generation limit) | Reduce target word count with `--length`; split into sections with `seo write --section`; retry |
| E004 | Duplicate content detected (>30% similarity with existing indexed content) | Show diff with matched content; suggest alternative angles; use `seo rewrite` for differentiation |
| E005 | Word count out of range (generated text deviates >20% from target) | Auto-trim or expand content to fit target range; report actual vs target count with adjustment suggestions |
| E006 | SEO score below threshold (generated article scores < 60/100) | Auto-run improvement pass; add missing co-occurrence terms; enhance E-E-A-T elements; regenerate weak sections |
| E007 | Image optimization failed (suggested image slots could not be resolved) | Fall back to text-only placeholders with `[IMAGE: description]` markers; provide alt-text suggestions |
| E008 | Schema markup validation error (JSON-LD failed Google validation) | Run schema through validator; fix missing required fields; regenerate with corrected structure |

**Error recovery strategy:** For E001-E002 (data acquisition errors), the agent retries up to 3 times with exponential backoff, then falls back to cached data. For E003-E006 (generation errors), the agent adjusts parameters and regenerates. For E007-E008 (post-processing errors), the agent provides manual correction guidance. All errors are logged to `~/.jp-seo-writer/scores/` for debugging.

---

## Data Storage & Persistence

```
~/.jp-seo-writer/
  config.yaml               # Default settings, API keys for search tools
  research/
    keyword_cache/
      副業_おすすめ.json         # Cached keyword research results (TTL: 7d)
    competitor_cache/
      副業_おすすめ_top10.json   # Cached competitor analysis (TTL: 3d)
    cooccurrence_cache/
      副業_おすすめ_cooc.json    # Cached co-occurrence data (TTL: 7d)
  outlines/
    副業_おすすめ_outline.json   # Saved outline for review/editing
  articles/
    副業_おすすめ_draft.md       # Generated article draft
    副業_おすすめ_meta.json      # Generated metadata
    副業_おすすめ_schema.json    # Structured data (JSON-LD)
  scores/
    2026-03-01_analysis.json     # SEO score history for tracking improvement
  templates/
    article_default.md           # Default article template
    article_howto.md             # How-to article template
    article_comparison.md        # Comparison article template
    article_listicle.md          # Listicle template
```

**Score History JSON (for tracking improvement over time):**
```json
{
  "url": "https://myblog.jp/副業-おすすめ",
  "keyword": "副業 おすすめ",
  "history": [
    { "date": "2026-02-15", "score": 52, "ranking": 18 },
    { "date": "2026-03-01", "score": 68, "ranking": 12 },
    { "date": "2026-03-15", "score": 85, "ranking": 5 }
  ]
}
```

---

## FAQ

**Q: 共起語分析は実際の検索結果を取得しますか？**
A: はい。`seo cooccurrence` は Google の検索結果上位10記事の本文を解析します。API経由またはスクレイピングで取得し、形態素解析を行います。キャッシュは7日間有効で、再分析時は最新データを取得します。

**Q: 記事生成にかかる時間は？**
A: フルパイプライン（リサーチ → 構成案 → 記事生成 → メタデータ）で5,000文字の記事を生成する場合、約2-3分です。構成案の承認ステップを入れる場合はユーザーの確認待ち時間が加わります。

**Q: 既存記事のリライトは元の文章をどこまで変えますか？**
A: `seo rewrite` は元の文章の文意と構造を尊重しつつ、SEOスコアを向上させるために必要な変更のみを行います。具体的には、共起語の追加、見出し構造の調整、メタデータの最適化、E-E-A-T要素の補強が中心です。変更箇所はdiff形式で提示されます。

**Q: キーワード密度の計算方法は？**
A: 日本語テキストをMeCab/Sudachiで形態素解析し、全形態素数に対するターゲットキーワードの出現回数で算出します。複合語（例: 「副業 おすすめ」）は、2語が近接（同一文内）で出現する場合もカウントします。英語のword countベースの計算とは根本的に異なります。

**Q: 構造化データ（JSON-LD）は自動生成されますか？**
A: はい。記事内容に応じて以下の構造化データを自動生成します:
- **FAQPage**: 記事内のFAQセクションから
- **HowTo**: 手順を含む記事から
- **Article**: 全記事に基本メタデータとして
- **BreadcrumbList**: サイト構造に合わせて
生成されたJSON-LDはコピー&ペーストでHTMLに埋め込めます。

**Q: E-E-A-Tスコアはどう算出していますか？**
A: 以下の4要素を各25点で評価します:
- **Experience (経験)**: 体験談、「実際に〜した」表現の有無 (25点)
- **Expertise (専門性)**: 専門用語の適切な使用、深い解説の有無 (25点)
- **Authoritativeness (権威性)**: データ引用、公式情報源の参照 (25点)
- **Trustworthiness (信頼性)**: 出典明示、更新日、正確な情報 (25点)

**Q: 複数キーワードを同時にターゲットできますか？**
A: はい。`seo write "副業 おすすめ" --secondary "副業 在宅,副業 安全"` のように、メインキーワードとサブキーワードを指定できます。構成案ではサブキーワード用のセクションが自動的に組み込まれ、全キーワードの密度バランスが最適化されます。

**Q: JP Humanizer と組み合わせて使えますか？**
A: はい、非常に有効です。JP SEO Writer で生成した記事を JP Humanizer に通すことで、SEO最適化を維持しつつAI臭さを除去できます。推奨フローは: `seo write` → `jpfix <output> --mode casual --preserve-keywords "キーワード"` です。

**Q: 記事の著作権・盗用チェックは行われますか？**
A: はい、生成された記事は自動的にオリジナリティスコアを算出します。既存コンテンツとの類似度が30%を超える段落は警告し、自動リライトを提案します。`seo plagiarism-check` で手動チェックも可能です。

**Q: WordPress への直接投稿は可能ですか？**
A: はい、`seo publish --platform wordpress --url https://your-site.com --auth $WP_TOKEN` で生成記事をWordPressに直接投稿できます。カテゴリ・タグ・アイキャッチ画像の自動設定にも対応しています。
