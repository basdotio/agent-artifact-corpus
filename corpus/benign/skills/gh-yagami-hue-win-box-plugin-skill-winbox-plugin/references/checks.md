# 发布前校验清单（工作流）

发布 `.winbox` 前，逐条核对；任一不通过就修，别发布。

## 1. 结构
- [ ] 根级有 `plugin.json`（**不得**多套目录层）
- [ ] 文件名 = `<id>.winbox`，且 `id` 与清单一致
- [ ] 包内附 `LICENSE`（= 插件**自身**许可，与 manifest `license` 一致）
- [ ] 若随包了**第三方资源**：`licenses/<上游名>.txt` 已原样归档，且根 `LICENSE` 有「署名 / 上游 / 许可」对照段（copyleft 上游如 GPL-3 / LGPL-3 必做）

## 2. 清单字段
- [ ] `manifestVersion = 1`
- [ ] `id` 符合 `[a-z0-9-]{3,40}`
- [ ] `apiVersion` 与目标宿主**大版本**一致
- [ ] `kind` 与 `permissions` 匹配：`asset` → `[]` 且无 `main`；`code` → 白名单非空且有 `main`
- [ ] `contributes[].type` 在宿主白名单内
- [ ] 所有路径（`main`/`files`/`shaders`）为**相对名**、无 `..`、无绝对路径
- [ ] ★ **`modes[].shaders` 的每一项都在包里真实存在**（`files/<名字>` 逐条命中；宿主安装期会拒装缺失项）
- [ ] 同一档位没有两条着色器抢**同一槽位**（`//!SAVE` 同名 ⇒ 互斥，应二选一）
- [ ] `runtimeDeps[].id` 都在**内置许可清单**内（未自报 url）
- [ ] `updateCheckUrl` 为 `https://`（作者自配）

### 2.1 怎么核「声明 ⊂ 包内」（可执行）
不要靠眼看。打包**之后**回读 zip 条目，逐条比对清单声明：

```powershell
# 把 .winbox 当 zip 读（★ Expand-Archive 只认 .zip 扩展名 → 先改个名）
Copy-Item <id>.winbox "$env:TEMP\pkg.zip" -Force
Expand-Archive "$env:TEMP\pkg.zip" -DestinationPath "$env:TEMP\pkg" -Force
(Get-Content "$env:TEMP\pkg\plugin.json" | ConvertFrom-Json).contributes[0].modes |
  ForEach-Object { $_.shaders } |
  ForEach-Object {
    $f = Join-Path "$env:TEMP\pkg\files" $_
    if (Test-Path $f) { Write-Host "OK   $_" } else { Write-Host "MISS $_" }
  }
```
出现任何 `MISS` ⇒ **不要发布**（宿主校验器会以 `INCOMPLETE` / 声明文件缺失拒装）。

## 2.2 皮肤（`type:"theme"`）—— 逐条核对
> 词表 / 枚举 / 自检全量口径：`references/theme-reference.md`；权威规范：`SPEC.md` §15。
- [ ] 插件是 `kind:"asset"` + `permissions: []`（**code 插件不得声明皮肤** → `UNKNOWN_CONTRIBUTE_KIND`）
- [ ] `theme.id` 匹配 `[a-z0-9-]{3,40}`；**不与内置皮肤（netflix/bilibili/apple/douban）或已装插件重名**（`THEME_ID_TAKEN`）
- [ ] `theme.label` 非空；`theme.base` ∈ `dark | light`
- [ ] `tokens` 非空，键**全部**在 39 项词表内（无 `--nf-*`/`--b-*`/自定义前缀 → `UNKNOWN_THEME_TOKEN`）
- [ ] 值类型正确：颜色合法；`--surface-glass`/`--accent-soft`/`--border-soft`/`--hairline` **必须含 alpha**；
      长度带 `px`（仅 `0` 可省）；时长带 `ms`/`s`；缓动仅 `cubic-bezier(a,b,c,d)`；阴影 `[inset] 2~4 长度 + 可选颜色`（`BAD_THEME_TOKEN_VALUE`）
