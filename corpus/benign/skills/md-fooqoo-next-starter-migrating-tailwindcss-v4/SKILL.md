---
name: migrating-tailwindcss-v4
description: Tailwind CSS v4 移行ルール。v3からv4への構文変更を自動修正。aria/data属性の短縮形、変数構文、shorthandクラス、important位置、競合クラスの解決パターンを提供。「Tailwind v4 移行」「Tailwind 最新構文」「cssConflict 修正」時に使用。
---

# Tailwind CSS v4 移行ガイド

## ESLint プラグイン設定

`eslint-plugin-better-tailwindcss` を使用してCLIで検出・自動修正する。

```bash
pnpm add -D eslint-plugin-better-tailwindcss
```

```js
// eslint.config.mjs
import betterTailwindcss from 'eslint-plugin-better-tailwindcss';

export default [
  {
    plugins: {
      'better-tailwindcss': betterTailwindcss,
    },
    settings: {
      'better-tailwindcss': {
        entryPoint: 'src/app/globals.css', // Tailwind v4 CSS設定ファイル
      },
    },
    rules: {
      'better-tailwindcss/enforce-consistent-class-order': 'warn',
      'better-tailwindcss/enforce-consistent-important-position': 'warn',
      'better-tailwindcss/enforce-consistent-line-wrapping': 'warn',
      'better-tailwindcss/enforce-consistent-variable-syntax': 'warn',
      'better-tailwindcss/enforce-shorthand-classes': 'warn',
      'better-tailwindcss/no-duplicate-classes': 'warn',
      'better-tailwindcss/no-unnecessary-whitespace': 'warn',
      'better-tailwindcss/no-conflicting-classes': 'error',
      'better-tailwindcss/no-unregistered-classes': 'off', // カスタムテーマ使用時はoff
    },
  },
];
```

自動修正: `npx eslint . --fix`

## 手動修正パターン

ESLint プラグインが未対応のパターンは `sed` で一括置換する。

### ARIA 属性の短縮形

```bash
# aria-[invalid=true] → aria-invalid
find src -name "*.tsx" -exec sed -i '' 's/aria-\[invalid=true\]/aria-invalid/g' {} \;

# aria-[selected=true] → aria-selected
find src -name "*.tsx" -exec sed -i '' 's/aria-\[selected=true\]/aria-selected/g' {} \;

# aria-[current=true] → aria-current
find src -name "*.tsx" -exec sed -i '' 's/aria-\[current=true\]/aria-current/g' {} \;

# aria-[disabled=true] → aria-disabled
find src -name "*.tsx" -exec sed -i '' 's/aria-\[disabled=true\]/aria-disabled/g' {} \;
```

### Data 属性の短縮形

```bash
# data-[x] → data-x (存在チェックのみの場合)
find src -name "*.tsx" -exec sed -i '' 's/data-\[\([a-z-]*\)\]/data-\1/g' {} \;
```

### CSS プロパティからユーティリティへ

```bash
# [grid-template-rows:auto] → grid-rows-[auto]
find src -name "*.tsx" -exec sed -i '' 's/\[grid-template-rows:auto\]/grid-rows-[auto]/g' {} \;
```

### ピクセル値の短縮形

| 旧 | 新 |
|---|---|
| `inset-[1px]` | `inset-px` |
| `inset-[2px]` | `inset-0.5` |
| `gap-[1px]` | `gap-px` |
| `p-[1px]` | `p-px` |

### 分数値の短縮形

| 旧 | 新 |
|---|---|
| `size-[calc(5/6*100%)]` | `size-5/6` |
| `w-[calc(1/2*100%)]` | `w-1/2` |

## 競合クラスの解決

`outline` と `outline-N` を同時に使用すると競合が発生する。

### 問題

```tsx
// NG: outline は style + width を設定、outline-4 は width のみ
className="focus:outline focus:outline-4"
```

### 解決策

```tsx
// OK: outline-solid は style のみ設定
className="focus:outline-solid focus:outline-4"
```

### 一括修正

```bash
find src -name "*.tsx" -exec sed -i '' 's/focus:outline focus:outline-/focus:outline-solid focus:outline-/g' {} \;
find src -name "*.tsx" -exec sed -i '' 's/focus-visible:outline focus-visible:outline-/focus-visible:outline-solid focus-visible:outline-/g' {} \;
find src -name "*.tsx" -exec sed -i '' 's/hover:outline hover:outline-/hover:outline-solid hover:outline-/g' {} \;
find src -name "*.tsx" -exec sed -i '' 's/outline outline-\([0-9]\)/outline-solid outline-\1/g' {} \;
```

## v4 新構文まとめ

| カテゴリ | 旧 (v3) | 新 (v4) |
|---------|---------|---------|
| 変数 | `size-[var(--x)]` | `size-(--x)` |
| Shorthand | `flex-shrink-0` | `shrink-0` |
| Shorthand | `flex-grow` | `grow` |
| Important | `!outline-black` | `outline-black!` |
| ARIA | `aria-[invalid=true]` | `aria-invalid` |
| Data | `data-[loading]` | `data-loading` |
| Outline | `outline outline-4` | `outline-solid outline-4` |
| Pixel | `inset-[1px]` | `inset-px` |
| height | `h-[1000px]` | `h-125` |
| width | `w-[1000px]` | `w-125` |
