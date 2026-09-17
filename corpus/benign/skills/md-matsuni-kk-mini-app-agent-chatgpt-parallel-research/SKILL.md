---
name: chatgpt-parallel-research
description: "Browser Controller拡張機能を使ってChatGPT 5.2 Thinkingで3並列以上のウェブ検索・ブレスト・情報収集を実行する。難問にはHeavy thinking（heavy/extended）を使用。指定時のみChatGPT Proで深い考察・ファクトチェック。マルチターン継続（chat）、再取得（recover）、ファイル添付、タブ管理にも対応。「ウェブ検索」「横断検索」「並列検索」「ブレスト」「情報収集」「リサーチ」「再取得」「追加質問」を依頼されたときに使用する。"
---

# ChatGPT Parallel Research Workflow

## Instructions
1. Preflight:
   - 概要: Browser Controller Chrome拡張機能を使用し、ChatGPTで3並列以上の検索・ブレストを実行して横断的に情報を収集する。
   - デフォルトモデル: ChatGPT 5.2 Thinking
   - オプション: ChatGPT Pro（`--model pro` 指定時のみ）- 深い考察・ファクトチェック用
   - 前提条件:
     - Browser Controller拡張機能がChromeにインストールされていること
     - ChatGPTにログイン済みであること
     - ブリッジサーバーは自動起動（手動起動不要）
   - ドキュメント精査原則（Preflight必須）：テンプレート確認後、生成前に必ず以下を実施すること。
     - アジェンダ・依頼文に記載された参照資料を全て読み込む。
     - Flow/Stock配下の関連資料（前回議事録・要望リスト・プロジェクトREADME等）を網羅的に検索・確認する。
     - 確認できなかった資料は「未参照一覧」として成果物に明記する。
     - これらを完了するまで生成を開始しない。
   - `./assets/chatgpt_research_template.md` を先に読み、章立て・必須項目・項目順序を確認する（テンプレートファースト）。
   - `./questions/chatgpt_research_questions.md` を使って必要情報を収集する。
   - 実行モードを確定する（自由度を絞る）。
     - `search`（デフォルト）: 3クエリ以上必須（3セッション以上で実行）
     - `search1`: 単一セッション検索（1タブで複数クエリを順次実行）
   - クエリを3個以上に分割・設計する（`search` を使う場合は必須）。
   - クエリ設計ルール:
     1. フルコンテキストで渡す: 各クエリは独立コンテキストとして成立させる。背景情報・前提・制約・目的を各クエリ本文に含める。ChatGPTは他のタブの内容を知らないため、省略禁止。
     2. 関連ファイルは添付: 関連する情報がファイルにある場合は `--files` で添付する（最大10ファイル）。ファイルを読んで口頭で伝えるのではなく、ファイル自体を渡す。
     3. 目的と検索対象を明記: 各クエリの冒頭に「何の目的で」「何を検索/議論するのか」を明示する。
     4. 背景情報は徹底的に詳しく: 「なぜこの質問をするのか」「どういう文脈でこの情報が必要なのか」を省略せずに書く。
     5. 極めて詳細に: クエリ自体を詳細に設計し、回答も詳細に返してもらうよう指示する。曖昧な表現や省略は禁止。
     6. 同一セッションで継続: 複数の追加質問は新規チャットを立てず、同じ会話セッションにchatで追加する。前回の回答が完了していることを確認してから次の質問を送信する。
   - クエリ設計の構造（5W1H + 背景）:
     ```
     【背景・文脈】
     - 現在の状況: □□という状態である
     - 経緯: ××があったため、△△を検討している
     - なぜこの質問をするのか: 〇〇を決定/解決するために必要な情報である

     【目的】〇〇のために△△を調査する

     【Who】誰が関係するか（対象者、ステークホルダー）
     【What】具体的に知りたいこと
     【When】時期・期間・タイミングの制約
     【Where】地域・市場・対象範囲
     【Why】なぜそれが重要か、どう活用するか
     【How】どのようなアプローチ・手法・形式で知りたいか

     【制約】あれば記載（日本語のみ、最新情報のみ、信頼性高いソースのみ等）
     【期待する出力形式】箇条書き/表形式/比較表/詳細説明 等

     【回答の詳細度】
     - 可能な限り詳細かつ網羅的に回答してください
     - 具体例、数値、事例を豊富に含めてください
     - 表面的な説明ではなく、深掘りした分析を提供してください
     - 結論だけでなく、その根拠と理由も詳しく説明してください
     ```
   - モデル/推論強度を決める（モデル名はUI更新により変更される場合があります。`python chatgpt_multi.py models` で確認）。
     - モデル選択ガイド:
       | 難易度 | モデル | Thinking | 用途 |
       |--------|--------|----------|------|
       | 簡単～普通 | ChatGPT 5.2 Thinking | light | 一般的な検索、簡単なブレスト（デフォルト） |
       | 普通～やや難 | ChatGPT 5.2 Thinking | standard | 比較分析、中程度のブレスト |
       | 難問 | ChatGPT 5.2 Thinking | heavy | 技術的な深掘り、複雑な分析 |
       | 非常に難問 | ChatGPT 5.2 Thinking | extended | 最高精度の推論、専門的分析 |
       | 指定時のみ | ChatGPT Pro | - | 深い考察、確実なファクトチェック |
       | レガシー | ChatGPT Classic | - | 旧モデルでの確認が必要な場合 |
     - モデル使い分けの指針:
       - デフォルト: ChatGPT 5.2 Thinking（モデル指定不要）
       - 難問: `--thinking heavy` または `--thinking extended` を追加
       - ファクトチェック・深い考察: `--model pro` を明示的に指定
   - 検索クエリ設計ガイドライン:
     | 用途 | クエリ例 |
     |------|----------|
     | ウェブ検索 | 「〇〇について最新情報を検索して」「△△の公式ドキュメントを調べて」 |
     | ブレスト | 「〇〇のアイデアを10個出して」「△△の課題と解決策をブレストして」 |
     | 比較分析 | 「AとBの違いを詳しく比較して」「〇〇の選択肢のメリデメを整理して」 |
     | 深掘り | 「〇〇の技術的な仕組みを詳しく解説して」「△△の設計パターンを分析して」 |

