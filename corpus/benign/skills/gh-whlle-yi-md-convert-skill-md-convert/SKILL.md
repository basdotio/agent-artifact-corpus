---
name: md-convert
description: 高质量把 Markdown 转换为 Word、PDF、HTML。用户要求"md 转 word/pdf/html"、"导出成 Word/PDF"、"生成可提交的正式文档/论文"，或任何以 .md 为源转成常见文档格式的场景都使用。中文排版规范：宋体 + Times New Roman、Heavy 强调无伪粗体、三线表、原生公式。
---

# md-convert — Markdown 高质量转换

把 Markdown 转成**排版达到交付标准**的 Word / PDF / HTML。电子表格 → xlsx 技能；演示文稿 → pptx 技能；读取 Office 内容 → anydoc-convert 技能。

按以下五步执行转换。**标注「先读」的 references 文件是进入对应步骤的准入条件——未读取就继续，视为未按规程执行**：

## ① 源处理与预检

只做一次，与产出几种格式无关。读一遍 Markdown，检查图片相对路径、公式 `$`/`$$` 成对、YAML 头完整；发现硬伤先与用户确认再转。

## ② 确认产出组合与场景

按顺序判断，本步结束时必须明确两件事：**产出格式集合（≥1 项）** 与 **是否学术论文场景**，供 ③④ 使用。

1. **场景判断（开放清单，随需求增长）**：
   - 命中 **学术论文场景**（期刊 / 学位 / 竞赛 / 技术报告）→ 产出定为 **仅 PDF（XeLaTeX）**；其专属规则在 `references/scenario-academic.md`，于 ③ 执行该格式时读取；
   - 未命中任何场景 → 走下方通用流程。新场景出现时：新建 `references/scenario-*.md` 并在此清单登记。
2. **非论文，用户已指明格式** → 按用户指定的执行，不追问；
3. **非论文，格式未指明** → 询问一次（PDF / Word / HTML / 多种组合），**推荐 PDF**；用户此前明确表示不想被问 → 跳过询问，直接 PDF，交付时说明可补产其他格式。

禁令：论文场景不得产出 Word；未经用户点名，不得产出任何未要求的格式。

## ③ 组装命令并执行

按格式运行对应脚本（在技能目录内执行）：

- docx → `scripts/to_docx.py`
- pdf → `scripts/to_pdf.py`（XeLaTeX 引擎）；**论文场景：先读 `references/scenario-academic.md`** 按其规则执行
- html → `scripts/to_html.py`

命令形态与全部参数：见 `references/params.md`（调整排版前先读）。

## ④ 验收与交付

对照下方清单逐项检查每种产物；失败 → 查 `references/troubleshooting.md` 定位重转（同一问题最多两次）；通过后报告产物路径与大小、需要用户动作的点。

## 转换后验收清单

1. **产物组合与 ② 的确认一致**：未要求的格式未产出；论文场景不得出现 Word 产物。
2. **文件能正常打开**，大小合理（>5KB 说明非空）。
3. **公式**：docx 中是可编辑的 Word 公式（OMML）；PDF 中公式无缺字。
4. **表格**：三线表边框正确（顶/底粗线、表头下细线、无竖线），表内文字单倍行距。
5. **目录**（若有）：Word 打开时点一次"更新域"后页码正确；PDF 目录页码由 LaTeX 编译生成。
6. **字体**：中文无豆腐块；强调是 Heavy 字重而非拉伸加粗。
7. **图片**：显示且未变形。

## 文件路由

| 何时读 | 文件 |
|---|---|
| 调排版参数 / 查默认值 | `references/params.md` |
| 学术论文场景 | `references/scenario-academic.md` |
| 转换报错 / 产物异常 | `references/troubleshooting.md` |
| 深度样式定制（固化模板） | `references/styles.md` |
