# 本地混合检索与原文回读

## 实际实现与边界

`retrieve.py` 用只读 SQLite 连接检索原文，不改正文、原件、发言人或原 chunk ID。保留 `library.py search/show` 作为无模型路径。

- 关键词：SQLite FTS5/BM25；支持中英文词表、英文停用词过滤及双引号短语。多个词仍是 OR，长问题应拆成几条有针对性的查询。
- 语义：本机 ONNX 多语言 E5 small，输入保留 `query:` / `passage:` 前缀，平均池化并归一化。索引文本只附原有标题、日期和发言人，不混入生成式摘要。
- 融合：对两路候选及显式补充查询使用 RRF；同一候选保留各路排名。补充查询不是新增的独立证据，也不能无限增加同方向查询以压过反证。
- 重排：本机多语言 mMARCO MiniLM cross-encoder，读取目标段及相邻一段的原始文本。结果分数只代表相关性，不是正确概率或人物相似度。
- 回读：返回目标段和指定相邻窗口，保留每段发言人、定位和证据资格；相邻段共用目标段的文档元数据，避免重复大段采集记录。窗口可能跨问题，操作者必须检查原问题、回答尾部及条件句。
- 去重：同一来源组的相同文本合并；结果附来源组提示及每文档数量限制。转载与拆信可能仍需人工去重，不能把候选数当作独立来源数。
- 原文索引与 Wiki 搜索分开返回。Wiki 属于归纳导航，不能用它取代原话核验。
- 人物归属在查询时计算，不改写库里的发言人标签：人物过滤会自动包含已审核的拼写变体（如 CNBC 稿中的 `WARREN BUFEFTT`、`CHALIE MUNGER`），每条结果附 `attribution` 说明归属基础（见下文“归属层级”）。
- 留出：`--exclude-document`（可重复）把指定文档排除在关键词和语义两路之外，用于盲测。
- 译本：`source_type` 为 `translation` 的文档（如用户自行导入的中文版《穷查理宝典》《滚雪球》《芒格之道》）默认不参与检索，否则中文问题会优先命中译文、挤掉英文原文。需要查中文表述、核对译法或《滚雪球》的叙述时加 `--include-translations`；指定 `--source-type translation` 时只查译本。

模型只读取本地文件，运行时不下载或调用外部服务，不执行模型仓库 Python 代码。固定版本、SHA256 及下载行为见 `scripts/setup_retrieval.py`；原始资料不会发送给嵌入或重排服务。首次下载及依赖准备属于配置任务，不在普通问答中自动执行。

## 日常使用

`PY`、`SKILL`、`LIB` 是占位符；实际 Python 及目录见 [local-library.md](local-library.md)。现代检索需要使用带 ONNX 依赖的 Python。

```sh
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" status
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" search \
  '为什么赚了利润，却没有多少钱可以分给股东？' \
  --lexical '"owner earnings" "capital expenditures"' --speaker Buffett \
  --rerank-query 'Why can reported profits differ from cash available to owners after necessary capital expenditures?' \
  --include-unassigned --wiki --limit 10 --output /实际工作目录/检索底稿.json
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" search \
  'size of that circle' --exact --speaker Buffett --context 3
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" search \
  'incentives' --mode lexical --no-rerank --speaker Munger
"$PY" "$SKILL/scripts/library.py" --library "$LIB" show '实际chunk_id' --context 8
```

`--lexical` 可重复，提供针对同一问题的英文术语或其他表述；不要加入结论性偏见。语义路径始终接收原问题。比较两人时分别运行，涉及时间变化时按所需时期分别运行。

本库大部分原文为英文，中文问题直接重排英文长段落可能漏掉相关材料；“多语言”不保证跨语言排序准确。可由操作者提供忠实的完整英文问题 `--rerank-query`，保留人物、条件和否定词，不塞入预期答案；输出保留中文原问题和实际重排问题便于复核。脚本不自动调用翻译服务。仍有缺口时补查英文关键词／Wiki 引用，并比较关闭重排的结果；不能仅因重排靠前就接受。

### 归属层级 `--attribution`

| 层级 | 召回范围 | 何时用 |
|---|---|---|
| `strict`（默认） | 段落发言人为该人物，含已审核的拼写变体 | 原话核验、需要逐段发言人的场合 |
| `author` | 另加 `assets/attribution_map.json` 中已审核文档的无标签段落。随仓库发布的表只列三份可按网址原样取得的芒格文档（Tilson 记录的 2005 年西科年会笔记、两篇仅由档案归属的芒格文章），用 `library.py fetch` 按表中 `url` 导入、不设自定义 `id` 时才生效。采集器建的库里两人的段落已逐段标注，此时结果与 `strict` 相同 | **芒格的思想检索默认用它**：库里有无发言人标签的芒格材料（会议笔记、档案文章）并已写进归属表时，不用它会漏掉这些段落 |
| `unassigned` | 另加所有无标签段落（等同旧参数 `--include-unassigned`） | 找未核定作者的材料，随后人工确认作者 |

每条结果的 `attribution.basis` 为 `chunk-speaker`、`document-author`、`meeting-notes-principal`、`archive-attributed`、`translation-of-own-words`（本人话语的中文译文，只在加 `--include-translations` 时出现）或 `unassigned`，并附 `caution`。写作时按基础措辞，规则见 [evidence-rules.md](evidence-rules.md)。归属表是人工审核的快照，新入库的文档不会自动加入：先运行 `attribution.py --library "$LIB" propose` 列出候选，核对署名后再写进归属表。

## 取完整句子

