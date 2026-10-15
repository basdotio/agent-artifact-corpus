# Interview flow: questions, option sets, Japanese phrasing

Read by SKILL.md Steps 0 to 4. Japanese user-facing text lives inside fenced blocks; the
instructions around it are English. Phrasing in the blocks is the exemplar, not a script:
keep the register and the shape, adapt the nouns to the actual site.

Register: polite Japanese (`keigo`), one idea per sentence, no filler, no praise. Explain a
design term the first time with an everyday example, then use the term.

`AskUserQuestion` limits that shape every call: 1 to 4 questions per call, 2 to 4 options per
question, the tool adds an Other free-text option by itself. Never write an "Other" option.

## Opening line

```
こんにちは。参考にしたいサイトから、あなたのサイト専用の DESIGN.md を作ります。
先に、作りたいサイトのことを 4 つだけ伺います。
```

## Step 0: the user's own site (one call, four questions)

Question 1 (header `業種`, single-select):

```
どんな業種・分野のサイトですか？
- 小売・EC・飲食
- サービス業・士業・教室
- IT・SaaS・スタートアップ
- 個人・クリエイター・ポートフォリオ
```

Question 2 (header `目的`, single-select):

```
サイトで一番してほしいことは何ですか？
- 購入・申込をしてもらう
- 問い合わせ・相談をしてもらう
- ブランドや世界観を知ってもらう
- 情報を読んでもらう・採用に応募してもらう
```

Question 3 (header `相手`, single-select):

```
主に誰が見るサイトですか？
- 一般の個人のお客さま
- 企業の担当者・決裁者
- すでに知っている既存のお客さま・会員
- 求職者・応募者・学生
```

Question 4 (header `印象`, single-select):

```
初めて訪れた人に、ひとつだけ覚えて帰ってほしいものは何ですか？
- 大きな写真や映像（ひと目で伝わる絵）
- 言葉（キャッチコピーや理念）
- 数字や実績（導入社数・事例など）
- 色や形の世界観（ブランドらしさ）
```

This is where the site spends its boldness. Everything else in the brief and the file stays
quieter than this one thing. A free-text answer ("代表の顔", "商品そのもの") is better than
any option; keep its wording.

## Step 1: reference URLs

```
気に入ったサイトデザインの URL をご共有ください。1 つから 3 つまでで大丈夫です。
「このサイトの、この部分」でも結構です。あとで一つずつ伺います。
```

Too many URLs:

```
4 つ以上いただきました。今回は最初の 3 つで進め、残りは次の回で扱います。
```

No URL after one prompt:

```
参考サイトなしでも進められます。その場合、色やフォントの値は「あとで決める」として残します。進めますか？
```

## Screenshot ask (once per run, only when no screenshot tool exists)

```
気になる箇所のスクリーンショットがあれば貼ってください。なくても進められます。
```

## Fetch errors (one line each, then continue)

`unreachable`:

```
このURLには接続できませんでした。URLをもう一度ご確認いただくか、スクリーンショットを貼っていただければ進められます。
```

`blocked`:

```
このサイトは自動取得を拒否しています。見た目の分析はスクリーンショットから行いますので、1 枚貼っていただけますか。
```

`login`:

```
ログインが必要なページのようです。公開されているページの URL をいただけますか。
```

`curl` missing:

```
取得ツール (curl) が見つからないため、ページの読み取りは簡易モードで行います。色やフォントの正確な値は取れないことがあります。
```

## Step 3: per site, two or three calls

Announce the site first, in one line, using its title from `facts.txt`:

```
1 つ目のサイト「<title>」について伺います。
```

### Call A: the four bundles (one question, multi-select, header `良かった点`)

```
このサイトのどこが良かったですか？ (複数選べます)
- 全体の構成・レイアウト (ページの流れ、並べ方、余白の取り方)
- 特定のセクションや部品 (ヒーロー、カード、メニュー、フッターなど)
- 色と文字 (配色、フォント、文字の大きさ)
- 雰囲気・動き・写真 (世界観、アニメーション、写真の使い方、言葉のトーン)
```

### Call B: concrete follow-ups (one question per picked bundle, multi-select)

Options are built from the Step 2 summary of THIS site. 3 to 4 per question. Each option
names something the user saw on the page. Templates by bundle, with the kind of noun to fill:

Bundle: structure and layout (header `構成`)

```
構成・レイアウトで、特にどこですか？
- <section order observed, e.g. 冒頭に大きな写真、その直下に 3 つの特徴を横並び>
- <grid/width observed, e.g. 中央 1 カラムで横幅を狭く、左右に大きな余白>
- <navigation observed, e.g. 上部メニューが少なく 4 項目だけ>
- <rhythm observed, e.g. セクションごとに背景色を白と薄いグレーで交互に>
```

Bundle: specific section or component (header `部品`)

```
どのセクション・部品ですか？
- <hero observed, e.g. 冒頭の全面写真と短いひとこと>
- <card observed, e.g. 角丸の白いカードに写真と 2 行の説明>
- <cta observed, e.g. 画面下に固定された申込ボタン>
- <footer/other observed, e.g. 最後の「お客さまの声」の横スクロール>
```

Bundle: colors and type (header `色と文字`)

```
色と文字で、特にどこですか？
- <palette observed, e.g. ほぼ白と黒だけで、アクセントは 1 色 (#E24A33 の赤)>
- <heading type observed, e.g. 見出しの太いセリフ体 (Playfair Display)>
- <body type observed, e.g. 本文が小さめで行間が広い>
- <contrast observed, e.g. 黒背景に白文字のセクションが途中に入る>
```

