---
name: feishu-voice-skill
description: 使用 edge-tts 生成语音并发送到飞书（语音气泡形式）。支持 XiaoxiaoNeural 等多种音色。
metadata: {"openclaw":{"emoji":"🎙️","requires":{"bins":["python3"]}}}
---

# feishu-voice-skill

使用 edge-tts 生成中文语音，并将语音文件以飞书气泡消息的形式发送给指定用户。

## 功能特性

- 🎙️ 使用 Microsoft Edge TTS 引擎，支持多种中文音色
- 🔄 自动转换音频格式为 opus（飞书语音气泡要求格式）
- 📤 直接发送语音气泡消息，无需手动上传
- ⚙️ 支持自定义音色和目标用户

## 支持的音色

| 音色名称 | 描述 |
|---------|------|
| `zh-CN-XiaoxiaoNeural` | 晓晓（女声，默认）|
| `zh-CN-YunxiNeural` | 云希（男声）|
| `zh-CN-YunyangNeural` | 云扬（男声，新闻）|
| `zh-CN-XiaoyiNeural` | 小艺（女声）|
| `zh-CN-liaoning-XiaobaiNeural` | 辽宁小白（女声）|
| `zh-CN-shaanxi-XiaoniNeural` | 陕西小妮（女声）|

## 环境依赖

- Python 3.8+
- `edge-tts` 包
- `requests` 包
- `ffmpeg`（需加入 PATH）

安装依赖：
```bash
pip install edge-tts requests
```

## 使用方式

```bash
python skill.py --text "你好" --voice "zh-CN-XiaoxiaoNeural"
```

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--text` | 是 | - | 要转换的文本内容 |
| `--voice` | 否 | zh-CN-XiaoxiaoNeural | 音色名称 |
| `--open-id` | 否 | ou_********************************** | 目标用户 open_id |
| `--app-id` | 否 | cli_************| 飞书应用 App ID |
| `--app-secret` | 否 | （内置默认值）| 飞书应用 App Secret |

## 工作流程

1. 调用 edge-tts 将文本转为 mp3 音频
2. 使用 ffmpeg 将 mp3 转换为 opus 格式（48kHz, 64kbps）
3. 获取飞书 tenant_access_token
4. 上传音频文件到飞书获取 file_key
5. 发送语音气泡消息给目标用户
6. 清理临时文件

## 注意事项

- 发送完成后会自动清理临时音频文件
- 建议单次文本不超过 300 字符
- 确保 ffmpeg 已安装并可从命令行调用