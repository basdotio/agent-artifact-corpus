# Alex Lin 个人网站 · 选型 brief

> 依据：`portfolio-archetypes` skill（数据来源：RicoUI 的 180 站清单，174 个有效）。参考站由 `scripts/find_refs.py` 检索，“看什么”取自各原型文档的代表站说明；链接请自行打开查看，不要搬运其中素材。

## 1. 需求摘要（工作流程第 1 步）

| 维度 | 用户情况 | 对选型的含义 |
|---|---|---|
| 身份与目标 | 5 年 B 端 SaaS 产品设计师，明年投海外科技公司 | 读者是招聘方 / 设计经理，要 30 秒内看懂“你是谁、做过什么、有多深” |
| 手里的作品 | 3 个可公开案例（数据看板改版、设计系统、移动端 onboarding），其余 NDA | 作品少 + 涉密 → 避开 `work-grid`；以界面 / 产品为主 → `statement-hero`、`bento-cards` |
| 性格与约束 | 偏安静，但想要一个让人记住的小细节；会写一点前端；约两周 | 安静 → `statement-hero`、`minimal-text`；“被记住”只靠**一个**细节实现，不换张扬原型；两周 + 能写代码 → 手写单页可行，不需要 Framer |

## 2. 候选原型（工作流程第 2 步）

### 候选 A：`statement-hero`（主）+ 一个 `minimal-text` 式的“藏起来的细节” —— **推荐**

- **理由**：决策表“产品 / UX 设计师求职”首选；“作品少或涉密”“以界面 / 产品为主”“想要安静、可信”三条筛选都命中。一句具体的宣言 + 3 个大案例卡，正好匹配“精选 2–4 个大案例”的建议，3 个案例不显得少。
- **短板与补法**：原型文档明说它“容易显得没特点，需要靠作品和细节撑”。用 `minimal-text` 的思路补——只做**一个**精致细节，而不是加 3D / 粒子：
  - 页脚的“时区重叠”小组件：显示 Alex 的本地时间，并根据访问者时区算出“我们的工作时间有 X 小时重叠”。对海外求职是有信息量的细节，不是纯装饰。
  - NDA 项目用“打码条”列出（行业、规模、角色可见，名称被黑条遮住），说明“可在面试中走查”。把 NDA 的劣势变成可信度信号。
- **代价**：需要一句写得很具体的宣言（给谁、做了什么、结果如何），以及 3 张高质量案例封面。两周内手写 HTML/CSS 足够；不需要 three.js（原型数据里 36% 用 three.js 放首屏 3D 小物件，这里刻意不用，保持安静）。
- **参考站**（`find_refs.py --archetype statement-hero --kind personal`）：
  - #61 [Nataliatimea](https://nataliatimea.com/)：宣言前半句黑、后半句灰的层次处理。
  - #53 [Mr March](https://www.mr-march.com/)：产品设计师作品集，开场方式直接（role 标为 product-designer）。
  - #94 [Ivan Duzhak](https://www.ivanduzhak.com/)：头像 + 一句粗体身份，极度直接，完全静态。
  - #179 [Xavi Nogueres](https://www.xavinogueres.work/)：静态、浅暖灰底的克制版本。

### 候选 B：`minimal-text`（主）+ `experimental-art` 点缀（决策表“常见组合”里的 #85 模式）

- **理由**：最安静、最适合 NDA 多的人；“文案就是设计”，适合会写的人；几天就能上线，两周还能把一个小交互打磨到很精。
- **代价**：几乎没有大图，3 个界面案例的视觉优势被浪费（决策表“高质量作品图多 → 避免 minimal-text”）；读者若不点进案例，很难判断 B 端复杂度。这个原型在数据里更偏设计工程师 / 写作者，对“5 年产品设计师”可能显得轻。
- **参考站**（`find_refs.py --archetype minimal-text --motion static,low`）：
  - #85 [Rauno Freiberg](https://rauno.me/)：极简框架里藏一个顶级交互细节。
  - #174 [Perry Wang](https://www.perryw.ca/)：产品设计师，留白到极致的两行字首页。
  - #13 [Juan Manuel Cornejo](https://juanmnl.com/)：product / web designer，用等宽字 + 语法高亮写自述。