2. 実行:
   - Browser Controller拡張機能がChromeにインストールされていること。
   - ChatGPTにログイン済みであること。
   - ブリッジサーバーは自動起動（手動起動不要）。接続確認:
     - `python chatgpt_multi.py status`

   - スクリプト実行パス:
     - `./scripts/chatgpt_multi.py`
   - 実行方法:
     - このSkillの `./scripts` に移動して実行:
       - `cd .cursor/skills/chatgpt-parallel-research/scripts && python chatgpt_multi.py "質問1" "質問2" "質問3"`
     - リポジトリルートからフルパス指定で実行:
       - `python .cursor/skills/chatgpt-parallel-research/scripts/chatgpt_multi.py "質問1" "質問2" "質問3"`
   - 外部依存:
     - Browser Controller Chrome拡張機能がインストール済みであること
     - Python 3.8以上

   - 3並列以上（search: 3クエリ以上必須）:
     - `python chatgpt_multi.py "検索クエリ1" "検索クエリ2" "検索クエリ3"`
     - `python chatgpt_multi.py "Q1" "Q2" "Q3" --thinking heavy`
     - `python chatgpt_multi.py "Q1" "Q2" "Q3" --model pro`

   - 単一セッション検索（search1: 1タブで順次）:
     - `python chatgpt_multi.py search1 "検索クエリ1" "検索クエリ2"`

   - ファイル添付:
     - 並列検索に添付: `python chatgpt_multi.py "Q1" "Q2" "Q3" --files /path/to/document.pdf`
     - 既存タブに添付: `python chatgpt_multi.py attach --file /path/to/document.pdf --tab <tab_id>`

   - 出力（保存先はこのSkill内に明記する）:
     - すべて `Flow/YYYYMM/YYYY-MM-DD/<topic>/` 配下に保存される。
     - `<topic>` は先頭の検索クエリ（または先頭の追加質問）から自動生成され、ファイル名に使えない文字は置換される。
     - 並列検索: `Flow/YYYYMM/YYYY-MM-DD/<topic>/chatgpt_q{N}_{timestamp}.md`
     - チャット: `Flow/YYYYMM/YYYY-MM-DD/<topic>/chatgpt_chat_tab{id}_{timestamp}.md`

   - 出力形式（タブごとに1ファイル・全ターンを統合）:
     - 各タブごとに1つのMDファイルを作成し、全ターンの会話を同一ファイルに記録する。
     - ファイル構造:
       ```markdown
       # ChatGPT Multi-Turn Session
       **Tab ID**: 12345
       **URL**: https://chatgpt.com/c/...
       **セッション開始**: 2026-01-28 10:00:00

       ---

       ## Turn 1
       **Query**: 最初の質問
       **Timestamp**: 2026-01-28 10:00:00
       **Elapsed**: 45.2s
       **Status**: Success

       （回答内容）

       ---

       ## Turn 2
       **Query**: 追加質問
       ...
       ```
     - 保存先: `Flow/YYYYMM/YYYY-MM-DD/<topic>/chatgpt_q{N}_{timestamp}.md`
     - 3並列3往復の場合 → 3ファイル（各ファイルに3ターン分）

   - セッション（マルチターン継続情報）:
     - `~/.chatgpt_multi_session.json` に `tab id/url/topic/md_path` を保存する。
     - タブが閉じている場合、`chat` / `recover` は保存済みURLからタブを再オープンして継続を試みる。
       - 旧形式のセッションファイルでURLが保存されていない場合は復元できない。

   - マルチターン（同じセッションに追加質問）:
     - 自動選択: `python chatgpt_multi.py chat -m "追加質問"`
     - 複数質問を同一セッションに順次送信: `python chatgpt_multi.py chat -m "Q1" "Q2" "Q3"`
     - タブを明示指定: `python chatgpt_multi.py chat -m "質問" --tab 123`

   - マルチターン並列（search後の継続質問）:
     - 並列検索後に継続質問する場合、`reply`コマンドで全タブ分の質問を同時に指定する。
     - 例: 3並列3往復
       ```bash
       # 1ターン目: 3並列検索（turnsで予定ターン数を宣言）
       python chatgpt_multi.py "Q1" "Q2" "Q3" --turns 3

       # 2ターン目: reply で3つの追加質問を同時指定
       python chatgpt_multi.py reply "Follow1" "Follow2" "Follow3"

       # 3ターン目: 同様に3つ指定
       python chatgpt_multi.py reply "Final1" "Final2" "Final3"
       ```
     - 制約:
       - `reply`の質問数はセッションタブ数と一致させる（3並列なら3つ）
       - 1つのタブだけに追加質問はできない（全タブ一括）
       - `--turns`で宣言したターン数分だけ往復する

    - 再取得（受け取り側エラー対策）:
      - `python chatgpt_multi.py recover --tab <tab_id>`
        - **スクロールしながら全会話履歴を取得**してMDファイルに保存する
        - ChatGPTの仮想スクロールに対応し、DOM上に表示されていないメッセージも収集
        - 3ターン続いたタブなら3ターン分全部取得
        - セッションに`md_path`があれば既存ファイルを上書き、なければ新規ファイル作成
        - 保存先: `Flow/YYYYMM/YYYY-MM-DD/<url_based_topic>/chatgpt_chat_tab{id}_{timestamp}.md`
        - タブが閉じている場合、セッションに保存されたURLから再オープンして取得
      - URLから直接recover: `python chatgpt_multi.py recover --url "https://chatgpt.com/c/..."`
      - 表示のみ: `python chatgpt_multi.py response --tab <tab_id>`

   - タブ管理:
     - 一覧: `python chatgpt_multi.py tabs`
     - 閉じる: `python chatgpt_multi.py close --tab <tab_id>`

   - CLI Reference（抜粋）:
     - タブ一覧: `python chatgpt_multi.py tabs`
     - モデル一覧: `python chatgpt_multi.py models`
     - Thinking強度確認: `python chatgpt_multi.py thinking`
     - Thinking強度設定: `python chatgpt_multi.py set-thinking --level heavy`
     - 単一チャット（マルチターン）: `python chatgpt_multi.py chat -m "質問内容"`
     - ファイル添付: `python chatgpt_multi.py attach --file /path/to/file.pdf --tab <tab_id>`
     - 回答取得（表示のみ）: `python chatgpt_multi.py response --tab <tab_id>`
     - 再取得（MD保存）: `python chatgpt_multi.py recover --tab <tab_id>`
     - ブリッジ状態確認: `python chatgpt_multi.py status`
     - ブリッジ起動（フォアグラウンド）: `python chatgpt_multi.py bridge`

   - 並列検索オプション（抜粋）:
      ```bash
      python chatgpt_multi.py [質問1] [質問2] [質問3] ...
        --model        : モデル選択（例: pro）
        --thinking, -t : 推論強度（light, standard, heavy, extended）
        --files        : 添付ファイル（複数可）
        --no-auto-bridge : ブリッジ自動起動を無効化
        --close-tabs   : search/search1/chat/recover 完了後にタブを閉じる
        --keep-tabs    : (Deprecated: デフォルトで保持) タブを保持
      ```

    - 待機設定（固定）:
      - タイムアウト: 1800秒（30分）
      - ポーリング間隔: 5秒
      - 待機中のタブ自動リフレッシュ: 600秒ごと（リフレッシュ後に固定3秒待機）
      - `--timeout` / `--interval` は指定不可（指定した瞬間にエラー）

    - 制約:
      - `search` は3クエリ未満を受け付けない（3セッション未満を禁止）。
      - `parallel_search` / `search1` / `chat` / `recover` の待機設定は固定（タイムアウト1800秒・ポーリング5秒）。
      - `--timeout` / `--interval` は使用不可（指定した瞬間にエラー）。
      - `response` は即時取得して終了（待機なし）。
      - エージェント側で `sleep` 等により独自の待機を足さない。

    - LLM実行ラッパー上の注意（重要）:
      - `chatgpt_multi.py` の待機は最大1800秒（30分）に固定でも、実行ラッパー（例: LLMのBash実行機能）が短いタイムアウトや中断（会話の次発話等）を持つ場合、プロセスが先に強制終了される。
      - 対策（ラッパーで実行する場合）:
        - ラッパー側のコマンド実行タイムアウトは `>= 1900秒`（30分+α）に設定する。
        - 実行中は追加の指示/発話で中断させない。
      - 対策（確実に30分待機させたい場合）:
        - 端末で直接実行するか、バックグラウンド実行（例: `nohup python3 ... &`）にして、完了後に `recover` で回収する。

