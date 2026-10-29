---
name: binance-market-maker
description: 为 Binance 市场提供流动性。每次调用自动扣费 0.001 USDT
version: 1.0.0
author: moson
tags:
  - binance
  - market-maker
  - liquidity
homepage: https://github.com/moson/binance-market-maker
metadata:
  clawdbot:
    requires:
      env:
        - SKILLPAY_API_KEY
triggers:
  - "market maker"
  - "liquidity"
  - "MM"
  - "provide liquidity"
config:
  SKILLPAY_API_KEY:
    type: string
    required: true
    secret: true
---

# Binance Market Maker

为 Binance 市场提供流动性，通过买卖价差获利。

## 什么是做市商？

做市商是持续为市场提供流动性的交易者，通过买入（报价）和卖出（报价）来创造市场深度。

### 核心功能

- **双边挂单**: 同时设置买单和卖单
- **价差管理**: 调整买卖价差
- **自动做市**: 自动化订单管理
- **持仓对冲**: 风险对冲策略

### 策略参数

- 交易对: 用户选择
- 价差: 0.05% - 1%
- 订单数量: 根据资金量
- 刷新频率: 自动

## 使用示例

```javascript
// 查看做市状态
await handler({ action: 'status' });

// 启动做市
await handler({ 
  action: 'start', 
  pair: 'BTC/USDT', 
  spread: 0.1,
  orders: 5
});

// 停止做市
await handler({ action: 'stop' });
```

## 价格

每次调用: 0.001 USDT

## 风险提示

1. 单边行情可能导致持仓风险
2. 需要充足资金
3. 手续费可能影响利润
4. 建议了解持仓风险

## 做市策略技巧

1. 选择高流动性交易对
2. 合理设置价差
3. 定期调整订单
4. 关注市场变化
5. 设置风险上限