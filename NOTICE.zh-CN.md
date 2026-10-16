> [English](NOTICE) · 中文

# NOTICE

本仓库 `corpus/` 下由 basdotio 编写的内容依 MIT 授权（见 `LICENSE`）。

`corpus/` 下**从第三方 vendored 进来的**样本各自保留原许可，逐项列在下面。每个这样的样本都在它的标签里记录 `origin.license` 和 `origin.source`（标签是 `corpus/<class>/<surface>/<id>.yaml`，放在样本树**旁边**，绝不放进树里），其许可必须与此表一致。

当前 vendored 的第三方内容：

  optimuslabs-io/skillsgoat —— MIT
    https://github.com/optimuslabs-io/skillsgoat @ c03d70d80c32
    76 个样本树，位于 corpus/malicious/skills/sg-* 和 corpus/benign/skills/sg-*，
    原样拷自该 commit 的 pasture/<category>/<id>/skill/ 目录。

    它们的标签是**生成的，不是 vendored 的**：坐标是我们的，按 manifest/corpora.yaml
    里的规则从 skillsgoat 自己的 expected.yaml 派生而来。每个标签都记着
    origin.type `derived` 和指回上游路径的 derived_from。

    上游自己的 expected.yaml **刻意不拷贝** —— 放在样本树里的标签会被当成样本的一部分
    读取，这个错误已经污染过本语料库的测量一次。

  Clay-HHK/skillcraft-audit —— MIT
    https://github.com/Clay-HHK/skillcraft-audit @ 0b9c36f28e05
    42 个样本树，位于 corpus/malicious/skills/sc-*，原样拷自该 commit 的
    experiments/poc-skills/T*/<难度>/ 目录。标签同样是生成的。

    这个上游**没有任何逐样本标签**，所以 class 和 severity 是本仓库**断言的常量**，
    不是读来的值；该条目的 fidelity 字段写明了这一点。

  NVIDIA/SkillSpector —— Apache-2.0
    https://github.com/NVIDIA/SkillSpector @ 2e9ae8d1cfa6，tests/fixtures
    24 个 fixture 中引入 6 个，位于 corpus/malicious/skills/ns-* 和
    corpus/hard-negative/skills/ns-ssd-clean，原样拷贝。

    它们的标签是**手工钉的**，不是生成的：硬负样本需要 differs_by 和 pairs_with，
    没有任何规则能产出这两样。其余 18 个 fixture 已逐个读过并**刻意不引入**，
    理由记在 manifest/corpora.yaml 该条目的 hazards 里。

  shenyimings/skillet —— MIT
    https://github.com/shenyimings/skillet @ b778fe53f456，benchmark/wild
    483 个样本树，位于 corpus/benign/skills/sk-*，原样拷贝。它们是真实的公开 skill，
    由 skillet 钉在各自的原始仓库和 commit 上；每个标签在 origin.source 里记录那个
    原始仓库，因为假阳性率必须按来源报告，而把来自 131 个仓库的 483 个样本报成一个
    数字，正是本仓库明令禁止的汇总数字。

  cisco-ai-defense/mcp-scanner —— Apache-2.0
    https://github.com/cisco-ai-defense/mcp-scanner @ be87b90d88bc，evals
    121 个样本树，位于 corpus/malicious/mcp/ci-*，每个是一份实现真实 MCP server 的
    单个 .py，原样拷贝并各自包进一个目录。上游 141 个测试用例中有 20 个被刻意排除，
    理由见该条目的 hazards。

    vendored 的目录只用测试用例名，绝不带类别名：类别目录是上游的标签，把它放进路径
    会让一个读路径的测试工具作弊。

  fevziegeyurtsevenler/prompt-injection-corpus —— CC-BY-4.0
    https://github.com/fevziegeyurtsevenler/prompt-injection-corpus @ 05fd3571d53a
    全部五篇文档，位于 corpus/hard-negative/instruction/fz-*，原样拷贝。

    它们是土耳其语的注入防御参考文档，密集包含着它们要教防御者识别的那些字面载荷，
    而这正是它们成为硬负样本的原因。标签是手工钉的：differs_by 派生不出来。

  automatelab/mcp-servers-tool-catalog —— CC-BY-4.0
    https://huggingface.co/datasets/automatelab/mcp-servers-tool-catalog @ a413afb7b02a
    357 个样本树，位于 corpus/benign/mcp/am-*，一个 package 一个，合计承载全部 9,922
    条工具声明。

    上游提供的是 parquet 表格而不是文件，所以这些树由 scripts/extract-automatelab.py
    从钉住的 parquet 生成；声明内容本身未作改动，没有任何一个工具列表被截断。

  FayeZC/SkillMD-138K —— CC-BY-4.0
    https://huggingface.co/datasets/FayeZC/SkillMD-138K @ 0d73048abf2f
    2,000 篇 SKILL.md，位于 corpus/benign/skills/md-*，原样拷贝，来自 1,505 个不同的
    原始仓库。

    每个标签的 origin.source 记的是那个原始仓库，而不是这个数据集——因为 CC-BY 的署名
    欠的是写下这篇 skill 的人，数据集只是它到达我们手里的路径，以「via」的形式记在后面。

    这是一个 138,133 篇的总体的**样本**，不是总体本身。采样方案就是
    scripts/sample-skillmd.py：按「仓库 + 包路径」分层，每层取一篇，抽 2,000 层，
    固定随机种子，并排除 skillet 已经覆盖的那 100 个仓库，使两个分母不重复计数。

    上游提供的是 parquet 表格而不是文件。每篇的来源信息放在 cache 里紧邻样本树的
    sidecar 文件中，绝不放进样本树内部，以免被当作样本内容读进去。

  osunlp/SkillHarm —— CC-BY-4.0
    https://huggingface.co/datasets/osunlp/SkillHarm @ cc21f90982ea
    240 个样本树，位于 corpus/malicious/skills/sh-*，是所选 Fixed-Payload Poisoning 样本各自
    被投毒的 skill 目录，原样拷贝（含 PDF 载荷；上游附带的其他二进制不抓取）。这是 641 个
    FPP 样本的一个**抽样**，不是总体：scripts/prep-skillharm.py --vendor 20 按固定种子顺序
    每类风险取 20 个。标签是生成的，不是 vendored 的：类别和严重度是本仓库断言的常量，
    维度、层级和规避手法按 manifest/corpora.yaml 里的规则从上游自己的 risk_id 和
    realization 派生；每个标签都记着 origin.type `derived`。每个样本都是上游点名的某个
    LLM（design_agent_id）写出来的，所以它们是 fixture，不是在野样本。
    署名：SkillHarm，OSU NLP group（osunlp），arXiv 2606.02540，CC-BY-4.0。

  modelcontextprotocol/servers —— Apache-2.0（尚未重新授权的贡献仍为 MIT）
    https://github.com/modelcontextprotocol/servers @ bbb701e7ac1e，src
    7 个样本树在 corpus/benign/mcp/ref-* 下，从该 commit 的 src/<server>/ 目录原样复制，
    lockfile 和 manifest 一并保留。该仓库的 LICENSE 记录了从 MIT 到 Apache-2.0 的过渡：
    作者同意的贡献为 Apache-2.0，其余仍为 MIT。两者都是宽松许可，整树保留即同时满足
    两份声明。标签是生成的（origin.type 为 `derived`），类别是常量。

  modelcontextprotocol/servers-archived —— MIT
    https://github.com/modelcontextprotocol/servers-archived @ 9be4674d1ddf，src
    14 个样本树在 corpus/benign/mcp/arch-* 下，从 src/<server>/ 原样复制。标签生成，类别常量。

  jlowin/fastmcp —— Apache-2.0
    https://github.com/jlowin/fastmcp @ e2fcc412001f，examples
    36 个样本树在 corpus/benign/mcp/fm-* 下：examples/ 直接下属的 19 个目录和 17 个单文件
    服务器，原样复制（单文件和其他所有文件型样本一样，各自包进一个目录）。旁边的三个
    .fastmcp.json 运行配置不是样本，在 manifest 里按名字排除。标签生成，类别常量。

  modelcontextprotocol/python-sdk —— MIT
    https://github.com/modelcontextprotocol/python-sdk @ c9356a2a8fb8，examples
    32 个样本树在 corpus/benign/mcp/sdk-* 下：examples/servers/ 下的 10 个目录和
    examples/snippets/servers/ 下的 22 个单文件服务器，原样复制；两个不构造服务器的
    snippet 文件按名字排除。标签生成，类别常量。

  采集来的 MCP 服务器源码和 skill —— 来自 858 个不同的仓库
    按仓库各自为 MIT、Apache-2.0、BSD-3-Clause、BSD-2-Clause、ISC、CC0-1.0 或 CC-BY-4.0。
    459 个服务器树在 corpus/benign/mcp/gh-* 下，400 个 skill 树在 corpus/benign/skills/gh-* 下，
    每个都是一台真实服务器入口文件所在的目录、或一份真实 SKILL.md 所在的目录，按
    scripts/harvest-mcp-servers.py 写明的边界从钉住的 commit 复制（不收 lockfile、二进制、
    依赖和缓存目录、超过 200 KiB 的文件；凡复制进来的文件一律不改）。和配置采集一样，
    署名是**逐样本**的：每个标签的 origin.source 是指向仓库、commit 和目录的永久链接，
    manifest/pins/mcp-servers.json 是完整清单，每棵树带一个树哈希。搜索找到但剔除的 5 个仓库
    在那里的 `dropped` 下连同理由列出；搜索找到但从未 vendor 的 983 个 skill 仓库在
    `sampled_out` 下列出，因为 skill 这个总体是按种子抽的 400 个。

  采集来的 agent 配置 —— 来自 389 个不同的仓库
    MIT 292、Apache-2.0 93、BSD-3-Clause 6、CC0-1.0 1、CC-BY-4.0 1。
    391 个样本位于 corpus/benign/{hooks,permission,connector}/，另有 2 个被提升到
    corpus/hard-negative/。每一个都是从公开仓库原样 vendoring 的真实
    `.claude/settings.json` 或 `.mcp.json`。

    这一条没法做成表格。这些 artifact 来自 389 个不同的作者，因此各许可证要求的署名是
    **逐样本**记录的：每个标签的 origin.source 都是一个点名了仓库、commit 和路径的
    永久链接，每个标签还带着 sha256，`make validate` 会拿它和 vendoring 的字节核对。
    完整清单在 manifest/pins/claude-config.json，由 scripts/harvest-claude-config.py
    生成，要看全量列表就读它。

    注意这项义务的形状：MIT 和 Apache-2.0 要求许可证文本和版权声明随材料一起传播，而面对
    389 个上游，这意味着要逐个履行而不是笼统履行。这里采用的办法就是逐标签的永久链接；
    如果你把这份语料再往下分发，那些永久链接和 pins 文件也是你必须一起带上的东西。

关于强制执行的说明：标签与 NOTICE 的一致性校验**尚未实现**。今天 `make validate` 只检查 `origin.license` 是否属于第 1 层允许的宽松许可之一，它不读这个文件。在那项检查落地之前，让此表与标签保持同步是一项人工义务。这一点写在这里而不是略去，因为署名是 Apache-2.0 和 CC-BY-4.0 的一项条件，因此是许可证义务，不是记账。

---

## 不在这里的东西

`manifest/corpora.yaml` 引用的语料库**没有** vendored —— 那一层只记录 `url + commit + sha256`，内容由 `make fetch` 拉到被 gitignore 的 `cache/`。

这个区分有法律意义：分发别人的作品受其分发条款约束，而**记录一个 URL 和一个哈希不是分发**。所以第 2 层可以引用无 license、CC-BY-NC-SA、AGPL 的语料，在本地测量并发布聚合数字，全部处在这些语料分发条款的管辖之外。这些材料一律不允许进入第 1 层。

详见 [docs/licensing.zh-CN.md](docs/licensing.zh-CN.md)。