- [ ] 值里没有 `;` `{` `}` `<` `url(` `expression(` `@import` `/*`
- [ ] 没有 `style` / `css` / `styles` / `stylesheet` 字段，包里也没有 `.css` 文件（`THEME_STYLE_NOT_ALLOWED`）
- [ ] `layout` 字段名与取值在枚举内（`shell` / `detailStyle` / `discoverStyle` / `filterStyle` / `nav` / `density` /
      `motion` / `radiusScale` / `navHeight` / `sideWidth` / `cardWidth`）（`BAD_THEME_LAYOUT`）
- [ ] **亮色皮肤已给全颜色类令牌**（surface×5 / accent×6 / text×3 / border×3 / 语义×4），否则未覆盖项会漏出深色基线
- [ ] 装上后三步走通：设置页出现该皮肤 → 选中即时生效 → 卸载回落默认皮肤

## 2.3 字幕源（`type:"subtitle.provider"`）—— 逐条核对
> 结构 / 占位符 / JSON 路径全量口径：`references/subtitle-provider-reference.md`；规范 §5.4。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**（code 插件不得声明 → `UNKNOWN_CONTRIBUTE_KIND`）
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`，且**不占用**内置源 `assrt` / `subtitlecat`（`SUBTITLE_ID_TAKEN`）
- [ ] `search.url` / `fetch.url` 均 `http(s)://`；**`fetch.url` 含 `{file}`**（`BAD_PROVIDER_URL`）
- [ ] 占位符在白名单内：search 用 `{keyword}/{keywords}/{title}/{ep}`，fetch 用 `{file}/{subname}/{title}/{ep}`
- [ ] `headers` 无 `Host`/`Content-Length`/`Connection`/`Transfer-Encoding`，值里无换行
- [ ] `search.list` 与 `map.file`/`map.subname` 是**合法点号路径**（只支持 `a.b[0]`，无 `[*]`/无函数）（`BAD_PROVIDER_PATH`）
- [ ] `map` 只含 `file/subname/title/lang/format/detail`，且 `file`/`subname` 必有
- [ ] **真机三步**：装上 → 字幕设置出现该源 → 搜到候选且能下载 → 卸载后源消失（内置源不受影响）

## 2.4 元数据源（`type:"meta.provider"`）—— 逐条核对
> 结构 / 兜底定位 / imageBase 全量口径：`references/meta-provider-reference.md`；规范 §5.5。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`，且**不占用**内置来源 `tmdb` / `douban`（`META_ID_TAKEN`）
- [ ] `search.url`（与 `imageBase`，若声明）均为 `http(s)://`
- [ ] 占位符只用 `{keyword}` / `{title}` / `{year}`
- [ ] `search.list` 与 `map.title` 是**合法点号路径**；`map` 只含 `title/year/poster/backdrop/overview/mediaType`
- [ ] **没有** `rating` 等宿主未提供字段（写了会被拒装）
- [ ] `headers` 无 `Host`/`Content-Length`/`Connection`/`Transfer-Encoding`，值里无换行
- [ ] 相对路径海报已配 `imageBase`（不配则该图被丢弃，不会产出坏图）
- [ ] **真机三步**：装 → 用一个内置查不到的片名走 `meta:search` 拿到该源的封面/简介 → 停用后回到内置行为

