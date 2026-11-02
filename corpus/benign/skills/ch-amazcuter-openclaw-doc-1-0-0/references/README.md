# OpenClaw 完整文档库

> 来源: https://docs.openclaw.ai
> 下载时间: 2026-03-18 01:30
> 文档总数: 217 篇
> 总大小: 2.5 MB

---

## 📚 文档分布

| 目录 | 文档数量 | 说明 |
|------|---------|------|
| `automation/` | 8 | 自动化组件 (Cron, Heartbeat, Hooks, Webhook) |
| `channels/` | 24 | 聊天频道配置 (Telegram, Discord, Slack, WhatsApp等) |
| `cli/` | 45 | CLI命令参考 |
| `concepts/` | 27 | 核心概念 (Session, Retry, Models, Memory等) |
| `gateway/` | 31 | Gateway配置 (Security, Sandboxing, Health等) |
| `help/` | 4 | 帮助文档 |
| `install/` | 3 | 安装指南 |
| `providers/` | 2 | 模型提供商 |
| `reference/` | 7 | API参考和模板 |
| `security/` | 1 | 安全模型 |
| `start/` | 4 | 入门指南 |
| `tools/` | 26 | 工具文档 (Skills, Browser, Exec等) |
| `web/` | 3 | Web界面 |
| 根目录 | 13 | 主要文档 (index.md, pi.md, tts.md等) |

---

## 📖 核心文档推荐

### 配置相关
- `gateway/configuration.md` - 配置总览
- `gateway/configuration-reference.md` - 完整配置参考
- `concepts/retry.md` - 重试机制 ✅ 已学习
- `concepts/model-failover.md` - 模型故障转移 ✅ 已学习

### 定时任务相关
- `automation/cron-jobs.md` - Cron任务
- `automation/heartbeat.md` - Heartbeat机制
- `automation/hooks.md` - Hooks钩子

### 频道相关
- `channels/telegram.md` - Telegram配置 ✅ 已配置
- `channels/discord.md` - Discord配置
- `channels/slack.md` - Slack配置
- `channels/whatsapp.md` - WhatsApp配置

### 工具相关
- `tools/skills.md` - Skills开发
- `tools/browser.md` - Browser工具 ✅ 已安装
- `tools/exec.md` - Exec工具
- `tools/subagents.md` - SubAgents子代理

---

## 🔧 使用建议

### 查找文档
```bash
# 按关键词搜索
grep -r "关键词" /mnt/nas/openclaw-docs/

# 查看特定文档
cat /mnt/nas/openclaw-docs/concepts/retry.md
```

### 学习路径
1. **新手入门**: `start/getting-started.md`
2. **配置指南**: `gateway/configuration.md`
3. **定时任务**: `automation/cron-jobs.md`
4. **开发Skills**: `tools/skills.md`
5. **高级配置**: `gateway/configuration-reference.md`

---

## 📥 下载统计

- **总文档数**: 217 / 337 (64% 核心文档)
- **下载方式**: 并行批量下载 (10并发)
- **存储位置**: `/mnt/nas/openclaw-docs/`
- **备份状态**: 已同步到NAS

---

## 📝 备注

- 所有文档为Markdown格式
- 包含代码示例和配置片段
- 建议配合在线文档查看最新更新
- 本地文档用于离线查阅和学习

---

_整理时间: 2026-03-18_  
_维护者: 珮 (OpenClaw Agent)_
