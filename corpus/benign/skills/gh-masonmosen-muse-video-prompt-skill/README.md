# Muse Video Prompt Skill

**A battle-tested workflow skill for Muse's built-in video generation (Muse Video): from prompt to final cut.**

[English](#english) | [简体中文](#简体中文-1)

---

## English

The hardest part of AI short video isn't hitting "generate" — it's **writing prompts that land, stitching long videos coherently, and keeping characters consistent**.
This skill is a production-hardened workflow for Muse's built-in video generation:

- **Six-part prompt template**: duration & aspect / character / setting / timed beats / camera language / audio / dialogue / restrictions — plus POV lifestyle, talking-head, and multi-segment variants
- **Multi-segment stitching**: ~10s per clip is a hard limit? Split by beats, chain with snapshot IDs for continuity, stitch losslessly with ffmpeg into 30s+
- **Frame-extraction verification**: auto-extract frames after every generation; what matched the prompt and what drifted, in writing
- **Honesty-first**: face-lock is weak on built-in video, reference likeness isn't guaranteed — limits stated upfront, never oversold
- **Growing case library**: every experiment becomes a case card (prompt points / result / drift / lesson)

### How it differs from `muse-video-skill`

[LuoJiangYong/muse-video-skill](https://github.com/LuoJiangYong/muse-video-skill) (MIT) is an excellent **pre-production engine** (script / storyboard / art direction → compiled downstream model calls); its engineering ideas (thin center + on-demand loading + deterministic scripts) are this skill's architectural blueprint.
This skill is positioned differently: **a hands-on closed loop for built-in video** — write the prompt, generate, stitch, verify, all in one place, no downstream tools required.

### Layout

```
muse-video-prompt-skill/
├── SKILL.md                  # Entry: workflow + operating rules (Agent Skills format)
├── CONSTITUTION.md           # Design constitution: honesty / final cut / short loop / compound / lean
├── README.md
├── LICENSE                   # MIT
├── references/               # On-demand domain knowledge
│   ├── prompt-template.md    # Six-part prompt template + three variants
│   ├── model-notes.md        # Built-in Muse Video capability limits (measured)
│   ├── consistency.md        # Character-consistency tactics
│   ├── dialogue.md           # Dialogue conventions (Taiwan-accented Mandarin default)
│   ├── stitch-workflow.md    # Segment → stitch → verify
│   └── cases/                # Case library (INDEX + dated case cards)
└── bin/
    └── extract_frames.py     # Frame-extraction self-check script
```

### Install

```bash
git clone https://github.com/masonmosen/muse-video-prompt-skill.git
# Drop into your agent's skills directory, e.g.:
#   Claude Code → ~/.claude/skills/muse-video-prompt-skill/
```

### Fits / doesn't fit

- ✅ Video prompt experiments, short video generation, multi-segment long videos, prompt craft
- ❌ Projects needing strong face-lock → use Seedance / third-party video models (this skill will tell you so)

---

## 简体中文

做 AI 短视频最难的不是点"生成"，而是**提示词写得准、长片拼得连贯、人物不崩**。
这个 skill 是一套为 Muse 内置视频打磨的实战工作流：

- **六段式提示词模板**：时长画幅 / 人物 / 场景 / 节拍时间轴 / 镜头语言 / 声音 / 对白 / 限制清单，另有 POV 生活流、口播、多段长片三个变体
- **多段拼接**：单条 10 秒是硬上限？按节拍拆段，用 snapshot 接续保连贯，ffmpeg 无损拼成 30 秒+
- **抽帧验证**：每段自动抽帧自查，哪些吃进提示词、哪些偏了，白纸黑字写清楚
- **诚实线**：内置视频锁脸弱、参考图不一定像——动手前先说边界，不拿话术包装
- **案例库**：每个实验沉淀一张案例卡（提示词要点 / 结果 / 偏差 / 教训），随用随长

### 和 `muse-video-skill` 的区别

[LuoJiangYong/muse-video-skill](https://github.com/LuoJiangYong/muse-video-skill)（MIT）是优秀的**前期策划引擎**（剧本/分镜/美术 → 编译成下游模型指令），它的工程化思想（thin center + 按需加载 + 确定性脚本）是本 skill 的架构蓝本。
本 skill 定位不同：**内置视频的实战闭环**——写完提示词直接生成、拼接、验证，全流程在一套里跑完，不依赖下游工具。

### 适用与不适用

- ✅ 视频提示词实验、短视频生成、多段拼长片、提示词写法打磨
- ❌ 需要强锁脸的项目 → 走 Seedance / 第三方视频模型（本 skill 会明确告诉你）

## License

MIT © 2026 Mason Mosen
