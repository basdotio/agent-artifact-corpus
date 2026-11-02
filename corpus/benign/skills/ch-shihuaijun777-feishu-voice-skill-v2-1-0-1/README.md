# feishu-voice-skill

> 🎙️ 使用 edge-tts 生成语音并发送到飞书（语音气泡形式）

## 功能

- 使用 Microsoft Edge TTS 引擎生成自然语音
- 自动转换音频为飞书所需的 opus 格式
- 一键发送语音气泡消息到指定用户

## 快速开始

### 1. 安装依赖

```bash
pip install edge-tts requests
```

确保 `ffmpeg` 已安装并加入系统 PATH。

### 2. 基本使用

```bash
python skill.py --text "你好，欢迎使用飞书语音助手"
```

### 3. 指定音色

```bash
# 晓晓（默认女声）
python skill.py --text "你好" --voice "zh-CN-XiaoxiaoNeural"

# 云希（男声）
python skill.py --text "你好" --voice "zh-CN-YunxiNeural"

# 云扬（新闻男声）
python skill.py --text "今日新闻" --voice "zh-CN-YunyangNeural"
```

## 完整参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--text` | 要转换的文本（必填） | - |
| `--voice` | 音色名称 | zh-CN-XiaoxiaoNeural |
| `--open-id` | 目标用户 open_id | ou_xxxxxxxxxxxxxxxx |
| `--app-id` | 飞书应用 App ID | cli_xxxxxxxxxxxxxxxx |
| `--app-secret` | 飞书应用 App Secret | 内置默认值 |
| `--keep-temp` | 保留临时文件 | False（自动清理） |

## 音色列表

| 音色 | 描述 |
|------|------|
| `zh-CN-XiaoxiaoNeural` | 晓晓（女声，推荐）|
| `zh-CN-YunxiNeural` | 云希（男声）|
| `zh-CN-YunyangNeural` | 云扬（男声，新闻风格）|
| `zh-CN-XiaoyiNeural` | 小艺（女声）|
| `zh-CN-liaoning-XiaobaiNeural` | 辽宁小白（女声）|
| `zh-CN-shaanxi-XiaoniNeural` | 陕西小妮（女声）|

更多音色请访问 [edge-tts 官方文档](https://github.com/rany2/edge-tts)。

## 工作流程

```
文本输入 → edge-tts 生成 MP3 → ffmpeg 转换 opus → 上传飞书 → 发送语音气泡
```

## 常见问题

### Q: ffmpeg 报错 "libopus not found"
A: 确保安装的是带 libopus 支持的 ffmpeg 版本，可从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载。

### Q: 消息发送失败
A: 检查：
1. App ID 和 App Secret 是否正确
2. 应用是否有发送消息的权限
3. 目标用户 open_id 是否有效

### Q: 如何查看支持的音色？
A: 运行 `edge-tts --list-voices` 可列出所有可用音色。

## 技术栈

- [edge-tts](https://github.com/rany2/edge-tts) - 微软 Edge TTS Python 接口
- [ffmpeg](https://ffmpeg.org/) - 音视频格式转换
- [飞书开放平台](https://open.feishu.cn/) - 消息发送 API
