# 让带「代码执行」的 AI 盲玩

适用于：ChatGPT（代码解释器 / 高级数据分析）、Claude（带代码执行）、或任何自带 Python 沙箱的 agent。

## 步骤

1. 把 **`fishing.py`**（盲玩版）上传给你的 AI。
2. 发一段类似下面的话给它（按你和 AI 的关系随意改口吻）：

> 这是我给你做的一个文字钓鱼小游戏，你来当玩家。请 `import fishing`，然后像真的在钓鱼一样、靠 `fishing.cmd("指令")` 返回的文字来体验和决策：
>
> ```python
> import fishing
> print(fishing.cmd("help"))     # 先看规则
> print(fishing.cmd("status"))   # 看状态
> print(fishing.cmd("cast"))     # 抛竿……看钓到什么
> ```
>
> ⚠️ 别去解码 / 查看文件里那段打包数据（那是引擎，提前看了就剧透了——你会提前知道有哪些鱼、稀有鱼在哪、概率多少）。当个蒙着眼的玩家，靠抛竿去发现。
>
> 想刷量就用 `cast 10`（一次连钓 10 竿）或 `cast 20 stop=rare`（钓到稀有就停），省得一竿一条。玩一会儿跟我说说手感呗～

## 小贴士

- **存档**会生成在 AI 沙箱里的 `fishing_save.json`。沙箱重置 = 进度清空；想长期玩，让 AI 每次把这个文件留着、或你帮它存。
- 想换一局全新的：`fishing.cmd` 不管用，用 `fishing.new_game(种子)`。
- 同一个种子 + 同样的指令顺序，结果完全一样（方便你俩复盘同一局）。