3. 結果統合:
   - 各タブの応答（個別MD）を収集し、`./assets/chatgpt_research_template.md` 形式で統合する。
   - 情報源・信頼性・矛盾点を整理し、結論と推奨アクションを明確化する。

4. Troubleshooting:
    - 症状: MDが `## 回答` の `(waiting...)` から更新されない。
      - 原因: 応答取得に失敗している。
      - 手順:
        - タブID確認: `python chatgpt_multi.py tabs`
        - 再取得（MD保存）: `python chatgpt_multi.py recover --tab <tab_id>`
        - 表示のみ: `python chatgpt_multi.py response --tab <tab_id>`
        - ChatGPT側のエラーメッセージや制限（Rate limit等）を確認する。
    - 症状: ブラウザ上は回答が完了しているのに、MDが `(waiting...)` のまま。
      - 原因: コマンド実行環境（例: エージェントのコマンド実行ラッパー）のタイムアウト/中断で、待機ループが最後まで走っていない。
      - 対策:
        - コマンド実行ラッパー側のタイムアウトは1800秒以上に設定する（設定できる場合）。
        - 実行中は別コマンド実行や別リクエスト送信で中断させない。
        - 中断された場合は `recover` でタブIDから回収する。

5. QC（必須）:
   - `recommended_subagents` のQC Subagentに評価を委譲する。
   - Subagentは `./evaluation/evaluation_criteria.md` に基づきQCを実施する。
   - 指摘があれば追加検索（`search` または `search1`）や `recover` を実行する。
   - 最大3回まで繰り返し確定する。

