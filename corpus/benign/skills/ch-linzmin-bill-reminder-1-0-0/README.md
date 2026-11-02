# bill-reminder

🦆 账单提醒技能 - 你的私人账单管家

[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://clawhub.com/skills/bill-reminder)
[![License](https://img.shields.io/badge/license-MIT--0-lightgrey)](./LICENSE)

---

## 🚀 快速开始

### 安装

```bash
# 自动安装
npx clawhub@latest install bill-reminder

# 或手动安装
cd ~/.openclaw/workspace/skills/bill-reminder
./install.sh
```

### 使用

```bash
# 添加账单
./scripts/add-bill.js "信用卡" 5000 15

# 查看账单
./scripts/list-bills.js

# 标记还款
./scripts/mark-paid.js 1

# 删除账单
./scripts/remove-bill.js 1
```

---

## ✨ 功能特性

- ✅ 支持多种账单类型（信用卡、花呗、房租、水电费）
- ✅ 灵活周期（每月/每周/每年）
- ✅ 提前 N 天提醒
- ✅ 微信消息提醒
- ✅ 还款记录自动保存
- ✅ 逾期提醒
- ✅ 每天自动检查（cron）

---

## 📋 命令速查

| 命令 | 说明 | 示例 |
|------|------|------|
| `add-bill.js` | 添加账单 | `./scripts/add-bill.js "信用卡" 5000 15` |
| `list-bills.js` | 查看账单 | `./scripts/list-bills.js` |
| `mark-paid.js` | 标记还款 | `./scripts/mark-paid.js 1` |
| `remove-bill.js` | 删除账单 | `./scripts/remove-bill.js 1` |

---

## ⏰ 自动提醒

安装后自动配置 cron 任务，每天 9:00 检查账单并发送微信提醒：

- ⏰ 提前 N 天提醒
- ⚠️ 到期当天提醒
- 🚨 逾期提醒（前 3 天）

---

## 📖 完整文档

详见 [SKILL.md](./SKILL.md)

---

## 🦆 作者

鸭鸭 (Yaya) - 你的私人账单管家

## 📄 许可证

MIT-0 License
