# 字幕源（`contributes.subtitle.provider`）参考

> 唯一权威：`SPEC.md` §5.4。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L2 声明式**（`kind:"asset"`、`permissions` **必须为空**）。骨架：`assets/plugin.subtitle-provider.json`。

## 1. 一句话

你的插件**不跑代码**：只声明「去哪儿取、怎么取字段」，**宿主按模板代发请求 + 按 JSON 路径取数**，
产出的候选会像内置源（`assrt` / `subtitlecat`）一样进入软件的字幕面板（检索 → 选择 → 下载）。

装上后**自动出现在「字幕设置」的源开关列表**里；用户可单独关掉。

## 2. 什么时候能用它 / 什么时候不行

| 情况 | 用 L2 声明式？ |
|---|---|
| 站点返回 **JSON**，`GET` + 查询串即可检索 | ✅ 本页 |
| 需要 **`POST`** 请求体 | ❌ 用 L4（`kind:"code"`） |
| 需要 **token / 登录 / 签名 / 时间戳** | ❌ 用 L4 |
| 需要**本地解析 HTML 页面**（非 JSON） | ❌ 用 L4 |
| 直接把固定地址列表写死（无需检索） | ⚠️ 勉强可用（`search.list` 指向固定假数组不现实）→ 建议 L4 |

> ★ v1 只有 **GET**、只认 **JSON** 响应、**不能**自报鉴权。这是"声明式"的边界，不是缺陷。

## 3. 结构

```jsonc
{
  "type": "subtitle.provider",
  "id": "my-subs",                     // [a-z0-9-]{3,40}；不得占用内置源 assrt / subtitlecat
  "name": "我的字幕站",                 // 字幕设置里的显示名
  "search": {
    "url": "https://sub.example.com/api/search?q={keyword}&ep={ep}",
    "headers": { "Referer": "https://sub.example.com/" },   // 可选，多为防盗链
    "list": "data.list",               // ★ 响应里**数组**所在的点号路径
    "map": {                           // 每项 → 候选字段
      "file":    "id",                 // ★ 必填：下载标识（会用进 fetch 的 {file}）
      "subname": "filename",           // ★ 必填：字幕文件名（UI 上就是这一列）
      "title":   "video_title",        // 可选
      "lang":    "language",           // 可选（简中/繁中/…；UI 会按中文优先排序）
      "format":  "ext",                // 可选（srt/ass/ssa/vtt…）
      "detail":  "note"                // 可选（备注）
    }
  },
  "fetch": {
    "url": "https://sub.example.com/api/download/{file}",   // ★ 必须含 {file}
    "headers": { "Referer": "https://sub.example.com/" }
  }
}
```

## 4. 占位符（模板里可用的变量）

| 位置 | 可用占位符 |
|---|---|
| `search.url` / `search.headers` | `{keyword}` `{keywords}` `{title}` `{ep}` |
| `fetch.url` / `fetch.headers` | `{file}` `{subname}` `{title}` `{ep}` |

- `{keyword}` = 首个检索关键词；`{keywords}` = 全部关键词（空格连接）；`{title}` = 剧名；`{ep}` = 集号（可能为空）。
- **URL 里的值会被 `%` 编码**（空格 → `%20`，中文自动转义）；**请求头里的值原样替换**（头值不该被编码）。
- 用了白名单外的占位符（如 `search.url` 里写 `{file}`）→ **拒装**（`BAD_PROVIDER_URL`）。

## 5. JSON 路径语法（受限，别当 JS 用）

- 只支持 **点号 + 下标**：`data.list`、`data.items[0].title`。
- **没有** `[*]`、没有过滤、没有函数、没有 `$..`。不是合法路径 → **拒装**（`BAD_PROVIDER_PATH`）。
- 值若是数字/布尔会被转成字符串；对象/数组**取不到**（视为该字段为空）。
- `file` 或 `subname` 取到空 → 该条候选**被丢弃**（不会报错）。

## 6. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `subtitle.provider.id` 匹配 `[a-z0-9-]{3,40}`，且**不是** `assrt` / `subtitlecat`（`SUBTITLE_ID_TAKEN`）
- [ ] `search.url` / `fetch.url` 都是 `http(s)://`（其他协议 → `BAD_PROVIDER_URL`）
- [ ] `fetch.url` **含 `{file}`**
- [ ] 占位符只用本页 §4 的白名单（越界即 `BAD_PROVIDER_URL`）
- [ ] `headers` 里没有 `Host` / `Content-Length` / `Connection` / `Transfer-Encoding`，值里无换行（`BAD_PROVIDER_URL`）
- [ ] `search.list` 与 `map.*` 都是合法点号路径（`BAD_PROVIDER_PATH`）；`map` 只含白名单字段
- [ ] **真机验证**：装上 → 字幕设置出现该源 → 搜一个剧能看到候选 → 下载能出字幕 → 卸载后该源消失

## 7. 打包（与皮肤一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-subtitle-source.winbox
```

## 8. 对照拒装原因码

`SUBTITLE_PROVIDER_INVALID`（结构/字段缺失或越界） · `SUBTITLE_ID_TAKEN`（占用内置源 id） ·
`BAD_PROVIDER_URL`（协议 / 占位符 / 请求头） · `BAD_PROVIDER_PATH`（JSON 路径语法）。

## 9. 常见坑

- **把 JSON 路径当 JS**：`data.list.filter(...)` 一律拒；宿主只做取值。
- **`map.file` 指向页面 URL**：`file` 是给 `{file}` 用的**下载标识**，通常就是源里的 id。
- **站点是 GBK 的 JSON**：宿主按 UTF-8 / GB18030 双解码选优，无需你处理；但**非 JSON**（HTML）会报「响应不是合法 JSON」。
- **想加鉴权**：别硬塞 `Authorization` 到 headers（无签名/无刷新）；这种源请写 L4 插件。
