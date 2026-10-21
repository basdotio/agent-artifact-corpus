# 设计师个人网站风格原型库（zhong-portfolio-archetypes）

面向设计师 / 创意开发者的个人网站选型技能：从 174 个优秀作品集网站实测提炼出 11 种风格原型。每种原型都给出版式骨架、字体、配色、动效、技术栈、反模式和代表站，帮 AI 把“我想要一个好看的个人网站”变成**有依据的风格决定**，再落到能直接写进代码的规范。

> 站点清单来自设计师 RicoUI（[@ricouii](https://x.com/ricouii)）公开分享的[《180 个优秀设计师 / 创意开发者个人网站清单》](https://x.com/ricouii/status/2111384617127387211)，收集与筛选归功于原作者。

## 核心思路

1. **先定原型，再谈细节**：按身份与目标、手里的作品、性格与约束三层筛选，给出 2–3 个候选原型和取舍理由。
2. **数据和判断分开**：原型文档里的百分比、中位数、字体、配色来自 174 站实测数据；决策表的首选 / 备选是编辑判断，冲突时向用户说明。
3. **只学模式，不搬作品**：参考站只给链接和“看什么”，不照搬文案、插画、照片和品牌元素。
4. **一个记忆点原则**：想安静又想被记住时，主原型保持克制，记忆点只做一个。

## 11 种原型

| 原型 | 中文 | 一句话 | 样本 |
|---|---|---|---|
| `poster-type` | 巨型字体海报型 | 首屏被超大名字 / 标语占满 | 36 |
| `work-grid` | 作品优先型 | 首屏就是作品图墙或项目索引 | 23 |
| `saas-landing` | 商业落地页型 | 服务、客户 logo、预约 CTA | 16 |
| `immersive-3d` | 沉浸式 3D 型 | 全屏 WebGL 场景、电影感光影 | 15 |
| `minimal-text` | 极简文字型 | 小字号单栏自述，靠文字和细节 | 15 |
| `statement-hero` | 一句话宣言型 | 一句宣言 + 少量精选作品 | 14 |
| `bento-cards` | Bento 卡片型 | 圆角卡片拼成仪表盘式网格 | 12 |
| `editorial-serif` | 编辑杂志型 | 衬线大标题、杂志版式 | 12 |
| `illustrated-world` | 插画世界型 | 插画 / 纸艺构成可探索场景 | 11 |
| `skeuo-desktop` | 拟物桌面型 | 桌面、操作系统、实物道具隐喻 | 11 |
| `experimental-art` | 实验艺术型 | 故障、像素、CRT、反常规导航 | 9 |

## 安装

Codex：

```bash
git clone https://github.com/jiamizhongshifu/zhong-portfolio-archetypes.git ~/.codex/skills/zhong-portfolio-archetypes
```

Claude Code：

```bash
git clone https://github.com/jiamizhongshifu/zhong-portfolio-archetypes.git ~/.claude/skills/zhong-portfolio-archetypes
```

装好后新开一个对话，说“帮我做个人网站 / 作品集”即可自动触发，也可以直接点名 `zhong-portfolio-archetypes`。

## 使用方法

直接描述你的情况，例如：

> 我是 5 年经验的 B 端产品设计师，想去海外科技公司。有 3 个能公开的案例，其余在 NDA 下。性格偏安静，但希望网站有一个让人记住的细节。会写一点前端，大概两周时间。

技能会依次：

1. 摸清身份与目标、作品条件、性格与约束；
2. 按决策表给出 2–3 个候选原型和取舍；
3. 按原型规范输出设计 brief、设计 token，或直接写首页代码；
4. 用数据检索 3–5 个最贴近的参考站，说明每个看什么。

上面这个例子的完整产出见 [`examples/product-designer/`](examples/product-designer/)：选型 brief + 单文件首页（由 1.0.0 版本生成，个别措辞与当前文档略有出入）。

### 参考站检索

脚本只依赖 Python 3 标准库：

```bash
python3 scripts/find_refs.py --archetype editorial-serif --theme light
python3 scripts/find_refs.py --role product-designer --kind personal
python3 scripts/find_refs.py --builder framer --motion high
python3 scripts/find_refs.py --stats     # 各原型数量
python3 scripts/find_refs.py --values    # 所有字段的可选值
```

## 方法与数据

| 环节 | 做法 |
|---|---|
| 抓取 | 2026-10-18，无头 Chromium，桌面 1440×900 / 移动 390×844 |
| 自动提取 | 搭建方式、前端框架、动效库、WebGL、字体、首屏标题字号、截图配色、自定义光标、加载动画、进站门 |
| 归类 | 人工逐张看截图，归入 11 种原型（主 + 次） |
| 剔除 | 6 个站无效：1 个被限流、1 个有人机验证（未绕过）、1 个域名被垃圾站占用、3 个域名停放 |

重新抓取与构建数据（可选）：

```bash
npm i playwright && npx playwright install chromium
pip install pillow
node tools/crawl.js tools          # 截图与特征写入 tools/screenshots、tools/data/crawl
python3 tools/build.py tools       # 生成 tools/data/sites.json 与截图总览页 tools/gallery.html
```

## 文件结构

```
zhong-portfolio-archetypes/
├── SKILL.md                        # 技能入口：工作流程、跨原型共性、通用底线
├── VERSION
├── CHANGELOG.md
├── agents/
│   └── openai.yaml                 # Codex 显示名与默认提示
├── references/
│   ├── decision-guide.md           # 选型决策表与条件冲突处理
│   ├── case-study.md               # 案例详情页结构、NDA 作品呈现
│   └── archetypes/*.md             # 11 种原型的详细规范
├── assets/
│   └── sites.json                  # 174 个站的特征数据
├── scripts/
│   └── find_refs.py                # 参考站检索
├── tools/                          # 数据抓取与构建（可选）
│   ├── crawl.js
│   ├── build.py
│   ├── gallery_template.html
│   └── data/{sites_raw.tsv, archetypes.json}
└── examples/product-designer/      # 试用示例：brief.md + index.html
```

## 适用场景与局限

- 适合设计师、设计工程师、创意开发者、插画师和小工作室的个人网站 / 作品集选型、改版与评估。
- 数据是 2026-10-18 的一次快照，网站会改版或下线；推荐参考站前请先打开确认。
- 字体分类靠字体名判断，自定义命名的字体会被误归为无衬线；站点类型和身份标签部分按标题关键词自动推断，可能有误。
- 截图只能看到静态画面，悬停、拖拽、声音等交互需要亲自体验。
- 仓库不包含任何第三方网站的截图、文案或素材，只提供链接；各网站版权归其作者所有。

## License

MIT。站点清单来自 RicoUI 的公开分享，引用时请注明出处。
