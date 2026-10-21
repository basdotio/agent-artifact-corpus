# 选型决策表

先看**身份与目标**定大方向，再用**作品条件**和**性格 / 约束**筛掉不合适的。

## 1. 按身份与目标

| 身份 / 目标 | 首选 | 备选 | 理由 |
|---|---|---|---|
| 产品 / UX 设计师求职 | `statement-hero` | `minimal-text`、`editorial-serif`、`bento-cards` | 招聘方要快速看懂“你是谁、做过什么”，克制比炫技重要（编辑判断，见下方数据说明） |
| 设计工程师 / 前端 | `minimal-text` | `skeuo-desktop`、`bento-cards` | 细节交互本身就是作品；拟物桌面适合展示动手能力 |
| 创意开发者炫技 | `immersive-3d` | `experimental-art`、`poster-type` | 网站即作品，重 WebGL / GSAP |
| 品牌 / 平面 / 艺术指导 | `poster-type` | `editorial-serif`、`work-grid` | 字体与构图就是专业能力的证明 |
| 插画师 / 动画师 | `illustrated-world` | `work-grid` | 画风就是品牌；作品多时直接用作品墙 |
| 摄影 / 视觉作品多 | `work-grid` | `editorial-serif` | 让图说话，界面退后 |
| 自由职业接单 | `saas-landing` | `statement-hero` | 需要服务说明、案例、报价 / 预约入口 |
| 小工作室获客 | `saas-landing` | `poster-type`、`editorial-serif` | 客户 logo + 案例 + CTA；有调性的工作室用海报或杂志 |
| 个人品牌 / 写作者 | `minimal-text` | `editorial-serif` | 以文章和思考为主体 |

> **数据说明**：35 个个人产品 / UX 设计师站分布很分散——编辑型、极简型、作品型各 5 个，宣言型、Bento 型、海报型各 4 个，没有绝对主流。所以这一行的首选是基于“招聘方扫读效率”的判断，不是数据多数。用户有强烈个人风格时，海报型、编辑型同样成立。

## 2. 按作品条件筛

| 条件 | 适合 | 避免 |
|---|---|---|
| 高质量作品图 / 视频多 | `work-grid`、`editorial-serif`、`poster-type` | `minimal-text`（浪费作品） |
| 作品少或涉密（NDA） | `minimal-text`、`statement-hero`、`skeuo-desktop` | `work-grid`（呈现方式见 `case-study.md`） |
| 以界面 / 产品为主 | `statement-hero`、`bento-cards` | `illustrated-world` |
| 有自己的画风 / 插画能力 | `illustrated-world` | `saas-landing` |
| 有 3D / 着色器能力 | `immersive-3d`、`experimental-art` | — |

## 3. 按性格与约束筛

| 约束 | 推荐 | 说明 |
|---|---|---|
| 只会 Framer / Webflow | `saas-landing`、`skeuo-desktop`、`poster-type`、`bento-cards` | 这几类在数据里 Framer + Webflow 占比 34–56% |
| 时间少（≤ 1 周） | `minimal-text`、`statement-hero`、`bento-cards` | 动效轻，内容驱动 |
| 想要安静、可信 | `minimal-text`、`statement-hero`、`editorial-serif` | |
| 想要张扬、被记住 | `poster-type`、`experimental-art`、`skeuo-desktop`、`illustrated-world` | |
| 看重性能 / 可访问性 | 避开 `immersive-3d`、`experimental-art` 的重型实现 | 若要用，务必提供降级与 `prefers-reduced-motion` |

### 条件冲突时

最常见的冲突是**“想安静，又想被记住”**。处理规则：主原型取安静类（`minimal-text` / `statement-hero` / `editorial-serif`），记忆点**只做一个**，从下面挑最贴近用户身份的：

| 记忆点 | 来源原型 | 适合 |
|---|---|---|
| 一个精致可玩的交互（光标、拖拽、切换动画） | `minimal-text` | 设计工程师、会前端 |
| 宣言里一个衬线斜体关键词 | `editorial-serif` | 任何人，成本最低 |
| 一个“活的”小组件（本地时间、时区重叠、正在听的歌） | `bento-cards` | 远程 / 跨时区求职 |
| 首屏一个可转动的 3D 小物件 | `immersive-3d` | 会 three.js |
| 一个手绘元素或签名 | `illustrated-world` | 有手绘能力 |

其他冲突（如“张扬”+“看重性能”）：保留原型的视觉语言，把动效降一档，并确保有静态兜底。

## 4. 主 + 次原型组合（数据中常见）

- `poster-type` + `experimental-art`：粗字体海报叠加故障 / 像素细节（#8、#26、#44、#99、#177）
- `immersive-3d` + `editorial-serif`：3D 场景配衬线标题，奢华感（#81、#82、#148）
- `skeuo-desktop` + `bento-cards`：拟物卡片组成仪表盘（#4、#14、#175）
- `minimal-text` + `experimental-art`：极简排版里藏一个精致交互（#85 rauno.me）
- `work-grid` + `illustrated-world`：插画作品墙（#33、#127）
- `editorial-serif` + `work-grid`：杂志式作品拼贴（#68、#128）
- `statement-hero` + `immersive-3d`：干净宣言 + 首屏 3D 小物件（#115；#53 同理）
- `statement-hero` + `editorial-serif` / `bento-cards` / `minimal-text`：数据中没有现成样本，属于推荐组合，用法见上方“条件冲突时”

## 给用户的输出格式

给 2–3 个候选，每个写：
- **原型**及一句话理由（对应用户的哪条条件）
- **代价**：需要什么能力 / 素材 / 时间
- **1–2 个参考站**（`find_refs.py` 查出来，附链接和“看什么”；合计 3–5 个）
然后给出你的推荐。
