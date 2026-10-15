# 酒馆正则（Regex）实战

正则系统是 ST 内置扩展（扩展面板 → 正则），也是变量卡的"管道工"：**去掉不该给 AI 看的文本、把占位符变成界面、把更新块折叠成好看的样子**。

## 1. 两个作用域 × 两个方向

每个正则脚本由两类开关确定作用方式：

- **作用范围 `placement`**：`[1]`=用户输入，`[2]`=AI 输出，两者可并存（1=用户输入, 2=AI 输出；导入 JSON 里是数字数组）。
- **短暂（作用方向）**：
  - `markdownOnly: true` = **仅格式显示**：只影响消息在屏幕上长什么样，不影响发给 AI 的文本；
  - `promptOnly: true` = **仅格式提示词**：只影响发给 AI 的文本，不影响显示；
  - 两者都 false = 显示与提示词都替换；
  - 两者都 true = 均不生效（无意义）。

配合 `minDepth`/`maxDepth` 限制生效楼层深度。**深度从最新消息数起（0 = 最新一楼）**，当 `minDepth ≤ 深度 ≤ maxDepth` 时正则才生效（两侧都可为 `null` 表示不限）：

```
深度 0: 最新一楼（生成时一般是最后一条用户输入）
深度 1: 倒数第 2 楼（一般是最后一条 AI 回复）
深度 2: 倒数第 3 楼 … 依此类推
```

- `minDepth: null, maxDepth: null` → 对所有楼层生效；
- **`minDepth: N`**（如 N=3）→ 跳过最新 N 楼、只清洗更早的楼层 = "给 AI 保留最近 N 楼的原文"（实测卡常用：只发送最新 6 楼的变量更新 → `minDepth: 6`）；
- `maxDepth: N`（配 minDepth null）→ **只**对最新 N+1 楼生效。对"清理旧楼层"是反方向（历史坑点，别写反）；但它是**显示层"只管最新楼层"的正当工具**（实测：创角表单/行动控制台用 `maxDepth: 1` 只让最新两楼渲染该界面）。

两条额外机制（写卡时经常用到）：

- **显示层同样按 0=最新 计深度**（ST 源码：`usableMessages.length - indexOf - 1`），且 `minDepth/maxDepth` 在显示层同样生效。
- **正则按数组顺序依次应用**：同一标记可被多条正则"接力消费"——先应用的正则会吃掉/改名标记，后面的正则只能匹配剩下的。实测用法：闸门先把 `Impl` 改名为 `READY`，状态栏打 `READY`；用深度限制做分流（最新楼层走"行动控制台"，其余楼层走"PC 状态栏"）。

> 命名约定（社区通行，便于排查）：`[不发送]` = 只改提示词（promptOnly）、`[隐藏]`/`[不显示]` = 只改显示（markdownOnly）、`[界面]`/`[状态栏]`/`[替换]`/`[开场]`/`[开局]` = 界面与创角、`[折叠]`/`[美化]` = 显示美化、`[闸门]`/`[校验]` = 变量块校验放行、`[变量]` = 变量相关的提示/警告。废弃条目留在列表里禁用即可，惯例命名如 `(作废)`、`（没用了，不开）`。

**样式变体切换**：同一 `findRegex` 准备多条正则（PC/手机、不同主题），**一次只启用一条**，其余置 `disabled: true` 备用——玩家换口味时作者只需启用另一条（实测卡 E 的状态栏有 4 个变体、D 有 PC/手机双版）。

## 2. 变量卡的标准正则集

以下 5 条覆盖 90% 的卡；JSON 模板在 `templates/regex-基础.json` 与 `templates/regex-界面.json`（**记得给每条换新 UUID**）。

### ① `[不发送]去除变量更新`（把更新块从提示词里清除）

```json
{
  "id": "<uuid>",
  "scriptName": "[不发送]去除变量更新",
  "disabled": false,
  "runOnEdit": false,
  "findRegex": "/<(update(?:variable)?)>(?:(?!.*<\\/\\1>)(?:(?!<\\1>).)*$|(?:(?!<\\1>).)*<\\/\\1?>)/gsi",
  "replaceString": "",
  "trimStrings": [],
  "placement": [1, 2],
  "substituteRegex": 0,
  "minDepth": null,
  "maxDepth": null,
  "markdownOnly": false,
  "promptOnly": true
}
```

- **默认对所有楼层生效（minDepth/maxDepth 均为 null）**：更新块已被 MVU 脚本解析使用，再发给 AI 只会浪费 token、分散注意力，甚至让 AI 偷懒照抄旧块。这是社区（青空莉资源仓库）发布版的默认配置。
- 正则用反向引用 `\1` 匹配开闭标签：既覆盖完整的 `<UpdateVariable>…</UpdateVariable>`，也覆盖**流式输出中途**未闭合的尾巴（第一个分支），并兼容 `<UpdateVariable>`/`<updatevariable>` 等大小写漂移（`i` 标志）。
- 若你发现 AI 重复依据旧剧情更新变量（看不到以前做过什么更新），可选择**给 AI 保留最近几楼的更新块**：设 **`minDepth: 3`**（跳过最新 3 楼）或 `minDepth: 4`（保留最新 4 楼）——**注意不是 maxDepth**，见上文深度语义。
- 大小写不敏感 `i` + 单行模式 `s`（让 `.` 跨行）。

