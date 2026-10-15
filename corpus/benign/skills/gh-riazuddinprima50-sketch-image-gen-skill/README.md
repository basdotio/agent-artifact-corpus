# image-gen

**面向电商的 AI 生图流水线** — 用任意 OpenAI 兼容的图像 API，批量生产拼多多/电商商品图，并在本地画廊里查看。

An **e-commerce image generation pipeline** for any OpenAI-compatible image
API: generate / edit images from the command line, apply platform templates and
style presets, batch from CSV, and view results in a local auto-refreshing
gallery.

---

## 效果示例

| 白底主图 `pdd-main`+`3c-white` | 场景图 `pdd-scene`+`home` | 国潮海报 `pdd-poster`+`guochao` |
|---|---|---|
| ![main](examples/01-main.png) | ![scene](examples/02-scene.png) | ![poster](examples/03-poster.png) |

## 它解决什么

通用生图工具能"画一张图"，但电商要的是**可复制的流水线**：白底主图、场景图、
带卖点的图、批量出图、统一风格、即时预览。本项目把这件事拆成清晰的四层：

```
[编排层]  batch.py   —— 读 CSV 批量出图 + 自动命名归档
[生成层]  gen.py     —— 调用 API 生成/改图（模板 + 预设 + 文字）
[模板层]  templates.json / presets.json —— 平台格式 + 行业风格
[展示层]  serve.py   —— 本地网页画廊，新图自动出现
```

## 特性

- **模板系统**：`pdd-main`(白底主图) / `pdd-scene`(场景) / `pdd-sellingpoint`(卖点) / `pdd-detail` / `pdd-poster`
- **风格预设**：`3c-white` `3c-dark` `home` `guochao` `beauty` `food` `apparel` `jewelry` `festive`
- **可叠加**：模板管"平台格式"，预设管"视觉风格"
- **批量 CSV**：并行、自动命名、生成 `manifest` 清单
- **改图 / 图生图**：`--ref` 传参考图，保持产品/角色一致
- **本地画廊**：零依赖 HTTP 服务，页面后台自动刷新
- **供应商解耦**：换 `IMAGE_API_BASE` 即可切换模型服务，代码不动

## 安装

需要 Python 3.8+ 和 `requests`。

```bash
git clone <this-repo> ~/.config/opencode/skills/image-gen
cd ~/.config/opencode/skills/image-gen
pip install requests
cp .env.example .env    # 填入你自己的 key 和接口地址
```

> 作为 opencode / Claude 等 agent 的 skill 使用：放到 skills 目录即可，重启 agent 生效。
> 也可以完全当独立 CLI 用。

## 配置 `.env`

```ini
IMAGE_API_KEY=sk-your-key-here
IMAGE_API_BASE=https://your-relay.example/v1   # 需支持 /images/generations
IMAGE_MODEL=gpt-image-2.5
```

任何 **OpenAI 兼容**的图像接口都可以：官方 OpenAI、中转站、自建网关均可。
`.env` 已被 `.gitignore` 排除，**绝不会**提交。

## 用法

### 单张：模板 + 预设

```bash
# 白底主图
python3 gen.py "无线蓝牙耳机充电仓" --template pdd-main --preset 3c-white

# 卖点图（中文文字）
python3 gen.py "不锈钢保温杯" --template pdd-sellingpoint --preset 3c-white \
  --text "24小时保温|316不锈钢|弹盖设计"

# 国潮促销海报
python3 gen.py "陶瓷茶杯礼盒" --template pdd-poster --preset guochao \
  --text "国潮好物|匠心传承"

# 改图 / 图生图
python3 gen.py "把背景换成夏季沙滩" --ref product.png

python3 gen.py --list-templates     # 看所有模板
python3 gen.py --list-presets       # 看所有预设
```

模板/预设给尺寸、背景、质量默认值；命令行参数可覆盖。优先级：
**命令行 > 模板 > 预设 > 内置**。

### 批量：CSV

```bash
python3 batch.py --sample > products.csv     # 生成示例
python3 batch.py --dry-run products.csv      # 预览提示词，不调 API
python3 batch.py products.csv --out product-images/ --workers 3
```

CSV 列（表头必需）：`name`(必填), `template`, `preset`, `text`(用 `|` 分隔),
`model`, `size`, `quality`, `background`, `n`, `ref`(用 `|` 分隔 → 改图), `slug`。

输出：`<out>/NNN-<slug>[-<template>][-<preset>].png` + `batch-manifest.csv`。

### 看图：本地画廊

```bash
python3 serve.py <images-dir> --port 8099 --open
# 浏览器打开 http://localhost:8099/ ；新图 2.5 秒内自动出现
```

终端无法内联显示图片，画廊就是本项目的"图片展示层"。支持缩放、方向键翻页、
搜索、下载；装 `Pillow` 可启用缩略图加速。

## 自定义模板 / 预设

编辑 `templates.json` / `presets.json`，字段：
`name`, `desc`, `size`, `quality`, `background`, `requires_text`,
`prompt_prefix`, `prompt_suffix`。

## 说明与限制

- 依赖第三方 API：稳定性、费用、条款由你选的供应商决定，本项目不捆绑任何 key。
- 默认模型名随供应商不同，用 `GET {API_BASE}/models` 查询。
- 提示词为英文（模型理解更好），面向中文电商场景。

## License

MIT

---

## English (quick start)

An e-commerce image-gen pipeline for any OpenAI-compatible image API.

```bash
pip install requests
cp .env.example .env          # set IMAGE_API_KEY + IMAGE_API_BASE
python3 gen.py "wireless earbuds case" --template pdd-main --preset 3c-white
python3 batch.py products.csv --out product-images/ --workers 3
python3 serve.py product-images --port 8099 --open   # local gallery
```

Layers: `batch.py` (orchestration/CSV) → `gen.py` (generate/edit) →
`templates.json`/`presets.json` (platform format + style) → `serve.py` (viewer).

Bring your own API key. MIT licensed.
