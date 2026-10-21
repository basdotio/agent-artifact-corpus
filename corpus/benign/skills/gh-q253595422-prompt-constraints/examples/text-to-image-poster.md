# 示例 1 · 文本生图 —— 竖版赛博朋克海报

> 演示：模糊需求 → 受约束的可执行提示词
> 路由：[`SKILL.md`](../SKILL.md) → [`references/templates.md`](../references/templates.md) §T1 + [`references/image.md`](../references/image.md)

---

## 用户输入

```
帮我做个赛博朋克城市夜景海报，竖版
```

信息量很低：只有一个主题、一个风格词、一个画幅。**不需要追问**——缺的部分按合理默认
推断即可（夜景城市 → 广角街景而非室内；海报 → 强视觉冲击的构图）。

---

## 输出

````markdown
**正向 Prompt**

中文：低机位仰拍视角的雨夜赛博朋克都市街景，两座高塔夹击形成强烈的透视收束，
画面中央是一条被雨水浸透的街道，湿滑路面完整倒映上方霓虹招牌的品红与青蓝双色光斑；
沿街密集的垂直灯牌与全息广告构成纵深光廊，空气中悬浮着雨雾，被光源切出数道清晰的体积光束；
主色为高饱和品红与青蓝的冷暖对撞，点缀少量琥珀色灯窗；
金属与玻璃幕墙呈湿润高反光质感，沥青路面泛着油亮镜面；
前景积水倒影 → 中景行走的人影剪影 → 背景朦胧的高塔轮廓，三层空间拉开空气透视；
由密集垂直光带与冷色调构成的秩序感与疏离感；电影级写实摄影质感，
轻微胶片颗粒与辉光，高细节密度。

English: Low-angle shot of a rainy cyberpunk city street at night, two towers framing
a converging perspective, a rain-soaked street at center with wet asphalt mirroring
magenta and cyan neon signs; dense vertical signage and holographic ads forming a
receding corridor of light, rain mist cut by volumetric light beams; high-saturation
magenta-teal color clash with sparse amber window accents; wet reflective metal and
glass curtain walls, oily mirror-like asphalt; foreground puddle reflection,
midground pedestrian silhouettes, hazy tower outlines in the background with deep
aerial perspective; order and detachment built from dense vertical light strips and
cold tones; cinematic photorealism, subtle film grain and bloom, high detail density.

**Negative Prompt**

illustration, cartoon, anime, 3d cartoon render, flat shading, readable text,
watermark, logo, signature, garbled characters, blurry, low resolution,
oversharpened, overexposed, cluttered composition, distorted perspective,
floating objects, plastic texture

**推荐参数**

比例 9:16 ｜ 分辨率 2K
````

---

## 这段提示词做了什么

| 约束层 | 具体动作 |
|---|---|
| **L1 事实** | 没有写 `85mm`、`f/1.8`、`Shot on ARRI` 这类无依据的参数；「疏离感」被拆解为「密集垂直光带 + 冷色调」 |
| **L2 媒介** | `电影级写实摄影质感` 定死媒介；Negative 里排除 `illustration / cartoon / anime / 3d cartoon render` 这四种最易混淆的媒介 |
| **L3 结构** | 前 1/3 是四组视觉锚点：**低机位仰拍 + 双塔夹击透视** ／ **品红-青蓝对撞** ／ **湿滑路面镜面倒影** ／ **雨雾体积光束**。其余细节（材质、层次、后期）全部后置 |
| **L4 一致性** | 单张图，无需声明不变量 |
| **L5 排除** | 排除项针对本图的真实风险：媒介混淆、文字乱码、过曝、构图杂乱、透视畸变 |
| **L6 参数** | `9:16` 与 `2K` 放在「推荐参数」行，**没有**混进提示词正文 |

### 为什么「疏离感」要这么写

`疏离感` 单独出现时对模型毫无信息量。这里它被绑定在**成因**上：

```
密集垂直光带（视觉密度↑）+ 冷色调（温度↓）+ 大量人造光源、无生命迹象
```

模型接收到的是**可渲染的视觉结构**，而不是一个需要它自己猜测的情绪标签。

### 为什么是 9:16 而不是 16:9

竖版海报的构图逻辑与横版完全不同：横向的「街景展开」要换成纵向的「光廊纵深」。
这就是为什么锚点里写的是**垂直灯牌构成纵深光廊**、**高塔夹击形成透视收束**——
这些结构在竖幅里才成立。

---

## 可调项

想改方向时，优先拧这几个旋钮：

| 想要的效果 | 改哪里 |
|---|---|
| 更冷 / 更压抑 | 主色改为深蓝-青灰，去掉琥珀色点缀 |
| 更有烟火气 | 增加中景人群密度、路边摊热食蒸汽 |
| 更干净高级 | 减少垂直灯牌密度，加大负空间，降低饱和度 |
| 改成横版宽银幕 | 比例改 21:9，锚点从「纵深光廊」改为「横向街景展开」 |
| 换成白天 | 移出霓虹与湿地面，「雨夜」改为「阴天正午」，色彩改为高对比硬光 |
