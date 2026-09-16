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
    原始仓库，因为假阳性率必须按来源报告，而把来自 178 个仓库的 483 个样本报成一个
    数字，正是本仓库明令禁止的汇总数字。

  cisco-ai-defense/mcp-scanner —— Apache-2.0
    https://github.com/cisco-ai-defense/mcp-scanner @ be87b90d88bc，evals
    121 个样本树，位于 corpus/malicious/mcp/ci-*，每个是一份实现真实 MCP server 的
    单个 .py，原样拷贝并各自包进一个目录。上游 141 个测试用例中有 20 个被刻意排除，
    理由见该条目的 hazards。

    vendored 的目录只用测试用例名，绝不带类别名：类别目录是上游的标签，把它放进路径
    会让一个读路径的测试工具作弊。

关于强制执行的说明：标签与 NOTICE 的一致性校验**尚未实现**。今天 `make validate` 只检查 `origin.license` 是否属于第 1 层允许的宽松许可之一，它不读这个文件。在那项检查落地之前，让此表与标签保持同步是一项人工义务。这一点写在这里而不是略去，因为署名是 Apache-2.0 和 CC-BY-4.0 的一项条件，因此是许可证义务，不是记账。

---

## 不在这里的东西

`manifest/corpora.yaml` 引用的语料库**没有** vendored —— 那一层只记录 `url + commit + sha256`，内容由 `make fetch` 拉到被 gitignore 的 `cache/`。

这个区分有法律意义：分发别人的作品受其分发条款约束，而**记录一个 URL 和一个哈希不是分发**。所以第 2 层可以引用无 license、CC-BY-NC-SA、AGPL 的语料，在本地测量并发布聚合数字，全部处在这些语料分发条款的管辖之外。这些材料一律不允许进入第 1 层。

详见 [docs/licensing.zh-CN.md](docs/licensing.zh-CN.md)。