Bundle: mood, motion, imagery (header `雰囲気`)

```
雰囲気・動き・写真で、特にどこですか？
- <mood observed, e.g. 静かで高級感がある (余白が多く、装飾がない)>
- <motion observed, e.g. スクロールすると要素がふわっと現れる>
- <imagery observed, e.g. 人物写真が大きく、商品写真は小さい>
- <tone observed, e.g. 言葉が短く、断定的>
```

### The avoid question (mandatory for every site, multi-select, header `避けたい`)

Where it goes: if the user picked 3 bundles or fewer in Call A, it is the last question of
Call B. If they picked all four, Call B is full (4 questions), so ask it alone in Call C.
Options are 3 things observed on THIS site that people commonly dislike, plus `特にない`:

```
逆に、このサイトで真似したくない点はありますか？ (複数選べます)
- 特にない
- <disliked thing observed, e.g. 開いてすぐ自動再生される動画>
- <disliked thing observed, e.g. 数秒後に出てくるメールマガジン登録のポップアップ>
- <disliked thing observed, e.g. 取引先ロゴがずらりと並ぶ帯>
```

Every answer other than `特にない` (free text included) becomes a `reject` line in picks.txt
and appears in the brief's "do not" part, in DESIGN.md `Do's and Don'ts`, and in `Sources`
(rejected: ...).

Rules for building options:
- Each option is one thing, nameable, visible on the page. Not "good hierarchy".
- Include the concrete value in parentheses when it is a color or font, so the user learns
  the vocabulary while choosing. The value comes from the source order in SKILL.md Step 2
  (the rendered page, else facts.txt, and a facts.txt value only if it agrees with the
  screenshot when one exists), never from a screenshot read by eye.
- If Step 2 produced fewer than 3 observations for a bundle, ask the user to describe it
  in free text instead of padding with generic options. Record the answer as a `said` line
  (rule below).
- Decide each Call B option's token patterns when you write the option, before the user
  answers (`colors.primary`, `typography.display-*.fontFamily`, or `-` for none). After the
  answer, write one `take` line per picked option and one `decline` line per offered option
  not picked (format: SKILL.md Step 3). The patterns never widen afterwards.
- An option's patterns cover every token group its words name: "no shadows, no rounded
  corners, no animation" covers `elevation.*,rounded.*,motion.*`. A page-width option
  covers `spacing.container,spacing.page-margin` when the site's side padding was measured,
  because the two together are the width the user saw.
- A free-text Other answer is a `said` line in the user's words. Its patterns are written
  after the answer, so they contain no `*` and name only the tokens for the attribute the
  user named (`ページ幅もこのサイトに近づけたい` is `spacing.container`), or `-`. A typed
  literal value (a hex, a font name) is a `user <group>` line instead.
- Everything after the first `|` on a `take`, `decline` or `said` line is the option text,
  verbatim: never add a trailing comment there.

## Step 3b: derivation inputs (one call, three questions, after the last site)

Lead-in line:

```
最後に、全体の手触りを 3 つだけ伺います。ここから余白や角丸の細かい値を計算します。
```

Question 1 (header `余白`, single-select):

```
余白の取り方は、どれが近いですか？
- きっちり詰める (情報量を優先、1 画面に多く見せる)
- ふつう
- ゆったり (余白を広く取り、1 画面に少なく見せる)
```

Question 2 (header `形`, single-select):

```
ボタンやカードの角は、どれが近いですか？
- 角張っている (直角〜ごくわずかな丸み)
- 少し丸い (一般的な丸み)
- かなり丸い (錠剤のような形まで含む)
```

Question 3 (header `明暗`, single-select):

```
色の基調はどちらですか？
- 明るい背景のみ
- 暗い背景のみ
- 両方 (明るい・暗いの切り替えあり)
```

Skip any question a site pick already answered, and say which pick answered it.

A `take` or `said` line that asks for little or no color sets the neutral palette seed
(derivation-rules sec.8 "Neutral palette seed") without a question.

## Step 4: brief ask

What the brief may contain: the Step 0 answers, the `take` and `said` lines, the `reject` lines, the
Step 3b answers, and anything the user typed. A declined option never appears in it, not
even reworded as a proposal.
Anything the skill adds that the user did not state (a page order, a section nobody picked)
is a proposal sentence, so the user can see it is not theirs:

```
ページの順番は、写真、特徴、お客さまの声、お申し込みの順をご提案します。
```

The user's OK does not turn a proposed or declined value into `chosen`; it stays
`defaulted` or `derived`.

After the full brief:

```
この内容で合っていますか。直したい点があれば、そのままお書きください。問題なければ「OK」とお願いします。
```

After a revision, show the full brief again, then:

```
直しました。この内容でよろしいですか。
```

## Step 5: file collision

```
すでに DESIGN.md があります。上書きしますか、それとも DESIGN.<名前>.md として別名で保存しますか？
- 別名で保存する (おすすめ: 既存ファイルを壊しません。欠点: AIツールは DESIGN.md という名前を探します)
- 上書きする
```

## Close (output contract)

```
DESIGN.md を書き出しました: ./DESIGN.md (<N> 行)
書式チェック: <lint OK | スキップ (npx が使えない環境でした)>
値の内訳: 選んだ値 <n> 個、ルールから導いた値 <n> 個、あとで決める値 <n> 個
あとで決める項目: <token name と、答えるべき問い。one per line, or この行を省く>
使い方: プロジェクトの一番上に置き、AI に「UI を触る前に DESIGN.md を読む」と伝えてください。Claude Code なら CLAUDE.md から参照させると確実です。
```
