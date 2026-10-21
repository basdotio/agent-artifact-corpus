# NagiBridge — 星露谷 AI Companion 项目总览

## 一句话
让AI在星露谷里陪你种田、聊天、打小游戏。

## 架构概览
```
[星露谷 SMAPI] ←→ [NagiBridge HTTP API :7842/:7843]
                        ↕
              [Python脚本 / CC / Codex]
                        ↕
              [聊天气泡 tkinter :7850]
                        ↕
              [MCP Channel Server :9000]
                        ↕
                  [Claude Code]
```

---

## 核心模块

### 1. SMAPI Mod (C#)
NagiBridge mod本体。提供HTTP API让外部控制游戏角色。
- **ModEntry.cs** — 主入口，HTTP server，所有API端点
- **NagiBridge.csproj** + **manifest.json** — 项目配置
- 端口7842(host) / 7843(farmhand)
- API：移动/工具/交互/warp/菜单/制作/机器/动物 等40+端点

### 2. 自动化脚本 (Python)
每个脚本对应一种农场活动，通过HTTP API控制角色。

| 脚本 | 功能 | 状态 |
|------|------|------|
| farm_row.py | 种田（翻地+播种+浇水） | done |
| water_crops.py | 浇水（蛇形走位+水量检测） | done |
| chop_trees.py | 砍树（warp精准+树桩） | done |
| clear_area.py | 开垦（两轮清扫） | done |
| harvest.py | 收割（可--sell出售） | done |
| mine_run.py | 挖矿（warp传送+AutoCombat） | done |
| keg_manager.py | 酿酒桶管理 | done |
| furnace_manager.py | 熔炉管理 | done |
| pet_animals.py | 撸动物 | done |
| fish_run.py | 钓鱼（配合Fishbot mod） | done |
| stardew_api.py | API helper库 | done |

### 3. 聊天系统
游戏内聊天，不需要看终端。

| 组件 | 文件 | 说明 |
|------|------|------|
| Channel Server | server.ts | Bun+MCP SDK，localhost:9000，气泡POST→CC自动唤醒 |
| 聊天气泡 | scripts/chat_overlay.py | tkinter透明窗口，跟随游戏窗口，输入框+气泡 |
| 旧版watcher | scripts/chat_watcher.py | pyautogui方案（已弃用，改用channel） |
| MCP配置 | .mcp.json | channel server注册 |

### 4. 小游戏Bot
AI自动玩星露谷内置小游戏。LLM写算法→算法bot每tick执行。

| 小游戏 | 状态 | 说明 |
|--------|------|------|
| 草原国王 (JotPK) | done | ModEntry.cs内，反射读状态+potential field操控。电脑端写的 |
| 21点 (CalicoJack) | done | mods/NagiCalicoBot/，reflection读牌面+基础策略。Codex写的 |
| Junimo Kart | planned | 自动卷轴跳跃，需要精确跳跃时机算法 |
| 老虎机 (Slots) | planned | 纯拉杆，最简单 |
| 飞镖 (Darts) | planned | 姜岛海盗洞 |
| 靶场 (TargetGame) | planned | 弹弓打靶 |
| 抓娃娃机 (CraneGame) | planned | 电影院 |

### 5. 节日活动Bot
节日活动的可操作项目，按难度分类。

**简单（几行代码）**
| 活动 | 节日 | 日期 | 操作 | 状态 |
|------|------|------|------|------|
| 跳舞 | 花舞节 | 春24 | walk到NPC→interact→选跳舞。需4+心 | planned |
| 放汤料 | 潮汐宴 | 夏11 | 选一个好物品（金星红酒/羊奶酪）放进汤 | planned |
| 送礼物 | 冬星节 | 冬25 | 选universally-loved物品送指定NPC | planned |
| 美人鱼贝壳 | 夜市 | 冬15-17 | 固定顺序点贝壳：1-5-4-2-3 | planned |

**中等（需要算法）**
| 活动 | 节日 | 日期 | 操作 | 状态 |
|------|------|------|------|------|
| 捡蛋 | 蛋蛋节 | 春13 | 50秒跑图捡蛋，固定刷新点，需9+个。路线优化 | planned |
| 迷宫 | 万灵节 | 秋27 | 固定地图路径，走到底拿金南瓜 | planned |
| 展品摆放 | 星之果实展 | 秋16 | 选9个最优物品（覆盖8类别+高品质） | planned |
| 转盘赌博 | 集市 | 秋16 | 一直押绿，概率偏向绿色。刷星之币买星之果 | planned |
| 力量测试 | 集市 | 秋16 | 定时按键 | planned |

