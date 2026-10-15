# 角色卡文件格式（JSON / PNG / 世界书 / 正则）

本文件是"手改格式"时的权威参照。打包与拆包优先用 `scripts/` 里的工具，除非工具不适用。

## 1. 角色卡 JSON（V2 / V3）

导入 ST 的卡是单个 JSON 对象。当前生态主流是 `"spec": "chara_card_v3", "spec_version": "3.0"`（实测 6 张线上卡全部 v3；v3 与 v2 的 `data` 布局一致，v3 增设可选字段如 `assets`/`nickname` 等）。**两种都被 ST 1.13+ 接受**；本技能的 extract 会保留原卡规格、build 新建卡默认 v3。顶层同时保留旧式字段与 `data`（兼容性写法，照抄结构）：

```jsonc
{
  "name": "卡名",
  "description": "……",            // 以下顶层字段与 data 内同名字段相同（历史兼容）
  "personality": "",
  "scenario": "",
  "first_mes": "开场白（第一条消息）",
  "mes_example": "",
  "creatorcomment": "作者备注",     // 注意：v1 位置字段名是 creatorcomment
  "avatar": "none",
  "chat": "",
  "talkativeness": "0.5",
  "fav": false,
  "tags": [],
  "spec": "chara_card_v2",
  "spec_version": "2.0",
  "data": {
    "name": "卡名",
    "description": "角色描述（人设主体）",
    "personality": "性格概要（可留空，很多卡把内容都写在 description）",
    "scenario": "场景设定",
    "first_mes": "开场白",
    "mes_example": "对话示例 <START> {{user}}: … {{char}}: …",
    "creator_notes": "作者备注/玩法说明",
    "system_prompt": "",
    "post_history_instructions": "",
    "alternate_greetings": ["开局2……", "开局3……"],
    "tags": [],
    "creator": "作者名",
    "character_version": "1.0",
    "extensions": {
      "world": "世界书名称",             // 关联的独立世界书名（可选）
      "talkativeness": "0.5",
      "fav": false,
      "regex_scripts": [ /* ST 正则数组，见 §4 */ ],
      "tavern_helper": {
        "scripts": [ /* 酒馆助手脚本，见 §5 */ ],
        "variables": {}
      }
    },
    "character_book": { /* 内嵌世界书，见 §3 */ }
  },
  "create_date": "2026-01-01T00:00:00.000Z"
}
```

要点：

- **`character_book` = 随卡世界书**：导入卡时 ST 自动据此建立世界书文件并关联（玩家无需单独导入世界书）。字段映射见 §3。
- **`extensions.regex_scripts`**：ST 读取卡内正则；玩家首次使用时会弹窗"此角色卡带有正则脚本，是否启用"——允许后该正则仅在该卡激活时生效（scoped）。被拒绝后可在 扩展→正则 里重新允许。
- **`extensions.tavern_helper`**：酒馆助手读取卡内脚本并在该卡激活时运行（角色卡脚本）。导出卡时酒馆助手会把最新脚本写回卡里。
- 需同时兼容旧格式时，酒馆助手认识旧字段 `TavernHelper_scripts`（数组）与 `TavernHelper_characterScriptVariables`，但**新卡一律用 `tavern_helper` 对象**。
- **未知扩展键必须透传保留**：实测卡都有 `depth_prompt`，部分卡带第三方编辑器元数据（如 `cfMvuVarGroups`——变量组定义，不参与运行但作者工具在用）。本技能的工作流用 `card.json` 里的 `"extensions_extra": {…}`（extract 自动生成）携带这些键，build 时原样写回 `data.extensions`；**手改工程时不要删掉它**，否则重建的卡会丢字段。

## 2. PNG 打包（chara / ccv3）

角色卡 PNG = 头像图 + 两个 `tEXt` 元数据块：

| 关键字 | 内容 |
|---|---|
| `chara` | 上面的 JSON 以 UTF-8 序列化后 **base64**（无换行）写入 tEXt 的文本部分 |
| `ccv3` | 同上的 V3 兼容副本（实践中与 `chara` 同内容亦可被 ST 接受） |

