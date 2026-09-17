---
name: ddd-summary
description: "為 Learning Domain-Driven Design 書籍的指定章節製作繁中摘要。觸發條件：用戶要求做 DDD 摘要、讀書筆記、章節翻譯，或說「摘要 Ch5」「幫我讀第六章」「DDD 第七章重點」等。"
---

# DDD 讀書摘要

為 "Learning Domain-Driven Design" 指定章節製作繁體中文摘要，分成 5 份 .md 檔，並推送到 Obsidian vault。

## 書籍目錄

根目錄：`~/Documents/Learning Domain-Driven Design`

### 章節對照表

| PART | 章節 | 主題 |
|------|------|------|
| PART I | Ch1-Ch4 | Strategic Design（業務領域、通用語言、限界上下文、上下文映射） |
| PART II | Ch5-Ch9 | Tactical Design（業務邏輯模式、架構模式、模型翻譯） |
| PART III | Ch10-Ch13 | Applying DDD in Practice（設計啟發、演進設計、EventStorming） |
| PART IV | Ch14-Ch16 | Relationships to Other Methodologies（微服務、事件驅動、Data Mesh） |

### PDF 檔案命名

- Ch1：`PART I/Ch1/ch1.pdf`
- Ch2-Ch16：`PART {X}/Ch{N}/Learning.Domain-Driven.Design.9781098100131.EBooksWorld.ir_part{N}.pdf`
- 注意：PART II 的第 8 章資料夾是大寫 `CH8`（不是 `Ch8`）

## 執行流程

### Step 1：解析用戶輸入

從用戶訊息中提取章節編號。支援格式：
- `Ch5`、`CH5`、`ch5`
- `第5章`、`第五章`
- `Chapter 5`

### Step 2：定位 PDF

根據章節編號對應到 PART 和資料夾：
- Ch1-Ch4 → `PART I/Ch{N}/`
- Ch5-Ch9 → `PART II/Ch{N}/`（Ch8 → `PART II/CH8/`）
- Ch10-Ch13 → `PART III/Ch{N}/`
- Ch14-Ch16 → `PART IV/Ch{N}/`

### Step 3：檢查是否已有摘要

檢查該章節資料夾是否已存在 `Ch{N}-摘要-*.md` 檔案。如果有，告知用戶並詢問是否覆蓋。

### Step 4-6：使用 Claude Code 讀取 PDF、製作摘要、輸出檔案

這一步使用 claude-code skill，透過 `claude` CLI 執行 PDF 讀取與摘要製作。Claude Code 具備原生 PDF 讀取能力，適合處理長篇翻譯與摘要。

在章節資料夾中執行以下指令（workdir 設為章節資料夾路徑）：

```bash
claude -p "請讀取此資料夾中的 PDF 檔案，為這個章節製作繁體中文摘要，並分成 5 份 .md 檔輸出到當前資料夾。

要求：
1. 讀取 PDF 全文，以繁體中文進行翻譯與重點整理
2. 提取核心概念、定義、實際範例
3. 保留重要術語的英文原文（用括號標註，如：限界上下文（Bounded Context））
4. 確保涵蓋章節所有小節，不遺漏
5. 依照章節內容的自然段落或小節，均勻分成 5 份，每份涵蓋約 1/5 的章節內容
6. 在邏輯上是完整的段落（不要在句子中間切割）

每個檔案格式：

# Ch{N} 摘要 - Part {1-5}

> 章節：{章節英文標題}
> 範圍：{本份涵蓋的小節名稱}

## 重點摘要

（正文內容：翻譯 + 重點整理，使用條列式、標題分段，易讀易記）

## 關鍵術語

| 術語 | 英文原文 | 說明 |
|------|---------|------|
| ... | ... | ... |

檔案命名：Ch{N}-摘要-1.md 到 Ch{N}-摘要-5.md
輸出到當前資料夾。" --output-format text
```

將 `{N}` 替換為實際章節編號。確認 claude 執行成功且 5 個 .md 檔案都已產生後再繼續下一步。

### Step 7：推送到 Obsidian

使用 `obsidian-cli create` 將 5 個 .md 檔建立到 Obsidian vault：

```bash
obsidian-cli create "Learning Domain-Driven Design/Ch{N}/Ch{N}-摘要-{i}" \
  --content "$(cat '{章節資料夾路徑}/Ch{N}-摘要-{i}.md')" --overwrite
```

對 5 個檔案各執行一次（i = 1 到 5）。

### Step 8：回報完成

告知用戶：
- 已完成哪一章的摘要
- 5 個檔案的位置
- Obsidian vault 中的筆記路徑
