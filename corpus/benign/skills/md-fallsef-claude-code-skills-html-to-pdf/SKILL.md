---
name: html-to-pdf
description: HTMLファイルをきれいなPDFに変換。印刷用CSSの最適化、改ページ制御、ChromeヘッドレスモードでのPDF生成。
---

# HTML to PDF 変換スキル

HTMLファイルをきれいなPDFに変換するスキル。

## When to Use

- HTMLをPDFに変換したいとき
- 旅行ガイド、レポート、資料などをPDF化したいとき
- 印刷用にHTMLを最適化したいとき

## 必要な環境

- Google Chrome（ヘッドレスモードでPDF生成に使用）

## Workflow

### 1. 印刷用CSSを追加

HTMLファイルに以下の印刷用CSSを追加：

```css
/* 印刷用 */
@page {
    size: A4;
    margin: 8mm;
}

@media print {
    * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    body {
        background: white;
        margin: 0;
        padding: 0;
    }
    .page {
        box-shadow: none;
        margin: 0;
        padding: 20px;
        border-radius: 0;
        max-width: 100%;
        page-break-after: always;
        overflow: visible;
    }
    .page:last-child {
        page-break-after: auto;
    }
    /* 途中で切れないようにする（小さい要素のみ） */
    .tips-box,
    .card,
    .important-box,
    .highlight-item {
        page-break-inside: avoid;
    }
    /* セクションヘッダーの後で切れないようにする */
    .section-header,
    h2, h3 {
        page-break-after: avoid;
    }
    /* 画像サイズ制限 */
    img {
        max-height: 300px;
        object-fit: contain;
    }
}
```

### 2. 表紙がある場合の追加CSS

表紙（全面色付き）がある場合は、印刷時に明示的にスタイルを上書き：

```css
@media print {
    /* 表紙専用 - 完全リセット */
    .cover {
        margin: 0 !important;
        padding: 30px !important;
        border-radius: 0 !important;
        background: #F97316 !important; /* 実際の色に変更 */
        min-height: auto;
        display: block;
    }
    .cover h1 {
        font-size: 2.2em;
        margin-bottom: 15px;
    }
    .cover img {
        max-width: 500px;
        max-height: 280px;
        margin: 20px auto;
    }
}
```

### 3. ChromeヘッドレスモードでPDF生成

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --headless \
    --print-to-pdf="/path/to/output.pdf" \
    --no-pdf-header-footer \
    --print-background \
    "file:///path/to/input.html"
```

**オプション説明:**
- `--headless`: GUIなしで実行
- `--print-to-pdf`: PDF出力先
- `--no-pdf-header-footer`: URLやページ番号のフッターを消す
- `--print-background`: 背景色も印刷

## Key Points

### 改ページのコツ

1. **page-break-inside: avoid** は小さい要素のみに適用
   - 大きなコンテナに適用すると、ページに収まらなくなる

2. **page-break-after: always** でページ区切り
   - 各セクション（.page）の後に適用

3. **page-break-after: avoid** で見出しの直後で切れるのを防止

### 色の印刷

```css
-webkit-print-color-adjust: exact !important;
print-color-adjust: exact !important;
```
これがないと背景色が印刷されない。

### 表紙の負のマージン問題

通常表示で `margin: -40px` などを使ってる場合、印刷時に `!important` で上書きが必要。

## Examples

```bash
# 基本的な変換
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --headless \
    --print-to-pdf="./output.pdf" \
    --no-pdf-header-footer \
    --print-background \
    "file://$(pwd)/input.html"
```

## Troubleshooting

| 問題 | 解決策 |
|------|--------|
| 背景色が出ない | `--print-background` と `print-color-adjust: exact` を確認 |
| 下にURLが出る | `--no-pdf-header-footer` を追加 |
| 変なところで切れる | `page-break-inside: avoid` を小さい要素のみに適用 |
| 表紙がはみ出す | 印刷用CSSで `margin: 0 !important` を追加 |