## 2.5 发现页数据源（`type:"discover.source"`）—— 逐条核对
> 分区结构 / 增补定位 / 图片中继口径：`references/discover-source-reference.md`；规范 §5.6。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] `discover.source.id` 与每个 `section.id` 匹配 `[a-z0-9-]{3,40}`；**同插件内 section.id 不重复**
- [ ] `sections` 非空；每个 section 有 `title`
- [ ] `url`（与 `imageBase`，若声明）均为 `http(s)://`；占位符只用 `{mediaType}`
- [ ] `list` 与 `map.title` 是合法点号路径；`map` 只含 `title/year/poster/backdrop/mediaType/tmdbId`
- [ ] **没有** `doubanId`（宿主会去取豆瓣剧照 → 图源错配，声明即拒装）
- [ ] `headers` 无 `Host`/`Content-Length`/`Connection`/`Transfer-Encoding`，值里无换行
- [ ] 相对路径海报已配 `imageBase`（未配则这张图被丢弃）
- [ ] **真机三步**：装 → 发现页出现你的分区（在内置榜单**之后**）且图能出 → 停用后该分区消失

## 2.6 弹幕源（`type:"danmaku.source"`）—— 逐条核对
> 三步链路 / 按段占位符 / 只收 XML：`references/danmaku-source-reference.md`；规范 §5.7。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`；`name` 非空
- [ ] **三段齐备**：`search` / `episodes` / `comments` 都在；每段 `url` 是 `http(s)://`
- [ ] 占位符按段白名单：search 用 `{keyword}/{season}`、episodes 用 `{animeId}/{title}`、comments 用 `{episodeId}`
- [ ] **`comments.url` 含 `{episodeId}`**（否则拒装）
- [ ] `search.map.animeId`/`title`、`episodes.map.episodeId` 是合法点号路径；映射字段无越界
- [ ] `comments` **没有** `list`/`map`（它只收 XML 文本）
- [ ] `headers` 无 `Host`/`Content-Length`/`Connection`/`Transfer-Encoding`，值里无换行
- [ ] **真机三步**：装 → 播放器「弹幕源」搜到该源命中的番剧（来源名 = `name`）→ 选剧集能出弹幕 → 停用后该源消失

## 2.7 直播输出模板（`type:"live.template"`）—— 逐条核对
> ★ **本类型不发请求、不解析**（只把宿主已解析的频道格式化输出）：`references/live-template-reference.md`；规范 §5.8。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] **没有任何 `url`/`headers`/`list`/`map`**（这是「输出模板」，不是数据源 provider）
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`（同插件可声明多个模板，id 各自不重复）；`label` 非空
- [ ] `format` ∈ `txt` / `m3u`
- [ ] **`line` 含 `{url}`**；`line`、`group`、`header` 各项**无 `\r`、无空行**；`group`/`header` 是单行
- [ ] `group` 里**不含 `{url}`**
- [ ] 占位符都在白名单内：`{group}` `{name}` `{url}` `{logo}` `{tvgId}` `{tvgName}` `{tvgChno}` `{index}`
- [ ] `ext`（若写）为 `[a-z0-9]{1,8}`、不带点
- [ ] **真机两步**：装 → 「配置 → 直播线路」某行「导出」能选到你的模板并写出文件 → 停用后模板消失（内置 2 个不受影响）

## 2.8 受限动作按钮（`type:"ui.command"`）—— 逐条核对
> ★ **只声明「按钮 + 宿主词表动作」**（插件不跑代码、不注入 UI）：`references/ui-command-reference.md`；规范 §5.9。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`（同插件可声明多条命令，id 各自不重复）；`label` 非空且 ≤40 字（不含换行）
- [ ] `placement` 非空数组、每项 ∈ `config` / `player`、不重复
- [ ] `action` ∈ `open-url` / `navigate` / `export-live` / `set-theme`
- [ ] **只带该动作自己的参数**：`open-url`→`url`；`navigate`→`to`(+`section`，仅 `to:"config"`)；`export-live`→`template?`；`set-theme`→`theme`
- [ ] `open-url` 的 `url` 是 `http(s)://` 且不含空白；`navigate` 的 `to` 是**语义名**（`discover/home/history/favorites/live/storage/config/about`，不是 `/xxx` 路径）
- [ ] `set-theme` 的 `theme` 是真实皮肤 id（内置 4 套或 `plugin:<skinId>`）
- [ ] 顶层**无多余字段**（`icon` / `onClick` / `script` 一律拒装）
- [ ] **真机两步**：装 → 「配置 → 插件」出现「插件命令」按钮且可点（`open-url` 会拉起系统浏览器）→ 停用后按钮消失

