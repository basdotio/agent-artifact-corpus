# 生态与选型：四个开源组件

## 组件一览

### 1. 酒馆助手（JS-Slash-Runner / TavernHelper）
- 仓库：`https://github.com/N0VI028/JS-Slash-Runner`，文档：`https://n0vi028.github.io/JS-Slash-Runner-Doc/`
- 安装：酒馆「扩展」面板 → 「安装扩展」→ 输入仓库 URL。**要求 SillyTavern 1.13.x 及以上**。
- 它是"底座"：本身不做具体功能，而是给角色卡/脚本/界面提供能力——
  - 渲染消息中的 HTML 代码块为**无沙盒 iframe**（前端界面的载体）；
  - 运行「脚本库」中的脚本（全局脚本 / 角色卡脚本 / 预设脚本），脚本以无沙盒 iframe 在后台运行；
  - 提供全套 API：`getVariables`/`replaceVariables`（酒馆变量）、`getChatMessages`/`setChatMessages`（楼层）、`eventOn`（事件）、`injectPrompts`（提示词注入）、`generate`/`generateRaw`（请求生成）、`triggerSlash`（STscript）等；
  - 宏：`{{format_message_variable::路径}}`、`{{get_message_variable::路径}}` 等；
  - 工具：日志查看器、变量管理器、提示词查看器、正则管理。
- 角色卡脚本存放于卡内 `data.extensions.tavern_helper.scripts`——**玩家导入卡即自动获得脚本**，无需手动导入。

### 2. MVU 变量框架（MagVarUpdate）
- 仓库：`https://github.com/MagicalAstrogy/MagVarUpdate`（另有镜像 `Mooooooon/MagVarUpdate`），教程：仓库内 `doc/tutorial.md`
- 形态：一个酒馆助手**脚本**，卡内以一行引入：
  ```js
  import 'https://testingcf.jsdelivr.net/gh/MagicalAstrogy/MagVarUpdate/artifact/bundle.js';
  ```
- 作用：把角色卡变成"变量卡"——
  - 变量按**消息楼层**存放于楼层变量的 `stat_data`；
  - 解析 AI 回复/用户输入中的 `<UpdateVariable>` 块（内部为新式 JSONPatch 或旧式 `_.set('路径', 值)` 命令），更新变量；
  - 每次 AI 回复结束后自动在末尾附加 `<StatusPlaceHolderImpl/>` 占位符，供正则替换为界面；
  - 支持：按开局初始化（`<initvar>` 块）、`_变量`（AI 不可更新）、`$变量`（AI 不可见）、事件钩子（`Mvu.events.*`）与自行解析（`Mvu.parseMessage`）。
- 变量结构（schema）通过 StageDog 的注册工具接入：
  ```js
  import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';
  ```

### 3. 提示词模板（ST-Prompt-Template）
- 仓库：`https://github.com/zonde306/ST-Prompt-Template`（镜像 `https://codeberg.org/zonde306/ST-Prompt-Template`）
- 安装：与酒馆助手相同的安装方式，URL 填 codeberg 或 GitHub 仓库地址。
- 作用：在提示词/角色卡/世界书里写 **EJS**，让"发哪段提示词"与变量、聊天情况挂钩：
  - `<%_ 代码 _%>`、`<%= 表达式 %>`；
  - `getvar('stat_data.角色.好感度')`、`print()`、`getwi('条目标题')`、`matchChatMessages([...])`；
  - 条目开头加 `@@preprocessing` 可在**世界书激活前**处理内容（ST 1.13.4+），从而支持绿灯/黏性/冷却。
- 常用场景：分阶段人设（好感度低/中/高各发不同提示词）、按开局发送不同世界观、按剧情进程切换主线/突发事件。
- 制作卡时注意：在写卡/调试 AI 时可通过写卡助手的「启用/禁用提示词模板和酒馆助手宏」按钮关闭处理，让 AI 看到原始提示词。

### 4. 小白X（LittleWhiteBox）
- 仓库：`https://github.com/RT15548/LittleWhiteBox`，文档：`https://docs.littlewhitebox.qzz.io/`
- 另一条路线：自带代码块渲染（```html/`<script>` 代码块 → 自适应高度 iframe）、**变量管理 2.0**（`<state>` 块 + `$schema` 约束）、变量面板、小白板（剧情地图）、四次元壁（OOC）、剧情总结、流式模板渲染、TTS/NovelAI 配图等。
- 选型建议：需要"剧情总结/地图/写实经营玩法"等小白X 独有特性时选它；纯 MVU 变量卡（社区教程、示例、模板最丰富）优先酒馆助手路线。二者可同装，卡片按目标渲染器决定输出格式（详见 `xiaobaix.md`）。
- 注意：小白X 的变量管理与 MVU 是两套体系，**同一张卡不要混用两套变量机制**，避免状态不同步。

## 依赖来源（CDN）

社区约定用 jsdelivr 加载公共脚本。镜像混用很常见：`testingcf.jsdelivr.net`（教程示例常用）、`gcore.jsdelivr.net`、`cdn.jsdelivr.net` 都在实测卡中出现；也可固定分支（`…/MagVarUpdate@master/…`、`@beta`）。任选其一即可：

| 资源 | URL |
|---|---|
| MVU 本体 | `https://testingcf.jsdelivr.net/gh/MagicalAstrogy/MagVarUpdate/artifact/bundle.js` |
| MVU schema 注册工具 | `https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js` |

