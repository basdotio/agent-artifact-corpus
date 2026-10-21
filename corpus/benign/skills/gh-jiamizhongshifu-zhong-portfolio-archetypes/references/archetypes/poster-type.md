# poster-type · 巨型字体海报型

首屏被超大字号的名字或标语占满，像一张海报。字体与构图本身就是作品。
样本最多的原型：36 / 174（21%）。

## 适合 / 不适合

- **适合**：品牌设计师、艺术指导、平面 / 字体设计师、有态度的小工作室、想被记住的自由职业者。
- **不适合**：作品以复杂界面为主、需要招聘方快速扫读的产品设计师（标题会抢走注意力）。

## 版式骨架

```
┌───────────────────────────────────────────┐
│ logo            work  about  contact      │ ← 极小导航，常大写、等距字
│                                           │
│ NAME / 标语，字号 = 视口宽度的 10–20vw     │ ← 允许出血、裁切、叠图
│ NAME                                       │
│ 小字身份描述 · 地点 · 年份    [scroll ↓]   │ ← 角落小字信息，形成大小对比
├───────────────────────────────────────────┤
│ 作品：大图 / 视频逐个出现，或横向滚动      │
└───────────────────────────────────────────┘
```

- 中位首屏标题 **88px**，42% 达到 120px+；用 `clamp()` 按视口宽度缩放，而不是固定 px。
- 22 / 36 的标题全大写或本身是大写字形。
- 页面长（中位 8.7 屏），作品往下排。

## 字体

- 94% 用无衬线，偏好**压缩 / 粗黑 / 怪诞体**：Neue Montreal、Neue Corp Tight、Clash、Barlow Condensed、Futura 系。
- 免费替代：`Anton`、`Archivo Black`、`Big Shoulders Display`、`Bebas Neue`（压缩）；`Clash Display`、`General Sans`（Fontshare）；`Space Grotesk`。
- 角落小字用等宽或小号无衬线，字距略开（`letter-spacing: 0.02–0.08em`）。

```css
.hero-title {
  font-size: clamp(64px, 16vw, 280px);
  line-height: 0.85;
  letter-spacing: -0.04em;
  text-transform: uppercase;
}
```

## 配色

- 61% 浅色底、61% 近单色。典型做法：**米白 / 浅灰底 + 黑字 + 一个高饱和强调色**。
- 数据中的强调色：`#ff3401` 橙红、`#4fe041` 荧光绿、`#9b1527` 酒红、`#ef6b44`、`#bd5119`。
- 也有整屏纯色底（#78 荧光绿字配红底、#106 橙底黑字），可作为大胆变体。

## 动效

- 动效最重的原型之一：高 39%、中 33%。61% 用 **Lenis** 平滑滚动，17% GSAP，19 / 36 有自定义光标。
- 招牌手法：
  1. **字母逐个入场**：标题拆成 span，`translateY(100%)` → 0，stagger 30–60ms。
  2. **滚动视差缩放**：标题随滚动放大或横移出屏（GSAP ScrollTrigger `scrub`）。
  3. **无限滚动跑马灯**：身份 / 城市 / 服务列表横向循环（#69）。
  4. **混合模式光标**：`mix-blend-mode: difference` 的圆形光标，经过大字时反色。
  5. **字里嵌图**：在字母之间或上方叠一张人像 / 作品图（#44、#122、#172）。

## 技术栈

- 自写 53%、Framer 19%、Webflow 17%。Framer 做这种排版很顺手；跑马灯和字母动画可以用 Framer 组件完成。

## 反模式

- 标题够大但没有对比——四个角也全是大字，画面就糊了。**大与小必须同时存在。**
- 移动端仍按桌面字号排，单词被拆行或横向溢出。务必 `clamp()` + 手动断行。
- 为了“酷”把名字换成难认的字体，结果访客不知道你叫什么。

## 代表站

| # | 站点 | 看什么 |
|---|---|---|
| 31 | [Spencer Gabor](https://spencergabor.work/) | 压缩体名字 + 中间叠作品卡片，海报感最纯 |
| 45 | [Graffio](https://graffio.co/) | 黑底白字超大 "Digital Products"，零装饰 |
| 78 | [A./CHEN](https://a-chen.webflow.io/) | 荧光绿字压红底，色彩冲击 |
| 119 | [The Bang](https://www.thebang.com/) | 名字里嵌入图形块，工作室版 |
| 122 | [Ylli Ramadani](https://www.ylliramadani.com/) | 多行大字杂志排版 + 小图穿插 |
| 173 | [Sebastiaan Scheer](https://sebastiaanscheer.com/) | 粗黑名字贴顶 + 作品大图 |
| 26 | [Gustaf Furusten](https://gustaffurusten.se/) | 像素体超大字 + 3D 背景，偏实验 |