6. バックログ反映:
   - 追加調査が必要な項目、未解決の論点、次アクションをバックログへ反映する。

subagent_policy:
  - 品質ループ（QC/チェック/フィードバック）は必ずサブエージェントへ委譲する
  - 指摘の反映は最小差分で行う
  - 指摘に対し「修正した/しない」と理由を最終成果物に残す

recommended_subagents:
  - qa-skill-qc: 3並列要件、クエリ多様性、統合内容、欠損の有無を検査

## Resources
- questions: ./questions/chatgpt_research_questions.md
- assets: ./assets/chatgpt_research_template.md
- evaluation: ./evaluation/evaluation_criteria.md
- scripts: ./scripts/chatgpt_multi.py
- references: ./references/guide.md

## Next Action
- 統合結果をもとに、設計・実装・追加調査の次アクションへ進む。
- 指摘が出た場合は、追加検索または再取得を実行して再QCする。

## Subagent Execution
このSkillはサブエージェントとして独立実行可能。
- サブエージェント: `agents/chatgpt-parallel-research-agent.md`
- 用途: 並列ウェブ検索、ブレインストーミング、横断情報収集、ファクトチェック
- 入力: `search_queries`（3個以上必須）, `model`（pro等）, `thinking`（light/standard/heavy/extended）
- 出力: 統合された検索結果レポート（chatgpt_research_template.md形式）
