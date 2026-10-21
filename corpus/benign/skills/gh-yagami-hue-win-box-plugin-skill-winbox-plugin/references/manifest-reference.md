# plugin.json 字段与白名单速查

> 唯一权威：`SPEC.md` §4~§6。本文件是**速查**，冲突时以规范为准。

## 字段
| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `manifestVersion` | int | ✅ | 恒 `1` |
| `id` | string | ✅ | `[a-z0-9-]{3,40}`，唯一；决定安装目录 `<id>.winbox` |
| `name` | string | ✅ | 显示名 |
| `version` | string | ✅ | 语义化版本（更新检测用） |
| `apiVersion` | string | ✅ | 宿主 API **大版本**（如 `1.x`）；不匹配 → 拒装 |
| `kind` | `asset` \| `code` | ✅ | asset=声明式；code=L4 沙箱代码 |
| `main` | string | `code` 必填 | 沙箱入口相对名（如 `main.js`）；`asset` **不得有** |
| `author` / `license` | string | ✅ | 署名 / 许可 |
| `homepage` | string | 可选 | |
| `description` | string | 可选 | |
| `permissions` | string[] | ✅ | `asset` **必须为空**；`code` **必须**取下方白名单 |
| `permissionNotes` | object | 可选 | 每个权限的一句话用途（安装时展示给用户） |
| `contributes` | object[] | ✅ | 见下方 contributes 白名单 |
| `runtimeDeps` | object[] | 可选 | **只引用内置许可清单的 dep id** |
| `updateCheckUrl` | string | 可选 | `https://`；作者自配的更新源 |

## contributes 白名单（含允许的 kind）
> ★ **「已在宿主实装」一列**：✅ = 现在就能真正生效；空白 = 宿主已认识、但装配接线尚未落地（装上会被忽略并告警）。

| type | 允许 kind | 阶段 | 已在宿主实装 |
|---|---|---|---|
| `mpv.shaders` | asset | M1 | ✅ |
| `theme` | asset | M2 | ✅ |
| `subtitle.provider` | asset / code | M2 | ✅（asset 声明式；★ code 形待后续） |
| `meta.provider` | asset / code | M2 | ✅（asset 声明式；★ code 形待后续） |
| `discover.source` | asset / code | M2 | ✅（asset 声明式；★ code 形待后续） |
| `danmaku.source` | asset / code | M2 | ✅（asset 声明式；★ code 形待后续） |
| `live.template` | asset | M2 | ✅（输出侧格式化；★ 不发请求） |
| `player.engine` | code | M2（风险高，需显式授权） | ✅（★ 宿主托管进程：插件只给描述符，**永不拉进程**；默认关 + 首次开启二次确认） |
| `ui.slot` | asset | M2 | ✅（asset 受限 UI 槽位；6 类受限组件，`link` 复用动作词表） |
| `ui.command` | asset / code | M2 | ✅（asset 受限动作按钮；★ code 形待后续） |
| `keymap` | asset | M2 | ✅（asset 追加快捷键；动作复用 `ui.command` 词表） |
| `settings.panel` | asset / code | M2 | ✅（设置面板；★ **asset / code 都可用** —— code 插件经 `winbox.settings` 读自己的值） |

> ★ **L4 沙箱已实装**（R10）：`kind:"code"` 的 `main` 在**独立 worker** 里跑，宿主 API 经 `permissions` **逐组授权**（未授权的 `winbox.*` **根本不存在**）。全量说明 / 用法 / 自检 → `references/l4-sandbox-reference.md`；骨架 → `assets/plugin.code.json`。

**禁用**：`code.spider`（引擎解析行为）· `main.hook`（主进程执行）· `drive.provider`（网盘凭据）

## permissions 白名单（**只属 L4 / `kind:"code"`**）
`net` · `net.download` · `kv` · `settings` · `fs.plugin` · `log` · `notify` · `clipboard.read` · `clipboard.write` · `dialog` · `player.control` · `openExternal`

**禁用（永不提供）**：`main` · `spawn`/`child_process` · `eval` · `fs`（任意文件系统）· `cred` · `proxy`（含 `raw.net`）· `registry`

## `mpv.shaders` 结构
```jsonc
{ "type": "mpv.shaders",
  "modes": [ { "id": "efficiency", "label": "效率档", "hint": "弱机可用", "shaders": ["a.glsl", "b.glsl"] } ] }
```
- `shaders` **顺序即生效顺序**；名称**先插件 `files/`、再 runtimeDeps 目录**解析为绝对路径（**不要写绝对路径**）。

