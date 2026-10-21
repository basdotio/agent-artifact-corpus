<p align="center"><b>中文</b> | <a href="README_en.md">English</a></p>

# Buffett & Munger Evidence Skill v0.3.1

一个 Claude Code / Claude Agent Skill：以巴菲特和芒格的**一手资料**（股东信、年会问答、演讲、访谈）为证据，按两人的思考顺序回答投资、商业与人生问题——先判断他们会不会接这个问题，再按他们的过滤标准给出“可以 / 不行 / 太难”的结论，最后附可核查的原文出处。

> A Claude skill that answers questions the way Warren Buffett and Charlie Munger would reason about them, grounded in a local, provenance-tracked corpus of their own letters, meeting transcripts, speeches and interviews. Every attributed claim must trace back to an opened source passage. Answers default to Chinese.

**这是基于本地资料库的检索增强问答，不是模型蒸馏，也不代表两人本人。** 未检索到不等于没说过；所有推演都会标明。

## 它做什么

- **两层回答**：先给人物回答（巴菲特讲结论、决定因素和一个真实案例；芒格先一句尖锐判断，再按问题需要用多个跨学科思维模型交叉检验，投资问题还会和手里最好的机会比），再给依据层（完整原句引文 + 中文译意 + 出处链接 + 适用性说明）。
- **证据纪律**：只引用实际打开并核对过的完整句子；区分本人原作、发布者文字稿、第三方笔记、传记与译本；区分材料年份与发表日期；芒格去世（2023-11-28）后的事件不替他表态。
- **本地混合检索**：SQLite FTS5/BM25 + 本地 ONNX 多语言 E5 语义检索 + cross-encoder 重排，全部离线运行，原文不发送给外部服务。
- **配套工具**：年会问答单元检索（`qa.py`）、有出处的主题/案例 Wiki（`wiki.py`）、完整句子取句（`quote.py`）、发言人归属审核（`attribution.py`）、盲测评估（`evaluate.py`），以及从伯克希尔官网、CNBC 巴菲特档案等公开来源采集资料的脚本。

## 不包含什么

本仓库**不附带任何原文、电子书、视频或索引**。资料库在 skill 目录之外，由你在本机用采集脚本从公开来源自行建立；受版权保护的书籍只能由你用合法持有的副本自行导入，且不应再分发。

## 版本

