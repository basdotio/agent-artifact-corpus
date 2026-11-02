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
| **召回率是多少** | `datadog-ai-skills`（在野，**须先去重**）加 `skillsgoat`（盲测）；那两份留薄的维度用 `skillharm`，按覆盖报，不按比率报 | 跨重叠语料的合并数。**按维度报，不要报聚合值** |
| **抓的是规避还是话题** | `trailofbits-overt`（4 个样本，4 种机制）、`nvidia-skillspector-fixtures`（成对孪生） | 按规模选的语料。这个问题由结构回答，不由 n 回答 |
| **会不会对安全内容过度告警** | `fevzi-injection-corpus`、`guarddog-benign`、`mcp-guardbench`、`skillsgoat` 的 10 个诱饵 | — |
| **hook / 权限 / MCP 配置** | `skillcraft-audit`（hook 武器化、权限绕过）、`cisco-mcp-scanner-evals`（MCP）—— **只有恶意侧** | 拿 cisco 的 3 个良性样本当 MCP 误报分母 |
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
一个人一次读一个样本，看不见分布。值得有的机制是一道构建闸门：任何支持度 ≥8 的结构特征能以
≥95% 纯度预测标签时直接让构建失败；本仓库在 `harness/internal/leakage` 里实现了它，`make validate`
会跑。（这条规则的早先版本把这道闸门记在 MaliciousSkillBench 的 `metrics/leakage.py` 名下。那个
文件在该仓库里不存在，2026-10-28 核实；MaliciousSkillBench 实际做的是五条轴的划分级重叠审计，
加一份人工整理的生成器脚手架字符串审计，是另一种互补的检查。）

**4. "没有扫描器报过问题"不是良性依据。** 从强到弱：密码学背书（只有 `NVIDIA/skills`）→
企业在自己命名空间下宽松发布 → 官方市场收录 → 市场"非可疑"标记加下载量 →
**扫描器结果干净，这一档是循环论证，权重为零**。Smithery 的 `verified`、
Glama 的 `qualityScore`（**付费位**）、各种信誉分，全是流行度或厂商策展，没有一个是安全评审。

---

## 已钉住可直接拉取的 20 份

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

**`clawhub-live`** —— 唯一会持续产出的恶意来源。
`https://huggingface.co/datasets/OpenClaw/clawhub-security-signals-live`，每周日重新导出，
**MIT**（skill 本身按注册表发布条款为 **MIT-0**），可 vendoring。任一时刻约 280 行被注册表自己的
判官判为恶意，带 SKILL.md 和附件。
*风险*：判定是扫描器的意见（在人工参照集上敏感度 61%、特异度 81%），所以一行只是*候选*，
要有人读过、引了那一行才成为样本；一个发布者换很多 slug 发同一个活动；导出是脱敏版，被隐藏的
skill 没法再从注册表取。
*必须的预处理*：每周跑 `scripts/intake-clawhub.py` —— 和上次导出做差分，按哈希和名字拒掉留出集，
每个发布者跨周累计最多 5 个，写出待读清单；决定写进 `dimension_overrides` 或 `exclude_samples`，
再 `promote` 和派生。没有任何样本只凭判定入库。

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
51 恶意（42 个单体 skill + 9 条链）/ 0 良性。**全世界唯一覆盖 hook 武器化和权限绕过的公开语料。**
*风险*：单一作者，形态在风格上相关；而且作为唯一来源，**没有第二份可以对照校验**。

**`skillharm`** —— 薄弱维度的合成覆盖。
`https://huggingface.co/datasets/osunlp/SkillHarm` @ `cc21f90982ea`，**CC-BY-4.0**，可 vendoring。
879 恶意（687 个固定载荷 + 192 个自变异）/ 0 良性；固定载荷样本里有 240 个已 vendoring 为 `sh-*`，按固定种子顺序每类风险 20 个，含 PDF 载荷。十二类风险横跨数据、系统、自主性三组；六种实现方式把载荷放在 `SKILL.md` 里、skill 会运行的脚本里、它导入的辅助模块里，或它让 agent 去读的文档或 PDF 里。
*风险*：每个样本都是上游点名的某个 LLM 写的，所以是覆盖不是比率；vendoring 的那部分是抽样不是普查；它的 `dos` 是破坏 dotfile 而不是消耗资源，所以落在 filesystem 而不是 resource-abuse。

**`cisco-mcp-scanner-evals`** —— MCP 面。
`https://github.com/cisco-ai-defense/mcp-scanner` @ `be87b90d88bc`，子集 `evals`，
**Apache-2.0**，可 vendoring。142 恶意 / 3 良性（141 个行为用例 + 1 个远端 server；已 vendoring 121 个）。
*风险*：3 个良性样本远不足以当 MCP 的误报分母；**目录名即标签**，能读路径的 harness 可以作弊。

**`trailofbits-overt`** —— 逃逸试金石。
`https://github.com/trailofbits/overtly-malicious-skills` @ `4ffbf9461ef0`，
**无 license**，**永不 vendoring**。4 个恶意。
四个样本、四种不同的绕过逐行规则的机制。小到几秒跑完，利到"通过"本身就是一句有分量的话。
*风险*：零授权；且同时被 `datadog-ai-skills` 和 `skilltrustbench` 包含，**绝不能与这两份同时计数**。

