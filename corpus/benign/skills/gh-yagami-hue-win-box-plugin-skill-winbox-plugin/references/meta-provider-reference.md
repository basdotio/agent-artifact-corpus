# 元数据源（`contributes.meta.provider`）参考

> 唯一权威：`SPEC.md` §5.5。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L2 声明式**（`kind:"asset"`、`permissions` **必须为空**）。骨架：`assets/plugin.meta-provider.json`。

## 1. 一句话

你的插件**不跑代码**：只声明「去哪儿查、怎么取字段」，宿主按模板代发请求 + 按 JSON 路径取数，
产出**一条元数据命中**（标题 / 年份 / 海报 / 简介 / 类型 / 可选横图），用于补全**封面与简介**。

## 2. 它在什么位置生效（★ 很关键）

宿主现有的元数据链路是：**用户配置了 TMDB Key → 走 TMDB；否则 / 未命中 → 走豆瓣**。
你的插件元数据源是**兜底**：

```
TMDB（有 Key 时） → 豆瓣 → ★ 你的插件源（按插件登记顺序，命中即止）
```

- **不抢占**内置来源：内置命中时根本不会用到你。
- **显式指定来源**（调用方传了 `provider=tmdb|douban`）时**也不走插件**。
- 因此它最适合「内置查不到的小众 / 外语 / 自制内容」这类补全场景。

## 3. 结构

```jsonc
{
  "type": "meta.provider",
  "id": "my-meta",                     // [a-z0-9-]{3,40}；不得占用内置 tmdb / douban
  "name": "我的元数据站",
  "imageBase": "https://img.example.com/t/p/w342",   // 可选：海报/横图是相对路径时的前缀
  "search": {
    "url": "https://api.example.com/search?q={keyword}&year={year}",
    "headers": { "Referer": "https://api.example.com/" },   // 可选
    "list": "data.results",            // 命中项路径：**数组**（取第一项）或**单个对象**
    "map": {
      "title":     "name",             // ★ 必填
      "year":      "year",             // 可选
      "poster":    "poster_path",      // 可选（相对路径会拼 imageBase）
      "backdrop":  "wide_path",        // 可选（横版图）
      "overview":  "overview",         // 可选（简介）
      "mediaType": "type"              // 可选（值含 tv/series/剧/集 → tv，否则 movie）
    }
  }
}
```

> ★ v1 **不提供评分（rating）**：宿主当前 UI 不展示评分 → 声明 `rating` 会被**拒装**（不提供假能力）。
> ★ `list` 取到数组就取第一项；取到单个对象直接用 —— 两种常见响应形态都行。

## 4. 占位符（`search.url` / `search.headers` 可用）

| 占位符 | 含义 |
|---|---|
| `{keyword}` / `{title}` | 剧名（两者等价，都传剧名） |
| `{year}` | 年份（调用方可能不传 → 展开为空串） |

- **URL 里的值会被 `%` 编码**；**请求头里的值原样替换**。
- 用了白名单外的占位符（如 `{file}`）→ **拒装**（`BAD_PROVIDER_URL`）。

## 5. JSON 路径语法（与字幕源同一套）

- 仅 **点号 + 下标**：`data.results`、`data.items[0].name`；**无 `[*]`、无函数、无过滤**。
- 不是合法路径 → **拒装**（`BAD_PROVIDER_PATH`）。
- 数字 / 布尔会被转成字符串；对象 / 数组取不到（视为空）。
- `title` 取到空 → **该源视作无命中**（返回 null，不影响其他源）。

## 6. 图片处理

- `poster` / `backdrop` 取到的值是**绝对 URL**（`http(s)://…`）→ 原样使用；
- 是**相对路径**（如 `/abc.jpg`）→ 拼 `imageBase`；
- **相对路径但没声明 `imageBase`** → 该图**被丢弃**（`poster` 为空串），**绝不产出坏图**。

## 7. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`，且**不是** `tmdb` / `douban`（`META_ID_TAKEN`）
- [ ] `search.url` 是 `http(s)://`；`imageBase`（若声明）也是 `http(s)://`
- [ ] 占位符只用 `{keyword}` / `{title}` / `{year}`
- [ ] `search.list` 与 `map.title` 是合法点号路径；`map` 只含 `title/year/poster/backdrop/overview/mediaType`
- [ ] `headers` 无 `Host`/`Content-Length`/`Connection`/`Transfer-Encoding`，值里无换行
- [ ] **真机验证**：装上一个内置查不到的片名 → `meta:search` 返回该源的封面/简介 → 停用后回落内置行为

## 8. 打包（与皮肤 / 字幕源一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-meta-source.winbox
```

## 9. 对照拒装原因码

`META_PROVIDER_INVALID`（结构 / 字段越界 / 出现 rating 等未提供字段） · `META_ID_TAKEN`（占用内置来源 id） ·
`BAD_PROVIDER_URL`（协议 / 占位符 / imageBase / 请求头） · `BAD_PROVIDER_PATH`（JSON 路径语法）。

## 10. 常见坑

- **以为能"接管封面"**：不能 —— 内置命中时轮不到你；你是兜底。
- **声明 `rating` 想显示评分**：宿主 UI 不展示 → 直接拒装。
- **`map.title` 指向一个嵌套对象**：取值只认标量；指向对象 → 视作空 → 该源无命中。
- **`list` 直接写 `results`**：要写**从响应根开始的完整路径**（如 `data.results`）。
