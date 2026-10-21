# saas-landing · 商业落地页型

像一个 SaaS 官网：价值主张、服务、客户 logo、案例、价格或预约入口。目标是**转化**，不是展示个性。
16 / 174（9%）；一半是工作室，19% 是产品。

## 适合 / 不适合

- **适合**：自由职业接单、订阅制设计服务、小工作室、Framer / Webflow 开发者（他们的网站就是销售页）。
- **不适合**：求职作品集（招聘方不需要被“推销”）、艺术导向的个人站。

## 版式骨架

```
┌───────────────────────────────────────────┐
│ logo   Services Work Pricing   [Book call]│ ← 右上角永远有一个主 CTA
│                                           │
│ 一句价值主张（48–72px）                    │
│ 一行副标题：你帮谁、解决什么                │
│ [主 CTA]  [次 CTA]                         │
│ ── 客户 logo 条 ──                         │ ← 社会证明紧跟首屏
├───────────────────────────────────────────┤
│ 案例卡片（结果数据：+40% 转化 / $32M 融资） │
│ 服务 / 流程 3–4 步                         │
│ 价格 or 订阅方案                           │
│ 评价 · FAQ · 再一个 CTA                    │
└───────────────────────────────────────────┘
```

- 首屏标题中位 **56px**；页面最长（中位 9.9 屏），信息密度高（31% dense）。

## 字体

- 100% 无衬线：`Inter`、`Suisse Intl`、`Neue Montreal`、`Manrope`、`Mori`。免费替代 `Inter`、`Manrope`、`Satoshi`、`General Sans`。
- 标题字重 500–600，字距 -0.02em；不要用花哨展示体，可信度优先。

## 配色

- 56% 浅色、44% 深色，62% 近单色。深色版用**深底 + 柔和渐变光 + 白卡片**（#18、#47、#103）；浅色版用白底 + 一个品牌色按钮。
- 数据中的强调色多为柔和的米色 / 浅紫（`#e9dcc9`、`#e5c6ff`、`#f6e3d1`），CTA 用高对比。

## 动效

- 中 38%、高 31%。Lenis 44%、GSAP + ScrollTrigger 25%、Rive 12%。
- 招牌手法：
  1. **logo 条无限滚动**（marquee）。
  2. **案例卡片滚动入场**：stagger 淡入 + 上移。
  3. **悬浮预约小组件**：右下角“预约通话”卡片（#21 "Talk to us"、#155 内嵌日历）。
  4. **数字滚动计数**：结果数据从 0 跳到目标值。

## 技术栈

- Framer 31%、Webflow 25%、自写 38%。这一类用 Framer / Webflow 最划算：CMS、表单、预约嵌入（Cal.com）开箱即用。

## 反模式

- 套模板后所有区块都一样重，没有一个让人记住的点。至少让首屏或案例区有一处独特设计。
- 只说“我们很专业”，没有具体结果数字或真实案例。
- CTA 太多：每屏都有 3 个按钮，用户不知道该点哪个。

## 代表站

| # | 站点 | 看什么 |
|---|---|---|
| 46 | [Designownow](https://designownow.com/) | 订阅制设计服务：大字 + 方案卡片 + 客户 logo |
| 47 | [Robert Licau](https://www.robertlicau.com/) | 个人版：深色、一句话主张 + "Book an intro call" |
| 49 | [Damian Fejdasz](https://damianfejdasz.pl/) | 浅色，作品截图悬浮 + 标签气泡 |
| 129 | [Quarter Digital](https://quarter.digital/) | Webflow 工作室：标题 + 3D 物件 + 客户融资新闻 |
| 155 | [Agence Norry](https://www.agencenorry.com/) | 法语工作室，首屏内嵌预约日历 |
| 21 | [Displace](https://displace.agency/) | 全屏视频背景 + "We build and run your site" |
| 103 | [Nick Stepuk](https://nickstepuk.com/) | Framer 开发者，深色 + 发光产品截图 |