- tEXt 块结构：`长度(4字节大端) + "tEXt" + 关键字 + 0x00 + 文本 + CRC(4字节)`。
- 写入位置：IHDR 之后、IDAT 之前均可（ST 解析所有块，位置不敏感）；覆盖旧卡时先剥掉已有 `chara`/`ccv3` 块再加。
- 关键：文本部分只允许 Latin-1 字节范围 → 必须 base64。keyword 固定小写 `chara`（ST 解析区分大小写）。
- `scripts/build_card.py` 已实现全部细节（含 CRC、已有块剥离）。

## 3. 世界书：两种形态与字段映射

### 3.1 ST 世界书 JSON（可导入文件；`worldbook.json` 用它）

```jsonc
{
  "name": "世界书名称",        // 可选但建议；ST 主要以文件名标识
  "entries": {
    "0": {
      "uid": 0,
      "key": ["关键词"],          // 蓝灯时留空数组
      "keysecondary": [],
      "comment": "条目标题（就是面板上显示的标题）",
      "content": "条目内容",
      "constant": true,           // true=蓝灯（常驻）；false=按 key 触发
      "vectorized": false,
      "selective": true,
      "selectiveLogic": 0,        // 0 AND_ANY, 1 NOT_ALL, 2 NOT_ANY, 3 AND_ALL
      "addMemo": false,
      "order": 100,               // 同一位置内排序
      "position": 1,              // 数字位置表（见下）
      "disable": false,           // true=条目禁用（[initvar] 用）
      "depth": 4,                 // position=4(@D) 时的注入深度
      "probability": 100,
      "useProbability": true,
      "role": 0,                  // 0 system, 1 user, 2 assistant（@D 时）
      "excludeRecursion": false,
      "preventRecursion": false,
      "delayUntilRecursion": 0,
      "scanDepth": null,
      "caseSensitive": null,
      "matchWholeWords": null,
      "group": "", "groupOverride": false, "groupWeight": 100,
      "sticky": null, "cooldown": null, "delay": null,
      "ignoreBudget": false,
      "automationId": "",
      "outletName": "",
      "triggers": []
    }
  }
}
```

**`position` 数字位置表**（ST 内部常量，务必按表填）：

| 值 | 位置 | 说明 |
|---|---|---|
| 0 | Character Before | 角色定义之前 |
| 1 | Character After | 角色定义之后 |
| 2 | AN Top | 作者注释顶部 |
| 3 | AN Bottom | 作者注释底部 |
| 4 | @D (atDepth) | 指定深度（配合 `depth` 与 `role`；**变量卡主要用这个，深度 0**） |
| 5 | EM Top | 示例消息顶部 |
| 6 | EM Bottom | 示例消息底部 |
| 7 | Outlet | 出口 |

**手改 `worldbook.json` 的注意（血泪点）**：`entries.<uid>.content` 在文件里是**单行 JSON 字符串**——换行是转义序列 `\n`（反斜杠+n 两个字符），文件里没有真换行。因此：

- 用文本编辑器/字符串替换修改时，查找串必须按**单行转义形式**写（`...\n...`）；拿"多行真实换行"的文本去做多行匹配**永远不会命中**（而单看每一行又都能匹配，极易误诊）；
- 更稳的做法是用脚本改：`json.load` 读入（此时 content 才是真换行）→ 修改字符串 → `json.dump(..., ensure_ascii=False, indent=2)` 写回（indent=2 与本技能模板格式一致，语义无损）；
- 程序化批量修改后，务必再用 `check_card.py` 校验落定。

### 3.2 卡内 `character_book`（打包时由 §3.1 转换而来）

