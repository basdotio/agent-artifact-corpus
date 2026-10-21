# 追加快捷键（`contributes.keymap`）参考

> 唯一权威：`SPEC.md` §5.10。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L3 声明式 UI**（`kind:"asset"`、`permissions` **必须为空**、**无 `main`**）。骨架：`assets/plugin.keymap.json`。

## 1. 一句话

你的插件**不跑代码**：只声明「按哪个键」+「触发**宿主预定义动作词表**里的哪一条动作」。
键盘 = 与 `ui.command`（§5.9 按钮）**完全同一套动作**，只是**触发方式**不同。

```
你声明：key（键位串）+ scope（在哪生效）+ action（做什么，词表内）
宿主做：把快捷键接进键盘分发（命中即执行），只在宿主既有表面展示一览（不注入任何插件 UI）
```

## 2. 键位串（★「不与宿主冲突」的硬护栏）

- 形如 `Ctrl+Alt+F`：`修饰键(+修饰键…)+主键`。
- 修饰键 ∈ `Ctrl` / `Alt` / `Shift` / `Meta`；别名归一（`Control`→Ctrl、`Option`→Alt、`Cmd`/`Command`/`Super`/`Win`→Meta）。
  大小写不敏感、顺序不限；宿主装配时归一到 `Ctrl → Alt → Shift → Meta` 顺序 + 主键大写。
- ★ **必须含 `Ctrl` / `Alt` / `Meta` 至少一个** —— 仅 `Shift` 不算（避免劫持普通按键）。
- ★ **主键仅允许**：单个字母 `A~Z`、数字 `0~9`、功能键 `F1~F24`。
  **不含**方向键 / `Backspace` / `Esc` / `Tab` 等宿主已占用键 —— 从**词法**上杜绝与宿主冲突。

| 合法 | 归一化后 |
|---|---|
| `ctrl+alt+f` | `Ctrl+Alt+F` |
| `alt+ctrl+1` | `Ctrl+Alt+1` |
| `Command+Shift+k` | `Shift+Meta+K` |
| `option+control+G` | `Ctrl+Alt+G` |

| 拒装（`BAD_KEYMAP_KEY`） | 原因 |
|---|---|
| `F` / `F1` | 只有主键、无修饰键 |
| `Shift+F` | 仅 Shift，缺 Ctrl/Alt/Meta |
| `Fn+F` | 未知修饰键 |
| `Ctrl+ArrowLeft` / `Ctrl+Escape` | 主键越界（宿主已占用键） |
| `Ctrl+` / `Ctrl+AB` | 主键缺失 / 多字符 |

## 3. 作用域（`scope`）

| 值 | 含义 |
|---|---|
| `app` | **主窗口**全局（发现 / 点播 / 历史 / 配置…任意页面都可触发） |
| `player` | **播放器窗口**（独立播放窗口内触发） |

- `scope` 是**非空数组**，≥1；每项 ∈ 白名单，不重复（可同时声明 `["app","player"]`）。
- ★ 命中后 `preventDefault` 并交给宿主动作词表执行；**输入控件内不触发**（与宿主键位同口径）。

## 4. 动作词表（★ 与 `ui.command` 完全相同，只能选、不能自己写逻辑）

| `action` | 必填参数 | 做什么（宿主实现） |
|---|---|---|
| `open-url` | `url`（**仅 http/https**） | 用**系统浏览器**打开链接 |
| `navigate` | `to`（宿主页语义名） | 跳到宿主页面；`to:"config"` 时可用 `section` 滚到某张配置卡片 |
| `export-live` | `template?`（模板 id，缺省=第一个可用模板） | 复用「导出直播线路」 |
| `set-theme` | `theme`（皮肤 id） | 复用「切换皮肤」（内置 4 套，或 `plugin:<skinId>`） |

- `to` 白名单：`discover`（发现）/ `home`（点播）/ `history` / `favorites` / `live` / `storage` / `config` / `about`。
  ★ **写语义名，不要写路径**（写路径会拒装）。
