# 第三方播放内核（`player.engine`）参考

> 唯一权威：`SPEC.md` §6.3。本文件是**全量口径 + 自检 + 常见坑**，冲突时以规范为准。
> ★ **风险最高的一类贡献**：它会让**宿主启动你提供的本机程序**。默认关闭 + 用户显式开启 + 二次确认，是刻意的。

## 1. 一句话定位

- 插件**只声明「引擎描述符」**：协议族 / 二进制来源 / 参数模板；**不含任何启动代码**。
- **宿主托管进程**：宿主编命令行 → `spawn` → （`mpv-ipc`）`--wid` 嵌入播放器窗口 + JSON IPC 管道 →
  状态归约 → 节流 200ms 推给界面。插件侧**只见描述符，不见进程**。
- ★ **插件永不拉进程**：`spawn` / `child_process` 是**永久禁止项**（规范 §6.2）。你没有这个权限，
  **也不需要**——写启动逻辑是宿主的事。
- `kind` **只能是 `code`**（`CONTRIBUTES['player.engine'].kinds` 已冻结为 `['code']`）：清单**必须**有
  `main`（沙箱入口，描述符型插件放个空脚本即可）+ **非空 `permissions`**（通常只需 `log`）。

## 2. 结构

```jsonc
{
  "type": "player.engine",
  "id": "my-mpv",                                   // [a-z0-9-]{3,40}；界面内核值 = "engine:my-mpv"
  "label": "我的 MPV",                              // 1~40 字，不含换行
  "protocol": "mpv-ipc",                            // mpv-ipc | json-lines
  "binary": { "source": "plugin-file", "file": "files/mpv.exe" },
  "args": [
    "--no-config",
    "--force-window=yes",
    "--wid={wid}",
    "--input-ipc-server={pipe}",
    "{url}",
    "--start={start}",
    "--volume={volume}",
    "--speed={rate}"
  ],
  "capabilities": ["seek", "rate", "tracks", "subtitle", "fit"]
}
```

| 字段 | 约束 |
|---|---|
| `type` | 恒 `"player.engine"` |
| `id` | `[a-z0-9-]{3,40}`；重复 id **先到先得**（同 id 后到的插件内核被忽略） |
| `label` | 1~40 字、不含换行（配置页 / 控制条内核列表显示） |
| `protocol` | `mpv-ipc` \| `json-lines`（见 §4） |
| `binary.source` | `plugin-file`（缺省）\| `local-path` |
| `binary.file` | `plugin-file` **必填**：插件内安全相对名（如 `files/mpv.exe`）；**`local-path` 不得带 `file`** |
| `args` | 非空数组、≤24 项；每项字符串、无换行；占位符须在白名单内 |
| `capabilities` | 若写：非空数组，每项 ∈ `seek` / `rate` / `tracks` / `subtitle` / `fit`，不重复（控制条据此收敛，不提供假能力） |

- ★ **exe 路径不写在 `args` 里** —— 它由 `binary` 决定，宿主拼命令行（`spawn(exe, args)`）。
- 顶层**无多余字段**（写别的字段 → 拒装）。

## 3. 占位符（宿主展开）

| 占位符 | 必需性 | 宿主填入的值 |
|---|---|---|
| `{wid}` | **必需**（两协议） | 播放器窗口 HWND（十进制整数串） |
| `{url}` | **必需**（两协议） | 播放地址（宿主既有 `/play` 中继地址，防盗链头 / cookie 已注入） |
| `{pipe}` | **`mpv-ipc` 必需** / ★ `json-lines` **禁止** | 宿主为该会话生成的 IPC 管道名（`\\.\pipe\winbox-engine-…`） |
| `{start}` | 可选 | 起播位置：**整数秒**（≤0 时**不提供** → 该参数项整项丢弃） |
| `{volume}` | 可选 | 初始音量：**整数百分比 0~130**（对齐 mpv CLI 的 `--volume`） |
| `{rate}` | 可选 | 倍速浮点（如 `1.5`，对齐 mpv CLI 的 `--speed`） |
| `{fit}` | 可选 | 画面比例串（`contain` / `fill` / `cover` / `r169` / `r43` / `none`） |

- ★ **可选占位符缺省 → 该参数项「整项丢弃」**（避免传空串把内核弄报错）。
  例：`--start={start}` 在「从头播」时不出现，而不是变成 `--start=`。
