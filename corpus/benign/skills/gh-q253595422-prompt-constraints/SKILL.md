---
name: prompt-constraints
description: |
  生图 / 视频提示词约束引擎。把模糊需求、关键词、粗糙草稿或参考图，转成受约束、可校验、可直接投喂的生图（t2i / i2i）与视频（t2v / i2v / 多镜头）提示词。
  用于：写/优化/扩写生图提示词，写/优化视频提示词，从参考图反推提示词（图画文 / img2prompt），锁定角色·场景·风格一致性（character sheet / 角色三视图 / 身份锚点），写负面约束与回避清单，按模型适配（Nano Banana Pro、即梦 Seedream、GPT Image、Midjourney、FLUX、Seedance、可灵 Kling、Veo、Sora、Hailuo、MiniMax、LTX、Wan）。
  当用户提到「生图提示词 / 视频提示词 / prompt / 提示词 / 反推提示词 / 图画文 / 一致性 / 首帧图 / 分镜 / 运镜」时使用。
version: 1.0.0
license: MIT
---

# Prompt Constraints —— 生图 / 视频提示词约束引擎

核心主张：**提示词的质量不来自形容词的堆砌，而来自约束的清晰度。**

这个 skill 不生产「好看的话」，它生产**受约束的、可校验的、模型能稳定执行的指令**。

---

## 一、先路由，再动手

判断用户到底要什么，走对应路径：

| 用户意图 | 信号 | 路径 |
|---|---|---|
| 生图 · 文本生图 | 描述一个画面 / 关键词 | → `references/templates.md` §T1 + `references/image.md` |
| 生图 · 图生图 / 编辑 | 给图 + 要求改 | → `references/templates.md` §T2 + `references/image.md` |
| 生图 · 参考图反推 | 上传图，「反推 / 图画文 / img2prompt」 | → `references/templates.md` §T3 + `references/image.md` §二 |
| 视频 · 文生视频 | 描述一段动态 | → `references/templates.md` §V1 + `references/video.md` |
| 视频 · 图生视频 | 给首帧/参考图 | → `references/templates.md` §V2 + `references/video.md` |
| 视频 · 多镜头 / 分镜 | 时间轴、Shot 1/2/3 | → `references/templates.md` §V3 |
| 视频 · FPV / 路径控制 | 路线、航拍、编号停靠 | → `references/templates.md` §V4 |
| 一致性 · 角色 / 场景锁定 | 要跨图跨镜一致 | → `references/templates.md` §C1 + `references/consistency.md` |
| 粗稿扩写 / 翻译 / 变量模板 | 「优化 / 扩写 / 变专业 / 转英文 / 做成模板」 | → `references/image.md` §三、§四 |
| 按模型调优 | 点名 Nano Banana / Seedance / Veo… | → `references/models.md` |
| 写负面约束 | 「避免什么 / negative prompt」 | → `references/negative.md` |

**只问一个澄清问题**，且只问真正会改变结果的那个。信息不足时先按默认合理推断，不要问卷式盘问。

---

## 二、约束体系速查

全部方法论的骨架是**六层约束模型**。这里是速查版，完整定义、判定标准与自检见
[`references/constraints-core.md`](references/constraints-core.md)。

| 层 | 一句话约束 | 典型失误 |
|---|---|---|
| **L1 事实** | 不编造焦距、光圈、型号、品牌、IP、地点；不确定就描述可见的视觉结果 | 写 `85mm f/1.4` 但画面毫无依据 |
| **L2 媒介** | 明确目标媒介，并排除最容易混淆的错误媒介 | 想要写实却出了插画感 |
| **L3 结构** | 3—5 个核心锚点写进正向提示词**前 1/3**，维度按序不堆砌 | 十二个维度各写一句，画面糊成一团 |
| **L4 一致性** | 需要跨图跨镜稳定的元素，显式声明为不变量 | 第二张图换脸、换服装 |
| **L5 排除** | 排除项**具象化**、有针对性，不写抽象「no X」 | `no man-made structures` 完全无效 |
| **L6 参数** | 模型名/版本/时长/比例/分辨率**外置**到「推荐参数」行 | `--ar 16:9` 混进给 Gemini 的正文 |

在六层之外，还有两条贯穿全程的行为准则：

- **B1 保意图** —— 扩写是补维度，不是换主题。用户说「简单点 / 只要一句」就只出极简版。
- **B2 语言** —— 默认中文。中文用于结构与说明，英文用于模型执行；技术术语（FPV、one-shot、prompt、Seedance）保留英文原名。用户要英文或目标工具只吃英文时全英文。

---

## 三、输出契约

- **默认只出成品提示词**，不展示分析过程、推理链、不确定度清单。用户问了才解释。
- **双语对照**：中文版给理解和校对，`English:` 版给模型执行。英文用图像/视频模型惯用表达，不做机械直译。
- **可复制**：成品放代码块，单段自然语言，不是散落的关键词碎片（除非目标模型要求结构化多行）。
- **给选项时**：2—3 个**各自自洽完整**的变体，不要半成品拼盘。
- **收尾简短**：最多补一句「可调项」，让用户知道下一步拧哪个旋钮。

---

## 四、按需加载（不要一次性全读）

| 文件 | 内容 | 何时读 |
|---|---|---|
| [`references/constraints-core.md`](references/constraints-core.md) | 六层约束模型完整定义与自检 | 复杂任务、需要解释方法论时 |
| [`references/image.md`](references/image.md) | 12 维图像维度、参考图反推流程、复杂度分级 | 所有生图任务 |
| [`references/video.md`](references/video.md) | 视频提示词结构、时间轴、POV 物理约束、路径控制 | 所有视频任务 |
| [`references/consistency.md`](references/consistency.md) | 三层锚点、character sheet 工作流、漂移诊断 | 需要跨图跨镜稳定 |
| [`references/negative.md`](references/negative.md) | 排除约束写法规范、分层词池 | 出负面词前 |
| [`references/vocab.md`](references/vocab.md) | 中英词汇银行（风格/色彩/光影/镜头/材质/情绪） | 需要词穷时 |
| [`references/models.md`](references/models.md) | 各模型偏好与禁忌、提示词形态、跨模型迁移 | 用户点模型名时 |
| [`references/templates.md`](references/templates.md) | T1—T3 / V1—V4 / C1 模板 | 直接套用 |
| [`references/checklists.md`](references/checklists.md) | 交付前质检清单 | **每次交付前必走** |

---

## 五、交付前

一切产出都要过 [`references/checklists.md`](references/checklists.md)。
不通过就改，**不要带着已知缺陷交付**。

---

## 六、来源与整合

本 skill 的方法是**整合提炼**，不是任何单一仓库的复制。方法学来源如下（均为公开仓库，用于启发结构）：

| 仓库 | 借鉴的部分 |
|---|---|
| `LunarXuan/image-prompt-reverse` | 图像 12 维分析框架、媒介边界、视觉锚点优先级、反推输出格式 |
| `Square-Zero-Labs/video-prompting-skill` | 全局视频提示词规则、模型路由、character sheet 工作流 |
| `zhouwei713/fpv-immersive-video-prompting` | 时间轴、POV 物理约束、编号停靠 / 路径控制、失败模式 |
| `TanShilongMario/PromptSkill4image` | 中文优先路由、复杂度分级、变量提炼、词汇银行 |
| `huangserva/skill-prompt-generator` | 结构化类目框架、约束分级、质检清单 |
| `YouMind-OpenLab/ai-image-prompts-skill` | 提示词库检索与推荐形态 |

六层约束模型、时间轴容量表、模型适配检查清单等为本项目原创整合。