当前版本 **v0.3.1**（预览版：从零安装只能自动采集部分资料，见“首次建库”）。名称和地址固定不变，版本号写在 `SKILL.md` 的 `metadata.version` 和 [Releases](https://github.com/muhaibao/buffett-munger-evidence-skill/releases) 里；本地安装的版本与最新 Release 相同即为同一版。

## 安装

```sh
git clone https://github.com/muhaibao/buffett-munger-evidence-skill ~/.claude/skills/buffett-munger-evidence
```

**交给 AI 代理安装**：把仓库地址交给代理，让它按 [INSTALL.md](INSTALL.md) 执行。那里有可直接复制的命令、实测耗时和需要向你汇报的内容，全程无需人工。

## 首次建库

```sh
SKILL=~/.claude/skills/buffett-munger-evidence
DATA=~/buffett-munger-data
PY="$DATA/runtime/bin/python"

# 独立 Python 环境（需要 uv）
uv venv --python 3.12 "$DATA/runtime"
uv pip install --python "$PY" -r "$SKILL/scripts/requirements-retrieval.txt" pypdf lxml brotli

# 采集全部公开资料、合并、下载模型、建语义索引和问答单元（可续跑）
"$PY" "$SKILL/scripts/bootstrap.py" --data "$DATA"
```

`bootstrap.py` 按固定顺序运行全部自动采集器（伯克希尔官网股东信、西科信、年报和季报，CNBC 1994–2024 年会文字稿，Stripe 版《穷查理宝典》），合并暂存批次，下载并校验模型，建语义索引和问答单元，最后分别用巴菲特和芒格各一条混合检索做冒烟测试，并输出 JSON 报告（同时保存为 `$DATA/bootstrap-report.json`）。实测约 80 分钟，另加约 270 MB 模型下载。中断或失败后重跑同一条命令即可续跑，已完成的采集不会重做。分步说明和手动命令见 [references/local-library.md](references/local-library.md)、[references/collection.md](references/collection.md) 和 [references/retrieval.md](references/retrieval.md)。

然后在 Claude Code 里提问，例如“巴菲特会怎么看一家技术变化很快的消费电子公司？”或用 `/buffett-munger-evidence` 调用。

### 已知限制（2026-10-16 在空目录实测）

在一台 Apple M5 Pro 上从空目录运行 `bootstrap.py`，结果如下（分步耗时见 [INSTALL.md](INSTALL.md)）：

- **新库内容**：279 份文档、86,096 段。伯克希尔股东信 48 封（1977–2024）、西科信 13 封（1997–2009）、年报 31 份（1995–2025）、季报 92 份（1996–2026）、CNBC 年会文字稿 62 场（1994–2024）、Stripe 版《穷查理宝典》33 份（11 篇演讲主体，另有后加回顾、独立问答和编者材料）。带发言人标签的段落中，巴菲特 38,617 段、芒格 7,616 段；年报季报、提问者和编者材料不归给任何人。
- **芒格部分明显偏薄**：访谈、Daily Journal 股东会、西科年会笔记、1983–1996 年西科信、合伙企业信、早期年报 OCR、Worldly 档案的芒格文章等没有采集脚本，新库里没有。维护者用的库包含这些人工整理的批次，所以比新库厚。
- **来源缺口**：首次运行有两处临时下载失败（2020 年报 PDF 损坏、2015 年一季报连接中断）。原样重跑后两处都补齐，缺口为 0，且只新增了 1 份文档，已入库的 217 份没有重复导入。补进新文档会让语义索引整体重建（实测约 16 分钟）。
- **归属表**：`assets/attribution_map.json` 只保留 3 份可按网址原样取得的芒格文档，用 `library.py fetch` 按表中 `url` 导入后才生效。采集器建的库里两人的段落已逐段标注，`attribution.py propose` 找不到需要补充的文档，`--attribution author` 的结果与 `strict` 相同。
- **主题 / 案例 Wiki 不随仓库发布**：`wiki.py check` 校验的元数据哈希包含采集时间和本机路径，别人新建的库永远对不上。实测把维护者的 25 页对新库检查：118 条证据中有 103 条在新库里段落、正文、原件和发言人完全一致，但元数据哈希全部不符；另 15 条来自没有采集脚本的资料。因此新库的 Wiki 为空，回答协议中的 Wiki 检索一步没有结果。
- **段落 ID 随 pypdf 版本变化**：同一份 PDF 用 pypdf 6.21 和 6.10 提取，有时切分不同。实测 61 封信中 25 封的段落 ID 不同，其中 22 封正文相同、只是切分不同。不同时间安装的库，chunk ID 不能互换；引用以网址、原件 SHA 和定位为准。
- **网络**：模型从 huggingface.co 下载，约 270 MB，不支持断点续传。实测时网络一度降到约 30 KB/s，模型下载会成为最慢的一步。
- **平台**：只在 Apple Silicon macOS 上实测；重排模型是 arm64 优化的量化版本，其他平台未实测。

## 测试

```sh
cd ~/.claude/skills/buffett-munger-evidence/scripts
"$PY" -m unittest discover -p 'test_*.py'
```

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 技能入口：回答协议、输出格式、证据底线 |
| `INSTALL.md` | 给 AI 代理的无人值守安装步骤与汇报模板 |
| `references/` | 思考顺序（`cognition.md`）、证据规则、检索、采集、Wiki、评估、来源地图 |
| `scripts/` | 一键建库（`bootstrap.py`），资料库、检索、问答、Wiki、取句、归属、评估与采集脚本及测试 |
| `assets/` | 已核验的来源入口、人工审核的归属表、演讲章节链接记录 |

## 声明

与伯克希尔·哈撒韦公司、巴菲特、芒格及其家族或代理人没有任何关联，也未获其认可。输出不构成投资建议。引用的原文版权归各自权利人所有。

## 许可

代码与文档以 [MIT License](LICENSE) 发布。