### ② `[折叠]变量更新中`（显示层：未完成的更新块）

```json
{
  "id": "<uuid>",
  "scriptName": "[折叠]变量更新中",
  "disabled": false,
  "runOnEdit": false,
  "findRegex": "/<(update(?:variable)?)>(?!.*<\\/\\1>)\\s*((?:(?!<\\1>).)*)\\s*$/gsi",
  "replaceString": "\n\n<details>\n<summary>变量更新中{{random::.::..::...}}</summary>\n$2\n</details>\n",
  "trimStrings": [],
  "placement": [1, 2],
  "substituteRegex": 0,
  "minDepth": null,
  "maxDepth": null,
  "markdownOnly": true,
  "promptOnly": false
}
```

- `{{random::.::..::...}}` 是 ST 内置宏，显示成随机的 "…" 点动画，表示“还在流式更新”。
- `<details>` 折叠块让消息保持清爽，玩家想看再展开。

### ③ `[折叠]完整变量更新`（显示层：已完成的更新块）

```json
{
  "id": "<uuid>",
  "scriptName": "[折叠]完整变量更新",
  "disabled": false,
  "runOnEdit": false,
  "findRegex": "/<(update(?:variable)?)>\\s*((?:(?!<\\1>).)*)\\s*<\\/\\1>/gsi",
  "replaceString": "\n\n<details>\n<summary>变量更新情况</summary>\n$2\n</details>\n",
  "trimStrings": [],
  "placement": [1, 2],
  "substituteRegex": 0,
  "minDepth": null,
  "maxDepth": null,
  "markdownOnly": true,
  "promptOnly": false
}
```

### ④ `[不发送]界面占位符`（占位符不占 token）

```json
{
  "id": "<uuid>",
  "scriptName": "[不发送]界面占位符",
  "findRegex": "/<StatusPlaceHolder(?:Impl|READY)\\s*\\/>/g",
  "replaceString": "",
  "placement": [2],
  "markdownOnly": false,
  "promptOnly": true,
  "minDepth": null, "maxDepth": null, "disabled": false, "runOnEdit": false,
  "trimStrings": [], "substituteRegex": 0
}
```

`(?:Impl|READY)` 与 `\s*` 让它同时覆盖闸门改名后的 READY 和 `<StatusPlaceHolderImpl />` 这类带空格的写法（实测卡惯例）。

### ⑤ `[界面]状态栏`（占位符 → 界面）

```json
{
  "id": "<uuid>",
  "scriptName": "[界面]状态栏",
  "findRegex": "/<StatusPlaceHolder(?:Impl|READY)\\s*\\/>/g",
  "replaceString": "```\n<body>\n<script>\n$('body').load('https://…/状态栏.html')\n</script>\n</body>\n```",
  "placement": [2],
  "markdownOnly": true,
  "promptOnly": false,
  "minDepth": null, "maxDepth": null, "disabled": false, "runOnEdit": false,
  "trimStrings": [], "substituteRegex": 0
}
```

两种替换内容二选一：

- **内联**（默认推荐，卡自包含）：直接把完整 HTML（含 `<head>`/`<body>`）写进替换内容；注意 JSON 里换行写 `\n`、双引号转义。
- **CDN 载入**（如卡要持续更新前端）：用上面的 `$('body').load('地址')` 片段——被酒馆助手渲染后，iframe 会用 jQuery 把远程 HTML 装载进 body。

想在**消息开头**显示界面（而非占位符原位）：把 findRegex 换成 `/(.*)<StatusPlaceHolderImpl\/>/s`，替换写成 `你的界面\n$1`。

### ⑥ 闸门校验组（可选，推荐：让"AI 没更新变量"可见）

实测卡（两张独立来源的卡完全一致的配置）常用一组"闸门"：**只有更新块正常出现时，界面才渲染；否则显示警告**。三个部件：

1. **`[闸门]变量块校验-放行`**（仅格式显示，`runOnEdit: true`）：

```json
{
  "id": "<uuid>",
  "scriptName": "[闸门]变量块校验-放行",
  "findRegex": "/(<\\/UpdateVariable(?:variable)?>[\\s\\S]*?)<StatusPlaceHolderImpl\\/>|()<StatusPlaceHolderImpl\\/>(?=[\\s\\S]*<UpdateVariable(?:variable)?>)/g",
  "replaceString": "$1<StatusPlaceHolderREADY/>",
  "placement": [2],
  "markdownOnly": true,
  "promptOnly": false,
  "minDepth": null, "maxDepth": null, "disabled": false, "runOnEdit": true,
  "trimStrings": [], "substituteRegex": 0
}
```

