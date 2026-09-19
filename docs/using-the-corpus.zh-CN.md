> [English](using-the-corpus.md) · 中文

# 用这份语料测量你的扫描器

写给任何把「AI agent 环境静态扫描器」指向这份语料的人或 agent。你不需要向我们要任何东西:不用账号、不用注册、不用在本仓库里登记任何条目。clone 下来,跑三条命令,读一张成绩单。

这份文档给的是协议,以及同样重要的另一半:**每个数字**允许**被读成什么**。一个只甩给你一个百分比、却不说它没覆盖什么的基准,正是扫描器拿到好分数却做出坏产品的原因。

---

## 三条命令的闭环

```bash
git clone https://github.com/basdotio/agent-artifact-corpus && cd agent-artifact-corpus
cd harness

go run ./cmd/corpus samples > samples.jsonl     # 1. 工作清单
<你的 runner> < samples.jsonl > verdicts.jsonl  # 2. 你写的那部分
go run ./cmd/corpus score verdicts.jsonl        # 3. 成绩单
```

第 2 步是唯一需要你写的。第 1、3 步是我们的,且对你的工具一无所知。

### 1. `corpus samples` —— 工作清单

每行一个 JSON,对应一个样本:

```json
{"sample":"mal-hook-sessionstart-rce","path":"corpus/malicious/hooks/sessionstart-rce","class":"malicious","surface":["hooks"],"severity":"critical"}
```

| 字段 | 含义 |
|---|---|
| `sample` | 你必须在判定里原样回传的 id |
| `path` | 样本树,仓库相对路径 —— **把你的扫描器指向这里** |
| `class` | `malicious` / `benign` / `hard-negative` —— 答案,公开给你 |
| `surface` | 这个 artifact 位于哪条(些)加载路径;是列表,因为一个文件可以同时属于两条 |
| `severity` | 恶意样本上有 |

**答案不藏着,这是有意的。** 这不是一场闭卷考试,而是一件仪器。没什么能阻止你拿它训练——但你那么做,你的分数就不再有任何意义,那是你要避免的问题,不是我们要监管的事。

### 2. 你的 runner —— 唯一了解你工具的那部分

对每一行:把扫描器指向 `path`,决定一个词,输出一行。

```json
{"sample":"mal-hook-sessionstart-rce","verdict":"malicious","severity":"high","dimensions":["execution"]}
```

| 字段 | 必需 | 说明 |
|---|---|---|
| `sample` | 是 | 必须匹配工作清单里的 id |
| `verdict` | 是 | 只能是 `malicious` 或 `benign`,别的都解析不了 |
| `severity` | 否 | 你的严重度,用通常那把梯子 |
| `dimensions` | 否 | 是哪一**类**,用本语料的词表 —— 填了才能算归类分 |

格式错误会**带行号报错**而不是跳过。一个悄悄丢记录的判卷器,报的是一个分母未知的率,比不跑更糟。重复 id 同样拒绝:同一个样本两个判定意味着答案有歧义,替你挑一个等于替你编一个。

**把你的多档状态压成一个词,是你要做、也要讲明的决定。** 多数扫描器不止两种结果——一个分数、一把严重度梯子、一个待复核档。选那个对应你产品**实际行为**的阈值(拦住加载、让构建失败),发布时说清你选了哪个。如果诚实的答案是两个阈值,就跑两遍。

#### 唯一的难点:你的扫描器的输入模型

一个样本是**单个 artifact** —— 一个 skill 目录、一个 `settings.json`、一个 `.mcp.json`。很多扫描器期望的却是一整个配置**根**(`~/.claude` 那种形状),并在其中自己发现 artifact。如果你把裸样本目录丢给这类扫描器,它可能什么都找不到、报告干净,而你测到的是**你的 runner**,不是你的扫描器。

用 `surface` 把每个样本摆到你的扫描器**会去找那类东西的位置**。一个实测例子:某扫描器下,skill 样本放到 `<root>/skills/<name>/` 被正确识别为 skill;同一个样本直接当根,则被当成一个松散的 instruction 文件、判为干净。**某个面上突然出现一整列 0,几乎总是这个原因,而不是真漏。** 相信之前先查摆放。

### 3. `corpus score` —— 成绩单

```
detection — recall per dimension. collected and constructed never merge:
  dimension        evidence          n   result
  execution        collected        61   18%  [10, 29]  (11/61)
  execution        constructed       6   caught 1 of 6 (coverage of chosen shapes, not a rate)
  reconnaissance   collected        28   4%  [1, 18]  (1/28)
  resource-abuse   collected        16   caught 0 of 16 (n too small for a rate; ±19 pts)

  per source — a rate over one source is a rate ABOUT that source, not the world:
  cisco-mcp-scanner-evals         127   11%  [7, 18]  (14/127)
  skillcraft-audit                 42   71%  [56, 83]  (30/42)

false positives per population — the benign pool, an estimate, reported per source:
  skillmd-138k                   1996   7%  [6, 8]  (133/1996)

hard negatives — the precision probe, a census, never pooled with the estimate above:
  flagged 5 of 19 (26%) — each one a false positive on a deliberate near-miss

attribution — of caught malicious with a read-basis dimension, was the KIND named:
  31 of 68 correct (46%, [34, 57])
```

---

## 怎么诚实地读它

这张成绩单的设计目标是**让不诚实的读法变难**。有五条规则是写进输出本身的,而不是留给你的判断力。

**collected 与 constructed 永不合并。** `collected` 行建立在来自我们之外的样本上——采集来的配置、上游数据集、真实捕获——所以在它们上面的率是**关于世界**的主张。`constructed` 行建立在对已披露攻击的复现和合成 fixture 上;它们测的是**我们选进来的那些形状的覆盖度**,**永远不是**能预测野外的率,所以无论 N 多大都印成 `caught K of N`。把两个数加起来,得到的东西没有意义。

