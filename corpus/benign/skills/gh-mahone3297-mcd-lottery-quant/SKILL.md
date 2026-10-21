---
name: mcd-lottery-quant
description: 麦当劳积分抽奖量化占卜。算清「1 积分值多少钱」「抽一次亏不亏」「该抽还是该换」，全程只读不替你抽奖。当用户问"积分抽奖值不值""该抽还是该换""抽奖保本线""积分商城哪件最划算""我的麦当劳积分怎么花"时使用。
---

# 积分抽奖量化占卜

把麦当劳积分抽奖从"感觉"变成"算术题"。

## 什么时候用它

- 用户问：积分抽奖值不值得抽 / 该抽还是该兑换
- 用户问：抽一次要多少积分、奖池里有什么、保本线是多少
- 用户问：我的积分怎么花最划算
- 用户问：积分商城里哪件东西最划算

## 它只做三件事

1. **1 积分值多少钱** —— 拿积分商城里每件商品的「售价 ÷ 所需积分」取中位数。
   用的是麦当劳自己标的售价，不是估算。
2. **抽一次亏不亏** —— 抽一次消耗的积分值多少钱，就是保本线；
   奖池逐件估价，标出赚 / 亏 / 看用法。
3. **该抽还是该换** —— 抽奖的"天花板"对比兑换的"最好档"，谁高听谁的。

## 怎么跑

```bash
# 零依赖、不联网、不用 Token
python run.py

# 连真实麦当劳 MCP（只读）—— 推荐用 --token，跟当前 shell 无关
python run.py --live --token 你的Token

# 也可以走环境变量，但注意写法随 shell 变：
#   cmd.exe          set MCD_MCP_TOKEN=你的Token
#   PowerShell       $env:MCD_MCP_TOKEN="你的Token"
#   Git Bash / mac   export MCD_MCP_TOKEN=你的Token
python run.py --live

# JSON 输出
python run.py --json
```

> ⚠️ PowerShell / Git Bash 里的 `set X=Y` **不会**设置环境变量（只有 cmd 认），
> 且不报错 —— 遇到 `[出错] 没拿到 MCP Token` 就改用 `--token`。

## 输出示例

```
【三】该抽，还是该换？

  抽奖（最好情况）抽到「下单立减3元券」　3.00 ÷ 24 = 0.1250 元/分
  兑换（最好档）  「6.9元香芋派/菠萝派任选」　0.1380 元/分

  → 结论：换。
```

## 硬边界（不可协商）

1. **不算期望值。** 官方不公开中奖概率，编一个出来就是算命。
   只算确定量：保本线、奖池上限。
2. **折扣券不估价。** 省多少取决于用户点什么，估了就是假的。
3. **只读。** 绝不调用 `draw-lottery`、`create-order`、`mall-create-order`、
   `party-order-create`。抽不抽、买不买，由用户自己按。

## 用到的 MCP 工具

`query-lottery-info` · `mall-points-products` · `query-my-account` ·
`query-my-prizes` · `campaign-calendar` —— 五个全是只读查询。

## 注意事项

- 麦当劳 MCP 的响应外面包了一层给模型看的 Markdown 说明，
  真正的 JSON 在 `## Original Response` 之后，解析要穿透（见 `mcd_quant/client.py`）。
- 活动日历返回的是**纯 Markdown**，不是 JSON，要单独解析。
- 积分商城返回的商品里，`point = 0` 的是花钱买的（派对、体验营），
  不是积分兑换，必须过滤掉。