- `0` 是**显式值**（如 `--volume=0` = 静音）→ 保留。
- ★ **按协议校验占位符**（不满足即拒装）：
  - `mpv-ipc`：必须有 `{wid}` + `{url}` + **`{pipe}`**；
  - `json-lines`：必须有 `{wid}` + `{url}`，且**不得出现 `{pipe}`**
    （该族的通道就是进程的 stdin/stdout，写 `{pipe}` 说明作者误解了协议）。

## 4. 两协议族的线格式

### 4.1 `mpv-ipc`（mpv 及其兼容构建）

宿主**逐字复用**内置 mpv 的全链路：`observe_property` → `property-change` → `loadfile` / `set_property`，
走 `--input-ipc-server=<pipe>` 的 JSON IPC。因此你的 exe **必须是 mpv 或 mpv 系兼容构建**（认
`--wid` / `--input-ipc-server` 这两个开关）。

- 典型形态：`binary` 指向**随包的 mpv.exe**，或用 `local-path` 指向本机已装的 mpv。
- 必需参数通常就是 `--wid={wid}` + `--input-ipc-server={pipe}` + `{url}`（地址由 args 承载，宿主**不会**再额外 `loadfile`）。
- 宿主的附加动作：连上管道后发属性观察、下发一次 `set_property pause`（`paused` 无对应占位符）、
  并按窗口高度调 `video-margin-ratio-top`（画面避开标题栏；与内置 mpv 同口径）。

### 4.2 `json-lines`（通用族：**线格式由宿主定死**）

进程的 **stdin / stdout 各一行一个 JSON 对象**（UTF-8，`\n` 分隔）。

**宿主 → 引擎（下行命令）**：
```
{"cmd":"load","url":"…","start":12.5,"paused":false,"volume":1,"rate":1,"fit":"contain"}
{"cmd":"play"}      {"cmd":"pause"}
{"cmd":"seek","value":12.5}   {"cmd":"volume","value":0.8}   {"cmd":"rate","value":1.5}
{"cmd":"fit","value":"contain"}   {"cmd":"quit"}
```

**引擎 → 宿主（上行状态事件；宿主用与 mpv 同一套状态归约）**：
```
{"event":"loaded","duration":123.4,"live":false}
{"event":"time","value":12.3}      {"event":"duration","value":123.4}
{"event":"paused","value":true}    {"event":"eof"}    {"event":"exit"}
{"event":"tracks","audio":[{"id":1,"title":"国语"}],"sub":[{"id":2}]}
{"event":"error","message":"…"}
```

- 字段名**就是上表**，宿主**不做字段重映射** —— 你的引擎若原生协议不同，
  **自己写一个小转发程序**（把原生协议翻译成上面这几行）即可。
- **未识别的事件 / 字段一律忽略**（前向兼容：你多发字段不会出错）。
- 引擎进程退出（进程 exit，或 `{"event":"exit"}`）→ 宿主置「已退出」并推送（与 mpv 同口径）。
- ★ 可选事件：`buffering`（`{"event":"buffering","value":true}`）与 `paused` 同形，用于缓冲指示。
- ★ 本族**不做真机探针**（宿主自带样本是 mpv 系）：其线格式由**纯函数单测**全覆盖，
  请严格按上表实现；`sub-add` / `aid` / `sid` / `sr-mode` 等 mpv 专属命令在通用族**无对应动作**（宿主不下发）。

## 5. 二进制来源与授权

| 来源 | 写法 | 解析口径 |
|---|---|---|
| **随包自带**（主） | `"binary": { "source": "plugin-file", "file": "files/my-engine.exe" }` | 宿主解析为 `<插件目录>/files/my-engine.exe`；**必须仍落在插件目录内**（越界即拒） |
| **用户本机路径**（次） | `"binary": { "source": "local-path" }` | 用户在「配置 → 播放 → **插件播放内核**」填路径（对位内置的 `mpvPath` 口径）；未填 / 路径不存在 → **未就绪**（列表里显示为不可选 + 原因） |

- ★ **不能靠 `runtimeDeps` 分发二进制**：v1 的 `runtimeDeps` **只有清单校验、没有下载装配管线**
  （且内置许可清单里只有着色器文本资源）。→ 二进制**要么随包自带，要么让用户指定本机路径**。
- ★ **授权闸门**（默认关）：
  1. **安装期**：`kind:"code"` 会弹权限清单请你确认；
  2. **启用期**：「插件播放内核」区**单独开关**，默认关；**首次开启有二次确认**
     （明确告知「该内核为插件提供的本机程序，将由宿主代为启动并通信」）；
  3. **运行期**：未启用时 `engine:start` 被宿主**明确拒绝**（不会「悄悄起来」）。
