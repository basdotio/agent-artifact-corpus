# 公开语料清单

我们找到的全部公开 agent artifact 语料，附上每一份**适合回答什么问题**、以及**用错了会把
数字变成什么样**。

**选之前先读这一页。** 这里面有两份语料能让一行正则拿到接近满分，四份永远不能再分发，
还有几份互相包含到"把条数相加"会得出一个朝好看方向错的数。这些事实是逐份记录的，
**从数据本身看不出来**。

机器可读的那一半在 [`../manifest/corpora.yaml`](../manifest/corpora.yaml)，
用 `make fetch E="<id> <id>"` 拉取。取样纪律见 [`design.zh-CN.md`](design.zh-CN.md)，
许可规则见 [`licensing.zh-CN.md`](licensing.zh-CN.md)。

---

## 按你要回答的问题来选

**不要按规模选，按问题选，然后核对风险项。**

| 你的问题 | 用 | 绝不要用 |
|---|---|---|
| **误报率是多少** | `skillmd-138k` 做头条；需要带脚本的完整树时用 `awesome-link-targets` | 任何"因为扫描器没响所以是良性"的标注。对一个规则源自 OWASP Agentic Top 10 的扫描器来说，`clawhub-security-signals` 是循环论证 |
| **召回率是多少** | `datadog-ai-skills`（在野，**须先去重**）加 `skillsgoat`（盲测） | 跨重叠语料的合并数。**按维度报，不要报聚合值** |
| **抓的是规避还是话题** | `trailofbits-overt`（4 个样本，4 种机制）、`nvidia-skillspector-fixtures`（成对孪生） | 按规模选的语料。这个问题由结构回答，不由 n 回答 |
| **会不会对安全内容过度告警** | `fevzi-injection-corpus`、`guarddog-benign`、`mcp-guardbench`、`skillsgoat` 的 10 个诱饵 | — |
| **hook / 权限 / MCP 配置** | `skillcraft-audit`（hook 武器化、权限绕过）、`cisco-mcp-scanner-evals`（MCP）—— **只有恶意侧** | 拿 cisco 的 4 个良性样本当 MCP 误报分母 |
| **工具说明投毒** | `automatelab-mcp-tools`（9,922 条真实工具说明）做良性侧 | — |
| **防御性文字被误判成攻击** | `skilltrustbench` 的 `injected_d8` 子集 —— **全世界唯一标注了这一类的** | over-refusal 基准（OR-Bench、XSTest、FalseReject）。它们测的是**模型**过度拒绝，不是**扫描器**过度告警，而且全是 prompt 串不是 artifact |

---

## 四条压倒任何选择的规则

**1. 这些条数不能相加。** 语料之间互相包含：

```
MaliciousSkillBench ⊃ SkillTrustBench + MalSkillBench + ATR + SkillFortifyBench + …
SkillTrustBench     ⊃ overtly-malicious-skills（4 个）
DataDog ai-skills   ⊃ overtly-malicious-skills（tjade273-* 即 simple-formatter）
snyk-labs           ∩ pyxeroai = 同源于 NET_NiNjA
```

manifest 里每条都声明 `overlaps:`。跨重叠求和会**放大分母、美化结果**。

**2. 四份永远不能再分发。** `trailofbits-overt` 和 `malskillbench` **完全没有 license** ——
零授权，这比 NonCommercial **更严**，不是更松。`skilltrustbench` 是 CC-BY-NC-SA，
ShareAlike 条款具有传染性。`anthropics/skills` 是**专有的**：逐 skill 的 `LICENSE.txt`
明文禁止复制与分发。

这四份**仍然可以本地测量并发布聚合数字**。用工具跑一遍你合法取得的材料不是分发。
这个区分正是本仓库用 URL 加哈希引用、而不是 vendoring 的全部理由。

**3. 两份埋了雷。** 两份都能给出漂亮成绩，而原因与检测能力无关：

- **`malskillbench`**：`_meta.json` 在 4,000 个良性样本里有 3,878 个，在 3,944 个恶意样本里
  **一个都没有**。**不读任何 skill 内容就能以 97% 纯度把两类分开。** 用前必须删掉那个文件。
