# 发现页数据源（`contributes.discover.source`）参考

> 唯一权威：`SPEC.md` §5.6。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L2 声明式**（`kind:"asset"`、`permissions` **必须为空**）。骨架：`assets/plugin.discover-source.json`。

## 1. 一句话

你的插件**不跑代码**：声明一个或多个**分区（榜单分组）**，宿主按模板代发请求 + 按 JSON 路径取数，
把它们**追加**到软件的「发现」页（每个分区 = 页面上的一行）。

## 2. 它在什么位置生效

发现页现有榜单是宿主内置的（有 TMDB Key 走 TMDB，否则走豆瓣）。你的插件分区是**增补**：

```
内置榜单（TMDB / 豆瓣） → ★ 你的插件分区（追加在末尾）
```

- **不抢占**内置榜单：插件分区一律加在后面。
- **同 id 被忽略**：内置分区先占 id；插件声明的分区 id 若与内置（或别的插件）重复，该分区**不显示**。
- 内置榜单**整条失败**时，你的插件分区**照样显示**（你是增补，不是替代）。

## 3. 结构

```jsonc
{
  "type": "discover.source",
  "id": "my-discover",                 // [a-z0-9-]{3,40}
  "name": "我的榜单",
  "sections": [                        // ★ ≥1；顺序 = 发现页上的显示顺序
    {
      "id": "my-top-movie",            // [a-z0-9-]{3,40}；同一插件内不得重复
      "title": "我的电影热榜",          // 页面上这一行的标题
      "mediaType": "movie",            // movie | tv（缺省 movie）
      "url": "https://api.example.com/top?type={mediaType}&limit=20",
      "headers": { "Referer": "https://api.example.com/" },   // 可选
      "list": "data.items",            // ★ 响应里**数组**所在的点号路径
      "imageBase": "https://img.example.com/t/p/w342",        // 可选（相对路径图的前缀）
      "map": {
        "title":     "name",           // ★ 必填
        "year":      "year",
        "poster":    "poster_path",
        "backdrop":  "wide_path",
        "mediaType": "type",
        "tmdbId":    "tmdb_id"
      }
    }
  ]
}
```

> ★ `map` **不允许 `doubanId`**：宿主拿到 `doubanId` 会去取「豆瓣剧照」，插件源并非豆瓣 ⇒ 图源错配。
> 需要横版图时用 `backdrop`（宿主会直接展示你给的那张）。
> ★ 需要两个不同类型的热榜？写**两个 section**（如上面的 movie + tv），别指望一个接口同时给。

## 4. 占位符（`url` / `headers` 可用）

| 占位符 | 含义 |
|---|---|
| `{mediaType}` | 该 section 声明的 `mediaType`（`movie` 或 `tv`） |

- **URL 里的值 `%` 编码**；**请求头里的值原样替换**。越界占位符（如 `{keyword}`）→ **拒装**。

## 5. 图片：宿主统一走本地中继

- 你的 `poster` / `backdrop` 值 → 宿主包成 `/img?u=<你的地址>` **再交给界面**（与内置榜单同口径：
  渲染层直连图床可能被 DNS 污染）。
- 值若是**相对路径**（`/abc.jpg`）→ 先拼 `imageBase`；**没配 `imageBase` 则这张图被丢弃**（不会产坏图）。
- 你只写**原始地址**即可，别自己拼 `/img`（宿主会识别并避免套两层）。

## 6. JSON 路径语法（与其它 provider 同一套）

- 仅 **点号 + 下标**：`data.items`、`data.list[0].rows`；**无 `[*]`、无函数、无过滤**（非法 → 拒装）。
- 数字 / 布尔转字符串；对象 / 数组取不到。
- `title` 取到空 → **该条被丢弃**；`list` 不是数组 → **该分区不出现**。
- 分区**取到 0 条**时**不显示**（不会留一行空白）。

## 7. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `discover.source.id` 与每个 `section.id` 都匹配 `[a-z0-9-]{3,40}`；**同插件内 section.id 不重复**
- [ ] `sections` 非空；每个 section 有 `title`
- [ ] `url`（与 `imageBase`，若声明）都是 `http(s)://`；占位符只用 `{mediaType}`
- [ ] `list` 与 `map.title` 是合法点号路径；`map` 只含 `title/year/poster/backdrop/mediaType/tmdbId`
- [ ] `headers` 无 `Host`/`Content-Length`/`Connection`/`Transfer-Encoding`，值里无换行
- [ ] **真机三步**：装 → 发现页出现你的分区（在内置榜单**之后**）且条目的图能出 → 停用后该分区消失

## 8. 打包（与皮肤 / 其它声明式 provider 一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-discover-source.winbox
```

## 9. 对照拒装原因码

`DISCOVER_PROVIDER_INVALID`（结构 / 字段越界 / section 重名 / 出现 `doubanId` 等） ·
`BAD_PROVIDER_URL`（协议 / 占位符 / imageBase / 请求头） · `BAD_PROVIDER_PATH`（JSON 路径语法）。

## 10. 常见坑

- **分区没出现**：先查 `section.id` 是否与内置/别的插件**撞名**；再看 `list` 是不是数组、是否取到 0 条。
- **图不显示**：多半是相对路径但没配 `imageBase`（那张图会被丢弃）。
- **面数不全**：单个分区失败**只跳过该分区**，不会影响同插件的其它分区 —— 别把所有榜单塞在一个 section 里。
- **想要「分类浏览」**：`discover.source` 只管**榜单分区**；分类浏览词表是宿主内置的（豆瓣），本期不开放给插件。
