# daily-report

📊 日报生成技能 - 你的私人日报助手

[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://clawhub.com/skills/daily-report)
[![License](https://img.shields.io/badge/license-MIT--0-lightgrey)](./LICENSE)

---

## 🚀 快速开始

### 安装

```bash
cd ~/.openclaw/workspace/skills/daily-report
./install.sh
```

### 使用

```bash
# 1. 收集数据
./scripts/collect-data.js

# 2. 生成日报
./scripts/generate-report.js --save --send
```

---

## ✨ 功能特性

- ✅ 自动收集日历/待办/邮件数据
- ✅ 多种模板（简单/详细/专业）
- ✅ 多格式输出（Markdown/文本/微信）
- ✅ 一键发送微信
- ✅ 定时自动生成
- ✅ 历史报告保存

---

## 📋 命令速查

| 命令 | 说明 | 示例 |
|------|------|------|
| `collect-data.js` | 收集数据 | `./scripts/collect-data.js` |
| `generate-report.js` | 生成日报 | `./scripts/generate-report.js --save` |
| `send-report.js` | 发送微信 | `./scripts/send-report.js` |
| `auto-report.js` | 自动生成 | cron 调用 |

---

## 📁 文件结构

```
daily-report/
├── scripts/
│   ├── collect-data.js      # 数据收集
│   ├── generate-report.js   # 生成日报
│   ├── send-report.js       # 发送微信
│   └── auto-report.js       # 自动生成
├── templates/
│   ├── simple.md            # 简单模板
│   ├── detailed.md          # 详细模板
│   └── weixin.md            # 微信模板
├── data/                    # 数据文件
├── reports/                 # 生成的报告
└── tests/                   # 测试脚本
```

---

## 📖 完整文档

详见 [SKILL.md](./SKILL.md)

---

## 🦆 作者

鸭鸭 (Yaya) - 你的私人日报助手

## 📄 许可证

MIT-0 License