- 第一个分支：占位符**在闭合的更新块之后**（常规顺序）→ 改名 READY；第二个分支：占位符**在更新块之前**（有些卡的输出协议先行占位符）→ 也放行。两个分支合起来兼容两种协议顺序。
- 放行是"仅显示层"的改名，不写入消息原文。

2. **界面正则改打 READY**：把⑤的 findRegex 改为 `<StatusPlaceHolderREADY/>`（**去掉 Impl**——没有更新块时不该渲染界面）。注意**数组顺序：闸门必须排在界面正则之前**。
3. **`[变量]变量未更新警告`**：findRegex 打 `<StatusPlaceHolderImpl\s*\/>`（没被放行的剩余占位符）→ 替换为一条"本轮未检测到变量更新"的小卡片。

模板见 `templates/regex-闸门.json`。不装闸门的卡照旧用 Impl|READY 版本即可（没有 READY 也无害）。`check_card.py` 会做闸门与界面的配套检查。

## 3. 正则语法注意（ST 用的是 JavaScript 正则）

- `findRegex` 是**字符串包着的字面量**：`"/pattern/flags"`。常用 flags：`g`(全局)、`i`(忽略大小写)、`s`(`.` 匹配换行)、`m`(多行)。
- **转义双保险**：JS 字面量里 `/` 写成 `\/`；写进 JSON 字符串时 `\/` 又要写成 `\\/`（同理 `\\d`、`\\s`）。`check_card.py` 会做基本的可编译性检查。
- `<UpdateVariable>` 大小写会飘（模型可能写 `<updatevariable>`），所以社区模板用 `/<update(?:variable)?>/gsi` 这样大小写不敏感 + 前缀可缺省的写法。
- 惰性匹配 `[\s\S]*?` 在多段更新块时常比贪婪匹配安全；但如果模型输出的块不闭合，就需要 ①/② 里的"尾巴"分支来兜底。
- 替换内容里的 `$1`、`$2` 是捕获组引用（`$&` = 全部匹配）。想输出字面 `$1` 请写 `$$1`。
- 正则**在每次渲染/每次请求都对全部（未裁剪的）楼层跑**——避免写会被大量回溯的模式（如 `.*.*.*`），卡顿的元凶常在这里。
- ST 正则扩展自带**调试器**（正则面板里的 "调试器" 按钮可试跑 findRegex），写完建议在酒馆里试一遍再打包。

## 4. 卡内正则（scoped regex）

- 打包时正则会写进卡 `data.extensions.regex_scripts`；玩家导入卡首次加载时 ST 弹窗询问是否启用"该角色卡的正则脚本"，允许后仅在该卡激活时生效。
- 玩家拒绝后重开的口子：扩展 → 正则 → 勾选/重新触发弹窗（或删掉账号存储里的告警标记）。交付说明里提醒一句"弹窗要允许"。
- 编辑器里手写正则当然也行：扩展 → 正则 → 新建 → 按 §1 的两个开关理解配置；导出则是**数组 JSON**（工具条上的导入/导出按钮），和卡内格式一致。

## 5. 常见坑

| 坑 | 说明 |
|---|---|
| 只勾了"仅格式显示"却指望 promptOnly 效果 | 两个方向相反，先想清楚"改显示还是改提示词" |
| 状态栏突然不显示（改装闸门后） | 闸门把 Impl 改名为 READY 了，但状态栏还在匹配 Impl → 状态栏应只匹配 READY（或双写 Impl\|READY 但去掉闸门） |
| 有 READY 正则但界面从不渲染 | 没装闸门（READY 从不产生）；或闸门被禁用；或数组顺序里界面正则排在闸门前 |
| AI 就是不肯输出更新块 | 加 `[mvu_update]变量输出格式强调` / `[mvu_update]强制结尾输出` 条目（见 references/mvu.md §4.3 与 templates/） |
| 正则清掉了不该清的 | `去除变量更新` 的深度设置写反（如误用 maxDepth）；先想清"清洗哪些楼层"，再用调试器看匹配段 |
| 显示里出现裸露的 `<UpdateVariable>` | 折叠正则没启用（或大小写没写 `i`） |
| 状态栏出现两份 | `[不发送]界面占位符` 与 `[界面]状态栏` 同时替换没问题；但若复制了多条替换占位符的正则，会一起生效 |
| 修改消息后不生效 | `runOnEdit: false` 时编辑消息不会重跑替换；需要时置 true |
| 更新块泄漏进提示词 | ①没启用 / promptOnly 没设 / 深度范围写反（默认应为 null/null，或按需设 minDepth） |
