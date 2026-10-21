# illustrated-world · 插画世界型

用手绘、插画或纸艺构成一个可以探索的场景：房间、街道、岛屿、桌面。画风就是个人品牌，导航藏在场景里的物件上。
11 / 174（6%）。

## 适合 / 不适合

- **适合**：插画师、动画师、有手绘能力的产品 / 创意开发者、想要温暖与个性的人。
- **不适合**：没有插画能力也没有预算请插画师（用素材会非常廉价）；严肃的企业求职。

## 版式骨架

```
┌───────────────────────────────────────────┐
│ (可选) 极小导航 / 声音开关                  │
│                                           │
│     一张满屏插画场景                       │
│     ├ 门 → 作品                            │ ← 场景里的物件 = 导航
│     ├ 窗户 / 电脑 → 关于                    │
│     └ 信箱 / 电话 → 联系                    │
│                                           │
│ 底部小提示："Click a door to enter"         │
└───────────────────────────────────────────┘
```

- 页面短（中位 1.3 屏）：主体就是一屏场景；进入物件后打开弹层或子页面。
- 必须同时提供**普通文字导航**作为后备。

## 字体

- 手写 / 圆润展示体做标题：`Gochi Hand`（#43）、`Slime Box`、`Kaio`；正文用中性无衬线（`Inter`、`Geist`）。
- 免费替代：`Caveat`、`Gochi Hand`、`Patrick Hand`（手写），`Fredoka`、`Baloo 2`（圆润）。

## 配色

- 73% 浅色，配色由插画决定。两种路线：
  - **单色线稿**：白 / 灰底 + 黑线（#3 Pablo Stanley、#28 ITom、#12 蓝色线稿）。
  - **暖色纸感**：米黄、奶油、陶土（#58 Sara Youssry 的客厅、#27 纸艺拼色）。
- 数据中的强调色：`#1851d3` 克莱因蓝、`#1e1977`、`#c68171` 陶土粉。

## 动效

- 偏轻（低 64%），但 three.js 占 55%——很多“插画”其实是 3D 场景配手绘贴图（#28、#37）。
- 招牌手法：
  1. **物件悬停反馈**：悬停的物件轻微晃动、描边加粗或出现标签。
  2. **待机小动画**：猫眨眼、树叶摆动、电视闪烁（Lottie / Rive / CSS 关键帧）。
  3. **纸张 / 手绘质感**：噪点纹理叠加、线条轻微抖动（SVG `feTurbulence` + `feDisplacementMap`）。
  4. **声音**：环境音、点击音效（#28 底部 "Audio is currently ON"）。

## 技术栈

- 自写 73%、React 45%。2D 用 SVG + GSAP / Rive；伪 3D 用 three.js 正交相机 + 手绘纹理。

## 反模式

- 用通用插画素材库拼场景——失去这一原型唯一的价值：独特画风。
- 物件太多，用户不知道哪些能点。可点击的物件控制在 3–6 个，并给出提示。
- 场景图过大导致首屏慢；用 WebP / AVIF + 分层懒加载。

## 代表站

| # | 站点 | 看什么 |
|---|---|---|
| 3 | [Pablo Stanley](https://world.pablostanley.com/) | 黑白手绘岛屿世界，插画师的终极个人站 |
| 28 | [ITom](https://itomdev.com/) | 铅笔线稿砖墙 + 门是入口 + 音效 |
| 12 | [Elaine Yu](https://www.elaineyu.design/) | 克莱因蓝线稿 + "Click to stamp" 互动 |
| 58 | [Sara Youssry](https://sarayoussry.com/) | 水彩客厅，物件即导航 |
| 27 | [Aimee's Papercraft World](https://aimees-papercraft-world.com/) | 纸艺拼色 + 撕纸边缘 |
| 37 | [Mr. Panda](https://www.mr-pandas-psychologically-safe-portfolio.com/) | 作业本纸上的手绘熊猫与飞机 |
| 35 | [Sleep Well Creatives](https://sleep-well-creatives.com/) | 进站门后是深蓝夜空与插画沙丘 |
