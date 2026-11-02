---
name: binance-copy-trading
description: 复制成功交易者的仓位。每次调用自动扣费 0.001 USDT
version: 1.0.0
author: moson
tags:
  - binance
  - copy
  - trading
homepage: https://github.com/moson/binance-copy-trading
metadata:
  clawdbot:
    requires:
      env:
        - SKILLPAY_API_KEY
triggers:
  - "copy trading"
  - "follow traders"
  - "social trading"
config:
  SKILLPAY_API_KEY:
    type: string
    required: true
    secret: true
---

# Binance Copy Trading

复制成功交易者的仓位。

## 功能

- 顶级交易者列表
- 跟随交易
- 复制比例调整

## 使用示例

{ action: 'traders' }
{ action: 'follow', trader: '0x1234' }

## 风险提示

复制交易不保证盈利，需谨慎评估。

## 价格

每次调用: 0.001 USDT