## 2.9 追加快捷键（`type:"keymap"`）—— 逐条核对
> ★ **只声明「键位 + 宿主词表动作」**（插件不跑代码、不注入 UI；动作与 `ui.command` **同一套词表**）：`references/keymap-reference.md`；规范 §5.10。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`（同插件可声明多条快捷键，id 各自不重复）；`label` 非空且 ≤40 字（不含换行）
- [ ] `scope` 非空数组、每项 ∈ `app` / `player`、不重复
- [ ] `key` **含 `Ctrl` / `Alt` / `Meta` 至少一个**（仅 `Shift` 不算）；主键是字母 / 数字 / `F1~F24`（**不含方向键 / `Backspace` / `Esc`**）
- [ ] `action` ∈ `open-url` / `navigate` / `export-live` / `set-theme`（与 `ui.command` 同词表）
- [ ] **只带该动作自己的参数**：`open-url`→`url`；`navigate`→`to`(+`section`，仅 `to:"config"`)；`export-live`→`template?`；`set-theme`→`theme`
- [ ] `open-url` 的 `url` 是 `http(s)://` 且不含空白；`navigate` 的 `to` 是**语义名**（不是 `/xxx` 路径）
- [ ] 顶层**无多余字段**（`when` / `handler` / `script` 一律拒装）
- [ ] **真机两步**：装 → 在 `scope` 对应窗口按键能触发（`navigate` 跳页 / `open-url` 拉起浏览器），配置页「快捷键」tab 出现「插件快捷键」一览 → 停用后一览与生效同时消失（宿主自身键位不受影响）

## 2.10 插件设置面板（`type:"settings.panel"`）—— 逐条核对
> ★ **只声明「一组受限字段」**（插件不跑代码、不注入 UI；宿主渲染表单 + 代持久化）：`references/settings-panel-reference.md`；规范 §5.11。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`（同插件可声明多个面板，id 各自不重复）；`label` 非空且 ≤40 字
- [ ] `fields` 1~24 项；每项 `key` 匹配 `[a-z0-9-]{1,40}` 且同面板内唯一；`label` 非空且 ≤40 字
- [ ] 每个字段 `type` ∈ `toggle` / `select` / `text` / `number`；`default` **与 type 匹配**
- [ ] `select` 有 `options`（1~50 项、`value` 唯一）且 `default` 是其之一；`text` 的 `maxLength`（若有）为 1~200 整数、`default` 不超长；`number` 的 `default` 落在 `[min, max]`
- [ ] **只带该类型自己的参数**（`toggle` 带 `options`、`text` 带 `min` → 拒装）；顶层**无多余字段**
- [ ] **真机两步**：装 → 「配置 → 插件」该插件卡片内出现表单 → 改一个字段后**重开软件值仍在**（已落盘）→ 停用后面板消失

## 2.11 受限 UI 槽位（`type:"ui.slot"`）—— 逐条核对
> ★ **只声明「槽位 + 受限组件树」**（插件不跑代码、不注入 UI；6 类组件，`link` 复用 §5.9 词表）：`references/ui-slot-reference.md`；规范 §5.12。
- [ ] 插件是 `kind:"asset"` + `permissions: []` + **无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`（同插件可声明多个槽位，id 各自不重复）；`label` 非空且 ≤40 字
- [ ] `slot` 非空数组、每项 ∈ `discover` / `home` / `detail` / `live` / `history` / `favorites`、不重复
- [ ] `items` 1~24 项；每项 `type` ∈ `heading` / `text` / `image` / `divider` / `kv` / `link`；**只带该类型自己的字段**
- [ ] `heading` 的 `text` 不含换行且 ≤80；`text` 的 `text` ≤500；`image` 的 `url` 为 `http(s)://`；`kv` 的 `items` 1~12 行且每行有 `label`/`value`
- [ ] `link` 有 `label` 与 `action`，且**动作参数与动作匹配**（`open-url`→`url`；`navigate`→`to`(+`section`)；`export-live`→`template?`；`set-theme`→`theme`）
- [ ] 顶层**无多余字段**（`html` / `script` / `style` 一律拒装）
- [ ] **真机两步**：装 → 打开对应页面 ⇒ 内容区顶部出现插件内容 → 停用后页面**恢复原样（零残留）**

