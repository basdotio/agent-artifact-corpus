# L4 沙箱代码插件参考（`kind:"code"`）

> 对应 `SPEC.md` §6。**L4 = 唯一会「跑你的代码」的级别**。
> 骨架见 `assets/plugin.code.json`。

---

## 1. 何时用 L4

- 需要**出网取数**（不止 GET / 需要鉴权 / 需要自己算签名）；
- 需要**存状态**（KV / 自己的设置项 / 自己目录里的文件）；
- 需要**控制播放**（播放/暂停/进度/音轨/字幕/音量）；
- 需要弹通知 / 读写剪贴板 / 打开外部链接。

> 纯声明式能解决的一律用 **L1/L2/L3（`kind:"asset"`）** —— 那不给用户任何权限提示，更安全。

## 2. 清单要点

```jsonc
{
  "kind": "code",          // 必填：code
  "main": "main.js",       // 必填：**沙箱入口文件**相对名（不得含 .. / 绝对路径）
  "permissions": ["net"],  // 必填：非空，且全部在白名单内
  "permissionNotes": {     // 可选：每个权限一句话用途（**安装时会展示给用户**）
    "net": "从站点接口取数据"
  }
}
```

- `kind:"code"` ⇒ **必须有 `main`**、**`permissions` 非空**；
- `kind:"asset"` ⇒ `permissions` 必须为空、**不得有 `main`**；
- `permissionNotes` 若写：**键必须 ⊆ 已声明权限**，值 1~200 字、不含换行（否则 `BAD_PERMISSION_NOTES`）。

## 3. 权限白名单（12 项，只有这些）

| 权限 | 注入 API | 用途 |
|---|---|---|
| `net` | `winbox.http(url, opts)` | 经宿主代理发 HTTP |
| `net.download` | `winbox.download(url, name, onProgress)` | 下载文件到插件目录 |
| `kv` | `winbox.kv.get/set/delete` | 插件私有 KV（键前缀 `plugin:<id>:`） |
| `settings` | `winbox.settings.get/set` | 读写**本插件**的设置项（与 settings.panel 同一份） |
| `fs.plugin` | `winbox.fs.read/write/list/exists/delete/mkdir` | **仅本插件目录**内的文件 |
| `log` | `winbox.log.i/w/e` | 写日志（前缀 `plugin:<id>`） |
| `notify` | `winbox.notify(title, body)` | 系统通知 |
| `clipboard.read` | `winbox.clipboard.read()` | 读剪贴板 |
| `clipboard.write` | `winbox.clipboard.write(text)` | 写剪贴板 |
| `dialog` | `winbox.dialog.alert/confirm` | 原生消息框（**仅展示**） |
| `player.control` | `winbox.player.play/pause/seek/volume/next/prev/audioTrack/subtitle` | 控制播放 |
| `openExternal` | `winbox.openExternal(url)` | 用系统程序打开链接（**仅 http/https**） |

**永不可用**（声明即拒装）：`main` `spawn` `child_process` `eval` `fs` `cred` `proxy` `registry` `raw.net`。

## 4. 沙箱边界（**必须知道**）

- **未授权的 API 根本不存在**：`winbox.kv` 若没授权 `kv`，它就是 `undefined` —— `winbox.kv.get()` 抛 `TypeError`，而不是「存在但报错」。
- 沙箱里**没有** `require` / `process` / `module` / `exports` / `global` / `Buffer` / `fs` / `child_process`。
- 只提供最小全局：`console`、`setTimeout`/`clearTimeout`/`setInterval`/`clearInterval`、`TextEncoder`/`TextDecoder`、`URL`/`URLSearchParams`、`atob`/`btoa`。
- 入口文件**整段在独立 worker 里跑**（第三方代码绝不进主进程）。
- `fs.*` 的路径必须是**安全相对路径**且解析后仍在插件目录内，越界即拒。
- `openExternal` 只接受 `http(s)://`。

## 5. 用法示例

```js
// main.js —— 注意：整段被包进 async IIFE，支持顶层 await
winbox.log.i('插件启动');

const res = await winbox.http('https://api.example.com/list', {
  method: 'get',
  headers: { 'User-Agent': 'WinBox' },
});
if (res.status === 200) {
  const data = JSON.parse(res.text());
  await winbox.kv.set('cache', JSON.stringify(data));
}

// 读本插件设置项（值来自 settings.panel 的字段）
const on = await winbox.settings.get('enabled');

// 下载到插件目录（进度 v1 只报「开始 / 完成」两帧）
await winbox.download('https://cdn.example.com/a.bin', 'files/a.bin', (loaded, total) => {
  winbox.log.i(`下载 ${loaded}/${total}`);
});

// 读自己目录里的文件（相对插件根）
const txt = await winbox.fs.read('files/a.bin');

// 控制播放（播放器没开时宿主会拒绝）
await winbox.player.pause();

winbox.notify('完成', '数据已更新');
```

## 6. 自检

- [ ] `kind:"code"`、`main` 存在且是安全相对名；
- [ ] `permissions` 非空且**逐条**都在 12 项白名单内（禁止项一律不写）；
- [ ] `permissionNotes` 键 ⊆ `permissions`（建议**每条都写**，安装时给用户看）；
- [ ] `main` 里**没有**用 `require` / `process` / `fs` / `child_process`（沙箱里不存在）；
- [ ] 用到的 `winbox.xxx` **都已在 `permissions` 里声明**（否则运行时 `undefined`）；
- [ ] `fs` 只用插件内相对路径；`openExternal` 只用 http(s)。

## 7. 常见坑

| 现象 | 原因 |
|---|---|
| `TypeError: Cannot read properties of undefined (reading 'get')` | 该权限没声明（未授权的 `winbox.*` 不存在） |
| 安装被拒 `UNKNOWN_PERMISSION` | 写了白名单外的权限（或禁止项如 `fs`/`proxy`） |
| 安装被拒 `KIND_PERM_MISMATCH` | `kind:"code"` 没写权限，或 `kind:"asset"` 写了权限/main |
| 安装被拒 `BAD_PERMISSION_NOTES` | `permissionNotes` 键含未声明权限 / 值含换行 / 空 |
| 脚本一进来就 `failed` | `main` 里用了沙箱没有的东西（`require`/`process`），或文件不在包内 |
| `winbox.player.*` 返回 `ok:false` | 播放器窗口没打开 |
