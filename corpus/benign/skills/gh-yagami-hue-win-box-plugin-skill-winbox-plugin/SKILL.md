---
name: winbox-plugin
description: Author, validate, and package Win-Box .winbox plugins. Use when the user asks to build a Win-Box plugin (插件), or about plugin.json, contributes, permissions, mpv.shaders, theme, providers, or player.engine (第三方播放内核). Do not use for TVBox source rules.
---

# Win-Box 插件开发

为 Win-Box 制作 / 校验 / 打包 `.winbox` 插件。

## 冷启动（先读这两页）
1. `references/host-overview.md` —— **宿主速览**（Win-Box 是什么 / 双内核与 GLSL 只作用 MPV / M1 白名单 / 插件在 UI 何处出现）。**冷启动必读**，补齐项目背景常识。
2. `SPEC.md`（仓库根）—— **规范**：字段 / 白名单 / 校验的唯一权威；**皮肤专项口径（令牌词表 / 布局枚举 / 拒装原因码）在 §15**。

> 你的产出**不得与规范冲突**；若发现冲突，**以规范为准**，并提醒用户更新规范。
> 需要核对白名单 / 宿主实现时才**定向**看主仓（`github.com/yagami-hue/Win-box`；M1 后看 `src/shared/plugin.ts`）——**不要通读整个仓库**。

## 铁律
1. **`permissions` 只属 L4**（`kind:"code"`）；L1/L2/L3（`kind:"asset"`）**必须** `permissions: []`。
2. 第三方代码**绝不进主进程**：L4 只在宿主**沙箱 worker** 里跑。
3. UI 不做任意 React 组件注入（受限词汇表 / `iframe`）。
4. **不触碰引擎解析行为**（`code.spider` 等贡献一律禁用）。
5. `runtimeDeps` **只能引用宿主内置许可清单的 dep id**，**不得自报 url/sha256**。

## 工作流
1. **定位级别** → 决定 `kind`：
   - 只是"给宿主一批文件 / 占个槽位" → `asset`（L1/L2/L3），`permissions` 留空；
   - 要"自己跑逻辑"（出网 / 存数据 / 控制播放）→ `code`（L4），且**必须**有 `main` + `permissions`。