## `subtitle.provider` 结构（L2 声明式字幕源）
```jsonc
{ "type": "subtitle.provider", "id": "my-subs", "name": "我的字幕站",
  "search": { "url": "https://sub.example.com/api/search?q={keyword}&ep={ep}",
              "list": "data.list",
              "map": { "file": "id", "subname": "filename", "title": "video_title", "lang": "language" } },
  "fetch":  { "url": "https://sub.example.com/api/download/{file}" } }
```
- **宿主代发请求**（插件不跑代码）：v1 仅 `GET` + **JSON** 响应；`fetch.url` 必须含 `{file}`。
- 占位符：search 用 `{keyword}/{keywords}/{title}/{ep}`；fetch 用 `{file}/{subname}/{title}/{ep}`。
- JSON 路径只支持**点号 + 下标**（`data.list` / `a.b[0]`），无 `[*]`、无函数。
- 全量口径 / 自检 / 常见坑 → `references/subtitle-provider-reference.md`；骨架 → `assets/plugin.subtitle-provider.json`。

## `meta.provider` 结构（L2 声明式元数据源）
```jsonc
{ "type": "meta.provider", "id": "my-meta", "name": "我的元数据站",
  "imageBase": "https://img.example.com/t/p/w342",
  "search": { "url": "https://api.example.com/search?q={keyword}&year={year}",
              "list": "data.results",
              "map": { "title": "name", "year": "year", "poster": "poster_path",
                       "backdrop": "wide_path", "overview": "overview", "mediaType": "type" } } }
```
- **兜底定位**：内置 TMDB → 豆瓣 都未命中时才轮到它；**不抢占内置来源**。
- 占位符：`{keyword}` / `{title}` / `{year}`；v1 **不提供评分**（`rating` 会被拒装）。
- 海报为相对路径时用 `imageBase` 拼前缀；未配则丢弃该图（不产出坏图）。
- 全量口径 / 自检 / 常见坑 → `references/meta-provider-reference.md`；骨架 → `assets/plugin.meta-provider.json`。

## `discover.source` 结构（L2 声明式发现页数据源）
```jsonc
{ "type": "discover.source", "id": "my-discover", "name": "我的榜单",
  "sections": [
    { "id": "my-top-movie", "title": "我的电影热榜", "mediaType": "movie",
      "url": "https://api.example.com/top?type={mediaType}",
      "list": "data.items",
      "imageBase": "https://img.example.com/t/p/w342",
      "map": { "title": "name", "year": "year", "poster": "poster_path", "backdrop": "wide_path", "mediaType": "type", "tmdbId": "tmdb_id" } }
  ] }
```
- **增补定位**：分区**追加**在发现页内置榜单**之后**；同 id 的分区被忽略。
- 占位符只有 `{mediaType}`；`sections` ≥1、同插件内 `section.id` 不重复；空分区不显示。
- **`map` 不含 `doubanId`**（会错配豆瓣剧照）；图片由宿主统一包 `/img` 中继（相对路径配 `imageBase`，未配则丢图）。
- 全量口径 / 自检 / 常见坑 → `references/discover-source-reference.md`；骨架 → `assets/plugin.discover-source.json`。

## `danmaku.source` 结构（L2 声明式弹幕源，**三步链路缺一不可**）
```jsonc
{ "type": "danmaku.source", "id": "my-danmaku", "name": "我的弹幕站",
  "search":   { "url": "https://dm.example.com/api/search?keyword={keyword}&season={season}",
                "list": "animes", "map": { "animeId": "animeId", "title": "animeTitle", "bangumiId": "bangumiId" } },
  "episodes": { "url": "https://dm.example.com/api/bangumi/{animeId}",
                "list": "bangumi.episodes", "map": { "episodeId": "episodeId", "episodeNumber": "episodeNumber" } },
  "comments": { "url": "https://dm.example.com/api/comment/{episodeId}?format=xml" } }
```
- ① 搜番剧 → ② 取剧集 → ③ 拉弹幕 **XML**（`comments` 无 `list`/`map`，**只收 XML 文本**）。
- 占位符按段白名单：`{keyword}/{season}` · `{animeId}/{title}` · `{episodeId}`；`comments.url` 必须含 `{episodeId}`。
- 与内置外部接口**并列**参与检索；★ v1 **不进**播放器「弹幕源」面板的开关清单（要停用请在「配置 → 插件」停用该插件）。
- 全量口径 / 自检 / 常见坑 → `references/danmaku-source-reference.md`；骨架 → `assets/plugin.danmaku-source.json`。

## `live.template` 结构（L2 声明式**输出**模板，★ **不发请求**）
```jsonc
{ "type": "live.template", "id": "my-live-txt", "label": "标准 TXT", "format": "txt",
  "group": "{group},#genre#", "line": "{name},{url}", "ext": "txt" }
```
- ★ 与前几个 provider **根本不同**：它**不取数、不发请求、不解析** —— 只把宿主**已解析**的直播频道
  （分组 / 频道 / 线路）按你的格式串**格式化导出**成 TXT / M3U 文件（出口：直播页顶栏 + 配置页直播线路每行「导出」）。
