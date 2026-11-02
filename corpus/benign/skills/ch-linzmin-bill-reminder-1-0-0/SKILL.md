---
name: bill-reminder
version: 1.0.0
description: 账单提醒技能 - 自动监控账单到期并发送微信提醒
author: linzmin1927
---

# 账单提醒技能

> 🦆 你的私人账单管家，再也不怕忘记还款！

---

## 🎯 功能特性

- ✅ 支持多种账单类型（信用卡、花呗、房租、水电费等）
- ✅ 灵活周期设置（每月、每周、每年）
- ✅ 提前 N 天提醒，避免逾期
- ✅ 微信消息提醒，及时触达
- ✅ 还款记录自动保存
- ✅ 逾期提醒（前 3 天持续提醒）
- ✅ 命令行操作，简单高效

---

## 🚀 快速开始

### 1. 安装

```bash
# 自动安装（发布后）
npx clawhub@latest install bill-reminder

# 或手动安装
cd ~/.openclaw/workspace/skills/bill-reminder
./install.sh
```

### 2. 添加账单

```bash
# 基本用法
./scripts/add-bill.js "信用卡" 5000 15

# 完整参数
./scripts/add-bill.js "信用卡" 5000 15 monthly 3
# 参数：名称 金额 日期 周期 提前天数
```

### 3. 查看账单

```bash
./scripts/list-bills.js
```

### 4. 标记还款

```bash
./scripts/mark-paid.js 1 "已还清"
```

---

## 📋 命令详解

### 添加账单 `add-bill.js`

```bash
./scripts/add-bill.js <名称> <金额> <日期> [周期] [提前天数]
```

**参数说明：**

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| 名称 | ✅ | - | 账单名称（如：信用卡、花呗、房租） |
| 金额 | ✅ | - | 账单金额（元） |
| 日期 | ✅ | - | 每月几号（1-31） |
| 周期 | ❌ | monthly | monthly/weekly/yearly |
| 提前天数 | ❌ | 3 | 提前几天提醒（0-30） |

**示例：**

```bash
# 信用卡每月 15 号 5000 元，提前 3 天提醒
./scripts/add-bill.js "信用卡" 5000 15

# 花呗每月 8 号 2000 元，提前 1 天提醒
./scripts/add-bill.js "花呗" 2000 8 monthly 1

# 房租每月 1 号 3000 元，提前 5 天提醒
./scripts/add-bill.js "房租" 3000 1 monthly 5

# 每周提醒（如：周报）
./scripts/add-bill.js "周报" 0 1 weekly 1

# 每年提醒（如：保险）
./scripts/add-bill.js "车险" 3000 15 yearly 7
```

---

### 查看账单 `list-bills.js`

```bash
# 查看活跃账单
./scripts/list-bills.js

# 查看所有账单（包括已删除）
./scripts/list-bills.js --all

# 查看还款历史
./scripts/list-bills.js --history
```

**输出示例：**

```
📋 账单列表

============================================================

1. ⚠️ 信用卡
   💰 ¥5000
   📅 每月 15 日
   ⏰ 提前 3 天提醒
   📆 还有 2 天到期
   ✓ 上次还款：2026/2/15

2. ✅ 房租
   💰 ¥3000
   📅 每月 1 日
   ⏰ 提前 5 天提醒
   📆 还有 15 天到期
   ✓ 上次还款：2026/3/1

============================================================
总计：2 个账单
```

---

### 标记还款 `mark-paid.js`

```bash
./scripts/mark-paid.js <序号> [备注]
```

**示例：**

```bash
# 标记第 1 个账单已还
./scripts/mark-paid.js 1

# 添加备注
./scripts/mark-paid.js 2 "已还清全部"
```

---

### 删除账单 `remove-bill.js`

```bash
./scripts/remove-bill.js <序号>
```

**示例：**

```bash
# 删除第 1 个账单
./scripts/remove-bill.js 1
```

---

## ⏰ 自动提醒

### 定时任务

安装时会自动添加 cron 任务，每天 9:00 检查账单：

```bash
0 9 * * * /path/to/bill-reminder/scripts/check-bills.js >> ~/.openclaw/logs/bill-reminder.log 2>&1
```

### 提醒规则

| 情况 | 提醒时间 | 提醒内容 |
|------|---------|---------|
| 提前 N 天 | 到期前 N 天的 9:00 | ⏰ 账单提醒 |
| 到期当天 | 到期日 9:00 | ⚠️ 今天到期！ |
| 逾期 1-3 天 | 逾期后每天 9:00 | 🚨 已逾期！ |

