# 排除约束（Negative）

负面提示词不是许愿池。**它只解决「模型确实会犯、且我明确知道要排除」的错误。**

---

## 一、第一原则：具象化

抽象否定对模型几乎无效，因为它描述的是「不存在的东西」。

| 差 | 好 |
|---|---|
| `no man-made structures` | `荒芜的景观，没有建筑和道路` |
| `不要现代元素` | `古代街道，两侧是木构店铺和石板路，画面中没有任何现代建筑或电线和车辆` |
| `不要文字` | `纯视觉画面，画面内没有任何可读文字、标识或水印` |

**做法**：把排除项**写进场景描述**，用「包含排除结果的完整画面」来表达。

---

## 二、分层组织

负面词按风险类别组织，逐类挑选，不套固定套餐：

| 类别 | 检查项 |
|---|---|
| 错误媒介 | 与目标媒介冲突的特征（写实图出现 CG 感；插画出现摄影景深） |
| 结构缺陷 | 畸形手、多指/少指、脸部崩坏、五官错位、穿模、比例失调、肢体粘连 |
| 内容错误 | 多余人物、多余肢体、缺少主体、元素悬浮、无支撑物 |
| 光影错误 | 过曝、欠曝、光源方向矛盾、无阴影、阴影方向错误 |
| 画质缺陷 | 低分辨率、噪点、伪影、过度锐化、过度磨皮、塑料感、色带 |
| 材质错误 | 错误反射、材质混淆（布料像塑料）、湿感错误 |
| 文字标识 | 可读品牌 Logo、车牌、包装文字、海报正文、衣服印花、角落水印、乱码错字 |
| 构图错误 | 错误裁切、主体被切、构图失衡 |
| 视频专属 | 跳切、瞬移、倒放、身份漂移、换脸、同脸、主目标数量变化、场景漂移、POV 错误、过度抖动、结构闪烁、地标变形 |
| 参数残留 | 编号残留、路线/箭头、文字标签、UI 元素、地图视角 |

---

## 三、生图通用池（按需取用，不要全抄）

```
low resolution, blurry, jpeg artifacts, oversharpened, over-smoothed,
deformed hands, extra fingers, missing fingers, fused fingers,
asymmetric face, distorted facial features, cross-eyed,
extra limbs, missing limbs, floating objects, disconnected parts,
bad anatomy, disproportional, unnatural pose,
overexposed, underexposed, flat lighting, contradictory shadows,
plastic skin, waxy texture, wrong reflections, material confusion,
readable text, watermark, signature, logo, garbled characters,
cluttered background, distracting elements, bad composition, awkward crop
```

**针对媒介追加：**
- 摄影：`3d render, cgi, cartoon, illustration, anime, digital painting`
- 写实 3D：`real photograph, anime, cel shading, flat 2d illustration`
- 二次元：`photorealistic, real photo, complex 3d volumes, noisy texture`
- 产品渲染：`lifestyle snapshot, cluttered scene, low-quality reflections`
- 扁平矢量：`photorealistic, complex 3d volume, unnecessary realistic materials`

**针对主体追加：**
- 人物：`malformed ears, bad teeth, uneven eyes, hair artifacts`
- 动物：`extra paws, wrong fur direction, human-like pose`
- 文字/Logo：`misspelled text, distorted letterforms, unreadable typography`
- 建筑：`impossible geometry, warped perspective, floating structure`

---

## 四、视频专属池

```
jump cuts, teleporting, reversed motion, identity drift, face swap,
same face on different people, changing number of main targets,
scene drift, wrong POV, excessive camera shake, flickering structures,
deformed landmarks, visible drone, guide characters, flat terrain,
visible annotations, visible route lines, numbers on screen, UI overlays,
map view, static frame, motionless subject
```
（最后两项按需——如果确实需要静态或慢动作就删掉。）

---

## 五、数量与形态

- 生图：**8—15 条**，英文逗号分隔。
- 视频：**8—20 条**，按类别分组可读性更好。
- 每条必须**有针对性**，能说出「为什么这条对这张图/这个镜头重要」。
- **不通过的信号**：负面词和正面描述无关、和用户主题无关、纯粹为了凑数。

---

## 六、反模式

| 反模式 | 问题 | 修正 |
|---|---|---|
| 抄固定 30 词套餐 | 稀释有效项，可能压掉用户想要的特征 | 按当前风险定制，8—15 条 |
| 负面词和正面描述矛盾 | 模型收到冲突指令，随机取舍 | 逐条对照正面描述，删掉冲突项 |
| 把风格需求写成负面词 | 「不要卡通」不如「写实摄影」 | 用正面描述定义，负面只做补充 |
| 用它承担一致性 | 负面词锁不住身份 | 一致性用不变量声明 + 参考图 |
| 用来修主体意图 | 「不要悲伤」想变开心 | 直接写开心，别否定 |