- **`skillfortifybench`**：恶意样本用 RFC-2606 保留域名，良性样本一个都不用。
  一行正则满分，泛化到真实世界是 0%。

逐个样本读的时候两份都看不出问题，所以这件事属于**构建闸门**而不是评审清单 ——
一个人一次读一个样本，看不见分布。它的后继版本给了该抄的机制：`metrics/leakage.py` 在
任何支持度 ≥8 的结构特征能以 ≥95% 纯度预测标签时**直接让构建失败**。

**4. "没有扫描器报过问题"不是良性依据。** 从强到弱：密码学背书（只有 `NVIDIA/skills`）→
企业在自己命名空间下宽松发布 → 官方市场收录 → 市场"非可疑"标记加下载量 →
**扫描器结果干净，这一档是循环论证，权重为零**。Smithery 的 `verified`、
Glama 的 `qualityScore`（**付费位**）、各种信誉分，全是流行度或厂商策展，没有一个是安全评审。

---

## 已钉住可直接拉取的 13 份

每一份都在 manifest 里钉到了 commit，用 `make fetch E="<id>"` 取。

### 召回 —— 恶意样本

**`datadog-ai-skills`** —— 主力召回语料。
`https://github.com/DataDog/malicious-software-packages-dataset` @ `d156188d1e45`，
子集 `samples/ai-skills`，**Apache-2.0**，可 vendoring。
204 恶意 / 0 良性。**唯一在野 + 人工分诊 + 许可干净**的 skill 集。
*风险*：204 个里 81 个（40%）带同一家厂商的名字，约 40 个是近重复；约 26 个（13%）是
别家扫描器的合成测试而非在野样本；压缩包用密码 `infected` 加密。与 `trailofbits-overt` 重叠。
*必须的预处理*：**按作者和 canonical 树哈希去重后再计数**，否则召回率测的是
"有没有抓住一个模板"。

**`skillsgoat`** —— 能力探针。
`https://github.com/optimuslabs-io/skillsgoat` @ `c03d70d80c32`，**MIT**，可 vendoring。
101 恶意 / 10 良性。设计上是盲测：答案放在样本树之外，**报错算漏报**。
布局是 `pasture/<类别>/<id>/{expected.yaml, skill/}`，31 个类别，
另有 `taxonomy.yaml` 把类别映射到 OWASP Agentic Top 10 和 SkillSpector 的 P 编码。
每个样本带 `verdict`、`severity`、`inert: true` 和一个 **canary 字符串**。
*风险*：那 10 个良性条目是**故意设置的误报诱饵** —— 在它们上面响是失败，不是修复。
*注*：它的标注文件放在 skill 目录**旁边**，不在里面。这是正确布局；本仓库是在
"放里面"版本污染了自己的测量之后独立得出同一结论的。

**`skillcraft-audit`** —— hook 与权限。
`https://github.com/Clay-HHK/skillcraft-audit` @ `0b9c36f28e05`，**MIT**，可 vendoring。
150 恶意 / 0 良性。**全世界唯一覆盖 hook 武器化和权限绕过的公开语料。**
*风险*：单一作者，形态在风格上相关；而且作为唯一来源，**没有第二份可以对照校验**。

**`cisco-mcp-scanner-evals`** —— MCP 面。
`https://github.com/cisco-ai-defense/mcp-scanner` @ `be87b90d88bc`，子集 `evals`，
**Apache-2.0**，可 vendoring。154 恶意 / 4 良性。
*风险*：4 个良性样本远不足以当 MCP 的误报分母；**目录名即标签**，能读路径的 harness 可以作弊。

**`trailofbits-overt`** —— 逃逸试金石。
`https://github.com/trailofbits/overtly-malicious-skills` @ `4ffbf9461ef0`，
**无 license**，**永不 vendoring**。4 个恶意。
四个样本、四种不同的绕过逐行规则的机制。小到几秒跑完，利到"通过"本身就是一句有分量的话。
*风险*：零授权；且同时被 `datadog-ai-skills` 和 `skilltrustbench` 包含，**绝不能与这两份同时计数**。

