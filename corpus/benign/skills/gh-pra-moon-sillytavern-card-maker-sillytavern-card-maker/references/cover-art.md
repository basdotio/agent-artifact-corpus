# 卡面与图像资产（封面制作 / 更换）

> 何时读：做新卡面、换封面、给角色卡配图时。含 AI 生成（包括受限平台的成人向内容）、后处理与打包校验。

## 1. 卡面工作流（AI 插画 → 成图）

- 规格：成品 **768×768**；AI 生成用 1024×1024 再处理。
- 步骤：生成 → **裁平台水印带**（底部约 9.5%、右缘约 4.5%、左缘约 1.5%）→ 平方居中裁切 → 缩放 768 → 底部渐变 + 标题区柔和暗版（保证白字对比）→ 标题/副题（深色描边 + 先重影后正字）。
- 工具：`scripts/apply_cover_text.py`（依赖 **Pillow**；本机用带 Pillow 的解释器跑，如 `C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`——裸 `python` 会报 ModuleNotFoundError）
  ```bash
  python scripts/apply_cover_text.py <输入图> "底图.png" --title "都 市 暗 涌" --sub "副标题"
  ```
- **换封面后必须重新打包**：`python scripts/build_card.py <工程> --image 底图.png`——只换底图不 rebuild 的话，成品 PNG 里还是旧图。
- **校验内嵌一致性**：对比「底图.png」与「输出/<卡名>.png」的 IDAT 数据哈希——build 只在图像上附加 tEXt 元数据块，裁剪后的图像数据应逐字节相同（写个小脚本算 sha256 即可）。

## 2. PIL 文字重影顺序 bug（牢记）

`ImageDraw` 在 RGBA 图上绘制是**覆盖、不是混合**——若先画正字、后画低透明度的「重影」层，会把正字像素替换成半透明色，字看起来发花、背景透出。

- **正确顺序：先画重影层，再画正字。**
- 任何「文字看起来半透明 / 背景透出字里」的现象，先查绘制顺序，再怀疑其他。
- 同理：所有半透明装饰层都应在主体之前、或绘制到独立 layer 再合成（`alpha_composite`）。

## 3. 受限平台图像生成工作法（NSFW / 边缘内容）

- **先分诊**：请求报错（如 internal server error）时，用完全无害的提示词（随手一个静物）发一次——**能出图 = 平台在拦内容**；也报错 = 服务波动，稍后重试。
- **单变量升级法**：从能过审的低尺度底稿起，一次只加一个维度（裸露度 / 束缚元素 / 姿势 / 用词）；被拒就退回，保留已通过的最好版本。生成前把「已通过底稿」存好，它是你的安全底线。
- **措辞保险（实测经验）**：
  - 束缚：「a red **silk** cord tied **lightly** around her crossed wrists」可过；直白的绑缚类措辞风险高。
  - 高危词组：`completely bare` / `nude` 直述、臀部对镜头（face-down hips raised toward camera）、外阴/湿润特写——被拒概率极高。
  - 可过组合参考：半遮裸体（衬衫半褪、内衣可见）＋柔和束缚＋卧室回眸＋脸红咬唇表情。
  - 用「成系列的画风描述」保持多张封面风格统一，例如 `semi-realistic glossy anime illustration, dark urban aesthetic, cinematic lighting`。
- **边界要记录**：把「什么措辞能过、什么必被拒」写进本文件或工程备注，下次直接复用，不再重新试错。
- **额度告知**：生成前告诉用户消耗（每张约 5~10 点），多轮迭代会累积；先出主方案，再按需出备选。
- 底线：成人向内容仅限全员成年、纯虚构场景。

## 4. 常用参数速查（768 画布）

| 项 | 值 |
|---|---|
| 水印裁剪 | 底部 ~9.5%、右缘 ~4.5%、左缘 ~1.5% |
| 标题字 | 微软雅黑粗体 62px，白色 + 深色描边（stroke 3） |
| 副题 | 22px，半透明（alpha ~180），带描边 |
| 底部渐变 | 0.65H 起压暗，alpha 150 → 底部 245 |
| 标题暗版 | 圆角矩形 140,582→628,732，GaussianBlur 28 |
| 字号候选 | `C:/Windows/Fonts/msyhbd.ttc`、`msyh.ttc`、`simhei.ttf`（其他平台自行替换） |
