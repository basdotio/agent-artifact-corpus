# rComfyUI-t2i

通过 ComfyUI WebSocket API 进行文生图，生成完毕后自动推送图片到飞书会话。

Text-to-image via ComfyUI WebSocket API, with automatic image delivery to Lark conversations.

---

## 项目结构 / Project Structure

```
rComfyUI-t2i/
├── README.md
├── SKILL.md              # Agent 使用指南 / Agent usage guide
├── .gitignore
└── scripts/
    ├── main.py           # CLI 入口，串联生图与发送 / CLI entry point
    ├── t2i.py            # ComfyUI 文生图客户端 / ComfyUI t2i client
    ├── lark_send.py      # 飞书图片推送 / Lark image sender
    └── config.ini        # 运行参数配置 / Runtime configuration
```

---

## 安装依赖 / Installation

```bash
pip install websocket-client requests requests-toolbelt Pillow
```

---

## 环境变量 / Environment Variables

| 变量名 / Variable | 必填 / Required | 说明 / Description |
|---|---|---|
| `COMFYUI_SERVER_ADDRESS` | 是 / Yes | ComfyUI 服务地址 / Server address, e.g. `192.168.1.1:8188` |
| `LARK_APP_ID` | 是 / Yes | 飞书/Lark 应用 App ID |
| `LARK_APP_SECRET` | 是 / Yes | 飞书/Lark 应用 App Secret |
| `LARK_BASE_URL` | 否 / No | API 域名 / API base URL（默认 / default: `https://open.larksuite.com`） |

`LARK_BASE_URL` 用于兼容飞书与 Lark 两个版本 / Used to switch between Feishu and Lark:
- 国际版 Lark（默认）：`https://open.larksuite.com`
- 国内版飞书：`https://open.feishu.cn`

---

## config.ini

```ini
[config]
model=ponyRealism_V22.safetensors
image-width=1024
image-height=1024
steps=45
cfg=5.0
sampler=euler
scheduler=karras
denoise_strength=1.0
selfeeModel=animePastelDream_softBakedVae.safetensors
selfeeWidth=512
selfeeHeight=768
```

| 参数 / Key | 说明 / Description |
|---|---|
| `model` | 默认模型文件名 / Default checkpoint filename |
| `image-width` / `image-height` | 默认输出分辨率 / Default output resolution |
| `steps` | 采样步数 / Sampling steps |
| `cfg` | CFG 强度 / CFG scale |
| `sampler` | 采样器 / Sampler |
| `scheduler` | 调度器 / Scheduler |
| `denoise_strength` | 去噪强度 / Denoise strength |
| `selfeeModel` | selfee 模式专用模型 / Model used in selfee mode |
| `selfeeWidth` / `selfeeHeight` | selfee 模式输出分辨率 / Resolution in selfee mode |

---

## 使用方法 / Usage

```bash
cd scripts
```

### 普通模式 / Standard Mode

```bash
python main.py \
  --chat_id "<chat_id or open_id>" \
  --positive_prompt "masterpiece, best quality, 1girl, solo, smile" \
  --negative_prompt "blurry, low quality"
```

### selfee 模式 / Selfee Mode

使用预设的粉发猫耳少女角色，只需描述动作、表情、环境、场所、天气等，人物与负向提示词均已内置。

Uses a preset pink-haired cat-ear girl character. Only describe actions, expressions, environment, location, weather, etc. — the character and negative prompt are built in.

```bash
python main.py \
  --chat_id "<chat_id or open_id>" \
  --selfee \
  --positive_prompt "laughing, sitting under cherry blossoms, petals falling, soft spring light"
```

### 参数说明 / Arguments

| 参数 / Argument | 必传 / Required | 说明 / Description |
|---|---|---|
| `--chat_id` | 是 / Yes | 飞书群 ID 或用户 open ID / Lark group ID or user open ID |
| `--positive_prompt` | 是 / Yes | 正向提示词（英文）/ Positive prompt (English) |
| `--negative_prompt` | 否 / No | 负向提示词，selfee 模式下忽略 / Negative prompt, ignored in selfee mode |
| `--selfee` | 否 / No | 启用 selfee 模式 / Enable selfee mode |

`--chat_id` 根据前缀自动判断发送类型 / The `receive_id_type` is inferred from the prefix:
- `oc_` → 群聊 / group chat (`chat_id`)
- `ou_` → 私聊 / direct message (`open_id`)

---

## 生成流程 / How It Works

1. 连接 ComfyUI WebSocket `/ws?clientId=xxx` / Connect to ComfyUI WebSocket
2. POST `/prompt` 提交工作流 / Submit workflow
3. 监听 WebSocket，收集生成完毕的图片数据 / Listen for completion events
4. 从 `/history/{prompt_id}` 下载图片，保存到 `output/` / Download and save image to `output/`
5. 上传图片到飞书，发送消息到指定会话 / Upload to Lark and send to the target conversation

参数校验通过后 CLI 立即返回 `OK`，生图与发送在后台进行。

The CLI returns `OK` immediately after parameter validation; generation and sending run in the background.

---

## 输出 / Output

| 文件 / File | 说明 / Description |
|---|---|
| `output/<uuid>.png` | 生成的图片 / Generated image |
| `output/run.log` | 运行日志 / Runtime log |
| `output/error.log` | 后台异常日志 / Background error log |

`run.log` 记录以下内容 / `run.log` records:
- 生图参数（模型、分辨率、steps、cfg、sampler、scheduler、denoise）/ Generation params
- 正向 / 负向提示词全文 / Full positive & negative prompts
- ComfyUI `prompt_id`
- 飞书 API 请求 URL、响应状态码与 body / Lark API requests, status codes and response bodies