**`skilltrustbench`** —— 形态最好，许可最差。
`https://huggingface.co/datasets/cuhk-zhuque/SkillTrustBench` @ `f90517b7058f`，
**CC-BY-NC-SA-4.0**，**永不 vendoring**。3,877 恶意 / 1,643 良性。
*风险*：NonCommercial 加 ShareAlike 传染，只能本地测量并发布聚合数字；包含 ToB 那四个样本。
*不可替代的价值*：**`injected_d8` 子集** —— 119 个样本，其中 118 个标为 `normal`，
作者原文描述为"不应被默认判成恶意的安全工具与测试夹具"。
**这是全世界唯一对'防御性文字误报'做过标注的公开数据。**

**`malskillbench`** —— 有规模，有雷。
`https://github.com/lxyeternal/MalSkillBench` @ `06e083125d5e`，**无 license**，
**永不 vendoring**。3,944 恶意 / 4,000 良性。
*风险*：**严重标签泄漏**，见上面第 3 条。
*必须的预处理*：**测量任何东西之前，先从每个样本里删掉 `_meta.json`。**
（"恶意目录是空的"那个传言是**假的** —— 3,944 个全都有 `SKILL.md`。）

### 误报分母 —— 良性样本

**`skillmd-138k`** —— 主分母。
`https://huggingface.co/datasets/FayeZC/SkillMD-138K` @ `0d73048abf2f`，**CC-BY-4.0**，
可 vendoring。138,133 个 skill，横跨 **20,556 个 repo** —— 现有最宽的真实世界分布。
*风险*：**只有 `SKILL.md` 正文，没有脚本**，所以所有脚本面的规则都没被它测到；
而且真正的 n 是 repo 数，按文件取样会让大 repo 占比过高。
*必须的预处理*：逐 repo 报数，每 repo 设上限，**同时发布按样本加权和按来源不加权两个比率**。
两者不一致时，**那个不一致本身就是结果**。

**`clawhub-security-signals`** —— 有规模，但有一条必须跟着它走的告诫。
`https://huggingface.co/datasets/OpenClaw/clawhub-security-signals` @ `69dcbd323c15`，
**MIT**，可 vendoring。41,743 个 clean。
*风险*：**部分循环** —— 它的标注来自 OWASP Agentic Top 10 评级，而那正是多数 agent artifact
扫描器规则的来源分类法。标注是银标准（模型判定），不是人工评审。
*必须的预处理*：**永远不做头条误报数字**，必须与一个非循环来源并列报出。

### Hard negative —— 良性但长得像攻击

**`automatelab-mcp-tools`** —— 真实工具说明。
`https://huggingface.co/datasets/automatelab/mcp-servers-tool-catalog` @ `a413afb7b02a`，
**CC-BY-4.0**，可 vendoring。**9,922 个工具，横跨 359 个 server。**
真实说明里合法地写着 `IMPORTANT:`、`<placeholder>`、token 和 URL —— 正是工具投毒规则要找的形状。
*风险*：数据本身无已知风险。风险在你这边：这通常比你的工具说明规则**此前验证过的规模大两个数量级**，
可能一次性冒出大量误报。

**`nvidia-skillspector-fixtures`** —— 成对孪生。
`https://github.com/NVIDIA/SkillSpector` @ `2e9ae8d1cfa6`，**Apache-2.0**，可 vendoring。
约 6 对，每个恶意 fixture 旁边配一个几乎相同的干净版本。
**唯一能测出"命中的是差异还是话题"的结构。**
*风险*：极小。它的价值是结构，不是条数。

**`guarddog-benign`** —— 带来历的误报样本。
`https://github.com/DataDog/guarddog` @ `1f4a66c064fb`，**Apache-2.0**，可 vendoring。
25 个良性 fixture，**每一个都自带注释说明它当初修的是哪次真实误报**。
*风险*：面向 Python 包规则而非 agent skill —— 形状可迁移，面不可迁移。

