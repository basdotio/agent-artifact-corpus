# 故障排查

按报错/症状索引。先运行 `python scripts/to_docx.py --version`、`pandoc --version` 确认基础环境，再加 `--verbose` 复现查看完整命令。

## 依赖问题

### 未找到 pandoc
脚本会给出安装指引。Windows 推荐任一：
- `winget install JohnMacFarlane.Pandoc`
- 官网 <https://pandoc.org/installing.html> 下载安装包
装完**重开终端**确认 `pandoc --version` 可用（PATH 刷新）。

### ModuleNotFoundError: No module named 'docx'
```bash
pip install python-docx
```

### 未找到 xelatex
PDF 唯一引擎是 XeLaTeX。安装：TeX Live / MiKTeX（建议含中文支持，Windows 可选装 ctex 方案）；装完重开终端确认 `xelatex --version` 可用。

## docx 问题

### Word 打开提示"是否更新此文档中的域"
预期行为：目录页码需 Word 排版后才能计算，点"是"即可。想消除提示：转换时不加 `--toc`；PDF 产物（LaTeX 编译）不存在此提示。

### 标题没有编号
`--number-sections` 依赖 pandoc ≥ 2.10 的 docx 编号实现。先升级 pandoc；仍无效说明 pandoc 版本实现变化，可改在 Word 中为 Heading 样式挂多级列表（一次性操作可接受）。

### 中文加粗仍是伪粗体 / 观感发虚
- 本机未安装思源宋体 Heavy X → 安装字体，或接受回退；
- 文档是从旧模板改的 → 重新从 md 转换，不要往旧 docx 上叠；
- 确认后处理执行了：日志中有"规范化的强调 run N"，N=0 说明文档里没有加粗 CJK 内容或走了 `--no-heavy`。

### 表格无边框 / 全是边框
表格样式由后处理控制：三线表是默认（`--table-style threeline`），全框线用 `--table-style grid`。若手动改过生成器，检查 `style_tables()` 是否被调用。

### 公式显示为原始 LaTeX 文本
数学分隔符必须 pandoc 可识别：行内 `$E=mc^2$`，块级 `$$...$$`。若用了 `\(...\)` 需要输入格式带 `tex_math_single_backslash` 扩展（`--reader markdown+tex_math_single_backslash`）。

### 图片不显示
- 相对路径以 md 文件所在目录为基准；确认文件存在；
- 网络图片需 pandoc 能下载（离线环境先下载到本地再引用）；
- 超大图片检查 `--dpi`（默认 96；提高 dpi 显示尺寸变小，公式：显示宽度 = 像素 ÷ dpi）。

## PDF 问题

### LaTeX 引擎：字体报错（fontspec 找不到字体）
- `SimSun` / `Times New Roman` 是 Windows 自带；Linux/macOS 需自行安装这两个字体，或 `--cjk-font Noto Serif CJK SC --latin-font "TeX Gyre Termes"`；
- Heavy 字体文件路径不对 → `--emph-font-file` 显式指定 `.ttf` 路径；
- 报 `AutoFakeBold` 相关警告无碍，属回退提示。

### LaTeX 引擎：中文断行异常 / 行距过大
行距由 `--line-spacing` 控制（同时影响 docx/PDF）；断行异常多为输入格式问题，确认使用默认 `--reader`。

## HTML 问题

### 打开后样式丢失
HTML 是单文件自包含（CSS 内嵌）；若用第三方工具二次处理过会剥离内嵌样式，请重新转换。

### 中文斜体没有变成楷体
楷体经 `local()` 查找，需要系统装有楷体（Windows 自带 KaiTi）；极简系统可用 `--cjk-font` 一并换字体方案。

## 转换内容问题

### 错误：输出文件被其他程序占用（退出码 3）
产物被 PDF 阅读器、Word、文件管理器预览窗格等占用。关闭占用程序后重试；Windows 下资源管理器预览窗格（Alt+P）也会锁文件。

### 中文硬换行处出现空格
默认 `markdown+east_asian_line_breaks` 已处理；若显式传了别的 reader（如 `--reader gfm`），加回扩展：`--reader gfm+east_asian_line_breaks`。

### 从其他编辑器复制的 md 转换后格式错乱
多半是 markdown 方言差异（表格变体、任务列表等）。先用 `pandoc 输入.md -t native` 查看 pandoc 解析结果定位，再补对应扩展。
