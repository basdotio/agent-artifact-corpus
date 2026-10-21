# md2docx-historypaper-skill

<p align="center">
  <img src="./assets/readme/hero@2x.png" width="100%" alt="md2docx-historypaper-skill：把 Markdown 论文转成《历史研究》体系投稿级 docx——左侧为 Markdown 源稿，中间朱笔批注列出转换动作，右侧为排版后的论文页（黑体标题、楷体关键词、宋体正文、当页下①脚注）。图中论文与引证为合成样例">
</p>

仓库：https://github.com/Haoo-7/md2docx-historypaper-skill

## 价值

不靠本 skill，Agent 每次都要从零摸索本地 Office 编辑通道的插入语义、脚注编号格式、中西文字体分治和一堆 XML 细节（首次实战约 2.5 小时、踩坑 12 处）。本 skill 把流程、参数、坑位和验证固化为可重复执行的脚本与规范。

最终得到：一份可直接投稿的 docx（黑体三号标题、楷体小四摘要、宋体小四正文、当页下①编号脚注、规范化引证），以及一份"补了哪些页码、改了哪些笔误、还剩哪些缺口"的清单。

<p align="center">
  <img src="./assets/readme/pipeline@2x.png" width="100%" alt="四步流水线：spec.json 经 build_paper.py、postprocess.py 到 verify_docx.py，全部脚本化，失败即报错、可复跑">
</p>

## 安装

方式一（推荐）：把仓库地址发给 Agent——"请帮我安装这个 Skill：`https://github.com/Haoo-7/md2docx-historypaper-skill`"。

方式二（命令行）：

```bash
npx skills add Haoo-7/md2docx-historypaper-skill
```

手动安装：克隆或下载仓库，将目录放到 Agent 的 skills 目录（WorkBuddy 用户级为 `~/.workbuddy/skills/`）。

## 配置

- **editor_sdk 目录**：默认取 WorkBuddy 安装路径；不同安装位置设环境变量 `MD2DOCX_EDSDK_DIR` 指向 edsdk.py 所在目录。
- **格式参数**：默认实现《历史研究》/《史星》体系（见 `references/format-spec.md`）。换目标期刊时，把该刊的格式要求提供给 Agent，按其重设 spec 的 `format` 字段（字体、字号、行距、缩进、页边距）即可，脚本不用改。
- **页码补全源**：Zotero 本机 API 自动探测（`127.0.0.1:23119`），未运行则跳过并要求用户补页，不会阻塞排版。
- 无需密钥、无需初始化配置；除 Zotero 探测外不联网。

## 使用

安装后对 Agent 说自然语言即可触发，例如：

- "把这篇 md 论文按论文格式转成 docx"
- "按《历史研究》的注释规范排版这篇稿子"
- "给这篇论文的注释补页码"

指定其他期刊格式时，提供该刊的格式要求文件（docx/pdf 均可），Agent 会按它重设格式参数。

## 测试与排查

```bash
<python> tests/test_pipeline.py        # 离线回归：后处理正确性/幂等性/孤儿脚注拦截
<python> scripts/verify_docx.py <docx> --spec <spec.json>   # 交付前验证，退出码非 0 即有问题
```

`tests/` 不依赖 editor_sdk 与网络，任何装了 Python ≥3.10 的机器可跑。排查先看 `references/pitfalls.md` 的踩坑记录。

## 依赖、平台与数据边界

- Python ≥ 3.10（仅标准库）。
- 构建通道依赖 WorkBuddy 宿主的 editor_sdk 本地服务；换宿主需替换 `scripts/build_paper.py` 的构建段，格式与后处理逻辑可保留。
- 已在 Windows + Git Bash 实测；macOS/Linux 未实测。
- 无凭据、不联网；只读写用户指定的文件，不在 skill 内保存论文内容或个人路径（样例为合成数据）。

## 适用边界与相邻 Skill

只做"md 论文 → 期刊格式 docx"的格式与引证规范化，不改写学术观点。不用于：编辑现有 docx 的局部内容、docx/PDF 转 md、公文合同等非论文文档的从零撰写、文件整理归档——这些走各自对应的编辑或整理通道。

## 文件说明

| 文件 | 作用 |
|---|---|
| `SKILL.md` | Agent 执行主流程（触发词在工作流的 description 中） |
| `scripts/build_paper.py` | 构建：spec JSON → docx（editor_sdk 通道） |
| `scripts/postprocess.py` | 后处理：脚注编号/字体/斜体等 XML 规范化（幂等） |
| `scripts/verify_docx.py` | 交付前验证（退出码非 0 即有问题） |
| `tests/test_pipeline.py` | 离线回归测试 |
| `references/format-spec.md` | 《历史研究》格式与引证体例参数表 |
| `references/pitfalls.md` | 踩坑记录与验证清单 |
| `references/spec-example.json` | 合成最小 spec 样例 |
| `assets/readme/hero@2x.png`<br>`assets/readme/pipeline@2x.png` | README 实际引用的配图（2 倍图，跨平台渲染一致） |
| `assets/readme/hero.svg`<br>`assets/readme/pipeline.svg` | 上述两图的矢量源文件，改图后需重新导出 |

## 配图重新导出

改过 SVG 后用 Chrome/Edge 无头渲染导出 2 倍图（`--window-size` 与 SVG 的 viewBox 一致）：

```bash
chrome --headless=new --default-background-color=00000000 --force-device-scale-factor=2 --window-size=1200,480 --screenshot=assets/readme/hero@2x.png "file://$PWD/assets/readme/hero.svg"
chrome --headless=new --default-background-color=00000000 --force-device-scale-factor=2 --window-size=1200,320 --screenshot=assets/readme/pipeline@2x.png "file://$PWD/assets/readme/pipeline.svg"
```

`--default-background-color=00000000` 保留圆角外的透明通道，避免深色模式下露出白色方角。

## 许可

MIT，见 [LICENSE](LICENSE)。
