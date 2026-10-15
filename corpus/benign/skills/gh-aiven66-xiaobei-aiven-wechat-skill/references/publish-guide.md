# 排版 · 配图 · 发布排障手册

---

## 一、Markdown 写作格式约定（决定最终排版效果）

写文章源文件（`.md`）时，只使用以下语法，渲染器只认这些：

| 你要的效果 | 源文件里怎么写 | 渲染结果 |
|---|---|---|
| 段落标题 | `## 标题文字` | 橙色左边框的粗体标题 |
| 引言 / 强调块 | `> 引用内容` | 灰底 + 橙色左边线的引言块 |
| 普通段落 | 直接写，段间**空一行** | 15px，行高 2.0，两端对齐 |
| 重点文字 | `**文字**` | 橙色加粗（克制使用） |
| 正文配图 | `![图片描述](图片路径或URL)` | 居中圆角带阴影的图 |

### ⚠️ 绝对不要用

- `---` 水平分隔线（渲染后会出现割裂感，V2.0 明确禁止）
- `- xxx` / `1. xxx` 列表（本风格禁用列表）
- `###` 三级标题（只识别 `##`，`###` 虽能渲染但会破坏"2-4 个标题"的原则）
- 表格（微信兼容性差）

### 关于第一段

渲染器会**无条件把第一段渲染成引言块**（灰底橙边）。
所以第一段要写成"引言"的语气，不要一上来就长段落。建议 1-3 句，一个钩子足矣。

---

## 二、封面 / 主图处理

### 2.1 规格

| 项目 | 值 |
|---|---|
| 尺寸 | 900 × 383（比例 2.35:1） |
| 格式 | 脚本会自动转 JPEG 并压缩 |
| 大小 | 压到 ≤ 64KB（实测 60-64KB） |

### 2.2 裁剪脚本（把任意尺寸裁成 900×383，居中裁剪不变形）

```python
from PIL import Image
img = Image.open("原始图.png").convert("RGB")
w, h = img.size
target_ratio = 900 / 383          # 2.3496
new_h = int(w / target_ratio)
top = (h - new_h) // 2
img = img.crop((0, top, w, top + new_h))     # 先按比例居中裁
img = img.resize((900, 383), Image.Resampling.LANCZOS)   # 再缩放
img.save("cover.png", "PNG")
```

> ⚠️ 不要跳过裁剪直接 resize，会把图压扁变形。

### 2.3 无水印校验（必做）

用 `Read` 工具打开生成的封面图，**肉眼确认**：
- [ ] 没有文字、字母、数字
- [ ] 没有水印、logo、签名
- [ ] 没有图库版权角标

有 → 重新生成或换图。

### 2.4 网络图片源（免版权、无水印）

| 图库 | 网址 |
|---|---|
| Unsplash | https://unsplash.com |
| Pexels | https://www.pexels.com/zh-cn/ |
| Pixabay | https://pixabay.com/zh/ |

---

## 三、发布

### 3.1 环境

```bash
# 必须用隔离虚拟环境（系统 python3 无 Pillow）
PY=/Users/aiven/.workbuddy/binaries/python/envs/default/bin/python
```

### 3.2 命令

```bash
$PY /Users/aiven/.workbuddy/skills/xiaobei-aiven-wechat-v2/scripts/publish.py \
   <md文件> "<标题>" "小北Aiven" ["<主图路径或URL>"]
```

参数：
- 第 4 个参数可省略 → 用默认封面
- 支持本地路径或网络 URL（URL 会自动下载）
- 标题建议 ≤20 字

### 3.3 输出

安装成功会打印：
```
✅ 发布成功! Media ID: xxxxx
```
并同时在 md 文件同目录生成 `xxx_draft_preview.html` 供本地预览。

---

## 四、排障手册

### 4.1 中文乱码（显示成 \u5c0f\u5317）

**成因**：`json.dump` 默认 `ensure_ascii=True`。

**三条件缺一不可**：
1. `json.dump(data, f, ensure_ascii=False)`
2. `curl` 用 `--data-binary`（**不是** `-d`）
3. 请求头带 `Content-Type: application/json; charset=utf-8`

### 4.2 `ModuleNotFoundError: No module named 'PIL'`

用系统 python3 跑了。改用 venv：
```bash
/Users/aiven/.workbuddy/binaries/python/envs/default/bin/pip install Pillow
```

### 4.3 列表项只显示数字没有内容

`<ol>` 里 `<li>` 之间有换行。本技能已禁用列表，一般不会遇到。

### 4.4 封面图不显示

- 封面必须用**永久素材**的 `media_id`（脚本走的 `material/add_material`，正确）
- 文章内配图需用可访问的公网 URL

### 4.5 发布成功但内容是空的

检查 md 文件路径是否正确、文件是否为空、以及是否误用了 `---` 被当成 front matter 切掉。

> 📌 渲染器会把文件开头以 `---` 开头的部分当作 front matter 移除。**所以正文绝对不要以 `---` 开头**。

### 4.6 access_token 失败

- 检查 `~/.workbuddy/.wx_config` 里的 AppID / AppSecret
- 微信后台 IP 白名单是否包含当前出口 IP

---

## 五、发布后回读校验（脚本已内置，手动时参考）

```python
import json, subprocess
APPID="..."; SECRET="..."
tok = json.loads(subprocess.run(['curl','-s',
  f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}'],
  capture_output=True,text=True).stdout)['access_token']

open('/tmp/get.json','w').write(json.dumps({"media_id": MEDIA_ID}, ensure_ascii=False))
r = subprocess.run(['curl','-s','-X','POST',
  f'https://api.weixin.qq.com/cgi-bin/draft/get?access_token={tok}',
  '-H','Content-Type: application/json; charset=utf-8','--data-binary','@/tmp/get.json'],
  capture_output=True, text=True)

d = json.loads(r.stdout)
item = d['news_item'][0]
assert item['title'], "标题为空"
assert '\\u' not in r.stdout, "存在中文转义（乱码风险）"
print("✅ 校验通过：", item['title'], "|", len(item['content']), "字符")
```
