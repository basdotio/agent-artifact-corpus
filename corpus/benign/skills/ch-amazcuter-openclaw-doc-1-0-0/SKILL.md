---
name: openclaw-guide
description: OpenClaw 平台完整使用指南。涵盖 Gateway 配置、频道设置（Telegram/Discord/WhatsApp/微信等）、定时任务、会话管理、安全策略、沙盒配置、模型管理、Agent 管理、设备配对、心跳机制、CLI 命令等。当需要：(1) 配置或排查 OpenClaw (2) 添加频道/定时任务/设备 (3) 安全审计或沙盒配置 (4) 理解 OpenClaw 架构和工作原理 (5) 编写 Agent 技能或插件时使用。
---

# OpenClaw 使用指南

OpenClaw 是一个开源的 AI 个人助手框架，通过 Gateway 连接多种频道（Telegram、Discord、WhatsApp、微信等），配合模型提供商（Kimi、GLM、OpenRouter 等）提供智能助手能力。

## 快速命令

| 需求 | 命令 |
|------|------|
| 查看状态 | `openclaw status` |
| 切换模型 | `/model kimi-coding/k2p5` |
| 压缩上下文 | `/compact` |
| 健康检查 | `openclaw doctor` |
| 安全审计 | `openclaw security audit [--fix]` |

## 核心架构

- **Gateway**: WebSocket 服务器，管理频道/节点/会话/hooks
- **Agent Loop**: 用户消息 → 模型推理 → 工具调用 → 循环直到完成
- **Context Engine**: 系统提示 + 工作区文件 + 对话历史 + 心跳
- **Compaction**: 上下文接近窗口限制时自动压缩

## 文档导航

本 Skill 包含 212 篇 OpenClaw 官方文档完整内容，按目录组织：

### 核心概念 - [references/concepts/](references/concepts/)
架构、Agent 循环、上下文引擎、模型故障转移、会话管理、记忆系统等 26 篇

### Gateway - [references/gateway/](references/gateway/)
配置、认证、安全、沙盒、心跳、远程访问、Tailscale、故障排除等 33 篇

### CLI 命令 - [references/cli/](references/cli/)
所有子命令：config、gateway、models、sessions、devices、nodes、cron、security 等 46 篇

### 频道配置 - [references/channels/](references/channels/)
Telegram、Discord、WhatsApp、Signal、Slack、微信等各平台配置 29 篇

### 工具 - [references/tools/](references/tools/)
exec、browser、web、PDF、skills、subagents、thinking 等 25 篇

### 自动化 - [references/automation/](references/automation/)
cron 定时任务、webhook、hooks、投票、认证监控 11 篇

### 模型提供商 - [references/providers/](references/providers/)
Anthropic、GLM、Moonshot、OpenAI、OpenRouter、Ollama、Qwen 9 篇

### 入门指南 - [references/start/](references/start/)
快速开始、安装、引导 5 篇

### 安全 - [references/security/](references/security/)
威胁模型 1 篇

### 帮助 - [references/help/](references/help/)
FAQ、调试、环境变量 4 篇

### 安装 - [references/install/](references/install/)
Docker、Node.js、更新 4 篇

### Web - [references/web/](references/web/)
Dashboard、Control UI 3 篇

### 参考模板 - [references/reference/](references/reference/)
AGENTS.md、SOUL.md、BOOTSTRAP.md 等工作区模板 8 篇

### 其他
- [overview.md](references/README.md) — 项目概览
- [index.md](references/index.md) — 文档索引
- [brave-search.md](references/brave-search.md) — 搜索配置
- [ci.md](references/ci.md) — CI 集成
- [tts.md](references/tts.md) — 语音合成
- [vps.md](references/vps.md) — VPS 部署

## 使用建议

遇到具体问题时，直接查阅对应目录下的文档。例如：
- 配置 Telegram → `references/channels/telegram.md`
- 设置定时任务 → `references/automation/cron-jobs.md` + `references/cli/cron.md`
- 安全审计 → `references/gateway/security/index.md` + `references/cli/security.md`
- 模型配置 → `references/concepts/models.md` + `references/cli/models.md`