# 弹幕源（`contributes.danmaku.source`）参考

> 唯一权威：`SPEC.md` §5.7。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L2 声明式**（`kind:"asset"`、`permissions` **必须为空**）。骨架：`assets/plugin.danmaku-source.json`。

## 1. 一句话

你的插件**不跑代码**：按软件既有的**三步链路**声明三段受限模板，宿主代发请求 + 按 JSON 路径取数：

```
① search   关键词 → 番剧候选（animeId / bangumiId / 标题…）
② episodes 番剧   → 剧集候选（episodeId / 集号…）      ← 播放器「弹幕源」面板里选中的那部
③ comment  剧集   → 弹幕 XML 文本（B 站格式）          ← 交给宿主解析上屏
```

## 2. 它在什么位置生效

- 插件弹幕源与宿主内置的**外部接口清单**（炊烟袅袅 / Logvar / 御坂…）**并列**参与检索：
  一起并行查询、一起按匹配度排序、共用同一套失败冷却。
- 插件源在候选里显示的来源名 = 你声明的 `name`。
- ★ **v1 边界**：插件弹幕源**不进**播放器「弹幕源」面板的接口开关清单 —— 要停用请到 **配置 → 插件**里停用该插件。

## 3. 结构（三段缺一不可）

```jsonc
{
  "type": "danmaku.source",
  "id": "my-danmaku",                  // [a-z0-9-]{3,40}（宿主合成 source 键 plugin:<id>）
  "name": "我的弹幕站",                 // 候选列表里标注来源用
  "search": {
    "url": "https://dm.example.com/api/search?keyword={keyword}&season={season}",
    "headers": { "Referer": "https://dm.example.com/" },   // 可选
    "list": "animes",                  // ★ 响应里**数组**所在的点号路径
    "map": {                           // animeId / title **必填**
      "animeId": "animeId",
      "title": "animeTitle",
      "bangumiId": "bangumiId",        // 可选（缺省用 animeId）
      "episodeCount": "episodeCount",  // 可选（同季条目优选「真剧集」用）
      "kind": "type"                   // 可选（tvseries / movie …）
    }
  },
  "episodes": {
    "url": "https://dm.example.com/api/bangumi/{animeId}",
    "list": "bangumi.episodes",
    "map": {
      "episodeId": "episodeId",        // ★ 必填
      "episodeTitle": "episodeTitle",  // 可选
      "episodeNumber": "episodeNumber" // 可选（数字串，1~4 位；用于显示与排序）
    }
  },
  "comments": {
    "url": "https://dm.example.com/api/comment/{episodeId}?format=xml"   // ★ 必须含 {episodeId}
  }
}
```

> ★ **`comments` 没有 `list`/`map`**：它的响应就是**弹幕本体**（XML 文本），由宿主的引擎解析器消费。
> ★ **只收 XML**（B 站弹幕格式）。你的接口若只给 **JSON 弹幕** → 本期做不了，请走 L4（`kind:"code"`）。

## 4. 占位符（按段各一套白名单）

| 段 | 可用占位符 | 含义 |
|---|---|---|
| `search.url` / `search.headers` | `{keyword}` `{season}` | 检索词 / 季号（无季号时展开为空串） |
| `episodes.url` / `episodes.headers` | `{animeId}` `{title}` | 番剧 id / 番剧标题 |
| `comments.url` / `comments.headers` | `{episodeId}` | 剧集 id |

- URL 里的值 `%` 编码；请求头里的值原样替换；**越界占位符 → 拒装**。

## 5. JSON 路径语法（与其它 provider 同一套）

- 仅 **点号 + 下标**：`animes`、`bangumi.episodes`、`data.list[0].rows`；无 `[*]`、无函数（非法 → 拒装）。
- 数字 / 布尔转字符串；对象 / 数组取不到。
- `animeId` 取不到数字 → 该条丢弃；`episodeId` 取不到数字 → 该条丢弃；`title` 为空 → 该条丢弃。

## 6. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`；`name` 非空
- [ ] 三段 `search` / `episodes` / `comments` **都在**；每段 `url` 是 `http(s)://`
- [ ] 占位符按段白名单（§4）；**`comments.url` 含 `{episodeId}`**
- [ ] `search.map.animeId` / `search.map.title` / `episodes.map.episodeId` 是合法点号路径
- [ ] 映射字段无越界（如 `score`/`cover` 等未提供字段一律拒装）
- [ ] `headers` 无 `Host`/`Content-Length`/`Connection`/`Transfer-Encoding`，值里无换行
- [ ] **真机三步**：装 → 播放器「弹幕源」里搜到该源命中的番剧（来源名 = 你的 `name`）→ 选到剧集能出弹幕
      → 停用插件后该源不再出现（内置源不受影响）

## 7. 打包（与其它声明式 provider 一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-danmaku-source.winbox
```

## 8. 对照拒装原因码

`DANMAKU_PROVIDER_INVALID`（结构 / 段缺失 / 字段越界）· `BAD_PROVIDER_URL`（协议 / 占位符 / 请求头）·
`BAD_PROVIDER_PATH`（JSON 路径语法）。

## 9. 常见坑

- **只声明 `search`**：三段缺一即拒装（没有 `episodes` 就没法从番剧走到剧集，没有 `comments` 拿不到弹幕）。
- **`comments` 返回 JSON**：会报「响应不是 XML」——本期只吃 XML。
- **`bangumiId` 与 `animeId` 填反**：`bangumiId` 是**取剧集列表**用的 id；你的接口若两者相同，可以**不写** `bangumiId`（宿主自动用 `animeId`）。
- **以为能在播放器面板单独开关**：v1 不支持 —— 请用「配置 → 插件」停用。
- **接口需要 token / 签名**：声明式做不了 → L4。
