# AGENTS.md

Claude Code スキル `style-guide` の本体。利用者は clone するだけで使い、`node` が `.ts` を直接実行する (型ストリッピング)。
**実行時の依存は持たない。** 開発用の道具だけを devDependencies に入れる。

## コマンド

| コマンド                            | 内容                                            |
| ----------------------------------- | ----------------------------------------------- |
| `pnpm install`                      | 開発用の道具を入れる (スキルを使うだけなら不要) |
| `pnpm lint`                         | ESLint (型情報つき、循環的複雑度の上限 10)      |
| `pnpm format` / `pnpm format:check` | Prettier で整える / 確かめる                    |
| `pnpm typecheck`                    | `tsc --noEmit`                                  |
| `pnpm test:unit`                    | `node --test`                                   |
| `pnpm check`                        | 上の検査をすべて通す。commit 前に必ず実行する   |

## 構成

- `core/`: 明示指定・質問セット・フォント選定・シード化・テーマ生成 (純粋関数)
- `app/`: ローカルの Web アプリ (サーバーと画面)、`claude` CLI の呼び出し
- `scripts/`: CLI (`pipeline.ts`)
- `lib/`: Jev クライアントと読み込み
- `data/` `examples/`: フォントカタログとテスト用の例

## 守ること

- 実行時の依存 (dependencies) を足さない。外部入力の検証は `core/explicit.ts` のように手で書く
- import には拡張子 `.ts` を付け、型だけの import は `import type` にする。`enum` / `namespace` / 引数プロパティは書かない (型ストリッピングで動かないため。tsconfig の `erasableSyntaxOnly` で止まる)
- ルールを緩めて検査を通さない。lint の無効化コメント (`eslint-disable`) や `@ts-ignore` は書かない
- ブランチは `develop` に PR を出す。`main` はルールセットで守られ、`develop` → `main` の PR (`ci-ok` 必須、Squash and merge のみ) でだけ更新する。squash 後は `main` を `develop` にマージして揃える