检索结果里的段落用于发现材料；要在回答中引用原话时，用 `quote.py` 取完整句子（规则见 [evidence-rules.md](evidence-rules.md) 的“完整句子引用”）：

```sh
"$PY" "$SKILL/scripts/quote.py" --library "$LIB" '<chunk_id>' --match 'size of that circle'
"$PY" "$SKILL/scripts/quote.py" --library "$LIB" '<chunk_id>' --match 'too hard pile' --before 1 --after 1
```

## 一次回答的检索计划

人物视角的问题至少跑四类检索，每类两人分开：

1. **原则线索**：`retrieve.py search` 加 `--rerank-query` 英文原问题，必要时用 `--lexical` 补英文术语。
2. **类比案例与错误**：`wiki.py search '<问题>' --type case --type mistake --type declined`，再打开案例页的原文证据。
3. **真实问答锚点**：`qa.py search '<问题>' --rerank-query '<English question>' --limit 5`，可用 `--answered-by Munger` 只看芒格回答过的。看结论、篇幅、是否拒答、谁先开口，再用 `library.py show <chunk_id>` 打开要引用的原文。
4. **反例**：针对主要判断，换年份或换措辞再查一次相反的材料。

```sh
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" search '一家技术变化快的消费电子公司值得投资吗' \
  --speaker Munger --attribution author \
  --rerank-query 'Would you invest in a consumer electronics company whose technology changes quickly?'
"$PY" "$SKILL/scripts/qa.py" --library "$LIB" status
"$PY" "$SKILL/scripts/qa.py" --library "$LIB" search '一家技术变化快的消费电子公司值得投资吗' \
  --rerank-query 'Would you invest in a consumer electronics company whose technology changes quickly?' --limit 5
"$PY" "$SKILL/scripts/qa.py" --library "$LIB" show '<unit id>'
"$PY" "$SKILL/scripts/qa.py" --library "$LIB" stats
"$PY" "$SKILL/scripts/wiki.py" --library "$LIB" search '技术变化快' --type case --type declined
```

`qa.py` 从带发言人标签的年会、访谈和会后谈话文字稿切出“问题 → 回答”单元。切分是启发式的：持续发言的非主讲人开启新单元，主持人的短插话、阿贝尔或贾因等其他回答人留在回答里。没有发言人标签的西科笔记不切分。问答单元只是导航，引用前要打开原段落。语料变化后 `qa.py status` 会报告过期，需要重新运行 `qa.py build`（约 5 分钟，用本地嵌入模型）。

`--mode auto`：可用时混合检索；语义依赖缺失或索引过期则以 `warnings` 明确报告关键词降级。`--mode hybrid`：语义路径不可用就报错，不伪装成功。重排不可用仍返回融合排名并记录警告；需要确认完整流程时同时检查 `mode_used` 与 `reranked`。`--exact` 强制短语关键词路径并关闭重排，再以原文连续字符串过滤（统一大小写及空白，保留标点），避免 FTS 把“90%”当成“90”。它仍受分词与提取质量限制，命中须核上下文与原件。

初始参数为两路各50个候选、最多100个融合候选参与重排、最终10条、每文档最多3条。它们是起点，不是最优值。全面梳理单份文献可设 `--max-per-document 0`；`--limit` 最大100，`--candidates` 最大500。增加条数之前先检查查询和材料覆盖。

## Wiki 导航

```sh
"$PY" "$SKILL/scripts/wiki.py" --library "$LIB" check
"$PY" "$SKILL/scripts/wiki.py" --library "$LIB" search '激励是否能解释所有行为？' --speaker Munger
"$PY" "$SKILL/scripts/wiki.py" --library "$LIB" search '多付了钱的收购' --type mistake
```

Wiki 少量主题的语义向量按查询现场计算，不依赖原文索引；没有模型时可 `--lexical-only`。来源失效的页面进入 `needs_review`，不作为有效导航结果。相似页面仅提供线索，低贴合页面可以不用。

## 配置或更新索引时才执行

在数据根目录下准备独立 Python 环境（见 [local-library.md](local-library.md)）并安装 `scripts/requirements-retrieval.txt`，不要修改系统 Python。模型约270 MB，原文语义向量约每10万段154 MB，另有映射和版本文件。实际大小以文件为准。

```sh
"$PY" "$SKILL/scripts/setup_retrieval.py" --models-dir "$LIB/retrieval/models"
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" build --max-tokens 512 --batch-size 32
"$PY" "$SKILL/scripts/retrieve.py" --library "$LIB" status
"$PY" "$SKILL/scripts/qa.py" --library "$LIB" build
```

全库重建在本机（8 线程）约 25–40 分钟，可在后台运行；期间 `status` 报告过期，`--mode auto` 会降级为关键词检索。`qa.py build` 依赖同一语料指纹，语料变化后也要重建。

索引绑定正文、chunk ID、来源元数据、模型版本和截断长度。资料变化会使旧索引失效；重新构建成功后才切换 current 指针。中断的同配置构建可以续跑；旧完整版本保留，便于恢复。构建、导入和 Wiki 更新顺序执行，不同时运行多个构建者或修改正在索引的资料库。

512是模型输入 token 上限，超长片段可能被截断；最终引用应读取未截断原文。扫描件和 OCR 错字仍需原页核验；向量模型无法补回缺失文字。问答边界只有 `qa.py` 的启发式切分；未实现图谱检索、全库增量向量更新或自动真实度判断。

方法参考：[E5 原始技术报告](https://arxiv.org/abs/2402.05672)、[关键词与向量融合](https://www.elastic.co/docs/solutions/search/hybrid-search)、[检索与重排](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)。它们解释方法，不代表已经证明本库的效果。