- ★ **动作之外的字段一律拒装**：写了 `navigate` 却带 `url`、写了 `open-url` 却带 `theme` → 直接拒装。

## 5. 结构

```jsonc
{
  "type": "keymap",
  "id": "go-discover",          // [a-z0-9-]{3,40}；同插件可声明多条（各自独立 id）
  "label": "去发现页",           // 中文说明（1~40 字，不含换行）
  "title": "跳到发现页",         // 可选：悬停提示（≤120 字）
  "scope": ["app"],             // ★ 生效范围，≥1：app（主窗口）/ player（播放器窗口）
  "key": "Ctrl+Alt+F",          // ★ 键位串（必须含 Ctrl/Alt/Meta；主键限字母/数字/F 键）
  "action": "navigate",         // 动作词表（与 ui.command 相同）
  "to": "discover",
  "confirm": false              // 可选：执行前二次确认
}
```

- 一个插件可以声明**多条**快捷键（每条一个 `type:"keymap"` 贡献项）。
- 展示 / 生效位置：**配置页「快捷键」tab**的「插件快捷键」只读一览（全部作用域）；
  `scope:"player"` 的还会出现在**播放器「键位」面板**。

## 6. 我该选哪条动作？（判定路径）

1. 要**开一个网页 / 文件链接**？ → `open-url`（只支持 http/https）。
2. 要**把用户带到宿主某个页面**？ → `navigate`（配 `section` 可直达配置卡片）。
3. 要**让用户导出直播线路**？ → `export-live`。
4. 要**换皮肤**？ → `set-theme`。
5. 以上都不是（要自己算 / 发请求 / 存数据 / 改播放 / 播放器控制）？ → ★ **本类型做不了**，那是 **L4**（`kind:"code"`）。

## 7. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`；同插件内不重复；`label` 非空且 ≤40 字
- [ ] `scope` 是非空数组，且每项 ∈ `app` / `player`（不重复）
- [ ] `key` **含 Ctrl/Alt/Meta 至少一个**；主键是字母 / 数字 / `F1~F24`（**不含方向键 / Backspace / Esc**）
- [ ] `action` ∈ 词表；**只带该动作自己的参数**（别的动作的字段一律删掉）
- [ ] 顶层**没有**多余字段（如 `when` / `handler` / `script` —— 一律拒装）
- [ ] **真机两步**：装 → 在对应窗口按下键位能触发（`navigate` 会跳页 / `open-url` 会拉起浏览器）
      → 配置页「快捷键」tab 出现「插件快捷键」一览；停用插件后一览与生效同时消失
      （宿主自身键位 / 老板键不受影响）

## 8. 打包（与其它声明式 contribute 一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-keymap.winbox
```

## 9. 对照拒装原因码

`KEYMAP_INVALID`（结构 / 字段 / `scope` / 动作词表 / 参数与动作不匹配 / `label`·`title`·`confirm` 边界）·
`BAD_KEYMAP_KEY`（键位串非法：缺修饰键 / 主键越界 / 未知修饰键）·
`BAD_KEYMAP_URL`（`open-url` 的 `url` 不是 http/https 或含空白）。

## 10. 常见坑

- **键位没带 Ctrl/Alt/Meta**（如 `Shift+F`、`F1`）：拒装 —— 这是「不与宿主冲突」的硬护栏。
- **用了方向键 / `Backspace` / `Esc` 当主键**：拒装（宿主已占用）。
- **`navigate` 里写路径**（`to: "/config"`）：拒装；要写语义名 `config`。
- **`open-url` 指向 `file://` 或 `javascript:`**：拒装（只允许 http/https）。
- **想让快捷键做"自定义逻辑"**（播放控制 / 发请求 / 算数据）：本类型做不到，请走 **L4**（`kind:"code"`）。
- **与老板键撞车**（默认 `Ctrl+Shift+B`）：老板键是**全局 OS 级**快捷键，会优先于本插件键位；建议避开该组合。
