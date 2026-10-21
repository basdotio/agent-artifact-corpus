# 本机资料库与运行环境

本技能**不附带任何原文**。资料库、模型和索引都放在 skill 目录之外，由使用者在本机自行采集和建立。

所有数据放在一个自选的根目录 `<DATA>` 下（例如 `~/buffett-munger-data`）：

| 用途 | 路径 |
|---|---|
| 资料库（`LIB`） | `<DATA>/buffett-munger-library` |
| Python（`PY`，采集与检索共用） | `<DATA>/runtime/bin/python` |
| 暂存采集批次（`STAGE`） | `<DATA>/staging/<批次名>` |
| 待补资料清单与缺口记录 | `<DATA>/buffett-munger-library/coverage/` |

路径优先级：用户在对话中指定的路径 → 环境变量 `BUFFETT_MUNGER_CLAUDE_LIBRARY`（指向资料库目录）→ 上表默认路径。始终向 CLI 显式传入 `--library`，避免在不同工作目录意外建立多个库。迁移到其他机器时修改本文件或设置环境变量；不要删除原库。

## 运行环境

用 uv 建立独立虚拟环境，不依赖、也不修改系统 Python：

```sh
uv venv --python 3.12 "<DATA>/runtime"
uv pip install --python "<DATA>/runtime/bin/python" -r "$SKILL/scripts/requirements-retrieval.txt" pypdf lxml brotli
```

- `numpy`、`onnxruntime`、`tokenizers`（固定版本见 `scripts/requirements-retrieval.txt`）：语义检索与重排。
- `pypdf`（或系统的 `pdftotext`）：PDF 提取；`lxml`：`collect_speeches.py`；`brotli`：解码 Brotli 压缩的网页，缺少时可把 Node 路径赋给 `BUFFETT_MUNGER_NODE`。
- 扫描件 OCR、电子书解包不在本技能脚本内；需要时自行处理后用 `library.py ingest` 导入，并保留原页与质量说明。

原文和索引不会发送给外部模型或向量服务；联网采集只访问选定的原始资料网站。

## 首次建库

一条命令跑完下面全部步骤（可续跑，结束时输出 JSON 报告；无人值守安装见仓库根目录的 `INSTALL.md`）：

```sh
"$PY" "$SKILL/scripts/bootstrap.py" --data "<DATA>"
```

手动执行时先建库：

```sh
"$PY" "$SKILL/scripts/library.py" --library "$LIB" init
```

然后按 [collection.md](collection.md) 采集与合并资料，再按 [retrieval.md](retrieval.md) 的“配置或更新索引时才执行”下载模型、建语义索引并运行 `qa.py build`。实际数量、年份、来源质量及失败记录每次运行 `library.py stats` 查看。

## 资料库内的派生数据

- 模型：`<资料库>/retrieval/models/`；固定版本与 SHA 见 `scripts/setup_retrieval.py`。
- 语义索引：`<资料库>/retrieval/index/`；原文变化后 `retrieve.py status` 会报告过期，需重建（约 13 万段的库在 8 线程机器上约 25–40 分钟，可后台运行）。
- 问答单元：`<资料库>/qa/`，由 `qa.py build` 生成，语料变化后过期。
- 主题 Wiki：`<资料库>/wiki/`；归纳与原始证据分开保存。
- 盲测集：`<资料库>/eval/`；`holdout.jsonl` 含真实答案，作答前不要打开。
- 归属表：skill 内 `assets/attribution_map.json`，人工审核快照；新文档入库后用 `attribution.py propose` 判断是否需要补充。

只有成功的 `status`、`mode_used` 和 `reranked` 返回值能证明检索路径实际启用；文件存在、模型已下载或构建进程已启动都不等于索引可用。