2. **写 `plugin.json`**：骨架见 `assets/plugin.asset.json` / `assets/plugin.code.json`；字段与约束见 `references/manifest-reference.md`。
3. **放资源**：资源进 `files/`；要 mpv 档位 → `contributes:[{type:"mpv.shaders", modes:[…]}]`（**顺序即生效顺序**）。
   - `modes[].shaders` 里的名字必须与 `files/` 里**实际文件同名**（`.glsl` / `.hook` 都行，mpv 不看扩展名）；**别照抄占位名**。
   - 着色器资源多为**第三方上游项目**：随包了第三方资源就要在 `licenses/` 归档其许可原文（copyleft 必做，见规范 §3）。
   - 要**皮肤** → `contributes:[{type:"theme", id, label, base, tokens, layout}]`：
     皮肤 = **令牌字典 + 布局声明**，**绝对不写任何 CSS / 选择器 / `.css` 文件**（v1 硬约束）。
     词表（39 项）/ 布局枚举 / `base` 口径 / 自检清单 / **可安装的发布产物示例** → `references/theme-reference.md`；
     骨架 → `assets/plugin.theme.json`；示例 `.winbox` → `assets/theme-sakura.winbox`。
   - 要**字幕源** → `contributes:[{type:"subtitle.provider", id, name, search:{url,list,map}, fetch:{url}}]`：
     宿主**代发请求**（你不跑代码）：v1 仅 `GET` + JSON 响应；URL 里用占位符、JSON 里用**受限点号路径**取值。
     需要 POST / token / 解析 HTML → **只能用 L4**（`kind:"code"`）。
     结构 / 占位符 / 路径语法 / 自检 / 常见坑 → `references/subtitle-provider-reference.md`；骨架 → `assets/plugin.subtitle-provider.json`。
   - 要**元数据源** → `contributes:[{type:"meta.provider", id, name, imageBase?, search:{url,list,map}}]`：
     同上仅 `GET` + JSON。★ 它是**兜底**（内置 TMDB / 豆瓣都未命中才轮到它），**不抢占内置来源**；
     v1 **不提供评分**（声明 `rating` 会被拒装）；海报为相对路径时用 `imageBase` 拼前缀。
     结构 / 自检 / 常见坑 → `references/meta-provider-reference.md`；骨架 → `assets/plugin.meta-provider.json`。
   - 要**发现页数据源** → `contributes:[{type:"discover.source", id, name, sections:[{id,title,mediaType?,url,list,map,imageBase?}]}]`：
     同上仅 `GET` + JSON。★ 它是**增补**：分区**追加**在发现页内置榜单**之后**（同 id 被忽略）；
     `map` **不含 `doubanId`**（会错配豆瓣剧照）；图片一律由宿主包 `/img` 中继，你只写原始地址。
     结构 / 自检 / 常见坑 → `references/discover-source-reference.md`；骨架 → `assets/plugin.discover-source.json`。
   - 要**弹幕源** → `contributes:[{type:"danmaku.source", id, name, search:{…}, episodes:{…}, comments:{…}}]`：
     ★ **三步链路缺一不可**（搜番剧 → 剧集列表 → 弹幕 XML）；三段 URL 各用占位符（`{keyword}/{season}`、`{animeId}/{title}`、`{episodeId}`）。
     ★ `comments` **只收 XML**（B 站格式；无 `list`/`map`）—— 只给 JSON 弹幕的接口本期做不了，需 L4。
     结构 / 自检 / 常见坑 → `references/danmaku-source-reference.md`；骨架 → `assets/plugin.danmaku-source.json`。
   - 要**直播输出模板** → `contributes:[{type:"live.template", id, label, format:"txt"|"m3u", group?, header?, line, ext?}]`：
     ★ **本类型不发请求、不解析** —— 只把宿主**已解析**的直播频道按你的格式串导出为 TXT / M3U（**没有** `url`/`map`）。
     ★ `line` **必须含 `{url}`**（m3u 可用 `\n` 让 EXTINF 与地址分两行）；一个插件可声明**多个**模板。
     结构 / 自检 / 常见坑 → `references/live-template-reference.md`；骨架 → `assets/plugin.live-template.json`。
   - 要**受限动作按钮** → `contributes:[{type:"ui.command", id, label, placement:["config"|"player"], action, …}]`：
     ★ **插件不跑代码、不注入 UI** —— 只声明「按钮」+ 宿主**动作词表**里的一条动作（`open-url` / `navigate` / `export-live` / `set-theme`）。
     ★ **只带该动作自己的参数**（`navigate` 写 `to` 语义名而不是路径）；顶层多余字段（`icon`/`onClick`/`script`）一律拒装。
     结构 / 自检 / 常见坑 → `references/ui-command-reference.md`；骨架 → `assets/plugin.ui-command.json`。
   - 要**追加快捷键** → `contributes:[{type:"keymap", id, label, scope:["app"|"player"], key, action, …}]`：
     ★ 与**受限动作按钮同一套动作词表**（`open-url` / `navigate` / `export-live` / `set-theme`），快捷键只是**另一种触发方式**。
     ★ **不与宿主冲突的硬护栏**：`key` **必须含 `Ctrl`/`Alt`/`Meta` 至少一个**，主键仅字母 / 数字 / `F1~F24`（**不含方向键/Backspace/Esc**）。
     结构 / 自检 / 常见坑 → `references/keymap-reference.md`；骨架 → `assets/plugin.keymap.json`。
   - 要**插件设置面板** → `contributes:[{type:"settings.panel", id, label, fields:[{key,label,type,default,…}]}]`：
     ★ **宿主渲染 + 代持久化**：字段是**受限词汇表**（只 4 类）—— `toggle` / `select`（必填 `options`）/ `text` / `number`；`default` **必须与 type 匹配**。
     ★ 值存 `<userData>/plugin-settings.json`（按插件 id 分桶）；★ **v1 的读取面留给 L4**（asset 插件自己读不到）。
     结构 / 自检 / 常见坑 → `references/settings-panel-reference.md`；骨架 → `assets/plugin.settings-panel.json`。
   - 要**往宿主页面追加受限 UI** → `contributes:[{type:"ui.slot", id, slot:["discover"|"home"|"detail"|"live"|"history"|"favorites"], items:[…]}]`：
     ★ **宿主渲染 + 不注入 UI**：组件是**受限词汇表**（只 6 类）—— `heading` / `text` / `image` / `divider` / `kv` / `link`；`link` 的 `action` **复用 §5.9 动作词表**。
     ★ 落在对应页面**内容区顶部**；无插件声明该槽位时页面**零变化**；★ 内容与页面数据**无关**（要动态逻辑 → L4）。
     结构 / 自检 / 常见坑 → `references/ui-slot-reference.md`；骨架 → `assets/plugin.ui-slot.json`。
   - 要**追加第三方播放内核** → `contributes:[{type:"player.engine", id, label, protocol, binary, args, capabilities?}]`（★ **`kind:"code"`**）：
     ★ **宿主托管进程**：你**只给「引擎描述符」**（协议 / 二进制来源 / 参数模板），宿主负责 `spawn` / `--wid` 嵌入 /
     通信 / 状态推送 —— 插件**永不拉进程**（`spawn` / `child_process` 是永久禁止项）。
     ★ 两协议族：`mpv-ipc`（复用 mpv 的 `--input-ipc-server` JSON IPC；必需 `{wid}` `{url}` **`{pipe}`**）｜
     `json-lines`（宿主定死的 stdin/stdout 一行一 JSON；必需 `{wid}` `{url}`，**不得**带 `{pipe}`）。
     ★ **exe 路径不写在 `args` 里**（由 `binary` 决定）；二进制**随包自带**（`plugin-file` + `files/…`）或让用户指本机路径（`local-path`）；
     ★ 不能靠 `runtimeDeps` 分发二进制（v1 无下载装配管线）。
     ★ **默认关**：用户须在「配置 → 播放 → 插件播放内核」开启（**首次开启二次确认**），再在控制条内核列表里选用（**不参与「自动」**）。
     结构 / 占位符 / **两协议线格式** / 自检 / 常见坑 → `references/player-engine-reference.md`；骨架 → `assets/plugin.player-engine.json`。
   - **要跑自己的代码**（出网 / 存数据 / 控制播放，声明式做不到）→ **L4 `kind:"code"`**：
     `main` 在**独立沙箱 worker** 里跑；`permissions` 逐组授权宿主 API（`winbox.*`）——**未授权的 API 根本不存在**（调用即 `TypeError`）；沙箱里**没有** `require`/`process`/`fs`。
     ★ 装 `kind:"code"` 时宿主会**弹窗展示权限清单**（`permissionNotes`），用户确认后才装。
     权限表 / 用法 / 边界 / 自检 / 常见坑 → `references/l4-sandbox-reference.md`；骨架 → `assets/plugin.code.json`。