## 玩家侧要求（写进交付说明）

1. 安装扩展：**酒馆助手** + **提示词模板**（两者缺一，变量卡的核心功能都会失效）。
2. 开启酒馆助手的渲染开关（扩展设置 → 酒馆助手 → 渲染；否则状态栏/前端不显示）。
3. 首次进入卡时会弹窗询问是否启用卡内正则 → 选择允许。
4. 新开聊天让变量初始化生效。

## 酒馆助手实用脚本库（交付增强）

青空莉的 `StageDog/tavern_resource` 仓库 `dist/酒馆助手/` 下有一批"即取即用"的工具脚本，一行 import 即可挂进任何卡：

```js
import 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/酒馆助手/<脚本名>/index.js';
```

常用（完整列表见仓库目录）：

| 脚本 | 用途 |
|---|---|
| `自动安装插件` | **交付利器**：检测玩家缺失的扩展并弹窗一键安装（内置 `/api/extensions/discover` + `/api/extensions/install` 流程），可把"请先安装酒馆助手/提示词模板"变成卡内自动化 |
| `自动开启角色卡局部正则` | 免去玩家手动"允许该卡正则"的步骤 |
| `角色卡绑定预设` / `自动更新角色卡` / `自动更新预设` | 卡与预设联动、热更新 |
| `快速回复随角色卡导入导出` | 让 QuickReply 组随卡分发/重建（QR 数据也存在卡 extensions 里） |
| `快速切换开局` / `世界书强制自定义排序` / `世界书强制用推荐的全局设置` | 玩家体验优化 |
| `资源预载` / `样式加载` / `消息接收完成时滚至消息开头` / `深度条目排斥器` / `流式传输` / `文生图` 等 | 各类体验增强 |

按需 import；交付说明里可只写"本卡已内置依赖自动安装，缺失时会弹窗提示"。

## 作者自建托管仓库（脚本/资源的 CDN 分发）

语料里大量卡把脚本/界面 HTML 托管在作者自建的 GitHub 仓库上，用 jsdelivr 一行 import（支持热更新、卡体变小）：

- `StageDog/tavern_resource`（青空莉：脚本与工具集合）、`KATOUIV/QHZ`（按卡分目录的脚本与美化 HTML，多张卡共用）、`vincentrong2005/Fatria`、`aaron4090185/tavern_dist`、`AlbusKen/shujuku`、`The-poem-of-destiny/FrontEnd-for-destined-journey`、`Youzini-afk/tavern_helper_template`（模板分支，如 Evolution World）等。

注意事项：

- 发布前把开发地址清掉——语料里有多张卡残留 `http://localhost:5500` 导入，玩家端必然失效（`check_card.py` 会警告）。
- 托管方式是双刃剑：能热更新，但仓库删档/改名/网络不可达 = 玩家侧功能消失；重要功能建议随卡内联或双写兜底。

## 大型工程工作流（量大时的工程化路径）

- **tavern_helper_template**（StageDog）：默认推荐的前端/脚本工程（VSCode + pnpm + 实时监听）。
- **Card Forge**（`config_card-forge.yaml` 驱动）：把角色卡"仓库化"——卡字段拆成 md、世界书条目拆成 `{insertion_order}_{comment}.yaml`、正则/脚本各自成文件，改完再打包回卡（语料里的 TESV 天际模拟器工程在用）。
- **TESV 式组织**（实测工程）：`lorebook/` 按内容包拆分（一本书一个目录）、`docs/` 放数据结构与流程设计文档、`shared/` 放共享 TS 库与资源、构建/校验脚本成套。上千条世界书的巨型卡基本都靠这种结构维持可维护性。

## 术语表（沟通时对齐）

| 术语 | 含义 |
|---|---|
| 变量卡 | 用 MVU 维护变量的角色卡 |
| 状态栏 | 显示在消息里的变量面板（由占位符+正则+HTML 实现） |
| 前端界面 | 消息里的可交互 iframe（点按钮改变量/请求生成） |
| D0 / 指定深度 | 世界书条目注入位置：对话最末端（深度 0） |
| 蓝灯 | 世界书"常驻"条目（constant），每轮都发送 |
| 绿灯 | 按关键字触发的世界书条目 |
| 变量管理器 | 酒馆助手提供的变量查看/编辑面板（输入框左侧魔棒 → 变量管理器） |
| 日志查看器 | 酒馆助手的脚本运行日志（排查变量结构/初始化错误） |
| 提示词查看器 | 查看实际发送给 AI 的提示词（验证 EJS/正则/注入效果） |
