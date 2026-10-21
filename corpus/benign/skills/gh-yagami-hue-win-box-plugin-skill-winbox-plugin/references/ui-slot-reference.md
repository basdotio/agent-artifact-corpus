# 受限 UI 槽位（`contributes.ui.slot`）参考

> 唯一权威：`SPEC.md` §5.12。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L3 声明式 UI**（`kind:"asset"`、`permissions` **必须为空**、**无 `main`**）。骨架：`assets/plugin.ui-slot.json`。

## 1. 一句话

你的插件**不跑代码、不注入任何 UI**（红线②：不做任意 React 组件注入）：只声明一棵**受限组件树**，
宿主把它渲染进**宿主既有页面的槽位**里（宿主样式、宿主交互）。

```
你声明：slot（投到哪个页面）+ items（组件树，6 类词汇表内）
宿主做：按自己的样式渲染到该页面内容区顶部；无插件声明该槽位时页面零变化
```

## 2. 槽位（`slot`）

| 值 | 落点 |
|---|---|
| `discover` | 发现页 |
| `home` | 点播页 |
| `detail` | 详情页 |
| `live` | 直播页 |
| `history` | 观看历史 |
| `favorites` | 我的收藏 |

- `slot` 是**非空数组**，≥1、不重复（同一个内容可同时投多个页面）。
- ★ 渲染位置 = 对应页面的**内容区顶部**（每次进该页都会显示）。

## 3. 受限组件词表（★ 只能选这 6 类，不能自己写控件 / 注入 HTML）

| `type` | 必填 / 可选字段 | 宿主渲染 |
|---|---|---|
| `heading` | `text` 必填（1~80 字，**不含换行**） | 小标题 |
| `text` | `text` 必填（1~500 字，**可含换行**） | 段落（保留换行） |
| `image` | `url` 必填（**仅 http/https**）、`alt?`（≤80 字） | 图片（**一律走宿主 `/img` 中继**） |
| `divider` | 无 | 分隔线 |
| `kv` | `items` 必填：1~12 行 `{ label(1~40 字), value(1~200 字) }` | 键值行列表 |
| `link` | `label` 必填（1~40 字）+ `action` 必填（**复用 §5.9 动作词表**） | 按钮 |

- ★ **参数必须与类型匹配**：`heading` 带 `url`、`divider` 带 `text`、`image` 带 `label`、`kv` 缺 `items` → **拒装**。

## 4. `link` 的动作（★ 与 `ui.command` / `keymap` **同一套词表**）

| `action` | 必填参数 | 做什么（宿主实现） |
|---|---|---|
| `open-url` | `url`（**仅 http/https**） | 用**系统浏览器**打开链接 |
| `navigate` | `to`（宿主页语义名） | 跳到宿主页面；`to:"config"` 时可用 `section` 滚到某张配置卡片 |
| `export-live` | `template?` | 复用「导出直播线路」 |
| `set-theme` | `theme`（皮肤 id） | 复用「切换皮肤」 |

- `to` 白名单：`discover` / `home` / `history` / `favorites` / `live` / `storage` / `config` / `about`（写**语义名**，写路径拒装）。
- ★ **只带该动作自己的参数**（`navigate` 带 `url`、`open-url` 带 `theme` → 拒装）。

## 5. 结构

```jsonc
{
  "type": "ui.slot",
  "id": "discover-tip",           // [a-z0-9-]{3,40}；同插件可声明多个槽位（各自独立 id）
  "slot": ["discover", "home"],    // 目标槽位，≥1
  "label": "插件推荐位",            // 可选：内容区小标题（1~40 字，不含换行）
  "title": "由插件提供的推荐位",     // 可选：悬停提示（≤120 字）
  "items": [                       // 组件树：≥1、≤24
    { "type": "heading", "text": "本周精选" },
    { "type": "text", "text": "第一行\n第二行" },
    { "type": "image", "url": "https://example.com/a.png", "alt": "示例图" },
    { "type": "divider" },
    { "type": "kv", "items": [ { "label": "来源", "value": "插件" } ] },
    { "type": "link", "label": "打开帮助", "action": "open-url", "url": "https://example.com/help" }
  ]
}
```

## 6. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`；同插件内不重复；`label` 非空且 ≤40 字
- [ ] `slot` 是非空数组、每项 ∈ 6 个槽位、不重复
- [ ] `items` 是 1~24 项；每个组件 `type` ∈ 6 类；**只带该类型自己的字段**
- [ ] `heading` 的 `text` 不含换行且 ≤80；`text` 的 `text` ≤500
- [ ] `image` 的 `url` 是 `http(s)://`；`kv` 的 `items` 1~12 行且每行有 `label`/`value`
- [ ] `link` 有 `label` 与 `action`，且**动作参数与动作匹配**（见 §4）
- [ ] 顶层**无多余字段**（如 `html` / `script` / `style` —— 一律拒装）
- [ ] **真机两步**：装 → 打开对应页面 ⇒ 内容区顶部出现插件内容（改一处文案重进页面即变）
      → 停用插件后页面恢复原样（**零残留**）

## 7. 打包（与其它声明式 contribute 一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-ui-slot.winbox
```

## 8. 对照拒装原因码

`UI_SLOT_INVALID`（结构 / 字段 / 组件类型白名单 / **参数与类型不匹配** / `slot` 白名单 / `items` 数量 / 文本与 kv 行边界 / `link` 的 label 与动作参数）·
`BAD_UI_SLOT_URL`（`image.url` 或 `link(open-url).url` 非 http(s) 或含空白）。

## 9. 常见坑

- **想塞自己的 HTML / 脚本 / 样式**（`html` / `script` / `style` 字段）：一律拒装 —— 本类型**只给受限组件树**（红线②）。
- **`image` 用相对路径或 `file://`**：拒装（只允许 http/https；图片会经宿主 `/img` 中继取）。
- **`kv` 写成对象**（`{来源: '插件'}`）：拒装；要写 `items: [{label, value}]` 数组。
- **`link` 忘了 `action`**：拒装（没有动作的按钮没有意义）。
- **以为能在详情页塞"跟当前影片相关"的动态数据**：v1 **做不到** —— 声明式内容**与页面数据无关**（要动态逻辑 → L4 代码插件）。
- **`slot` 写页面路径**（`"/discover"`）：拒装；要写语义名 `discover`。