### 防重复机制

- 同一天的同类型提醒只发送一次
- 次日自动清除标记，允许再次提醒

---

## 💬 微信提醒示例

### 提前提醒

```
⏰ 账单提醒

📋 招商银行信用卡
💰 ¥5000
📅 15 日到期

还有 3 天，别忘了哦～ 🦆
```

### 到期提醒

```
⚠️ 今天到期！

📋 招商银行信用卡
💰 ¥5000

今天最后期限，快还！🦆
```

### 逾期提醒

```
🚨 已逾期！

📋 招商银行信用卡
💰 ¥5000
📅 逾期 2 天

赶紧还，要产生利息了！🦆
```

### 还款确认

```
✅ 已记录还款！

📋 招商银行信用卡
💰 ¥5000
📅 下次到期：4 月 15 日

继续保持良好的信用记录～ 🦆
```

---

## 📁 文件结构

```
bill-reminder/
├── SKILL.md                    # 本文件
├── README.md                   # 快速入门
├── package.json                # 项目配置
├── install.sh                  # 安装脚本
├── scripts/
│   ├── add-bill.js             # 添加账单
│   ├── list-bills.js           # 查看账单
│   ├── remove-bill.js          # 删除账单
│   ├── mark-paid.js            # 标记还款
│   └── check-bills.js          # 检查到期（cron 用）
├── data/
│   └── bills.json              # 账单数据存储
└── tests/
    └── test-bill-reminder.sh   # 测试脚本
```

---

## 💾 数据格式

`data/bills.json` 存储所有账单数据：

```json
{
  "bills": [
    {
      "id": "bill_1711432800000",
      "name": "招商银行信用卡",
      "amount": 5000,
      "dueDay": 15,
      "cycle": "monthly",
      "advanceDays": 3,
      "userId": "[REDACTED_SECRET]",
      "createdAt": "2026-03-26T13:00:00Z",
      "lastPaid": "2026-02-15T10:30:00Z",
      "nextDue": "2026-04-15T00:00:00Z",
      "status": "active"
    }
  ],
  "paymentHistory": [
    {
      "billId": "bill_1711432800000",
      "paidAt": "2026-02-15T10:30:00Z",
      "amount": 5000,
      "note": "已还清"
    }
  ]
}
```

---

## 🔧 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEIXIN_CHANNEL` | openclaw-weixin | 微信渠道 ID |
| `WEIXIN_ACCOUNT` | d72d5b576646-im-bot | 微信账号 ID |
| `WEIXIN_USER_ID` | [REDACTED_SECRET] | 接收提醒的用户 ID |

### 修改提醒时间

编辑 crontab：

```bash
crontab -e
```

修改第一行（9 改成你想要的小时）：

```
0 9 * * * /path/to/check-bills.js >> ...
```

---

## ❓ 常见问题

### Q: 支持多个用户吗？

**A:** 目前每个用户需要单独配置。可以在添加账单时指定不同的 `userId`。

### Q: 可以设置多个提醒时间吗？

**A:** 目前固定每天 9:00 检查。如需多次提醒，可以添加多个 cron 任务：

```bash
# 早晚各检查一次
0 9 * * * /path/to/check-bills.js >> ...
0 20 * * * /path/to/check-bills.js >> ...
```

### Q: 数据会丢失吗？

**A:** 数据存储在本地 JSON 文件，建议定期备份：

```bash
cp ~/.openclaw/workspace/skills/bill-reminder/data/bills.json ~/backup/bills-$(date +%Y%m%d).json
```

### Q: 支持农历日期吗？

**A:** 目前只支持公历。农历需求可以提 Issue～

### Q: 逾期后怎么停止提醒？

**A:** 标记还款即可：

```bash
./scripts/mark-paid.js <序号>
```

---

## 🔒 安全说明

- 所有数据存储在本地，不会上传
- 微信消息通过 OpenClaw 官方渠道发送
- 建议定期备份 `data/bills.json`

---

## 📝 更新日志

### v1.0.0 (2026-03-26)
- ✅ 初始版本发布
- ✅ 支持添加/查看/删除账单
- ✅ 支持标记还款
- ✅ 自动到期检查（cron）
- ✅ 微信提醒（提前/到期/逾期）
- ✅ 还款历史记录

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT-0 License

---

## 🦆 作者

鸭鸭 (Yaya) - 你的私人账单管家