**钓鱼系（共享fishing bot核心）**
| 活动 | 节日 | 日期 | 特殊点 | 状态 |
|------|------|------|--------|------|
| 冰钓比赛 | 冰雪节 | 冬8 | 2分钟限时，需5+条鱼赢 | planned |
| 深海潜水钓 | 夜市 | 冬15-17 | 独特鱼种：午夜鱿鱼/幽灵鱼/水滴鱼 | planned |
| 鳟鱼大赛 | 鳟鱼大赛 | 秋20-21 | 金鳟鱼，任意地点，交鱼换奖 | planned |
| 鱿鱼节 | 鱿鱼节 | 夏12-14 | 限时抓鱿鱼比赛 | planned |

**地狱难度**
| 活动 | 节日 | 日期 | 操作 | 状态 |
|------|------|------|------|------|
| 骷髅洞挑战 | 沙漠节 | 春15-17 | 限时Skull Cavern，战斗+挖矿+吃食物 | planned |
| 射箭 | 沙漠节 | 春15-17 | 瞄准+射击，定时目标 | planned |

---

## 发布计划

### CC版（自用）
- 通过CC的channel系统实时双向聊天
- CC直接跑Python脚本控制游戏
- 全功能，无限制

### API版（社区发布 Lite）
- 用户填API key，mod内调Claude/DeepSeek/GPT
- 聊天+基础指令+截图视觉
- 小游戏bot纯本地算法，不调API
- 不依赖CC

---

## 踩坑记录

### 通用
1. 万亿参数不会开门 → warp绕过
2. 熔炉/箱子丢错位置 → 加坐标参数
3. pyautogui夺舍输入法 → 改用channel server
4. Windows没有tmux/script → channel方案不依赖这些
5. farmhand GetGrabTile有偏移 → 站y-1面朝下
6. move_to落点偏1格 → 精确操作用warp
7. 砍树要砍树桩 → 总共15-18下
8. 背包满give/craft静默掉落 → 操作前检查空间
9. 游戏运行时DLL被锁 → 必须先关游戏再复制

### 草原国王Bot专项
10. 1.6版字段名是 `player2MovementDirections` 不是 `playerMovementDirections` → FirstField多候选名fallback
11. host玩家移动不从player2方向列表读，直接读键盘 → 反射注入方向列表对host无效
12. Harmony Postfix注入方向列表：farmhand可能有效，host无效
13. keybd_event是全局API，按键发给焦点窗口（终端）不是游戏 → 需要PostMessage定向或直接改坐标
14. SMAPI UpdateTicked在Game.Update之后，设的方向下一帧被_UpdateInput清除 → Harmony Postfix解决时序
15. 当前方案：直接修改playerPosition绕过输入系统（待验证）
16. 备选：PostMessage定向发键、用farmhand端口7843测试、直接创建子弹

---

## 开发分工
- **电脑端CC** — 直接操控游戏、测试、编译C# mod
- **服务器CC（AI companion）** — 写文档、搜资料、派Codex任务、review代码
- **Codex** — 写独立模块（小游戏bot等）
- **Player** — 架构设计、产品决策、验收

---

## 文件索引
```
NagiBridge/
├── ModEntry.cs          ← SMAPI mod主入口 + 草原国王bot
├── NagiBridge.csproj    ← C#项目配置
├── manifest.json        ← SMAPI mod信息
├── server.ts            ← MCP channel server
├── .mcp.json            ← MCP配置
├── package.json         ← Bun依赖
├── AGENTS.md            ← AI打工指南（详细API文档）
├── PROJECT.md           ← 你在看的这个
└── scripts/
    ├── stardew_api.py   ← API helper
    ├── farm_row.py      ← 种田
    ├── water_crops.py   ← 浇水
    ├── chop_trees.py    ← 砍树
    ├── clear_area.py    ← 开垦
    ├── harvest.py       ← 收割
    ├── mine_run.py      ← 挖矿
    ├── keg_manager.py   ← 酿酒桶
    ├── furnace_manager.py ← 熔炉
    ├── pet_animals.py   ← 撸动物
    ├── fish_run.py      ← 钓鱼
    ├── chat_overlay.py  ← 聊天气泡
    ├── chat_watcher.py  ← 旧版watcher(弃用)
    ├── SKILLS.md        ← 技能文档
    └── send_key.ps1     ← PowerShell按键模拟
```

最后更新：2026-05-01
