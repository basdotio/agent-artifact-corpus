# 插件设置面板（`contributes.settings.panel`）参考

> 唯一权威：`SPEC.md` §5.11。本页是**速查 + 自检**，冲突时以规范为准。
> 级别：**L3 声明式 UI**（`kind:"asset"`、`permissions` **必须为空**、**无 `main`**）。骨架：`assets/plugin.settings-panel.json`。

## 1. 一句话

你的插件**不跑代码、不注入任何 UI**：只声明「一组**受限字段**」（label / type / default），
宿主把它渲染成**宿主样式的表单**，并**代你把字段值存下来**。

```
你声明：fields（label + type + default，4 类词汇表内）
宿主做：按自己的样式渲染表单 + 把值存进 plugin-settings.json（按插件 id 分桶）
★ v1 的读取面留给 L4：kind:"code" 的沙箱代码经 settings 权限读 winbox.settings（asset 插件自己读不到）
```

## 2. 受限字段词表（★ 只能选这 4 类，不能自己写控件）

| `type` | 值类型 | 必填 / 可选参数 |
|---|---|---|
| `toggle` | `boolean` | `default` 必填（布尔）；**无**专属参数 |
| `select` | `string` | `default` 必填（须是某个 option 的 `value`）；`options` **必填**：1~50 项 |
| `text` | `string` | `default` 必填（不含换行、≤`maxLength`）；`maxLength?`（1~200 整数）、`placeholder?`（≤60 字） |
| `number` | `number` | `default` 必填（有限数字且落在 `[min,max]`）；`min?` / `max?` / `step?`（正数），`min ≤ max` |

- `select.options` 每项：`{ value: 1~60 字且唯一, label?: 1~40 字 }`。
- 公共字段：`key`（`[a-z0-9-]{1,40}`，同面板内唯一 —— **L4 读取时按它取值**）、`label`（1~40 字）、`type`、`default`；可选 `hint`（≤120 字）。
- ★ **参数必须与类型匹配**：`toggle` 带 `options`、`text` 带 `min`、`number` 带 `maxLength`、`select` 缺 `options` → **拒装**。

## 3. 结构

```jsonc
{
  "type": "settings.panel",
  "id": "general",                 // [a-z0-9-]{3,40}；同插件可声明多个面板（各自独立 id）
  "label": "常规设置",             // 面板标题（1~40 字，不含换行）
  "title": "插件常规设置",          // 可选：悬停提示（≤120 字）
  "fields": [                      // ★ ≥1、≤24；key 不得重复
    { "key": "enhance", "label": "启用增强", "type": "toggle", "default": true, "hint": "说明文字" },
    { "key": "quality", "label": "画质档", "type": "select", "default": "hd",
      "options": [ { "value": "sd", "label": "标清" }, { "value": "hd", "label": "高清" } ] },
    { "key": "proxy", "label": "代理地址", "type": "text", "default": "", "maxLength": 100, "placeholder": "http://…" },
    { "key": "threads", "label": "线程数", "type": "number", "default": 4, "min": 1, "max": 16, "step": 1 }
  ]
}
```

- 展示位置：**配置 → 插件/组件**页里**每个插件的卡片内**（仅声明了面板的插件显示）。
- 值的持久化：宿主按 `pluginId → panelId → fieldKey` 分桶存 `<userData>/plugin-settings.json`；
  **读回时存值合法则用存值、否则回落 `default`**（防记忆损坏 / 旧版本残留）。

## 4. 我该选哪个字段类型？（判定路径）

1. 开 / 关？ → `toggle`。
2. 从几个固定档里选一个？ → `select`（**必须**给 `options`，且 `default` 要在里面）。
3. 一个数字（并发数 / 超时 / 端口…）？ → `number`（给 `min`/`max` 收窄范围）。
4. 一段短文本（代理地址 / 自定义 UA…）？ → `text`。
5. 想要**其它控件**（滑块 / 多选 / 富文本 / 自定义组件）？ → ★ **本类型做不了**（v1 只有这 4 类）。

## 5. 自检（发布前逐条）

- [ ] `kind:"asset"`、`permissions: []`、**无 `main`**
- [ ] `id` 匹配 `[a-z0-9-]{3,40}`；同插件内不重复；`label` 非空且 ≤40 字
- [ ] `fields` 是 1~24 项数组；`key` 各自唯一且匹配 `[a-z0-9-]{1,40}`
- [ ] 每个字段的 `type` ∈ `toggle` / `select` / `text` / `number`；`default` **与 type 匹配**
- [ ] `select` 给了 `options`（1~50 项、`value` 唯一）且 `default` 是其中之一
- [ ] `text` 的 `maxLength`（若有）是 1~200 整数；`default` 不超长
- [ ] `number` 的 `min`/`max`/`step`（若有）合法且 `default` 落在 `[min, max]`
- [ ] **只带该类型自己的参数**（`toggle` 带 `options` 等一律拒装）；顶层**无多余字段**
- [ ] **真机两步**：装 → 「配置 → 插件」该插件卡片内出现表单；改一个字段 → 重开软件值仍在（宿主已落盘）
      → 停用插件后面板消失

## 6. 打包（与其它声明式 contribute 一样：**没有 `files/`**）

```powershell
Compress-Archive -Path plugin.json, LICENSE -DestinationPath out.zip
Rename-Item out.zip my-settings-panel.winbox
```

## 7. 对照拒装原因码

`SETTINGS_PANEL_INVALID`（结构 / 字段 / 类型白名单 / **参数与类型不匹配** / `key`·`label`·`title`·`hint` 边界 / options 边界）·
`BAD_SETTINGS_DEFAULT`（`default` 与 `type` 不匹配：toggle 非布尔 / select 不在 options / text 超 `maxLength` / number 越界或非数字）。

## 8. 常见坑

- **`select` 忘了 `options`**：拒装（下拉没有选项是没有意义的）。
- **`default` 不在 `options` 里**：拒装（`BAD_SETTINGS_DEFAULT`）。
- **`toggle` 的 `default` 写成字符串 `"true"`**：拒装（要真正的布尔 `true`）。
- **给 `text` 写 `min`（或给 `number` 写 `maxLength`）**：拒装 —— 参数必须与类型匹配。
- **以为面板值能被自己的插件读到**：v1 **读不到**（asset 插件不跑代码）；读取面在 **L4**（`kind:"code"` + `settings` 权限）。
- **卸载后以为设置会被清掉**：★ **不会** —— 宿主**保留**设置值（便于重装后沿用）。
