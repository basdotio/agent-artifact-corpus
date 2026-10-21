---
name: md2docx-historypaper-skill
description: 把 Markdown 论文转换为按期刊格式规范排版的 docx（《历史研究》/《史星》体系：黑体三号标题、楷体小四摘要、宋体小四正文、脚注当页下①编号每页重排、引证体例规范化）。当用户要求"md 转 docx 论文"、"论文格式规范化/排版"、"按期刊/投稿格式转换"、"补充注释页码"时使用。不用于：编辑现有 docx 的局部内容（走本地 Office 编辑通道）、docx/PDF 转 md、公文合同等非论文文档的从零撰写、文件整理归档。包含 edsdk 构建脚本、XML 后处理脚本、验证脚本、格式规范与踩坑记录。
agent_created: true
---

# md 论文 → 期刊格式 docx

## 用途

把 Obsidian/Markdown 论文转换成符合《历史研究》引文注释规定（=《史星》审稿自检表体系）的投稿级 docx：版面字体、脚注（真页下注、①编号每页重排）、引证体例（卷期页码补全、重复引证简化、外文题名斜体）一次性到位。

## 前置

- 本 skill 的构建通道依赖 WorkBuddy 宿主的 **editor_sdk（edsdk.py）**；换宿主需替换 `scripts/build_paper.py` 的构建段，格式参数、引证规则与后处理逻辑可保留。edsdk 目录默认取 WorkBuddy 安装路径，可用环境变量 `MD2DOCX_EDSDK_DIR` 覆盖。
- 解释器：用任一 Python ≥3.10 运行脚本（脚本内部调用 edsdk 时复用同一解释器）；Git Bash 下 `python3` 可用即可。

## 工作流

### 0. 预检（首次使用必做）

```text
<python> <edsdk-dir>/edsdk.py list
```

能列出工具 = editor_sdk 服务在跑。起不来时先修服务再继续，不要中途失败留半成品。Zotero 本地 API（`http://127.0.0.1:23119`）只在补页码时用，Zotero 没开就降级：把补不到的页码列清单交用户，禁止编造。

### 1. 读取输入，确定格式参数

读源 md 全文。若用户给了格式参考 docx（如期刊自检表），按本地 Office 路由走 edsdk 打开它，用 `doc_get_table_info` / `doc_resolve_document_structure` 提取格式参数（自检表通常是表格，单元格全文在 `cells[].text`）。没有参考文件时，直接用 `references/format-spec.md` 的默认参数表。

### 2. 内容规格化（写 spec JSON）

照 `references/spec-example.json`（合成最小样例，照抄改内容）写一份 spec。字段：`output`（绝对路径，正斜杠）、`format`（格式配置）、`title`、`meta`（摘要/关键词段）、`blocks`（h1/p，段内 `{"t":文本,"fmt":{"bold":true}}` 混排 + `{"fn":编号}` 脚注占位）、`footnotes`（`{"编号":{"text":...,"italics":[...]}}`）。

- **正文清理**：剥 wikilink（`[[X]]`→X）；删从未被引用的孤儿脚注；修笔误（记录清单，最后逐条回报）。
- **脚注编号**：按正文出现顺序重排（md 的 [^n] 序号作废）；spec 的 footnotes 必须与占位符一一对应，不允许孤儿——build 有断言拦截。
- **卷期页码补全**：依次尝试 ① 库内文献笔记 frontmatter ② Zotero 本地 API（key 从笔记 frontmatter 的 zotero-key 取）③ statutes 类去用户原始笔记按锚点块定位页码。
- **斜体登记**：外文文献题名/期刊名作为 `italics` 子串登记。
- 摘要为空：代拟一版（严格据论文自身论点）并在交付说明 flag；无作者信息不编造。

### 3. 构建 docx

```text
<python> <skill-dir>/scripts/build_paper.py <spec.json>
```

自动完成：create_doc → docDefaults（中西文字体/1.5倍行距/缩进2字符/A4）→ 标题（黑体大字居中无缩进）→ 摘要关键词（楷体无缩进）→ 正文段（h1 黑体、p 继承默认）→ 占位符转真脚注 → 页码 → save_file。输出路径取 spec 的 `output`。中途失败时，已建文档在 editor_sdk 的 upload 目录，重跑会 create 新文档，不影响磁盘交付物。

### 4. XML 后处理

```text
<python> <skill-dir>/scripts/postprocess.py <output.docx> <spec.json>
```

修五件工具链做不到的事：脚注①编号+每页重排（sectPr footnotePr）、docDefaults 对齐 end→both、首行缩进 firstLineChars=200（标题按 16pt 精确 2 字符）、正文西文 SimSun→Times New Roman、footnotes.xml 整体重建（separator 条目+id 顺延+宋体小五+题名斜体）。**幂等：重复运行会检测到已处理并跳过重建。原理与避坑先读 `references/pitfalls.md`。**

### 5. 验证

```text
<python> <skill-dir>/scripts/verify_docx.py <output.docx> --spec <spec.json>
```

脚本固化全部可机械判定项（zip、脚注对应、编号格式、docDefaults、字体、斜体数、标题、页码、残留占位符），退出码非 0 即有失败项，逐项修完再交付。editor_sdk 通道的最终确认：全新 `open_file` 一次能解析。

### 6. 交付与回报

`present_files` 交付 docx。回复必须包含：① 格式落实对照表 ② 补全的卷期页码清单（含来源）③ 仍缺页码的脚注清单（交用户补）④ 笔误修改逐条清单 ⑤ 代拟内容/存疑处理（摘要、法条名统一等）的 flag。

## 兼容性

- 实测平台：Windows + Git Bash（editor_sdk 通道本身是 WorkBuddy 宿主组件）；macOS/Linux 未实测。
- 无凭据需求：edsdk 本地服务无鉴权，Zotero API 只读本机。
- frontmatter 的 `agent_created: true` 是 WorkBuddy 宿主 skill 管理系统的要求，与部分公开校验器的字段白名单冲突，属宿主差异而非缺陷。
- 渲染依据为 Word 行为；WPS 对 ①编号+每页重排 的渲染未实测。

## 边界

- 只做格式与引证规范化，不改写学术观点；事实存疑（如影响方向、年代）只 flag 不改。
- 交付后用户可能自行改文档——每轮后续问答先重扒 docx 核对当前状态，勿用交付快照答话。
- 换目标期刊（非《历史研究》体系）时，以用户当次提供的格式文件重写 `references/format-spec.md` 的参数表，spec 的 format 字段随之调整。