## 2.12 L4 沙箱代码插件（`kind:"code"`）—— 逐条核对
> ★ **唯一会「跑你的代码」的级别**（在**独立沙箱 worker** 内）；`references/l4-sandbox-reference.md`；规范 §6。
- [ ] `kind:"code"` + **`main` 存在且是安全相对名**（无 `..` / 无绝对路径）+ **`permissions` 非空**
- [ ] `permissions` **逐条**都在 12 项白名单内（`net` / `net.download` / `kv` / `settings` / `fs.plugin` / `log` / `notify` / `clipboard.read` / `clipboard.write` / `dialog` / `player.control` / `openExternal`）
- [ ] **未写禁止项**（`main` / `spawn` / `child_process` / `eval` / `fs` / `cred` / `proxy` / `registry` / `raw.net`）
- [ ] `permissionNotes`（建议每条都写）：**键 ⊆ `permissions`**、值 1~200 字无换行
- [ ] `main` 里**没有** `require` / `process` / `fs` / `child_process`（沙箱里不存在）
- [ ] 用到的 `winbox.xxx` 全部已在 `permissions` 声明（**未授权的 API 不存在**，调用即 `TypeError`）
- [ ] `fs.*` 只用**插件内相对路径**；`openExternal` 只用 `http(s)://`
- [ ] **真机**：装（会弹**权限确认**）→ 配置页可见 **沙箱运行中**；停用后沙箱停；日志里有 `plugin:<id>` 前缀输出