### 候选 C：`bento-cards`

- **理由**：B 端 SaaS 设计师做“仪表盘式”首页有天然的叙事呼应；能把设计系统、看板、onboarding、工具栈、所在时区各放一格。
- **代价**：原型文档警告“只有 1–2 类作品的人格子会空”“为了填格子放无意义的装饰卡”。3 个案例 + NDA 很容易出现填充卡；移动端需要单独重排。视觉上比 A 更“热闹”，与“偏安静”有张力。
- **参考站**（`find_refs.py --archetype bento-cards`）：
  - #176 [Yann-Edern Gillet](https://yannglt.com/)：Linear 产品设计师，深色小卡片承载文章 / 作品 / 身份。
  - #7 [Noman Ijaz](https://iamnoman.com/)：左侧短简介 + 右侧原型作品卡片墙。
  - #175 [Kuldar Kalvik](https://kuldar.com/)：实时时间这类“活的小组件”的做法。

## 3. 推荐

**选 A：`statement-hero` 为主，借 `minimal-text` 的“只做一个精致细节”原则。**

取舍：B 最安静但浪费可公开的界面作品、显得轻；C 最贴 B 端题材但作品数量撑不满格子，也偏热闹。A 在“快速被看懂”和“专业可信”上最稳，短板（没特点）可用一个有信息量的细节补足，不需要换到张扬的原型。

## 4. 设计规范（来自 `references/archetypes/statement-hero.md`，按本例落地）

| 项 | 规范 | 本例取值 |
|---|---|---|
| 版式 | 左上名字、右上导航；2–4 行宣言；小字 Currently / Previously；下接 2–4 个大案例 | 宣言 3 行；案例 01 通栏、02/03 两列；之后是 NDA 打码列表、About、页脚 |
| 宣言字号 | 48–96px，中位 67px；句子大小写，0 个全大写 | `clamp(36px, 6.4vw, 80px)`；390px 宽约 36px（文档没给移动端值，自定） |
| 宣言排版 | 字重 400–500，行高 1.05–1.15，字距 -0.02 到 -0.03em | 450 / 1.08 / -0.028em |
| 字体 | 无衬线为主，免费替代 Inter Display / Geist / Satoshi / Switzer；一个词换 Instrument Serif 斜体 | `Geist` + `Instrument Serif` italic（Google Fonts），等宽小字 `Geist Mono` |
| 配色 | 浅色、近单色，重点词灰色或一个强调色 | 底 `#f6f5f2`，字 `#141414`，次要 `#77756f`；唯一强调色 `#3b5bfd` 只用在 3 处：衬线词下划线、时区重叠条、焦点环 |
| 动效 | 宣言逐词浮现；案例卡悬停图片轻放大 + “View” 圆标 | 两者都做；`prefers-reduced-motion: reduce` 时全部关闭，文字直接显示 |
| 技术 | 自写或 Framer；Next.js + MDX 写案例最方便 | 首页示例为单文件 HTML/CSS/原生 JS；正式站建议 Astro 或 Next.js + MDX 承载案例页 |

### 文案方向（避开反模式“空话宣言”）

- 宣言：“I design *calm* interfaces for complex B2B software — dashboards, design systems and the first five minutes of a product.”
- 每个案例卡写结果而不是过程：例如“Dashboard redesign · Time-to-insight −38%”。数字为占位，需替换为真实且可公开的指标。

## 5. 两周排期建议

| 天 | 事项 |
|---|---|
| 1–2 | 写宣言、About、3 个案例的一句话结果；整理 NDA 项目的可公开元信息 |
| 3–5 | 首页（本示例为起点）+ 设计 token |
| 6–10 | 3 个案例详情页（问题 → 约束 → 决策 → 结果），每页 1 张主图 + 3–5 张过程图 |
| 11–12 | 时区细节打磨、可访问性检查（键盘、对比度、reduced-motion） |
| 13–14 | 性能、OG 图、域名部署；找 2 位海外设计师读一遍英文文案 |
