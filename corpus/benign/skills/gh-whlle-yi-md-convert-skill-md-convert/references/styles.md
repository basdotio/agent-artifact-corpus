# 样式体系详解

本文档说明 md-convert 的样式实现机制与全部定制手段。日常调参数看 `SKILL.md` 的"排版规范"表即可，本文是深入理解和二次定制的参考。

## 样式链路

```text
demo.md ──pandoc──► docx（引用 reference.docx 的样式）──python-docx 后处理──► 成品
                          │
                          ├─ 由 make_reference_docx.py 程序化生成（每次转换自动重建）
                          └─ 也可手动微调后固定使用（见下文"固定 reference.docx"）
```

pandoc 的 docx 写入器**不自带排版**，一切外观都取自 `--reference-doc` 里的样式。因此样式质量取决于两处：

1. **reference.docx 生成器**（`scripts/make_reference_docx.py`）——控制字体、字号、行距、缩进、颜色；
2. **后处理**（`scripts/docx_lib.py`）——控制 pandoc 样式体系做不到的事：中西文分别加粗、三线表边框、目录域自动刷新。

## pandoc 样式名对照

生成器只改写下列样式，其余保持 pandoc 默认。**这些名字是 pandoc 的契约，改名会导致对应元素回退默认外观。**

| pandoc 样式名 | 用途 | 本项目的处理 |
|---|---|---|
| `Normal` | 全局基准 | 宋体 + Times New Roman，12pt，1.5 倍行距，黑色 |
| `Body Text` / `First Paragraph` | 正文段落 | 首行缩进 2 字符（`w:firstLineChars=200`） |
| `Compact` | 列表项、表格单元格 | 行距恢复 1.0，避免表格虚高 |
| `Heading 1`–`Heading 4` | 标题 | 16/14/13/12pt，Heavy 中文字体，黑色，与下段同页 |
| `Title` / `Author` / `Date` | YAML 元数据区 | 居中，Title 22pt Heavy |
| `Strong` | `**加粗**` | 西文 Times New Roman Bold；中文由后处理拆分 |
| `Emphasis` | `*斜体*` | 西文斜体；中文在 HTML/PDF 中映射楷体 |
| `Source Code` / `Verbatim Char` | 代码块 / 行内代码 | Consolas，10pt，浅灰底纹；语法高亮默认关闭（`--highlight` 开启），保持黑白正式文档风格 |
| `Block Text` | 引用块 | 左缩进 0.75cm，取消斜体 |
| `Table Caption` / `Image Caption` | 题注 | 居中，10.5pt Heavy |
| `Footnote Text` | 脚注 | 9pt |
| `Table` | 表格边框样式 | 边框由后处理按三线表/全框线重设 |

## "中文加粗无伪粗体"的实现

宋体没有粗体字形，Word 对加粗的宋体做**算法加粗（伪粗体）**，笔画生硬。本项目要求中文强调使用 Heavy 字重的宋体（思源宋体 Heavy），且**不得再叠加伪粗体**：

1. `Strong` 样式保留 `w:b`（供西文使用），eastAsia 指向 Heavy 字体；
2. 后处理 `fix_cjk_bold()` 扫描所有 run：
   - 判定"实际加粗"（直接 `w:b` > `rStyle=Strong` > 段落样式属于标题族）；
   - 按 CJK / 非 CJK 把 run 文本**拆成多段**；
   - 中文段：eastAsia 设为 Heavy 字体，并**显式写入 `w:b w:val="0"`**（run 级关闭会覆盖样式级加粗，这是关键——删除 `w:b` 反而会继承样式的加粗）；
   - 西文段：保持原样，由 `Strong` 样式提供 Times New Roman Bold。
3. 表头加粗发生在 `fix_cjk_bold()` 之前，因此表头中文同样被规范化。

同一段中英文混排（如 **本系统采用 Transformer 架构**）会被拆成"中文 Heavy + 西文 TNR Bold"交替的多个 run，这正是 Word 手工排版的做法。

## Heavy 字体说明

- 字体族名：`Noto Serif SC Heavy X`（本仓库默认），文件默认从 `%USERPROFILE%\.zcode\fonts\NotoSerifSC-HeavyX.ttf` 自动探测（仅影响 XeLaTeX 路径；docx 只引用族名）。
- 读者机器上没有该字体时：docx 中该字体名回退为 Word 默认中文字体（观感降级但可读）；HTML 中经 `local()` 回退链自动降级为宋体伪粗体；LaTeX 中经 `\IfFontExistsTF` 回退。
- 发布给"不装字体也要最好效果"的读者：PDF 由 LaTeX 编译、字体天然嵌入，是最佳分发格式。
- 完全不同的字体需求：`--heading-cjk-font <族名>` 全局替换；或 `--no-heavy` 退回宋体伪粗体。

## 固定 reference.docx（高级）

需要页眉页脚、封面、页码样式等生成器不覆盖的元素时：

```bash
# 1. 生成基线
python scripts/make_reference_docx.py -o my-ref.docx
# 2. 在 Word 中打开 my-ref.docx 修改样式/页面/页眉页脚后保存
# 3. 直接用于转换（绕过生成器）
pandoc 文档.md --reference-doc my-ref.docx -o 文档.docx
```

注意：手动微调的成果**不会**被转换流程使用（reference.docx 每次转换重新生成）。要让定制进入日常管线，需把改动固化回 `make_reference_docx.py` 并提交 PR；`my-ref.docx` 方式适合一次性任务。

## XeLaTeX 路径的字体

`to_pdf.py` 的 XeLaTeX 引擎动态生成导言（等价于 `assets/latex-header.tex`）：

- `\setmainfont{Times New Roman}`；`\setCJKmainfont{SimSun}[AutoFakeBold=2.5]`
- 检测到 Heavy 字体文件时，用 `Path=` 精确加载并把 `BoldFont` 指向 Heavy 文件 → `\textbf{中文}` 直接得到 Heavy 字重，无伪粗体；
- 定义 `\key{...}`（Heavy + bfseries）供强调使用；
- 链接用 `-V colorlinks=true -V linkcolor=black ...`：黑色文字链接，无彩色也无超链接框。

数学字体保持 LaTeX 默认（Computer Modern）；如需 STIX/新罗马数学字体，在自定义导言中加 `unicode-math` 并 `\setmathfont{...}`。
