# 排版参数速查

深度定制（固定 reference.docx、样式机制）见 `styles.md`；转换故障见 `troubleshooting.md`。

## 命令形态

在技能目录内执行，按产出格式选择脚本：

    python scripts/to_docx.py 文档.md -o 输出.docx [参数]
    python scripts/to_pdf.py  文档.md -o 输出.pdf  [参数]
    python scripts/to_html.py 文档.md -o 输出.html [参数]

- 未指定 `-o` 时与输入同目录同名输出；`-o` 为目录时按脚本默认后缀落盘
- 多种格式 = 依次运行对应脚本

## PDF（to_pdf.py 专属）

- 唯一引擎为 **XeLaTeX**（需要 TeX Live / MiKTeX，建议含中文支持），输出跨机器一致
- 排版与 docx 规范一致：宋体 + Times New Roman、Heavy 强调（`\key`）、A4、首行缩进 2 字符
- 引擎不可用：见 `troubleshooting.md`
- 学术论文场景（编号、文献、摘要）见 `scenario-academic.md`

## 默认值与覆盖参数

| 项目 | 默认 | 覆盖参数 |
|---|---|---|
| 中文正文 | 宋体 SimSun | `--cjk-font` |
| 西文/数字 | Times New Roman | `--latin-font` |
| 标题/加粗中文 | 思源宋体 Heavy X，**不伪粗** | `--heading-cjk-font` / `--no-heavy` |
| 中文斜体（HTML/PDF） | 楷体，禁用合成斜体 | — |
| 代码 | Consolas + 浅灰底纹，语法高亮默认关 | `--mono-font`；`--highlight` 开启 |
| 正文 | 12pt（小四）、1.5 倍行距、首行缩进 2 字符 | `--font-size` `--line-spacing` `--no-body-indent` |
| 表格 | 三线表；表内文字单倍行距 | `--table-style grid` 换全框线 |
| 目录 | 默认无 | `--toc --toc-depth 3` |
| 页面 | A4，上下 2.54cm、左右 3.17cm | — |
| 图片分辨率 | 96 dpi | `--dpi` |
| 输入格式 | `markdown+east_asian_line_breaks`（中文硬换行不产生多余空格） | `--reader gfm`（严格 GFM 源） |
| 参考文献 | 默认关闭 | `--citeproc` + `--bibliography 文献.bib`（BibTeX / BibLaTeX / CSL JSON / YAML）；`--csl` 指定样式；引用键写 `[@id]` |

## 常用组合

```bash
# 标准交付（默认即规范值）
to_docx.py 文档.md

# 学术论文（编号 + 文献）
to_pdf.py 论文.md --number-sections --citeproc --bibliography refs.bib

# 紧凑报告
to_docx.py 报告.md && to_pdf.py 报告.md
```

## 注意

- `--font-size` 同步影响标题字号（正文 +4 / +2 / +1 / 0 pt 阶梯）。
- `--dpi` 影响位图显示尺寸（显示宽度 = 像素 ÷ dpi）。
- 字体名须与系统已安装字体精确匹配，缺失时回退（见 `troubleshooting.md`）。