**`skilltrustbench`** —— 形态最好，许可最差。
`https://huggingface.co/datasets/cuhk-zhuque/SkillTrustBench` @ `f90517b7058f`，
**CC-BY-NC-SA-4.0**，**永不 vendoring**。2,863 恶意 / 1,643 良性，另有 1,014 个 `suspicious`——这是更弱的标签（高风险写法、无隐藏触发），不能和恶意相加；这一行早先的版本加了。
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

**`mcp-reference-servers`**、**`mcp-archived-servers`** —— 真实的 MCP 服务器源码，`mcp` 作用面
从来没有过的良性侧。
`https://github.com/modelcontextprotocol/servers` @ `bbb701e7ac1e`（子集 `src`，**Apache-2.0**，
尚未重新授权的贡献仍为 MIT）和 `https://github.com/modelcontextprotocol/servers-archived` @
`9be4674d1ddf`（子集 `src`，**MIT**），都可 vendor。7 + 14 个服务器树，整树保留，lockfile 一并在内。
在它们之前，mcp 作用面上每一棵*源码*树都标为恶意（cisco），唯一的良性样本是工具目录（automatelab）；
一个读服务器代码的扫描器能量召回，量不了过度告警。
*风险*：21 个里 14 个是 TypeScript，只读 Python 的扫描器能评 7 个、其余什么也读不到——那是声明过的
边界，不是漏报，也绝不能折成良性判定。有几个（`everything`、`filesystem`、`puppeteer`、`postgres`）
按设计就会读、写、执行或持有凭证；在它们上面报警是「在良性样本上报了警」，还不是假阳性。
*必要准备*：无。总体就是「`src/` 下的每一个目录」，写在 manifest 里。

**`fastmcp-examples`**、**`python-sdk-examples`** —— 框架自带的示例服务器。
`https://github.com/jlowin/fastmcp` @ `e2fcc412001f`（子集 `examples`，**Apache-2.0**）和
`https://github.com/modelcontextprotocol/python-sdk` @ `c9356a2a8fb8`（子集 `examples`，**MIT**），
都可 vendor。36 + 32 个可运行的服务器，目录型和单文件型都有。
*风险*：**是 fixture，不是野生样本**——写来演示 API 的代码，没人部署，所以 `corpus score` 把它的
比率和上面两条分开报。它是公开世界里最密集的一批地道 FastMCP / SDK 服务器写法，这是收它的理由。
三个 `.fastmcp.json` 伴随文件和两个不构造服务器的 snippet 按名字排除，理由写在 manifest 里每一条旁边。

挨着这四条的还有三个只含 Python、从 GitHub 采集来的总体——代码搜索找到的第三方服务器源码、
2026-09-20 当天或之后创建的仓库里的服务器源码、同一日期之后创建的仓库里的 skill——它们不是
manifest 条目，理由和配置采集一样：那是几百个仓库，不是一个。完整清单是
`manifest/pins/mcp-servers.json`，由 `scripts/harvest-mcp-servers.py` 生成，脚本的 docstring 写明了
那里的 `benign` 是什么意思、一棵树按什么边界裁。

### Hard negative —— 良性但长得像攻击

**`automatelab-mcp-tools`** —— 真实工具说明。
`https://huggingface.co/datasets/automatelab/mcp-servers-tool-catalog` @ `a413afb7b02a`，
**CC-BY-4.0**，可 vendoring。**9,922 条工具声明，横跨 357 个 package**（285 个不同的 server 名）。
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

**恶意的 hook、恶意的权限授权、恶意的 connector 配置。** 这一条自写下以来已经反过来了，
而反转本身就是重点。

缺的曾经是**良性侧**：没有任何公开数据集收集过"正常的 hook 或权限配置长什么样"，因为
几乎没人扫这些面。这一格现在靠**采集**而不是下载补上了——`scripts/harvest-claude-config.py`
存着 391 个来自 389 个公开仓库的真实 `.claude/settings.json` 和 `.mcp.json`，另有 2 个
被提升为硬负样本。

**公开世界里完全没有来源的，是这三个作用面的恶意侧。** 没有任何数据集把"被武器化的 hook"
或"过宽的权限授予"**当作 artifact** 收录过；`skillcraft-audit` 覆盖 hook 武器化和权限绕过，
但它的 artifact 是**安装 hook 的 skill**，那是另一条加载路径。所以在 hooks、permission 和
connector 上，这份语料能量过度告警，**完全量不了召回**——这一点写在 README 的已知缺口里，
而不是留给读者自己发现。

这是唯一一格只能靠**采集**而不是下载来补的，**而它也是整个语料里最容易做出一个好看的
误报率的地方**。本仓库采用的规则：**良性 hook 与权限样本只能从真实机器上采**（自己的、
同事的、公开 dotfiles 仓库），**绝不手写**。手写的良性 hook 和手写的良性 skill 是同一个毛病，
理由见 [`design.zh-CN.md`](design.zh-CN.md)。
