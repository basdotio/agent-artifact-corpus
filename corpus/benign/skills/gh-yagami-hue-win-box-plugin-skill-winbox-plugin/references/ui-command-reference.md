# 受限动作按钮（`contributes.ui.command`）参考

> 唯一权威：`SPEC.md` §5.9。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L3 声明式 UI**（`kind:"asset"`、`permissions` **必须为空**、**无 `main`**）。骨架：`assets/plugin.ui-command.json`。

## 1. 一句话

你的插件**不跑代码**：只声明「往哪个界面加一个什么按钮」+「这个按钮执行**宿主预定义动作词表**里的哪一条动作」。

```
你声明：label + placement（挂哪）+ action（做什么，词表内）
宿主做：把按钮渲染成宿主自己的样式（不注入你的任何 UI），并按词表执行动作
```

## 2. 动作词表（★ 只能选，不能自己写逻辑）

| `action` | 必填参数 | 做什么（宿主实现） |
|---|---|---|
| `open-url` | `url`（**仅 http/https**） | 用**系统浏览器**打开链接（主进程 `shell.openExternal`） |
| `navigate` | `to`（宿主页语义名） | 跳到宿主页面；`to:"config"` 时可用 `section` 滚到某张配置卡片 |
| `export-live` | `template?`（模板 id，缺省=第一个可用模板） | 复用「导出直播线路」（当前活动线路 → 保存对话框） |
| `set-theme` | `theme`（皮肤 id） | 复用「切换皮肤」（内置 4 套，或 `plugin:<skinId>`） |

- `to` 白名单：`discover`（发现）/ `home`（点播）/ `history` / `favorites` / `live` / `storage` / `config` / `about`。
  ★ **写语义名，不要写路径**（`/config` 这种由宿主映射，写路径会拒装）。
- `section`（仅 `to:"config"`）：配置卡片锚点后缀，如 `plugins`（= `#cfg-plugins`）、`appearance`、`lives`。
- ★ **动作之外的字段一律拒装**：写了 `navigate` 却带 `url`、写了 `open-url` 却带 `theme` → 直接拒装
  （防止"以为能做、实际不做"）。

## 3. 结构

```jsonc
{
  "type": "ui.command",
  "id": "open-help",                 // [a-z0-9-]{3,40}；同插件可声明多个命令（各自独立 id）
  "label": "打开帮助",                // 按钮文字（1~40 字，不含换行）
  "title": "在系统浏览器里打开帮助页",   // 可选：悬停提示
  "placement": ["config", "player"],  // ★ 挂载点，≥1：config（配置 → 插件页）/ player（播放器控制条）
  "action": "open-url",               // 动作词表（见 §2）
  "url": "https://example.com/help",  // action=open-url 必填
  "confirm": false                    // 可选：执行前二次确认（防误点）
}
```

- 一个插件可以声明**多条**命令（每条一个 `type:"ui.command"` 贡献项）。
- 按钮会显示在：**配置 → 插件**页的「插件命令」区，以及**播放器控制条**（与「统计/键位」同一排控件）。

## 4. 我该选哪条动作？（判定路径）

1. 要**开一个网页 / 文件链接**？ → `open-url`（注意：只支持 http/https，`file:` 等一律拒装）。
2. 要**把用户带到宿主某个页面**？ → `navigate`（配 `section` 可直达配置卡片）。
3. 要**让用户导出直播线路**？ → `export-live`（想指定格式就写 `template`，如 `builtin:m3u`）。
4. 要**换皮肤**？ → `set-theme`。
5. 以上都不是（要自己算 / 发请求 / 存数据 / 改播放）？ → ★ **本类型做不了**，那是 **L4**（`kind:"code"`）。

## 5. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`；同插件内不重复；`label` 非空且 ≤40 字
- [ ] `placement` 是非空数组，且每项 ∈ `config` / `player`（不重复）
- [ ] `action` ∈ 词表；**只带该动作自己的参数**（别的动作的字段一律删掉）
- [ ] `open-url` 的 `url` 是 `http(s)://`；`navigate` 的 `to` 是**语义名**（不是路径）；`set-theme` 的 `theme` 是真实皮肤 id
- [ ] 顶层**没有**多余字段（如 `icon` / `onClick` / `script` —— 一律拒装）
- [ ] **真机两步**：装 → 「配置 → 插件」出现「插件命令」按钮且点得动（`open-url` 会拉起浏览器）
      → 停用插件后按钮消失（宿主其它功能不受影响）

## 6. 打包（与其它声明式 contribute 一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-ui-command.winbox
```

## 7. 对照拒装原因码

`UI_COMMAND_INVALID`（结构 / 字段 / 挂载点 / 动作词表 / 参数与动作不匹配 / label·title·confirm 边界）·
`BAD_UI_COMMAND_URL`（`open-url` 的 `url` 不是 http/https 或含空白）。

## 8. 常见坑

- **写了 `icon` / `onClick` / `script`**：一律拒装 —— 本类型只声明「文字按钮 + 词表动作」，**不做任意 UI 注入**（红线②）。
- **`navigate` 里写路径**（`to: "/config"`）：拒装；要写语义名 `config`。
- **`open-url` 指向 `file://` 或 `javascript:`**：拒装（只允许 http/https）。
- **`set-theme` 指向不存在的皮肤**（如别的插件已卸载）：按钮**不报错**，但会提示"皮肤不存在"——不会静默换到默认皮肤。
- **想让按钮做"自定义逻辑"**（发请求 / 算数据 / 控制播放）：本类型做不到，请走 **L4**（`kind:"code"`，需 `permissions`）。
