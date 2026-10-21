# immersive-3d · 沉浸式 3D 型

全屏 WebGL 场景、3D 物体、粒子和电影感光影。网站本身就是作品，文字退居角落。
15 / 174（9%）。

## 适合 / 不适合

- **适合**：创意开发者、3D / 动效设计师、想用网站拿 Awwwards 的人。
- **不适合**：没有 3D / 着色器能力又想一周上线；需要被快速扫读的求职场景（可以作为首屏，但必须有清晰的文字版作品入口）。

## 版式骨架

```
┌───────────────────────────────────────────┐
│ name                        nav  sound ◐  │ ← 角落小字，常带音效开关
│                                           │
│            [ 全屏 3D 场景 / canvas ]       │ ← 跟随光标或滚动变化
│                                           │
│ 一句身份（18–40px）            [scroll]    │ ← 左下角
└───────────────────────────────────────────┘
（可选）进站门：Enter with sound / Enter muted
```

- 首屏文字很小（中位 **19px**），80% 是小号。
- 页面极短（中位 1 屏）：很多站是单屏场景，内容在场景内部或弹层里。

## 字体

- 93% 无衬线：`Neue Montreal`、`Geist`、`TWK Lausanne`；等宽 / 像素点缀：`Azeret Mono`、`VT323`。
- 文字通常白色小号 + 大写 + 开字距，像电影字幕。

## 配色

- **73% 深色底**，53% 高饱和——深色背景让光效和材质发亮。
- 典型：近黑底 + 一种霓虹 / 发光色（#11 红色光柱、#52 紫色像素手、#100 蓝色网格）。
- 数据中的深色主色：`#100b2d`、`#07022b` 深紫蓝，`#17434b` 墨绿，`#62040d` 暗红。

## 动效

- three.js 67%，11 / 15 实际创建了 WebGL context；4 / 15 有加载动画或进站门。
- 招牌手法：
  1. **光标驱动的相机视差**：鼠标位置轻微旋转相机或物体（`lerp` 缓动，幅度 ≤ 5°）。
  2. **滚动驱动的场景推进**：滚动 = 时间轴，镜头穿过场景（GSAP ScrollTrigger + three.js）。
  3. **进站门 + 音效**："Enter with sound / Enter muted" 二选一（#11、#52、#63）。
  4. **后期处理**：bloom、颗粒、色差（`postprocessing` 库），营造电影感。
  5. **点阵 / 抖动材质**：用像素或 dither 着色器重绘 3D 物体（#52 ASTRODITHER）。

## 技术栈

- 自写 80%。常用组合：`three.js` / `@react-three/fiber` + `drei` + `postprocessing` + GSAP；Next.js 33%。
- 不写代码的替代：Spline 导出嵌入（数据中 1 例），效果有限但上手快。

## 反模式

- 加载 10MB 模型、首屏白屏 8 秒，没有加载进度。
- 不做降级：移动端 / 低端设备 / `prefers-reduced-motion` 时直接卡死。必须准备静态图兜底。
- 场景很酷但找不到作品和联系方式。

## 代表站

| # | 站点 | 看什么 |
|---|---|---|
| 11 | [Yogi Suria](https://ysuriadesign.co/) | 进站门 + 红色光柱和漂浮陨石，电影感最强 |
| 9 | [Felix Rieseberg](https://felixrieseberg.com/) | 写实 3D 房间 + 电视里显示名字，温暖叙事 |
| 52 | [ASTRODITHER](https://astrodither.robertborghesi.is/) | 像素点阵着色器 + 星空，偏实验 |
| 100 | [Maxime Heckel](https://maximeheckel.com/) | 蓝色网格空间里的玻璃 3D 字，着色器教学博主 |
| 107 | [Max Yinger](https://yinger.dev/) | 粉色方块堆叠 3D + 实时时钟，UI 工程师 |
| 116 | [Xavier Coulombe-Murray](https://xavier.works/) | 全屏 3D 扫描石头，极简 |
| 63 | [Joseph Santamaria](https://joseph-san.com/) | "Dive into the experience" 进站门 + 墨绿建筑场景 |
