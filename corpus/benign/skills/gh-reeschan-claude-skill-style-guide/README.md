# claude-skill-style-guide

[![ci](https://github.com/reeschan/claude-skill-style-guide/actions/workflows/ci.yml/badge.svg)](https://github.com/reeschan/claude-skill-style-guide/actions/workflows/ci.yml)

A Claude Code skill that turns a free-form description (e.g. "a calm, Japanese-style invoicing SaaS") into a UI theme: colors, radius, spacing, shadows and fonts.
It outputs a Tailwind v4 `theme.css`, a `theme.json` and a style guide document.
Estimation can be done by Jev (TypeSafe) or by Claude itself; everything after that is deterministic.

自由記述から UI テーマ (配色・角丸・余白・影・フォント) を推定し、Tailwind v4 の `theme.css`・`theme.json`・スタイルガイド文書を作る Claude Code スキルです。

![作業台: ダーク基調のニュートラルなテーマ。このスキルの Web アプリ自体の見た目](docs/images/app-workbench.png)

ダーク基調でニュートラルなテーマ「作業台」を Web アプリで開いたところ。

![藍の請求書: ライト基調で明朝体のテーマ](docs/images/app-wa-invoice.png)

ライト基調で明朝体を使ったテーマ「藍の請求書」を Web アプリで開いたところ。

## 特長

- 明示指定 (ブランド色の色コード、ライト/ダーク、フォント名) は推定より常に優先される
- 推定は Jev (TypeSafe) か Claude 自身が行う。Jev のキーが無くても使える
- 推定結果から決定的にシード化するので、同じ入力なら同じテーマになる
- WCAG のコントラストを自動で検証し、足りない色は補正する
- Web アプリで、スライダーや選択による調整、ライト/ダークのプレビューができる
- Google Fonts の無料フォントから、見出し・本文・等幅の 48 組のカタログを持つ

## 必要なもの

- Claude Code
- Node.js 22.18 以上 (`.ts` をそのまま実行するため。開発は v26)
- 任意: Jev (TypeSafe) の API キー

## インストール

```sh
git clone https://github.com/reeschan/claude-skill-style-guide ~/.claude/skills/style-guide
```

Windows の PowerShell:

```powershell
git clone https://github.com/reeschan/claude-skill-style-guide "$env:USERPROFILE\.claude\skills\style-guide"
```

`npm install` は不要です (依存パッケージはありません)。

## 使い方

Claude Code で次のように呼び出します。

```text
/style-guide 落ち着いた和風の請求書 SaaS。藍色が基調
```

自由記述が英語の要約 (ブリーフ) になり、推定、フォント選定、シード化、テーマ生成の順に進みます。結果は `~/.claude/style-guide/themes/<id>/` に 8 ファイルとして保存され、テーマ名・トンマナ・主な値・コントラストの結果・別案が報告されます。

- `/style-guide app`: Web アプリ (ブラウザ) で作る・調整する
- `/style-guide app <id>`: 保存済みのテーマを Web アプリで開く
- `/style-guide list`: 保存済みテーマの一覧

CLI を直接使うこともできます。

```sh
node scripts/pipeline.ts run --request request.json --brief brief.json
```

`request.json` の最小例:

```json
{ "prompt": "落ち着いた和風の請求書 SaaS。藍色が基調" }
```

色・モード・フォントを明示するときだけ `brandColor` (`#RRGGBB`)、`baseMode` (`light` / `dark`)、`fonts` (`{ "heading": "...", "body": "...", "mono": "..." }`) を足します。

`brief.json` の最小例:

```json
{
  "id": "aizome",
  "name": "藍の請求書",
  "tone": "藍色を基調にした、落ち着いて端正な請求書の見た目。",
  "needsJapanese": true,
  "state": {
    "product": "Invoicing SaaS for small businesses",
    "audience": "accountants and freelancers",
    "mood": ["calm", "refined", "trustworthy"],
    "references": "",
    "avoid": ""
  },
  "explicit": { "brandColor": null, "baseMode": null }
}
```

保存先は環境変数 `STYLE_GUIDE_HOME` で変えられます (既定は `~/.claude/style-guide`)。

## できあがるもの

`~/.claude/style-guide/themes/<id>/` に次の 8 ファイルができます。

| ファイル           | 中身                                                  |
| ------------------ | ----------------------------------------------------- |
| `request.json`     | 入力 (自由記述と明示指定)                             |
| `brief.json`       | 英語の要約 (ブリーフ)                                 |
| `estimate.json`    | 質問への回答 (推定結果)                               |
| `seed.json`        | テーマの元になるシード (色・形・フォント)             |
| `seed-result.json` | シード化の詳細 (別案、確度の低い項目、推定の出どころ) |
| `theme.css`        | Tailwind v4 のテーマ (CSS 変数)                       |
| `theme.json`       | ライト/ダーク両モードのトークン                       |
| `style-guide.md`   | スタイルガイド文書                                    |

`theme.css` は自分のプロジェクトの CSS から `@import` し、ルート要素に `data-theme="<id>"` を付けて使います。基調と逆のモードにしたいときは `data-mode` を付けます。

```html
<html data-theme="aizome" data-mode="dark"></html>
```

## Jev (任意)

Jev は推定に使う外部 API です。キーは次のどちらかに置きます。

- 環境変数 `TYPESAFE_API_KEY`
- `~/.config/typesafe/credentials.json` に `{"api_key": "..."}`

キーが無ければ、Claude Code のエージェント自身が同じ形の推定を書くので、無くても使えます。Jev に送るのは英語の要約 (`brief.state`) と質問だけで、自由記述の本文・色コード・ソースコードは送りません。

クライアントは `lib/jev.mjs` を同梱しています。`~/.claude/shared/jev/jev.mjs` があればそちらを使い、環境変数 `STYLE_GUIDE_JEV_MODULE` で差し替えることもできます。

## Web アプリ

`/style-guide app` で、ローカルの `127.0.0.1` だけで動くサーバーが起動します。外部には公開されません。ブリーフ化と、Jev が失敗したときの推定にはローカルの `claude` CLI (`claude -p`) を使うので、API キーは不要です。

画面でできること: 生成、ブリーフの編集、スライダーと選択での調整、別案の切り替え、ライト/ダークのプレビュー、コントラスト表、保存、書き出し。

## 仕組み

1. 明示指定の確定 (色・モード・フォントは推定より優先)
2. ブリーフ化 (自由記述を英語の要約にする)
3. 判定 (ブリーフと質問セットから推定を作る。Jev またはエージェント)
4. フォント選定 (カタログから候補を絞り、1 問で選ぶ)
5. シード化 (結果を `Seed` と別案にする。ここから先は決定的)
6. generate-theme (`Seed` から `theme.css` / `theme.json` を作る)

ディレクトリ構成:

- `core/`: 明示指定・質問セット・フォント選定・シード化・テーマ生成・保存
- `data/`: フォントカタログ (`fonts.json`)
- `scripts/`: CLI (`pipeline.ts`: `questions` / `fonts` / `run` / `list`)
- `app/`: Web アプリ (ローカルサーバーと画面)
- `lib/`: Jev クライアント (`jev.mjs`) と読み込み
- `examples/`: テスト用の例 (シードと期待するテーマ)

## 開発

スキルを使うだけなら不要ですが、開発には pnpm で検査用の道具 (TypeScript・ESLint・Prettier) を入れます。

```sh
pnpm install
pnpm check   # lint・書式・型・テストをまとめて通す
```

Jev や `claude` CLI は、テストでは偽物に差し替わります。実際のキーは不要です。

## ライセンス

MIT (`LICENSE` を参照)。フォントは各フォントのライセンス (Google Fonts の OFL など) に従います。