- 未就绪 / 未启用 → 内核**仍出现在列表**里但**不可选**（带人话原因），绝不静默假装成功。

## 6. 用户在哪里看到它

- **配置 → 播放 → MPV 播放内核 卡片内「插件播放内核」区**：每项一个开关 + 就绪状态
  （未就绪显示原因：「未指定本机程序路径」/「插件内的引擎可执行文件缺失」…）；`local-path` 来源额外给**路径输入框**。
- **播放器控制条的内核按钮**：可选内核 **> 2** 时按钮变**列表**（内置 HTML5 / 内置 MPV / 你的内核）；
  仅有内置两个时仍是原来的 MPV 一键切换。
- ★ **插件内核不参与「自动」**：`auto` 只在 HTML5 ↔ MPV 之间按资源形态选择 ——
  插件内核涉及运行本机程序，**必须由用户显式选**。
- 起播失败（未启用 / 未就绪 / 进程起不来）→ 界面**明确报错 + 自动回落内置 HTML5**，不会停在黑屏。

## 7. 自检（装前 + 装后）

**装前（清单层）**
- [ ] `kind:"code"` + 有 `main` + `permissions` 非空（描述符型插件写 `["log"]` 即可）
- [ ] `contributes[].type = "player.engine"`；只写本文档 §2 的字段（无多余顶层字段）
- [ ] `id` `[a-z0-9-]{3,40}`；`label` 1~40 字不含换行；`protocol` ∈ `mpv-ipc` / `json-lines`
- [ ] `binary` 形态正确：`plugin-file` 带**安全相对** `file`（无 `..` / 无盘符 / 无前导 `/`）；
      `local-path` **不带** `file`
- [ ] `args` 非空、≤24、每项无换行；占位符全在白名单内
- [ ] **按协议**：`mpv-ipc` 含 `{wid}` `{url}` `{pipe}`；`json-lines` 含 `{wid}` `{url}` 且**不含 `{pipe}`**
- [ ] `capabilities`（若写）只含 `seek` / `rate` / `tracks` / `subtitle` / `fit`，不重复
- [ ] 随包的 exe 真的在 `files/` 里（`plugin-file` 来源；参照 `checks.md` §2.1 回读 zip 核对）

**装后（行为层）**
- [ ] 「配置 → 播放 → 插件播放内核」出现你的内核；`plugin-file` 来源显示**就绪 + 绝对路径**；
      `local-path` 来源填路径后由「未就绪」变为「就绪」
- [ ] 打开播放器窗口 → 内核按钮变**列表**，里面有你的内核
- [ ] 选中后：画面真起、进度推进、暂停/快进/音量/倍速/画面比例**都能用且状态回流对得上**
- [ ] 关闭开关（或停用插件）→ 内核从列表消失 / 回落内置；**不留孤儿进程**（任务管理器无残留）
- [ ] 起播失败时界面**明确报错**并回落内置（不是黑屏、不是静默）

## 8. 常见坑

1. **把 exe 路径写进 `args`** —— 错。exe 由 `binary` 决定；`args` 只是**开关模板**。
2. **`json-lines` 里写了 `{pipe}`** → 直接拒装（该族通道是 stdin/stdout，不是命名管道）。
3. **`mpv-ipc` 忘了 `--input-ipc-server={pipe}`** → 拒装（缺必需占位符）；即便绕过，宿主也连不上管道、拿不到状态。
4. **以为宿主会替你 `loadfile`** → 不会。`mpv-ipc` 的**播放地址由 `{url}` 参数项承载**（记得把 `{url}` 放进 `args`）。
5. **`{start}` 传了 0 却指望出现 `--start=0`** → 不会：≤0 视为「无值」→ **整项丢弃**（本来就是从头播，无需该开关）。
6. **`binary.file` 写绝对路径 / `..`** → 拒装（安全相对名）。
7. **指望 `auto` 会选到你的内核** → 不会，必须用户显式选（插件内核不参与自动切换）。
8. **指望用 `runtimeDeps` 分发二进制** → v1 无下载装配管线；请随包自带（`plugin-file`）或让用户指路径（`local-path`）。
9. **`mpv-ipc` 却给了非 mpv 的 exe**（不认 `--wid` / `--input-ipc-server`）→ 起不来或连不上管道；
   非 mpv 系引擎请改用 `json-lines` 并按 §4.2 的线格式实现（或写个小转发程序）。
10. **`local-path` 来源写死 `file`** → 拒装（路径必须由用户在配置页给）。