```jsonc
{
  "name": "世界书名称",
  "entries": [
    {
      "id": 0,                       // 数字，唯一；转换回 ST 格式时成为 uid
      "keys": [],                    // 对应 key
      "secondary_keys": [],
      "comment": "标题",
      "content": "内容",
      "constant": true,
      "selective": false,
      "insertion_order": 14720,      // 对应 order
      "enabled": true,               // 对应 !disable
      "position": "after_char",      // "before_char"|"after_char"（粗略位置）
      "use_regex": true,
      "extensions": {
        "position": 4,               // 精确位置用数字表（同 §3.1），优先于 position 字符串
        "exclude_recursion": true, "prevent_recursion": true,
        "display_index": 0, "probability": 100, "useProbability": true,
        "depth": 0, "selectiveLogic": 0, "role": 0,
        "group": "", "group_override": false, "group_weight": 100,
        "scan_depth": null, "match_whole_words": null, "use_group_scoring": false,
        "case_sensitive": null, "automation_id": "", "vectorized": false,
        "sticky": null, "cooldown": null, "delay": null,
        "match_persona_description": false, "match_character_description": false,
        "match_character_personality": false, "match_character_depth_prompt": false,
        "match_scenario": false, "match_creator_notes": false,
        "triggers": [], "ignore_budget": false
      }
    }
  ]
}
```

映射规则（`scripts/` 已实现）：`key→keys`、`comment→comment`、`content→content`、`constant→constant`、`order→insertion_order`、`disable→!enabled`、`position(数字)→extensions.position` 且 `before_char/after_char` 由数字 0/1 推导、其余字段按上表一一对应；`delay_until_recursion` 在卡内写作布尔。

**变量卡约定的条目组织**（照此命名，别自创）：

| 标题 | 位置 | 状态 | 内容要点 |
|---|---|---|---|
| `===变量开始===` / `===变量结束===` | before_char, 禁用 | 分隔条，方便肉眼组织 |
| `[initvar]变量初始化勿开` | before_char, **禁用** | YAML 初始变量值；MVU 按标题含 `[initvar]` 识别 |
| `变量列表` | @D0, 蓝灯启用 | `{{format_message_variable::stat_data}}` |
| `[mvu_update]变量更新规则` | @D0, 蓝灯启用 | 逐变量更新条件 |
| `[mvu_update]变量输出格式` | @D0, 蓝灯启用 | 固定的 JSONPatch 输出模板 |
| `===角色开始===` 等其余分隔条 | before_char, 禁用 | 正文档区隔 |

## 4. ST 正则脚本（`extensions.regex_scripts` 项）

```jsonc
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",  // UUID
  "scriptName": "[不发送]去除变量更新",             // 命名约定见 regex.md
  "disabled": false,
  "runOnEdit": false,
  "findRegex": "/<(update(?:variable)?)>(?:(?!.*<\\/\\1>)(?:(?!<\\1>).)*$|(?:(?!<\\1>).)*<\\/\\1?>)/gsi",
  "replaceString": "",                            // 替换内容；可为空串
  "trimStrings": [],
  "placement": [1, 2],                            // 1=用户输入 2=AI输出
  "substituteRegex": 0,                           // 0=不替换 1=原始 2=转义 3=两者
  "minDepth": null,                               // 深度自最新楼数起（0=最新）；见 regex.md 深度语义
  "maxDepth": null,
  "markdownOnly": false,                          // true=仅格式显示
  "promptOnly": true                              // true=仅格式提示词
}
```

- 导入 ST 的正则文件是**上述对象的 JSON 数组**（`[ {...}, {...} ]`）；ST 也接受带 `scripts` 包装的格式，但数组最通用。
- `findRegex` 是**字符串里的 JS 正则字面量**：`/pattern/flags`。多行用 `s`，全局用 `g`，忽略大小写 `i`。
- `替换内容` 中 `$1` 等反向引用照 JS `String.replace` 语义；写 JSON 时 `\\` 表示一个反斜杠。
- 卡内正则同样此格式（`extensions.regex_scripts`）。

## 5. 酒馆助手脚本条目（`extensions.tavern_helper.scripts` 项）

