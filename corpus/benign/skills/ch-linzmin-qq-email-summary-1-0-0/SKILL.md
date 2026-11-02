---
name: email-summary
version: 1.0.0
description: 邮件摘要技能 - 自动获取并摘要每日邮件（QQ 邮箱）
author: linzmin1927
---

# 邮件摘要技能

> 📧 你的私人邮件秘书，让处理邮件更高效！

---

## 🎯 功能特性

- ✅ QQ 邮箱 IMAP 自动获取
- ✅ 智能分类（重要/普通/推广/垃圾）
- ✅ 每日摘要生成
- ✅ 微信推送摘要
- ✅ 自动定时任务

---

## 🚀 快速开始

### 1. 配置 QQ 邮箱

```bash
./scripts/setup-qq-email.js
```

按提示输入：
- QQ 邮箱地址
- IMAP 授权码

### 2. 获取邮件

```bash
./scripts/fetch-emails.js
```

### 3. 生成摘要

```bash
./scripts/summarize-emails.js --save --send
```

---

## 📋 命令详解

### 配置邮箱 `setup-qq-email.js`

```bash
./scripts/setup-qq-email.js
```

交互式配置向导，自动测试连接。

### 获取邮件 `fetch-emails.js`

```bash
# 获取最近 50 封邮件
./scripts/fetch-emails.js
```

### 生成摘要 `summarize-emails.js`

```bash
# 预览
./scripts/summarize-emails.js

# 保存并发送
./scripts/summarize-emails.js --save --send
```

### 测试连接 `test-connection.js`

```bash
./scripts/test-connection.js
```

---

## 📁 文件结构

```
email-summary/
├── scripts/
│   ├── setup-qq-email.js      # 配置向导
│   ├── fetch-emails.js        # 获取邮件
│   ├── summarize-emails.js    # 生成摘要
│   └── test-connection.js     # 测试连接
├── config/
│   └── email-config.json      # 邮箱配置（敏感！）
├── data/
│   └── emails.json            # 邮件数据
├── reports/                   # 生成的摘要
└── tests/                     # 测试脚本
```

---

## 🔧 QQ 邮箱配置

### 开启 IMAP/SMTP

1. 登录 https://mail.qq.com
2. 点击"设置" → "账户"
3. 开启"IMAP/SMTP 服务"
4. 生成授权码

### 配置参数

```json
{
  "email": {
    "provider": "qq",
    "address": "[REDACTED_SECRET]",
    "imap": {
      "host": "imap.qq.com",
      "port": 993,
      "tls": true
    }
  }
}
```

---

## 📊 邮件分类规则

| 分类 | 关键词 |
|------|--------|
| **重要** | urgent, important, 紧急，重要，会议，report |
| **推广** | promo, discount, 优惠，促销，订阅，营销 |
| **垃圾** | 发票，代开，赌博，彩票 |
| **普通** | 其他 |

---

## ⏰ 定时任务

安装时可选择添加 cron 任务，每天 20:00 自动获取并发送摘要：

```bash
0 20 * * * /path/to/fetch-emails.js && /path/to/summarize-emails.js --send
```

---

## 🔒 安全说明

- **配置文件** `config/email-config.json` 包含敏感信息
- 文件权限已设置为 `600`（仅所有者可读写）
- **不要**将配置文件提交到 Git
- 授权码泄露可重新生成

---

## ❓ 常见问题

### Q: 授权码是什么？

**A:** QQ 邮箱生成的专用密码，不是 QQ 登录密码。在"设置→账户"中生成。

### Q: 连接失败怎么办？

**A:** 检查：
1. IMAP/SMTP 服务是否开启
2. 授权码是否正确
3. 网络连接是否正常

运行 `./scripts/test-connection.js` 测试连接。

### Q: 支持其他邮箱吗？

**A:** 目前只支持 QQ 邮箱。Gmail/Outlook/163 等支持计划中。

---

## 📝 更新日志

### v1.0.0 (2026-03-26)
- ✅ QQ 邮箱 IMAP 集成
- ✅ 邮件获取和分类
- ✅ 摘要生成
- ✅ 微信推送
- ✅ 配置向导

---

## 🦆 作者

鸭鸭 (Yaya) - 你的私人邮件秘书

## 📄 许可证

MIT-0 License