## 2.13 第三方播放内核（`type:"player.engine"`）—— 逐条核对
> ★ **风险最高的一类**：会让**宿主启动你提供的本机程序**（插件只给描述符，**永不拉进程**）：`references/player-engine-reference.md`；规范 §6.3。
- [ ] `kind:"code"` + 有 `main` + `permissions` 非空（描述符型插件通常只写 `["log"]`）
- [ ] `contributes[].type = "player.engine"`；**只写 §2 的那几个字段**（顶层多余字段一律拒装）
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`；`label` 1~40 字不含换行；`protocol` ∈ `mpv-ipc` / `json-lines`
- [ ] `binary`：`plugin-file` 带**安全相对** `file`（无 `..` / 无盘符 / 无前导 `/`）；`local-path` **不带 `file`**（路径由用户在配置页填）
- [ ] `args` 非空、≤24、每项无换行；占位符**全在白名单**（`{wid}` `{pipe}` `{url}` `{start}` `{volume}` `{fit}` `{rate}`）
- [ ] ★ **按协议的必需 / 禁止占位符**：`mpv-ipc` 含 `{wid}` `{url}` **`{pipe}`**；`json-lines` 含 `{wid}` `{url}` 且**不含 `{pipe}`**
- [ ] ★ **exe 路径不在 `args` 里**（由 `binary` 决定；宿主拼命令行）
- [ ] ★ `mpv-ipc` 的**播放地址由 `{url}` 参数项承载**（宿主不会再替你 `loadfile`）——忘写 `{url}` 会被拒装
- [ ] `capabilities`（若写）只含 `seek` / `rate` / `tracks` / `subtitle` / `fit`，不重复
- [ ] 随包的 exe 真在 `files/` 里（`plugin-file` 来源；回读 zip 核对，见 §2.1）
- [ ] ★ **不要用 `runtimeDeps` 分发二进制**（v1 无下载装配管线）；要么随包自带，要么 `local-path` 让用户指路径
- [ ] **真机四步**：装（弹权限确认）→ 「配置 → 播放 → 插件播放内核」出现且状态=就绪（`local-path` 先填路径）→
      打开开关（**首次有二次确认**）→ 播放器内核列表里选中它，画面真起且暂停/快进/音量/倍速/比例**状态回流对得上** →
      关开关 / 停用插件后内核消失、**无孤儿进程**、失败时**明确报错并回落内置**（不黑屏不静默）

## 3. 行为约定
- [ ] 插件可被**随时停用**而不报错
- [ ] 若贡献正生效（如超分档位），**移除**时能回落默认
- [ ] 需要 `net` 的插件已在 `permissions` + `permissionNotes` 说明用途

## 4. 对照拒装原因码（规范 §10）
`MISSING_MANIFEST` · `ID_INVALID` · `API_VERSION_MISMATCH` · `KIND_PERM_MISMATCH` · `UNKNOWN_CONTRIBUTE` · `PATH_ESCAPE` · `SHA_MISMATCH` · `INCOMPLETE` · `DEP_NOT_ALLOWED`
皮肤专属（规范 §5）：`THEME_TOKENS_REQUIRED` · `UNKNOWN_THEME_TOKEN` · `BAD_THEME_TOKEN_VALUE` · `THEME_STYLE_NOT_ALLOWED` · `BAD_THEME_LAYOUT` · `THEME_ID_TAKEN`
字幕源专属（规范 §5.4）：`SUBTITLE_PROVIDER_INVALID` · `SUBTITLE_ID_TAKEN` · `BAD_PROVIDER_URL` · `BAD_PROVIDER_PATH`
元数据源专属（规范 §5.5）：`META_PROVIDER_INVALID` · `META_ID_TAKEN` · `BAD_PROVIDER_URL` · `BAD_PROVIDER_PATH`
发现页数据源专属（规范 §5.6）：`DISCOVER_PROVIDER_INVALID` · `BAD_PROVIDER_URL` · `BAD_PROVIDER_PATH`
弹幕源专属（规范 §5.7）：`DANMAKU_PROVIDER_INVALID` · `BAD_PROVIDER_URL` · `BAD_PROVIDER_PATH`
直播输出模板专属（规范 §5.8）：`LIVE_TEMPLATE_INVALID` · `BAD_LIVE_TEMPLATE_LINE`
> ★ 直播输出模板**没有** `BAD_PROVIDER_URL` / `BAD_PROVIDER_PATH` —— 它不发请求、不取 JSON。
受限动作按钮专属（规范 §5.9）：`UI_COMMAND_INVALID` · `BAD_UI_COMMAND_URL`
> ★ 它**不取数、不跑代码**：动作词表外的写法、参数与动作不匹配、`open-url` 非 http(s) → 拒装。
追加快捷键专属（规范 §5.10）：`KEYMAP_INVALID` · `BAD_KEYMAP_KEY` · `BAD_KEYMAP_URL`
> ★ 它同样**不取数、不跑代码**，动作词表与 §5.9 相同；键位缺修饰键 / 主键越界 → `BAD_KEYMAP_KEY`。
插件设置面板专属（规范 §5.11）：`SETTINGS_PANEL_INVALID` · `BAD_SETTINGS_DEFAULT`
> ★ 它**不取数、不跑代码**：宿主渲染表单并**代持久化**；参数与类型不匹配 → INVALID，`default` 与类型不符 → `BAD_SETTINGS_DEFAULT`。
受限 UI 槽位专属（规范 §5.12）：`UI_SLOT_INVALID` · `BAD_UI_SLOT_URL`
> ★ 它**不取数、不跑代码**：只声明受限组件树；参数与类型不匹配 / `slot` 越界 → INVALID，`image`·`link` 的 url 非 http(s) → URL。

第三方播放内核专属（规范 §6.3）：`PLAYER_ENGINE_INVALID` · `BAD_ENGINE_ARGS`
> ★ **插件侧不取数、不跑代码**（只给描述符），但**宿主要替它启动本机程序** ⇒ 风险最高、默认关。
> ★ `BAD_ENGINE_ARGS` = `args` 的**结构性**问题：非数组 / 空 / 超 24 项 / 含换行 / 空串 /
>   占位符越界 / **缺协议必需占位符**（`mpv-ipc` 的 `{pipe}` 等）/ **`json-lines` 带了 `{pipe}`**。
> ★ `PLAYER_ENGINE_INVALID` = 其余（`id`/`label`/`protocol`/`binary` 形态 / `capabilities` / 顶层未知字段）。

L4 沙箱专属（规范 §6）：`UNKNOWN_PERMISSION` · `BAD_PERMISSION_NOTES`
> ★ `UNKNOWN_PERMISSION`：`permissions` 里有白名单外（含禁止项）的权限；`BAD_PERMISSION_NOTES`：`permissionNotes` 键 ⊆ 已声明权限 不成立，或值含换行 / 为空 / 超 200 字。

## 5. 打包（PowerShell 示例）
```powershell
# ★ -Path 直接列条目（别传父目录，否则会多套一层）；plugin.json 必须在包根级
Compress-Archive -Path plugin.json, files, LICENSE, licenses -DestinationPath out.zip
Rename-Item out.zip <id>.winbox
```
- ★ `Compress-Archive -DestinationPath` **必须以 `.zip` 结尾**（不是 `.zip` 会被自动补成 `.zip`，得到 `out.winbox.zip`）；正确做法 = 先出 `.zip` 再 `Rename-Item` 成 `.winbox`。
- ★ 回读校验时 `Expand-Archive` **只认 `.zip` 扩展名**（见 §2.1：先 `Copy-Item` 成 `.zip`）。
- 宿主侧读 `.winbox` 是**按字节**解（不看扩展名），所以扩展名只影响 PowerShell 工具链，不影响安装。
- ★ **皮肤插件（`type:"theme"`）的包形态与别的插件不同**：包内**只有** `plugin.json` + `LICENSE`（+ 需要时 `licenses/`），
  **没有 `files/`、没有任何 `.css`**。照抄命令时把 `files` 去掉：
  `Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip` → `Rename-Item out.zip <插件 id>.winbox`。
  可直接对照归档的发布产物示例 **`assets/theme-sakura.winbox`**（见 `references/theme-reference.md` §6；含自测三步）。
- ★ **四个声明式 provider（`subtitle.provider` / `meta.provider` / `discover.source` / `danmaku.source`）同理**：声明式、**无代码、无 `files/`**，
  包内只有 `plugin.json` + `LICENSE`（作者自建的公开 JSON 接口不需要随包任何资源）。
- ★ **直播输出模板（`live.template`）也一样**：声明式、**无代码、无 `files/`**，包内只有 `plugin.json` + `LICENSE`（它连接口都没有）。
- ★ **第三方播放内核（`player.engine`）是 `kind:"code"`**：包形态 = `plugin.json` + **`main.js`**（描述符型放空脚本即可）
  + **`files/`（含你随包自带的可执行文件，如 `files/mpv.exe`）** + `LICENSE`；
  若随包了**第三方本机程序**（mpv / ffmpeg 等），必须按 §1 在 `licenses/` 原样归档其许可原文并在根 `LICENSE` 署名
  （copyleft 上游如 GPL 系**必做**）。