4. **打包**：zip → 改名 `<id>.winbox`（`plugin.json` 必须在**根级**，不得多套目录层）。
5. **自检**：逐条走 `references/checks.md`；对照规范 §10 的拒装原因码。

## 速查
| 级别 | kind | contributes | permissions | 例子 |
|---|---|---|---|---|
| L1 声明式资源 | `asset` | 必填 | 空 | `mpv.shaders`、`theme` |
| L2 声明式数据源 | `asset` | 必填 | 空 | 弹幕 / 字幕 / 元数据源；`live.template`（输出模板） |
| L2 描述符（**恒 `code`**） | `code` | 必填 | 必填（白名单） | `player.engine`（★ 宿主托管进程；默认关 + 首次开启二次确认；**不参与「自动」**） |
| L3 UI 槽位 | `asset` | 必填 | 空 | `ui.slot`（受限组件树）、`ui.command`（受限动作按钮）、`keymap`（追加快捷键）、`settings.panel`（设置面板） |
| L4 沙箱代码 | `code` | 可组合 | 必填（白名单） | 需出网 / 存数据 / 控制播放 |

## 参考
- 宿主速览（冷启动必读）：`references/host-overview.md`
- 字段与白名单速查：`references/manifest-reference.md`
- **皮肤（theme）参考**：`references/theme-reference.md`（令牌词表 + 布局枚举 + 自检 + **发布产物示例与自测三步**）
- **字幕源（subtitle.provider）参考**：`references/subtitle-provider-reference.md`（结构 + 占位符 + JSON 路径 + 自检 + 常见坑）
- **元数据源（meta.provider）参考**：`references/meta-provider-reference.md`（结构 + 兜底定位 + imageBase + 自检 + 常见坑）
- **发现页数据源（discover.source）参考**：`references/discover-source-reference.md`（分区结构 + 增补定位 + /img 中继 + 自检 + 常见坑）
- **弹幕源（danmaku.source）参考**：`references/danmaku-source-reference.md`（三步链路 + 按段占位符 + 只收 XML + 自检 + 常见坑）
- **直播输出模板（live.template）参考**：`references/live-template-reference.md`（结构 + 占位符 + 渲染规则 + ★ 不发请求 + 自检 + 常见坑）
- **受限动作按钮（ui.command）参考**：`references/ui-command-reference.md`（动作词表 + 挂载点 + 判定路径 + 自检 + 常见坑）
- **追加快捷键（keymap）参考**：`references/keymap-reference.md`（键位护栏 + 作用域 + 复用动作词表 + 自检 + 常见坑）
- **插件设置面板（settings.panel）参考**：`references/settings-panel-reference.md`（受限词汇表 4 类 + 值持久化 + 自检 + 常见坑）
- **受限 UI 槽位（ui.slot）参考**：`references/ui-slot-reference.md`（6 类受限组件 + 槽位表 + 复用动作词表 + 自检 + 常见坑）
- **第三方播放内核（player.engine）参考**：`references/player-engine-reference.md`（引擎描述符 + 占位符表 + **两协议线格式** + 二进制来源与授权 + 自检 + 常见坑）
- **L4 沙箱代码插件参考**：`references/l4-sandbox-reference.md`（12 权限表 + `winbox.*` 用法 + 沙箱边界「未授权 API 不存在」+ 自检 + 常见坑）
- 发布前校验清单：`references/checks.md`
- 骨架与示例产物：`assets/`（`plugin.asset.json` / `plugin.code.json` / `plugin.theme.json` / `plugin.subtitle-provider.json` / `plugin.meta-provider.json` / `plugin.discover-source.json` / `plugin.danmaku-source.json` / `plugin.live-template.json` / `plugin.ui-command.json` / `plugin.keymap.json` / `plugin.settings-panel.json` / `plugin.ui-slot.json` / `plugin.player-engine.json` / `example-super-resolution.plugin.json` / **`theme-sakura.winbox`（可直接装的示例皮肤包）**）