```jsonc
{
  "name": "变量结构",
  "id": "f65ab164-4268-4366-8228-16af904c2251",   // UUID
  "enabled": true,
  "type": "script",                                // 固定 "script"（还有 "folder"）
  "content": "import 'https://…/bundle.js';",      // 脚本代码，可含 ESM import
  "info": "",
  "button": { "enabled": true, "buttons": [] },    // 脚本库按钮（可选）
  "data": {},                                      // 脚本变量（默认随卡导出时清理）
  "export_with": { "data": true, "button": true }
}
```

- `content` 支持 `import 'https://…'`（脚本运行在 ES Module 环境）；内容**外面套一层 ``` 围栏会被酒馆助手自动剥离**（复制粘贴安全），但**不能是 JSON 导出格式**（`{"type":"script","content":"…"}` 原样注入会因语法错误不执行——实测有卡犯过此错，`check_card.py` 会检出）。
- 旧格式 `data.extensions.TavernHelper_scripts` 为数组、无 `type` 字段——不要在新卡中使用。

## 6. 常用校验点

打包/改卡后逐项检查（`check_card.py` 自动查大部分）：

1. `data.first_mes` 非空；`name` 非空。
2. `[initvar]` 条目 `disable: true`。
3. `变量列表` 的 `constant: true` 且含 `{{format_message_variable::stat_data}}`。
4. `[mvu_update]变量输出格式` 内容包含 `<UpdateVariable>` 与 `JSONPatch`。
5. 每个正则 `findRegex` 能被 JS 解析（`/…/flags` 字面量）。
6. 脚本数组里有且只有**一个** MVU 引入脚本 + **一个**变量结构脚本。
7. 世界书 `entries` 的 uid（或 character_book 的 id）无重复、无空洞引用。

## 7. 第三方扩展键清单与历史脚本格式（保真要点）

291 张语料卡的 `data.extensions` 出现过的键（除本技能已知的五件套外）：

| 键 | 来源 / 含义 | 处理 |
|---|---|---|
| `depth_prompt` | ST 自身的 @D 深度提示 | 透传（98% 的卡都有；本技能的 `extensions_extra` 自动携带） |
| `xiaobaix-tasks` / `xiaobaix-template` | 小白X 的模块数据（任务 / 沉浸式模板配置） | 透传 |
| `cfMvuVarGroups` | 第三方编辑器：变量组定义 | 透传 |
| `quick-response-force` | 卡管理工具：按卡保存的世界书条目启用状态（`apiSettings.disabledWorldbookEntries` 等） | 透传 |
| `QuickReply_Profile_V54` | 快速回复（QuickReply）相关配置 | 透传 |
| `cm_manager` / `luker` | 卡管理工具元数据（tags 等） | 透传 |
| `mvu_worldbook_name` / `source_owner` / `odysseia_trace` / `juqingtuijin` / `chub` | 各工具/平台的标记与元数据 | 透传 |

原则：**遇到不认识的键，一律原样保留**——它们多半是某个扩展/工具的状态，删掉会改变玩家侧行为（spec 层面 ST 也允许任意键）。本技能 extract→build 的 `extensions_extra` 机制已覆盖；用手工方式改卡时留意本表。

### 历史脚本存储格式（extract 已兼容，遇问题时可人工核对）

`tavern_helper` / `TavernHelper_scripts` 在野存在四种形态：

1. **现代**：`tavern_helper.scripts = [ {type:'script', name, content, ...}, {type:'folder', scripts:[…]} ]`
2. **Object.fromEntries 旧型**：`tavern_helper = [ ["scripts", [...]], ["variables", {...}] ]`（酒馆助手读卡时用 `Object.fromEntries` 兼容）
3. **嵌套脚本型**：`TavernHelper_scripts = [ {"type":"script","value":{id,name,content,info,buttons,data,enabled}}, … ]`
4. **名值对型**：`TavernHelper_scripts = [ [name, content], … ]`

`extract_card.py` 对四种都能拆出脚本；`check_card.py` 会提示需要人工处理的异常（如 JSON 包裹、localhost 残留）。