- 因此**没有** `url` / `headers` / `list` / `map`（写了即拒装）。
- `format` ∈ `txt` | `m3u`（决定默认扩展名）；`line` **必须含 `{url}`**（允许 `\n` 让 m3u 的 EXTINF 与地址分两行）；
  `group` / `header` 是单行；占位符仅 `{group}/{name}/{url}/{logo}/{tvgId}/{tvgName}/{tvgChno}/{index}`。
- 一个插件可声明**多个**模板（各自独立 id）；宿主自带 2 个内置模板（`builtin:txt` / `builtin:m3u`）。
- 全量口径 / 自检 / 常见坑 → `references/live-template-reference.md`；骨架 → `assets/plugin.live-template.json`。

## `ui.command` 结构（L3 声明式**受限动作按钮**，★ 不跑代码、不注入 UI）
```jsonc
{ "type": "ui.command", "id": "open-help", "label": "打开帮助", "placement": ["config"],
  "action": "open-url", "url": "https://example.com/help" }
```
- 插件只声明「**按钮**（label / placement）+ **动作**（词表）」；按钮由宿主按自己的样式渲染，动作由宿主执行。
- `placement` ≥1：`config`（配置 → 插件页）/ `player`（播放器控制条）。
- **动作词表**（只能选）：`open-url`（`url`，仅 http/https）· `navigate`（`to` 语义名 + 仅 `to:"config"` 可用 `section`）·
  `export-live`（`template?`）· `set-theme`（`theme`，皮肤 id）。
- ★ **只允许该动作自己的参数**（`navigate` 带 `url`、`open-url` 带 `theme` → 拒装）；顶层多余字段（`icon`/`onClick`/`script`）→ 拒装。
- 全量口径 / 自检 / 常见坑 → `references/ui-command-reference.md`；骨架 → `assets/plugin.ui-command.json`。

## `keymap` 结构（L3 声明式**追加快捷键**，★ 动作复用 `ui.command` 词表）
```jsonc
{ "type": "keymap", "id": "go-discover", "label": "去发现页", "scope": ["app"],
  "key": "Ctrl+Alt+F", "action": "navigate", "to": "discover" }
```
- ★「不与宿主冲突」的**硬护栏**：`key` **必须含 `Ctrl` / `Alt` / `Meta` 至少一个**（仅 `Shift` 不算）；
  主键**仅允许**字母 `A~Z` / 数字 `0~9` / 功能键 `F1~F24`（不含方向键 / `Backspace` / `Esc`）。
  归一化：修饰键固定顺序 `Ctrl→Alt→Shift→Meta` + 主键大写（`alt+ctrl+f` → `Ctrl+Alt+F`）。
- `scope` 非空数组 ∈ `app`（主窗口）/ `player`（播放器窗口）；可同时声明两者。
- **动作词表**（与 `ui.command` 完全相同）：`open-url`（`url`，仅 http/https）· `navigate`（`to` 语义名 + 仅 `to:"config"` 可用 `section`）·
  `export-live`（`template?`）· `set-theme`（`theme`）。★ 只允许该动作自己的参数；顶层多余字段（`when`/`handler`/`script`）→ 拒装。
- 于**配置页「快捷键」tab** 有「插件快捷键」只读一览；`player` 作用域亦出现在播放器「键位」面板。
- 全量口径 / 自检 / 常见坑 → `references/keymap-reference.md`；骨架 → `assets/plugin.keymap.json`。

## `settings.panel` 结构（L3 声明式**插件设置面板**，★ 宿主渲染 + 代持久化）
```jsonc
{ "type": "settings.panel", "id": "general", "label": "常规设置",
  "fields": [ { "key": "enhance", "label": "启用增强", "type": "toggle", "default": true } ] }
```
- ★ 字段是**受限词汇表**（只 4 类，不能自己写控件）：`toggle`(boolean) · `select`(string，**必填** `options` 1~50 项) ·
  `text`(string，可选 `maxLength` 1~200 / `placeholder` ≤60) · `number`(可选 `min`/`max`/`step`)。
  每项须有 `key`（`[a-z0-9-]{1,40}`，同面板内唯一）、`label`、`type`、`default`（**必须与 type 匹配**）；可选 `hint`。
- ★ **参数必须与类型匹配**（`toggle` 带 `options`、`text` 带 `min` → 拒装）；`select` 缺 `options` → 拒装。
- 值由宿主按 `pluginId → panelId → fieldKey` 存 `<userData>/plugin-settings.json`；读回时存值合法则用存值、否则回落 `default`。
- 展示在**配置 → 插件**页每个插件卡片内；★ **值的读取面留给 L4**（`kind:"code"` + `settings` 权限）；卸载**不清理**值。
- 全量口径 / 自检 / 常见坑 → `references/settings-panel-reference.md`；骨架 → `assets/plugin.settings-panel.json`。

