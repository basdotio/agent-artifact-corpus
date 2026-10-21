# Prompt Constraints

> **生图 / 视频提示词约束引擎** —— 少一点形容词，多一点约束。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-compatible-blue.svg)](#安装)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](CHANGELOG.md)

一个 Agent Skill，把模糊需求、关键词、粗糙草稿或一张参考图，转成**受约束、可校验、可直接投喂**的生图与视频提示词。

支持生图（t2i / i2i）、视频（t2v / i2v / 多镜头）、参考图反推、角色一致性锁定、负面约束、多模型适配。

---

## 为什么需要它

大多数人写提示词的方式，是把想到的形容词都堆上去：

```
一个非常高级的、有电影感的、氛围感很强的赛博朋克城市，超高清，8K，大师作品
```

这段话的问题不是「不够华丽」，而是**没有一条是可以被执行的约束**：

- 「电影感」——是光比？是色温？是镜头关系？模型不知道。
- 「8K」——你以为在描述原图，模型只当作一个虚高的期望。
- 「高级」——这是一个评价，不是一个视觉特征。

结果是：每次生成都不一样，改一处崩一片，永远无法稳定复现。

**这个 skill 的做法是换一套语言**——不说「要什么感觉」，只说「约束是什么」。

---

## 核心方法论：六层约束模型

提示词失控，几乎总能归因到某一层约束缺失。

```
L1 事实   → L2 媒介   → L3 结构   → L4 一致性 → L5 排除   → L6 参数
不编造        定边界      排顺序      锁变量        划红线      剥离元数据
```

| 层 | 一句话约束 | 典型失误 |
|---|---|---|
| **L1 事实** | 不编造焦距、光圈、型号、品牌、IP、地点；不确定就描述可见的视觉结果 | 写 `85mm f/1.4` 但画面毫无依据 |
| **L2 媒介** | 明确目标媒介，并排除最容易混淆的错误媒介 | 想要写实却出了插画感 |
| **L3 结构** | 3—5 个核心锚点写进正向提示词**前 1/3**，维度按序不堆砌 | 十二个维度各写一句，画面糊成一团 |
| **L4 一致性** | 需要跨图跨镜稳定的元素，显式声明为不变量 | 第二张图换脸、换服装 |
| **L5 排除** | 排除项**具象化**、有针对性，不写抽象「no X」 | `no man-made structures` 完全无效 |
| **L6 参数** | 模型名/版本/时长/比例/分辨率**外置**到「推荐参数」行 | `--ar 16:9` 混进给 Gemini 的正文 |

层层可自检。排查时逐层对照，基本都能定位到具体是哪一层缺了。

完整定义、判定标准与自检项见 [`references/constraints-core.md`](references/constraints-core.md)。

---

## 安装

这是一个标准的 Agent Skill（纯 Markdown，无依赖、无构建）。把整个
`prompt-constraints/` 目录放进你所用平台的 skills 目录即可。

```bash
git clone https://github.com/q253595422/prompt-constraints.git

# WorkBuddy
cp -r prompt-constraints ~/.workbuddy/skills/

# Claude Code
cp -r prompt-constraints ~/.claude/skills/

# Codex
cp -r prompt-constraints ~/.codex/skills/

# 项目级（Cursor / 其他）
mkdir -p .cursor/skills && cp -r prompt-constraints .cursor/skills/
```

安装后，当你说「帮我写个生图提示词」「这张图反推一下提示词」「做个 10 秒的视频提示词」时，
Agent 会自动加载这个 skill。

---

## 快速上手

### 例 1 · 生图（模糊需求 → 可执行提示词）

**输入**
```
帮我做个赛博朋克城市夜景海报，竖版
```

**输出**（节选，完整见 [`examples/text-to-image-poster.md`](examples/text-to-image-poster.md)）
```text
中文：低机位仰拍视角的雨夜赛博朋克都市街景，两座高塔夹击形成强烈的透视收束，
画面中央是一条被雨水浸透的街道，湿滑路面完整倒映上方霓虹招牌的品红与青蓝双色光斑；
沿街密集的垂直灯牌与全息广告构成纵深光廊，空气中悬浮着雨雾，被光源切出数道清晰的体积光束；
主色为高饱和品红与青蓝的冷暖对撞，点缀少量琥珀色灯窗；
金属与玻璃幕墙呈湿润高反光质感，沥青路面泛着油亮镜面；
前景积水倒影 → 中景行走的人影剪影 → 背景朦胧的高塔轮廓，三层空间拉开空气透视；
由密集垂直光带与冷色调构成的秩序感与疏离感；电影级写实摄影质感，轻微胶片颗粒与辉光，高细节密度。
```

**这里做了 4 件事**：`电影级写实摄影` 定了媒介（L2）；四组视觉锚点前置（L3）；「疏离感」被
`密集垂直光带 + 冷色调` 解释（L1）；比例被移出正文（L6）。

### 例 2 · 图生视频（只描述变化）

**输入**
```
用这张图做首帧，要一个 10 秒缓慢推近的镜头
```

**输出**（节选，完整见 [`examples/image-to-video.md`](examples/image-to-video.md)）
```text
使用上传图片作为首帧视觉锚点，不重新描述画面内容。

镜头运动：从全景缓慢匀速推近，10 秒内推进至中景，焦点始终保持在前景主体，
机位高度不变，无侧向位移，加速度先缓后匀、结尾轻微减速收住。
...
保持：主体身份与五官、服装轮廓、构图中心位置、光线方向与色温、主色调、
背景建筑结构与整体写实风格不变。
```

**关键约束**：图已经是视觉锚点，正文不重复描述画面，只写运动、镜头、表演、声音（L3）。
时长不进正文（L6）。

### 例 3 · 角色一致性（防止跨镜头换脸）

先出角色工作表，再以它为参考生成场景静帧，最后从静帧生成视频镜头。

完整流程见 [`examples/character-consistency.md`](examples/character-consistency.md)。

---

## 目录结构

```
prompt-constraints/
├── SKILL.md                        # skill 入口：路由 + 速查 + 输出契约
├── README.md                       # 本文件
├── LICENSE                         # MIT
├── CONTRIBUTING.md                 # 贡献指南
├── CHANGELOG.md                    # 版本记录
├── .gitattributes                  # 统一换行符为 LF
├── .gitignore
├── references/                     # 按需加载的知识库
│   ├── constraints-core.md         # ★ 六层约束模型
│   ├── image.md                    # 12 维图像维度 + 参考图反推 + 复杂度分级
│   ├── video.md                    # 视频结构 + 时间轴 + POV + 路径控制
│   ├── consistency.md              # 三层锚点 + character sheet + 漂移诊断
│   ├── negative.md                 # 排除约束规范 + 分层词池
│   ├── vocab.md                    # 中英词汇银行
│   ├── models.md                   # 模型适配表 + 跨模型迁移
│   ├── templates.md                # T1—T3 / V1—V4 / C1 模板
│   └── checklists.md               # 交付前质检清单
└── examples/                       # 经实测的完整用例
    ├── text-to-image-poster.md
    ├── image-to-video.md
    └── character-consistency.md
```

**设计取舍**：入口保持轻薄（`SKILL.md`），重内容全部下沉到 `references/`，
**按需加载**而不是一次性塞进上下文。这是 Agent Skill 的上下文预算约束决定的，不是文件洁癖。

---

## 支持范围

| 类别 | 已覆盖 |
|---|---|
| **生图** | Nano Banana Pro / Nano Banana 2、Seedream 即梦、GPT Image、Midjourney、FLUX、Stable Diffusion、Ideogram、Imagen |
| **视频** | Seedance 2.0 / 2.5、可灵 Kling、Veo 3 / 3.1、Sora、Hailuo / MiniMax H3、LTX-2 系列、Wan 2.2 / Animate 2、Ovi |
| **任务类型** | 文生图、图生图 / 编辑、参考图反推、文生视频、图生视频、多镜头分镜、FPV / 路径控制、角色一致性 |

模型的能力边界以官方文档为准；`references/models.md` 中的归纳属经验性总结，已明确标注。

---

## 设计原则

1. **不编造。** 没有依据的参数、品牌、身份一律不写。
2. **不堆砌。** 五个维度写透，胜过十二个维度写平。
3. **具象化。** 「高级感」必须翻译成可见的视觉元素。
4. **可校验。** 每条约束都能判定通过或不通过。
5. **参数与画面分离。** 给模型的指令和给工具的设置，各归各位。
6. **按需加载。** 上下文是预算，不是垃圾桶。

---

## 常见问题

**Q：它和「某个模型的提示词 skill」有什么区别？**

模型专属 skill 教你「这个模型怎么用」。这个 skill 教你「怎么让提示词受控」——是**跨模型的
方法论层**，与具体模型正交。两者可以叠加使用。

**Q：为什么默认中文，英文只用于执行？**

中文用于结构理解与校对，英文用于模型执行，各取所长。中文模型（Seedream、可灵、Seedance）
直接用中文版本即可。

**Q：负面提示词是不是越多越好？**

不是。抄固定套餐会稀释有效项，甚至压掉你想要的正面特征。规范做法是**按当前这张图/这个
镜头的真实风险定制 8—15 条**。见 [`references/negative.md`](references/negative.md)。

**Q：为什么时长、比例不能写进提示词？**

因为模型会把它当成画面内容的一部分去「理解」，而不是当成生成设置。
正确做法是外置成「推荐参数」行。例外：目标模型的官方 schema 本身要求这些字段时
（如 MiniMax H3 的对齐指令、Seedance 多镜头时间轴），按官方格式写。

**Q：可以只用其中一部分吗？**

可以。每个 `references/` 文件都能独立取用。但六层约束模型是骨架，建议至少读那一份。

---

## 贡献

欢迎纠错、补充模型、扩充词库、提交实测示例。动手前请先读
[CONTRIBUTING.md](CONTRIBUTING.md)——本项目有**明确的写作约束**（不许堆形容词、
不许写抽象否定、不许编参数），不满足的 PR 不会被合并。

## 致谢与来源

本项目的方法论是**整合提炼**，不是任何单一仓库的复制。结构灵感来自以下公开仓库：

| 仓库 | 借鉴的部分 |
|---|---|
| [LunarXuan/image-prompt-reverse](https://github.com/LunarXuan/image-prompt-reverse) | 图像 12 维分析框架、媒介边界、视觉锚点优先级、反推输出格式 |
| [Square-Zero-Labs/video-prompting-skill](https://github.com/Square-Zero-Labs/video-prompting-skill) | 全局视频提示词规则、模型路由、character sheet 工作流 |
| [zhouwei713/fpv-immersive-video-prompting](https://github.com/zhouwei713/fpv-immersive-video-prompting) | 时间轴、POV 物理约束、编号停靠 / 路径控制、失败模式 |
| [TanShilongMario/PromptSkill4image](https://github.com/TanShilongMario/PromptSkill4image) | 中文优先路由、复杂度分级、变量提炼、词汇银行 |
| [huangserva/skill-prompt-generator](https://github.com/huangserva/skill-prompt-generator) | 结构化类目框架、约束分级、质检清单 |
| [YouMind-OpenLab/ai-image-prompts-skill](https://github.com/YouMind-OpenLab/ai-image-prompts-skill) | 提示词库检索与推荐形态 |

六层约束模型、时间轴容量表、模型适配检查清单等为本项目原创整合。
各来源仓库的许可证归其各自作者所有。

## License

[MIT](LICENSE) © 2026 q253595422
