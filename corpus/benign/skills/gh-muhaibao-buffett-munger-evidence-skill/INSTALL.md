# 代理安装指南

> For AI agents: follow these steps verbatim to install the skill and build its local library without human help. Every command is copy-paste ready; report back using the template at the end.

本文件写给拿到仓库地址、要独立完成安装的 AI 代理。按顺序执行，命令可以直接复制。整个过程只写入两个目录：skill 目录和自选的数据根目录 `DATA`。

## 0. 前提

- macOS 或 Linux（`bootstrap.py` 用 `fcntl` 文件锁）；`git`（或 `curl`）、[uv](https://docs.astral.sh/uv/)。
- 能访问：`github.com`、`www.berkshirehathaway.com`、`buffett.cnbc.com`、`www.stripe.press`、`huggingface.co`（模型约 270 MB）。
- 磁盘：约 1 GB（资料库与索引约 0.6 GB，含模型；暂存约 0.15 GB；Python 环境约 0.15 GB）。
- 时间：首次约 80 分钟，另加模型下载（约 270 MB，取决于网络）；大部分时间花在采集和解析 PDF。见第 5 节分步耗时。

## 1. 安装 skill

```sh
git clone https://github.com/muhaibao/buffett-munger-evidence-skill ~/.claude/skills/buffett-munger-evidence
```

目录名必须是 `buffett-munger-evidence`。已经装过就 `git -C ~/.claude/skills/buffett-munger-evidence pull`。没有可用的 `git` 时，下载 main 分支的压缩包：

```sh
mkdir -p ~/.claude/skills/buffett-munger-evidence
curl -L https://github.com/muhaibao/buffett-munger-evidence-skill/archive/refs/heads/main.tar.gz \
  | tar -xz --strip-components=1 -C ~/.claude/skills/buffett-munger-evidence
```

## 2. 准备 Python 环境

```sh
SKILL=~/.claude/skills/buffett-munger-evidence
DATA=~/buffett-munger-data
PY="$DATA/runtime/bin/python"
uv venv --python 3.12 "$DATA/runtime"
uv pip install --python "$PY" -r "$SKILL/scripts/requirements-retrieval.txt" pypdf lxml brotli
```

不要改系统 Python。`DATA` 可以换成别的路径，但之后所有命令要用同一个；skill 回答问题时默认用 `$DATA/runtime/bin/python` 和 `$DATA/buffett-munger-library`。

## 3. 建库（一条命令，可续跑）

运行时间远超一般命令超时，放到后台：

```sh
nohup "$PY" "$SKILL/scripts/bootstrap.py" --data "$DATA" > "$DATA/bootstrap.log" 2>&1 &
```

它依次做：检查依赖 → `library.py init` → 伯克希尔官网股东信、西科信、年报（`collect.py`）→ 年报与季报（`collect_financials.py`）→ CNBC 1994–2024 年会文字稿（`collect_meetings.py`）→ Stripe 版《穷查理宝典》十一篇演讲（`collect_speeches.py`，自动复制 `assets/chapter-links.json`）→ `merge_staged.py` → 下载并校验模型 → `retrieve.py build` → `qa.py build` → 两条混合检索冒烟测试（巴菲特、芒格各一条）。

查看进度：

```sh
grep '^\[bootstrap\]' "$DATA/bootstrap.log" | tail -n 5
```

每步的详细输出在 `$DATA/staging/bootstrap/logs/<步骤>.log`。最终报告写到 `$DATA/bootstrap-report.json`（也打印在 `bootstrap.log` 末尾），出现 `[bootstrap] done:` 一行即结束。退出码 0 表示可用。

**中断或失败后，原样再运行同一条命令。** 已完成的采集步骤会跳过，失败或部分失败的会重试；采集器、合并和索引构建本身都是增量的，不会重复入库。同一个 `DATA` 同时只能跑一个 bootstrap，第二个会直接拒绝。如果库目录被删除，下次运行会重新采集全部来源。

## 4. 核对

```sh
LIB="$DATA/buffett-munger-library"
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" status
"$PY" "$SKILL/scripts/qa.py" --library "$LIB" status
cd "$SKILL/scripts" && "$PY" -m unittest discover -p 'test_*.py'
```

前两条都应返回 `"ready": true`（`qa.py` 还应有 `"semantic": true`）；测试全部离线运行。

## 5. 预期结果（维护者 2026-10-16 在空目录实测）

测试机：Apple M5 Pro（18 核）、64 GB 内存、macOS 27，uv 安装的 CPython 3.12，pypdf 6.21.0；默认参数（`--workers 3 --threads 4`）。

| 步骤 | 实测耗时 | 结果 |
|---|---|---|
| 伯克希尔股东信（`collect.py --kind buffett-letters`） | 8 分钟 | 48 封，1977–2024 |
| 西科信（`collect.py --kind wesco-letters`） | 1 分钟 | 13 封，1997–2009 |
| 年报 PDF（`collect.py --kind reports`） | 23 分钟 | 2009–2025 年 17 份中取得 16 份；2020 年 PDF 下载损坏，同一文件已由下一步取得 |
| 年报与季报（`collect_financials.py`） | 11 分钟 | 暂存 106 份（1995–2008 年报、1996–2026 季报及 2020 年报），16 份已在库内跳过；2015 年一季报连接中断 |
| CNBC 年会文字稿（`collect_meetings.py`，1994–2024） | 15 分钟 | 62 场，无缺口 |
| Stripe 版《穷查理宝典》（`collect_speeches.py`） | 不到 1 分钟 | 33 份：11 篇演讲主体，另有后加回顾、独立问答和编者材料 |
| 合并（`merge_staged.py`） | 1 分钟 | 201 份入库，0 失败 |
| 模型（`setup_retrieval.py`） | 取决于网络 | 两个模型约 270 MB，按固定 SHA256 校验；中断后重跑会重新下载未完成的文件 |
| 语义索引（`retrieve.py build`） | 16 分钟 | 85,686 段 |
| 问答单元（`qa.py build`） | 1 分钟 | 2,475 个 |
| 冒烟测试 | 10 秒 | 巴菲特、芒格各一条，均为 `hybrid` + `reranked` |

第一次运行结束时库里有 278 份文档、85,686 段：巴菲特带标签的段落 38,617 段，芒格 7,616 段，其余是年报季报、提问者、主持人和编者材料，不归给任何人。实测时网络一度降到约 30 KB/s，模型改用了 SHA256 相同的本地副本，所以上表不含模型下载时间。

第一次运行的报告 `ok` 为 false：两处临时下载失败（2020 年报 PDF 损坏、2015 年一季报连接中断），另有一条模型步骤失败，是测试时手动中断了过慢的下载。原样重跑同一条命令用了 19 分钟：已完成的四个采集器直接跳过，补进 2015 年一季报，2020 年报已由季报采集器取得；合并只新增 1 份，其余 217 份未改动；语义索引因语料变化整体重建（16 分钟）。最终报告 `ok: true`，0 失败、0 缺口：279 份文档、86,096 段（巴菲特 38,617 段、芒格 7,616 段），季报 92 份，问答单元 2,475 个。在已完成的库上再跑一次只需约 10 秒，什么都不改变。

报告里的 `source_gaps` 是采集器发现但没取到的条目，`filled_gaps` 是一个采集器没取到、另一个采集器已经取到的条目（例如 2020 年报），后者不算缺口。`attribution_map.matching_documents` 为 0 是正常的，见 README“已知限制”。

## 6. 向用户汇报

从 `$DATA/bootstrap-report.json` 取值，照实填写，不要省略失败和缺口：

```text
Buffett & Munger Evidence Skill <skill_version> 安装结果：<ok 为 true 写“可用”，否则写“未完成”>
- 资料库：<library>，<documents> 份文档，<chunks> 段；巴菲特 <chunks_by_speaker.Warren Buffett> 段，芒格 <chunks_by_speaker.Charlie Munger> 段
- 按系列：<documents_by_series 逐项>
- 语义索引：<semantic_index.ready>；问答单元：<qa_units.units> 个
- 冒烟测试：巴菲特 <smoke_test.Warren Buffett.mode_used>/<reranked>，芒格 <smoke_test.Charlie Munger.mode_used>/<reranked>
- 失败（<failures 条数>）：<每条的 step 和 error；为 0 时写“无”>
- 来源缺口（<source_gaps 条数>）：<每条的 step、年份或 URL 和 error>
- 警告：<warnings>
- 用时：<elapsed_seconds> 秒
- 未包含：访谈、Daily Journal、西科年会笔记、合伙企业信、早期年报 OCR 等没有采集脚本的资料；主题 Wiki 为空（见 README“已知限制”）
```

`ok` 为 false 时，先按 `failures` 里的 `error`、`log_tail` 和 `fix` 处理（依赖缺失会给出安装命令），再重跑第 3 步；网络超时一般重跑即可。重跑后仍失败就把报告原样交给用户，不要声称安装完成。

## 不要做

- 不要把资料库、模型或索引放进 skill 目录，也不要提交或再分发它们。
- 不要为了“补全”去下载电子书、视频或付费内容；受版权保护的书只能由用户用合法副本自行导入。
- 不要同时运行两个 bootstrap 或在它运行时另行导入资料。