**一个分来源的率,是关于那个来源的率。** 同一个扫描器上 `cisco 11%` 和 `skillcraft 71%` 差了六十个百分点,汇总成一个数恰好会藏掉最值得知道的东西。**按来源发布,带 `n`,带来源数。** 这份语料正是在一个发布出去的 11.0% 被发现在完整总体上是 12.9% 之后建起来的。

**区间太宽时印计数,不印率。** 在百分比会误导的宽度以下,那一行写的是 `caught 0 of 16 (n too small for a rate; ±19 pts)`。这不是排版选择:来自少数几个样本的召回带着宽到不成其为数字的区间,印一个 `0%` 会邀请一个数据支撑不了的结论。

**census 和 estimate 永不合成一个数。** 19 个硬负样本是**逐个读过**的——每一个都是刻意构造的近似命中,其中任何一个被报都是你可以去看的一个真实误报。而几千个良性样本是一个总体的**抽样**。它们回答不同的问题,所以分开印。

**归类只在「维度依据是人读出来的」那些样本上计分。** 说清「这是哪一类攻击」,只能对照一个**有人引用 artifact 原文**建立起来的维度来评,不能对照一条批次规则指派的维度。所以归类的分母比你的命中数小——那是诚实的分母,不是缺斤少两。

**没被覆盖的样本不算通过。** 如果你的 runner 对某个样本什么都没输出,表头会写明,而下面的召回只覆盖被评分的那个子集。沉默**永远不会**被算作一次正确的良性判定。

---

## 注入故障 fixtures

扫描器必须扛住的一些东西,git 存不下来——目录权限位、命名管道、符号链接环。这些按需构造:

```bash
go run ./cmd/corpus fixtures                        # 列出，含每个断言什么
go run ./cmd/corpus fixtures --materialize /tmp/fx  # 构造出敌意树
<把你的扫描器指向 /tmp/fx/*>
go run ./cmd/corpus fixtures --restore /tmp/fx      # 删除前必须执行
```

现有六个。一个是**披露**测试:一个 `0111` 子目录,遍历列不出它——对此**什么都不说**的扫描器,等于把一个没读完的 skill 当成读过了。其余是**健壮性**:一个顶替 `SKILL.md` 的 FIFO(open-and-read 会不会永久挂住)、一个符号链接环(遍历会不会死循环)、一个逃逸到 `/etc/passwd` 的链接(宿主内容会不会被当成 skill 内容读)、一条 4096 层深的链、一个 8 GiB 稀疏 `.mcp.json`(解析前会不会把整个文件读进内存)。

这些是**逐个 fixture 的通过/失败,不是率**——单个反例就能定论。它们由**你的 runner** 判,不由 `corpus score` 判,因为通过条件取决于你的工具承诺了什么。`--restore` 不是可选的:`0111` 目录会挡住 `rm -rf` 所需的枚举。

---

## 这份语料**不能**告诉你什么

明说,因为一个藏起自己边界的基准,比一个小基准更糟。

| 边界 | 原因 |
|---|---|
| **配置面报的是覆盖度,不是率。** hooks、permission、connector 各只有几个复现形状 | 召回**率**需要独立的真实世界样本。对八个公开数据集的普查发现这些面一个都没有:有这些维度的来源全是合成的,而真实世界的来源带的都是已经覆盖过的注入/外泄形状。**天花板是世界,不是投入** |
| **有些维度是计数不是率** | filesystem、reconnaissance、resource-abuse 各 16–28 个样本。够发现系统性空洞,远不够区分 60% 和 80% |
| **良性不等于「审过、安全」** | 它的含义是*有人把它提交上去以供加载*。这些文件没有任何安全审查存在,我们也不声称有 |
| **高分不是安全认证** | 它测的是这份语料**包含**什么。一个公开语料覆盖的是其作者选的话题,不是威胁面 |

语料对自己的洞也用同样方式声明:`corpus stats` 会印出**每一个没有样本的 technique**和**每一个空的「维度 × 层级」格子**。一个声明出来的洞是你能据以行动的东西;一个藏起来的洞是谎言。

---

## 如果你想要规则级精度

上面的一切都不需要你在本仓库里登记任何条目。如果你想要的不止一个判定——而是**你的哪些规则**必须在某个样本上触发、哪些必须保持沉默——把你的工具加进 [`taxonomy/tools.yaml`](../taxonomy/tools.yaml),标签就可以携带 `expect.<你的工具>` 块,并按**你自己的**严重度梯子校验。两个刻度不同的扫描器可以标注同一个样本,而谁都不必采用对方的刻度。

这是叠在上面的**可选**精度。单靠 `truth` 块就能给任何扫描器打分,这正是把两半分开的意义——见 [`label-schema.md`](label-schema.zh-CN.md#两个半部分)。

---

## 引用本语料发布数字时

三条语料对自己执行、也请求引用方遵守的规则:

1. **按来源报,带 `n` 和来源数。** 绝不只给一个汇总平均。
2. **任何排除都必须出现在结论行里,并给出两个数字**——含它的和不含它的。一个悄悄丢掉了最差那组的分母,正是 11.0% 藏住 12.9% 的方式。
3. **说明你用的是哪个判定阈值**,因为把扫描器的多档状态压成一个词是一个**选择**,不是一个事实。

还有一条值得重复的禁令:*「这份语料里没有这种东西,所以我们的规则没问题」***不是一个论据**。这份语料覆盖的,只是它的来源覆盖过的。