**`fevzi-injection-corpus`** —— 讲注入的文档。
`https://github.com/fevziegeyurtsevenler/prompt-injection-corpus` @ `05fd3571d53a`，
**CC-BY-4.0**，可 vendoring。5 个 markdown，密集包含字面的 `ignore previous instructions`。
*风险*：它是**关于**注入的文档，所以**任何注入规则在它上面的命中，按构造都是误报**。
这恰恰是它有用的原因。

---

## 已找到但尚未钉住的 10 份

都是真实可用的，只是还没有 manifest 条目，因而没有钉住的 commit、不支持 `make fetch`。
依赖它们之前请自行核实条数与许可。

| 语料 | 许可 | 规模 | 为什么可能需要它 |
|---|---|---:|---|
| `Agent-Threat-Rule/atr-skill-benchmark` | MIT | 466 | 含 `evasive-stub`，**显式为误报测试而建**。是 MaliciousSkillBench 的子集 |
| `NVIDIA/skills` | Apache-2.0 | 356 | **唯一带密码学签名的语料**（Sigstore，私有 PKI） |
| `anthropics/claude-plugins-official` | Apache-2.0 | 31 skill / 39 插件 | 第一方策展。**先查你的工具是否已把其中某些列入白名单** —— 若已列入，它对你就不独立 |
| `ossf/package-analysis` 的 detections | Apache-2.0 | 约 191 | Go 表驱动，同语言同写法。URL fixture 内联标注了作者自己判错的条目，含十六进制转义与 IDN 同形字 |
| `protectskills/MaliciousSkillBench` | 码 Apache-2.0 / 数据 CC-BY-4.0 | 7,505 / 2,235 | 有规模 —— 但它**聚合了 13 个来源**，与本清单大部分重叠 |
| `shenyimings/skillet` 的 `benchmark/wild/` | MIT | 483 safe | **构造上就是 repo-disjoint**，并记录 `label_source`，能看出每条标注是怎么来的 |
| `mcp-guardbench` 的 `cases/benign/` | MIT | 20 | 故意设陷：西里尔散文、`ignore` flag 文档、AWS **示例** key |
| 厂商 repo（google、adobe、stripe、microsoft、forcedotcom） | Apache-2.0 / MIT | 各 14–337 | 企业在自己命名空间下宽松发布，良性可信度高，但每家风格同质 |
| `anthropics/.../security-guidance` | Apache-2.0 | 1 | 攻击模式正则加警告散文，**且注册成 hook**，会落在真实加载路径上 |
| awesome 清单的链接目标 | 573 个里 457 个宽松 | 1,231 棵树 / 382 个 repo | **完整树含真实脚本、人工收集、非循环** —— 最好的非"裸清单"良性来源 |

最后一行是**故意没进** manifest 的。它是一批仓库而不是一个仓库，不符合"一个 url 一个 commit"
的形状，需要自己的解析器：读清单、按许可过滤、每 repo 限 5 棵树、逐个钉住。
用占位 URL 记进去是能通过校验的，而**通过校验的占位符正是 manifest 要防的那种失败**。

---

## 硬红线

**`anthropics/skills` 是专有的。** 每个 skill 的 `LICENSE.txt` 写着 All rights reserved，
明文禁止复制与分发。**它不能进入任何一层。** 如果你本机装了它，可以本地测量；不要分发任何内容。

---

## 公开世界缺的那一格

**良性的 hook、良性的权限授权、良性的 MCP server 配置。** 这些面的**恶意侧**是有的
（`skillcraft-audit`、`cisco-mcp-scanner-evals`），**良性侧全世界都没有** ——
因为几乎没人扫这些面，所以没人收集过"正常的长什么样"。

这是唯一一格只能靠**采集**而不是下载来补的，**而它也是整个语料里最容易做出一个好看的
误报率的地方**。本仓库采用的规则：**良性 hook 与权限样本只能从真实机器上采**（自己的、
同事的、公开 dotfiles 仓库），**绝不手写**。手写的良性 hook 和手写的良性 skill 是同一个毛病，
理由见 [`design.zh-CN.md`](design.zh-CN.md)。
