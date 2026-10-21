# 用 WorkBuddy 复现这个项目

这个项目从「看比赛规则」到「跑通真机」全程在 WorkBuddy 里完成。下面是可复现的步骤。

---

## 一、把麦当劳 MCP 接进 WorkBuddy

编辑 `~/.workbuddy/mcp.json`（注意不是 `.mcp.json`）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer <你的 Token>"
      }
    }
  }
}
```

Token 在 https://open.mcd.cn/mcp 申请（手机号登录 → 控制台 → 激活）。

**接完不会自动生效** —— 到连接器管理页右上角的「自定义连接器」入口里，
找到 `mcd-mcp` 点「信任」，工具列表就会挂上来。

仓库里的 `mcp-config.example.json` 是脱敏版本，只有环境变量占位符，可以放心提交。

---

## 二、先探查真实数据，再动手写代码

**这一步最重要，别跳过。**

接上 MCP 之后，第一步不是写代码，是让 WorkBuddy 把每个工具真调一遍，看返回什么。

结果直接推翻了最初的设想：

| 原以为 | 实际 |
|---|---|
| 抽奖接口会返回中奖概率 | **不返回**，只有奖品名称/图片/类型 |
| 响应是干净的 JSON | 外面包了一层给模型看的 Markdown 说明 |
| 活动日历返回 JSON | 返回的是**纯 Markdown** |
| 商城 `price` 是商品售价 | `price = 0` 表示纯积分兑换，售价写在**商品名**里 |

如果先写代码再对接，这四条每一条都要返工。

对话里可以直接说：

> 帮我把麦当劳 MCP 的 query-lottery-info、mall-points-products、
> query-my-account、campaign-calendar 各真调一次，把原始返回贴出来给我看。

---

## 三、让 WorkBuddy 生成代码

数据形状确认之后，剩下的是常规工程活。给 WorkBuddy 的约束是：

- **只用 Python 标准库**（`urllib` + `json`），不引第三方依赖 —— 别人 clone 下来就能跑
- **核心计算和 IO 分离**：`engine.py` 纯算术不联网，`live.py` 只管抓数据
- **样例数据必须是真实抓取的**，不能编 —— 否则样例模式和真机模式结论会不一致

WorkBuddy 一次性产出了 `client.py` / `live.py` / `engine.py` / `report.py` /
`sample.py` / `run.py`，以及 45 项单测。

---

## 四、验证（这一步是分水岭）

代码写完不算完，要跑三件事：

```bash
python tests/test_engine.py       # 单测：45 项
python run.py --date 2026-10-09   # 样例模式：看报告排版
python run.py --live --token xxx  # 真机模式：看能不能连通（--token 跨 shell 通用）
```

**真机模式第一次跑是失败的**：`[出错] 没拿到可用的抽奖活动信息`。

排查发现响应被包了一层 Markdown（见 `MCP_INTEGRATION.md` 第 4 节），
修完 `_parse_text` 之后，真机和样例跑出来的结论完全一致：

```
保本线 = 1.308 元
抽奖上限 = 0.1250 元/分  vs  兑换最好档 = 0.1380 元/分
建议 = 换
```

**单测也在这个过程中抓到过一个真 bug**：
`_first_json` 的括号扫描会跳过响应体开头的数组（`test_scan_skips_array_before_object`）。
没有这一步测试，这个 bug 会潜伏到某个返回数组的工具上才炸。

---

## 五、截图给 README 用

`demo/index.html` 是手写的静态演示页（数据来自真实 JSON 导出），
用本机 Chrome 无头模式截的图：

```bash
chrome --headless=new --disable-gpu --hide-scrollbars \
  --virtual-time-budget=6000 --force-device-scale-factor=2 \
  --window-size=1000,1382 \
  --screenshot=docs/demo-screenshot.png \
  file:///<项目路径>/demo/index.html
```

---

## 六、一句话复现

```bash
git clone <本仓库>
python run.py          # 立刻能看到完整结论，不需要 Token、不联网
```

---

## 用到的 WorkBuddy 能力

| 能力 | 用在哪 |
|---|---|
| MCP 连接器 | 接麦当劳 MCP，真调 5 个只读工具 |
| 代码生成与重构 | 生成全部源码、单测、演示页 |
| 终端执行 | 跑单测、跑真机、编译检查、导出 JSON |
| 无头浏览器截图 | 生成 README 里的演示图 |

**没有用到的**：任何需要人工反复确认的环节 —— 从探查数据到真机跑通是连贯的。
