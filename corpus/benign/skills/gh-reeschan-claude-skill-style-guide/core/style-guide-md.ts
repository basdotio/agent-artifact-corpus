// シード結果とテーマから、人が読むスタイルガイド (Markdown) を作る。決定的 (日時を入れない)
import type { FontPair, SeedResult } from "./types.ts";
import { resolveTheme } from "./generate-theme.ts";

type Theme = ReturnType<typeof resolveTheme>;
type Mode = "light" | "dark";

const MODE_LABEL: Record<Mode, string> = { light: "ライト", dark: "ダーク" };
const SHADOW_LABEL: Record<string, string> = { none: "なし", soft: "やわらかい影", hard: "くっきりした影" };
const SOURCE_LABEL: Record<string, string> = { explicit: "指定", jev: "Jev", "llm-fallback": "LLM" };

const cell = (v: unknown): string => String(v).replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
const row = (...cols: unknown[]): string => `| ${cols.map(cell).join(" | ")} |`;
const table = (head: string[], rows: unknown[][]): string[] => [
  row(...head),
  `|${head.map(() => "---").join("|")}|`,
  ...rows.map((r) => row(...r)),
];

export function renderStyleGuideMd(args: { seedResult: SeedResult; theme: Theme; fontPair: FontPair | null; fontsUrl: string }): string {
  const { seedResult, theme, fontPair, fontsUrl } = args;
  const seed = seedResult.seed;
  const other: Mode = seed.baseMode === "light" ? "dark" : "light";
  const out: string[] = [];

  // 1. 見出し
  out.push(`# ${seed.name} スタイルガイド`, seed.tone, "");

  // 2. 基本
  out.push("## 基本", "");
  out.push(
    ...table(
      ["項目", "値"],
      [
        ["テーマ ID", `\`${seed.id}\``],
        ["基調", MODE_LABEL[seed.baseMode]],
        ["角丸", `${seed.shape.radiusPx}px`],
        ["余白の倍率", seed.shape.spacingScale],
        ["影", SHADOW_LABEL[seed.shape.shadow] ?? seed.shape.shadow],
        ["ブランドの色相", seed.color.brandHue],
        ["アクセントの色相", seed.color.accentHue === null ? "なし" : seed.color.accentHue],
      ],
    ),
    "",
  );

  // 3. フォント
  out.push("## フォント", "");
  out.push(
    ...table(
      ["役割", "フォント"],
      [
        ["見出し", seed.font.heading],
        ["本文", seed.font.body],
        ["等幅", seed.font.mono],
      ],
    ),
    "",
  );
  out.push(
    "```html",
    `<link rel="preconnect" href="https://fonts.googleapis.com">`,
    `<link rel="stylesheet" href="${fontsUrl}">`,
    "```",
    "",
  );
  if (fontPair) out.push(`> ${fontPair.description.replace(/\r?\n/g, " ")}`, "");

  // 4. 色トークン
  out.push("## 色トークン", "");
  const light = theme.modes.light.tokens;
  const dark = theme.modes.dark.tokens;
  out.push(
    ...table(
      ["トークン", "ライト", "ダーク"],
      Object.keys(light).map((k) => [k, light[k], dark[k] ?? ""]),
    ),
    "",
  );

  // 5. コントラスト
  out.push("## コントラスト", "");
  for (const mode of ["light", "dark"] as Mode[]) {
    out.push(`### ${MODE_LABEL[mode]}`, "");
    out.push(
      ...table(
        ["文字", "背景", "比", "基準", "結果"],
        theme.modes[mode].checks.map((c) => [c.fg, c.bg, c.ratio, c.min, !c.pass ? "FAIL" : c.adjusted ? "pass (補正)" : "pass"]),
      ),
      "",
    );
  }

  // 6. 使い方
  out.push("## 使い方", "");
  out.push(
    `- \`theme.css\` を読み込む (Tailwind v4 の \`@import "tailwindcss"\` を含む)`,
    `- ルート要素に \`data-theme="${seed.id}"\` を付ける`,
    `- ${MODE_LABEL[other]}で表示するときは \`data-mode="${other}"\` を足す`,
    `- Tailwind のユーティリティ例: \`bg-primary text-primary-foreground\`, \`rounded-md\`, \`shadow-md\`, \`font-heading\``,
    "",
  );

  // 7. 推定の出どころ
  out.push("## 推定の出どころ", "");
  out.push(
    ...table(
      ["項目", "出どころ"],
      Object.entries(seedResult.sources).map(([k, v]) => [k, SOURCE_LABEL[v] ?? v]),
    ),
    "",
  );

  // 8. 別案
  out.push("## 別案", "");
  if (seedResult.alternatives.length === 0) out.push("なし");
  else {
    out.push(
      ...table(
        ["項目", "値", "確率 (%)"],
        seedResult.alternatives.map((a) => [a.field, a.value, Math.round(a.probability * 100)]),
      ),
    );
  }

  return out.join("\n") + "\n";
}
