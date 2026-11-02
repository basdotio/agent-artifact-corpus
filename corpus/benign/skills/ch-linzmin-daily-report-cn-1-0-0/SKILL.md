---
name: daily-report
version: 1.0.0
description: 日报生成技能 - 自动收集数据并生成工作日报
author: linzmin1927
---

# 日报生成技能

> 📊 你的私人日报助手，让写日报变得简单！

---

## 🎯 功能特性

- ✅ 自动收集日历、待办、邮件数据
- ✅ 多种模板可选（简单/详细/专业）
- ✅ 支持多种输出格式（Markdown/文本/微信）
- ✅ 一键发送微信
- ✅ 自动定时生成（cron）
- ✅ 历史报告保存和查看

---

## 🚀 快速开始

### 1. 安装

```bash
cd ~/.openclaw/workspace/skills/daily-report
./install.sh
```

### 2. 收集数据

```bash
./scripts/collect-data.js
```

### 3. 生成日报

```bash
./scripts/generate-report.js --save --send
```

---

## 📋 命令详解

### 收集数据 `collect-data.js`

```bash
# 收集所有数据
./scripts/collect-data.js

# 单独收集
./scripts/collect-data.js --calendar
./scripts/collect-data.js --todo
./scripts/collect-data.js --email
./scripts/collect-data.js --manual

# 查看已收集数据
./scripts/collect-data.js --output
```

### 生成日报 `generate-report.js`

```bash
# 预览
./scripts/generate-report.js

# 保存并发送
./scripts/generate-report.js --save --send

# 使用详细模板
./scripts/generate-report.js --template detailed --save

# 微信格式输出
./scripts/generate-report.js --output weixin --send
```

### 发送日报 `send-report.js`

```bash
# 发送今日日报
./scripts/send-report.js

# 发送指定日期
./scripts/send-report.js 2026-03-26
```

---

## 📁 模板示例

### 简单模板 (simple)

```markdown
# 工作日报 - 2026-03-26

## 📅 今日工作

- 09:00-10:00 晨会
- 14:00-15:00 项目评审

## ✅ 完成情况

- ✅ 完成日报技能开发
- ⏳ 代码审查

## 📧 邮件处理

收到：15 封
发送：8 封

## 💡 今日总结

今天完成了日报技能的开发...

## 🎯 明日计划

- [ ] 
```

### 详细模板 (detailed)

包含更多字段：收获与成长、遇到的问题、改进建议、本周进度表等。

---

## ⏰ 自动定时

安装时可选择添加 cron 任务，每天 18:00 自动生成日报：

```bash
0 18 * * * /path/to/auto-report.js >> ~/.openclaw/logs/daily-report.log 2>&1
```

---

## 💾 数据存储

**数据文件：** `data/daily-data.json`

**报告目录：** `reports/`

```
reports/
├── report-2026-03-26.md
├── report-2026-03-25.md
└── ...
```

---

## 🔧 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEIXIN_CHANNEL` | openclaw-weixin | 微信渠道 ID |
| `WEIXIN_ACCOUNT` | d72d5b576646-im-bot | 微信账号 ID |
| `WEIXIN_USER_ID` | [REDACTED_SECRET] | 接收用户 ID |

### 自定义模板

在 `templates/` 目录创建新模板：

```bash
cp templates/simple.md templates/my-template.md
# 编辑 my-template.md
```

使用：

```bash
./scripts/generate-report.js --template my-template
```

---

## 📝 完整文档

详见 [SKILL.md](./SKILL.md)

---

## 🦆 作者

鸭鸭 (Yaya) - 你的私人日报助手

## 📄 许可证

MIT-0 License