## `ui.slot` 结构（L3 **受限 UI 槽位**，★ 6 类受限组件，宿主渲染）
```jsonc
{ "type": "ui.slot", "id": "discover-tip", "slot": ["discover", "home"],
  "items": [ { "type": "heading", "text": "本周精选" },
             { "type": "link", "label": "打开帮助", "action": "open-url", "url": "https://example.com/help" } ] }
```
- 槽位 `slot`（非空数组 ∈ 6 个）：`discover` / `home` / `detail` / `live` / `history` / `favorites`；
  ★ 渲染位置 = 对应页面**内容区顶部**；无插件声明该槽位时**页面零变化**。
- ★ 组件是**受限词汇表**（只 6 类，不能自己写控件 / 注入 HTML）：`heading`(text ≤80 不含换行) · `text`(text ≤500 可换行) ·
  `image`(`url` 仅 http/https + `alt?`) · `divider` · `kv`(`items` 1~12 行 `{label,value}`) ·
  `link`(`label` + `action` **复用 §5.9 词表**，参数规则同 §5.9)。
- ★ **参数必须与类型匹配**（`heading` 带 `url`、`divider` 带 `text`、`kv` 缺 `items` → 拒装）；`items` 1~24。
- 图片一律走宿主 `/img` 中继；★ 内容与页面数据**无关**（要动态逻辑 → L4）。
- 全量口径 / 自检 / 常见坑 → `references/ui-slot-reference.md`；骨架 → `assets/plugin.ui-slot.json`。

## `player.engine` 结构（第三方播放内核，★ **宿主托管进程**；只可能 `kind:"code"`）
```jsonc
{ "type": "player.engine", "id": "my-mpv", "label": "我的 MPV", "protocol": "mpv-ipc",
  "binary": { "source": "plugin-file", "file": "files/mpv.exe" },
  "args": ["--no-config", "--wid={wid}", "--input-ipc-server={pipe}", "{url}", "--start={start}"],
  "capabilities": ["seek", "rate", "tracks", "subtitle", "fit"] }
```
- ★ 插件**只给「引擎描述符」**（协议 / 二进制来源 / 参数模板），**宿主**负责 `spawn` + `--wid` 嵌入 + 协议通信 + 状态推送；
  ★ 插件**永不拉进程**（`spawn` / `child_process` 是永久禁止项）。清单须 `kind:"code"` + `main` + 非空 `permissions`（描述符型通常只写 `["log"]`）。
- **协议族两个**：`mpv-ipc`（复用 mpv 的 `--input-ipc-server` JSON IPC；必需 `{wid}` `{url}` **`{pipe}`**）｜
  `json-lines`（宿主定死的 stdin/stdout 一行一 JSON；必需 `{wid}` `{url}`，**不得**带 `{pipe}`）。
- **占位符**（宿主展开）：`{wid}` / `{url}` / `{pipe}` / `{start}`（整数秒，≤0 不下发）/ `{volume}`（整数百分比 0~130）/
  `{rate}`（浮点）/ `{fit}`（`contain`/`fill`/`cover`/`r169`/`r43`/`none`）。
  ★ **exe 路径不在 `args` 里**（由 `binary` 决定）；★ **可选占位符无值时该参数项整项丢弃**。
- **二进制来源**：`plugin-file`（随包自带，`file` 必须是包内**安全相对名**）｜ `local-path`（用户在「配置 → 播放 → 插件播放内核」填路径，对位 `mpvPath`）。
  ★ v1 **不能用 `runtimeDeps` 分发二进制**（无下载装配管线）。
- **授权**：**默认关**；配置页单独开关 + **首次开启二次确认**；未启用时 `engine:start` 被明确拒绝。
  ★ 用户显式选才生效（**插件内核不参与「自动」**）；起播失败会**明确报错并回落内置 HTML5**。
- 全量口径（两协议**线格式**）/ 自检 / 常见坑 → `references/player-engine-reference.md`；骨架 → `assets/plugin.player-engine.json`。

## runtimeDeps
```jsonc
"runtimeDeps": [ { "id": "anime4k-shaders", "files": ["Anime4K_Upscale_CNN_x2_M.glsl"] } ]
```
- 小资源（<1MB）建议直接进 `files/` 随包；重运行库才走 `runtimeDeps`（**安装后**才下载）。
- ★ **二进制（exe/dll）不走 `runtimeDeps`**（v1 无下载装配管线，且许可清单只有着色器文本资源）——
  `player.engine` 的可执行文件请随包自带或让用户指定本机路径。
