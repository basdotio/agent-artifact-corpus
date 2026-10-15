---
name: sillytavern-card-maker
description: 为 SillyTavern（酒馆）制作与修改角色卡，尤其基于「酒馆助手(JS-Slash-Runner/TavernHelper) + MVU 变量框架(zod) + 提示词模板(ST-Prompt-Template/EJS) + 小白X」的高级变量卡：变量结构设计、世界书条目（变量列表/更新规则/输出格式/initvar）、酒馆正则（含闸门校验）、状态栏与交互式前端界面美化、创角/开局表单、内嵌脚本，并打包成含内嵌脚本/正则/世界书的完备角色卡（PNG/JSON），附带校验与玩家安装说明。只要用户提到酒馆、角色卡、写卡/做卡/改卡、MVU、变量卡、状态栏、前端界面、创角表单/开局表单、酒馆正则、酒馆助手、小白X、提示词模板、EJS 动态提示词，或要求把创意做成可导入 SillyTavern 的卡，就必须使用本技能。
---

# SillyTavern 角色卡制作

目标产物：一个**卡工程目录** + 由 `scripts/build_card.py` 打包出的**完备角色卡**——玩家只需导入一个 PNG/JSON，卡内已自带世界书、正则脚本和酒馆助手脚本；再安装两个开源扩展即可游玩（`酒馆助手`、`提示词模板`）。

## 技术栈四件套

| 组件 | 开源仓库 | 作用 | 谁需要安装 |
|---|---|---|---|
| 酒馆助手 (TavernHelper) | `N0VI028/JS-Slash-Runner` | 底座：在酒馆内运行脚本/前端界面、渲染消息中的 HTML 代码块为 iframe、提供 `getVariables`/`eventOn`/`injectPrompts` 等全套 API | 作者+玩家 |
| MVU 变量框架 (MagVarUpdate) | `MagicalAstrogy/MagVarUpdate` | 按楼层维护变量；解析 AI 输出里的 `<UpdateVariable>` 更新变量；自动在回复末尾附加 `<StatusPlaceHolderImpl/>` 占位符 | 作者+玩家（卡内嵌脚本自动引入） |
| 提示词模板 (ST-Prompt-Template) | `zonde306/ST-Prompt-Template` | 在提示词/世界书中用 EJS (`<%_ _%>`) 写条件逻辑，按变量动态发送提示词 | 作者+玩家 |
| 小白X (LittleWhiteBox) | `RT15548/LittleWhiteBox` | 另一套渲染+变量方案：代码块渲染、变量管理 2.0、小白板、剧情总结等 | 仅当用户点名小白X时 |

**默认技术栈**：酒馆助手 + MVU(zod) + 提示词模板（社区称"变量卡三件套"，示例卡与教程最完善）。只有用户明确要求"小白X"或其玩法需要小白X特性（剧情总结/小白板/OOC 四次元壁等）时，才走小白X路线；详见 `references/xiaobaix.md`。

## 工作流

### 0. 需求确认

先弄清（缺的可以问用户，但不要用一堆术语轰炸，用"玩法语言"问）：

1. **题材与玩法**：什么世界观、玩家扮演谁、核心乐趣是什么（恋爱养成 / 冒险 / 经营 / 系统流……）。
2. **变量需求**：需要记什么状态（好感度、时间、物品栏、任务、NPC……）。这决定一切，先想清楚。
3. **界面需求**：要不要状态栏？要不要可交互前端（点按钮买东西/接任务）？要不要**创角/开局表单**（填表选配置再开局，系统流卡几乎必备）？
4. **是否改现有卡**：是则用 `python scripts/extract_card.py <卡.png|json> <输出目录>` 先拆出卡内容再改（`card.json` 里自动生成的 `extensions_extra` 原样保留，重建时不会丢 `depth_prompt` 等字段）；改卡的维护流程与陷阱见下文「**修改与维护现有卡**」一章，动工前先读。

### 1. 建立卡工程目录

在会话工作区建立（`<卡名>` 用中文没问题）：

```
<卡名>/
├── card.json          # 角色卡本体字段（不含 extensions/character_book，打包时自动合并）
├── worldbook.json     # 世界书（ST 导入格式，含变量条目+正文档条目）
├── regex.json         # 酒馆正则数组（ST 导入格式；把 templates/regex-基础.json 与 regex-界面.json 合并成这一个文件）
├── scripts/           # 酒馆助手角色脚本，每个 .js 文件 = 一个脚本（文件名即脚本名）
│   ├── MVU.js         # 一行引入 MVU 本体
│   ├── 变量结构.js
│   └── ...
├── 界面/              # 可选：前端界面 HTML 源文件（供维护；打包时内联进正则）
│   └── 状态栏.html
├── tools/             # 可选：维护脚本（patch_*.py 幂等补丁、assemble_regex.py、audit_consistency.py、apply_cover_text.py），见「修改与维护现有卡」
├── meta.json          # 可选：{"scripts_disabled": [...], "script_buttons": {...}}
├── 说明.md            # 玩家安装/使用说明（用 templates/readme-template.md）
└── (底图.png)         # 可选：卡面图，打包 PNG 用
```

从 `templates/` 拷贝骨架再改，不要从零手写格式。

### 2. 内容构筑

角色卡字段、世界书正文档条目的写法与质量标准 → `references/content-craft.md`。

### 3. 变量体系（MVU zod）

顺序固定：**先想变量 → 写 schema → 写 initvar → 写三大变量提示词**。

1. `scripts/变量结构.js`：用 zod 4 写 `Schema` 并 `registerMvuSchema`。规则（幂等、`z.coerce.number()`、`z.record` 优于数组、`prefault`、用 `transform` 纠错而非拒绝……）→ `references/mvu.md`。
2. `worldbook.json` 中四个变量条目（名称与状态是硬接口，不能改名/改开关）：
   - `变量列表` — 启用，蓝灯，内容含 `{{format_message_variable::stat_data}}`
   - `[initvar]变量初始化勿开` — **必须禁用**（MVU 照样读取）
   - `[mvu_update]变量更新规则` — 按 schema 逐变量写更新条件
   - `[mvu_update]变量输出格式` — 固定模板（JSONPatch 格式），照抄 `templates/变量输出格式.yaml`
3. 多开局：在各 `alternate_greetings` 里用 `<UpdateVariable><initvar>…</initvar></UpdateVariable>` 块覆盖初始值。

### 4. 脚本

- `变量结构.js`（必需）：注册 schema。
- `MVU 引入`不需要单独文件——打包脚本会为 `scripts/` 里每个文件生成脚本条目；**MVU 本体的引入写成 `scripts/MVU.js`**，内容就一行 `import 'https://testingcf.jsdelivr.net/gh/MagicalAstrogy/MagVarUpdate/artifact/bundle.js';`。
- 可选：立即事件（`injectPrompts` + 世界书关键字联动）、事件监听（`Mvu.events.VARIABLE_UPDATE_ENDED` 纠错/回调）→ `references/mvu.md` 脚本节。

### 5. 正则

标准三件套 + 界面正则，模板在 `templates/regex-*.json`（改 id 即可用；组合规则见 `templates/README.md`）：

1. `[不发送]去除变量更新` — `仅格式提示词`，默认对所有楼层生效（`minDepth/maxDepth: null`）；若希望 AI 参考最近几楼的更新，改设 **`minDepth: 3`（或 4）**——深度自最新楼数起 0，写 `maxDepth` 会把方向弄反（历史坑点，见 `references/regex.md`）。
2. `[折叠]变量更新中` / `[折叠]完整变量更新` — `仅格式显示`，把更新块折叠成 `<details>`。
3. `[不发送]界面占位符` — `仅格式提示词`，把占位符从提示词中抹掉（不占 token）。
4. `[界面]状态栏` — `仅格式显示`，把占位符替换成前端界面（见下一步）。
5. （可选，推荐）`[闸门]变量块校验-放行` + `[变量]变量未更新警告` — 更新块缺失时给出可见提示；配套细节（READY 改名、数组顺序、界面正则配套改法）见 `references/regex.md` §⑥，模板 `templates/regex-闸门.json`。

正则字段语义、命名约定、语法坑 → `references/regex.md`。

### 6. 前端界面（前端美化）

三种档位，按需求选：

| 档位 | 做法 | 适用 |
|---|---|---|
| 纯文本状态栏 | 正则把占位符替换为 `💖 好感度: {{format_message_variable::stat_data.角色.好感度}}` | 最快 |
| 静态美化状态栏 | 占位符替换为 `<style>…</style><div>…宏…</div>` | 简单美化 |
| 交互式前端（推荐上限） | 占位符替换为 ```html 代码块，内含完整 `<head><body>`+JS：读变量、点按钮改变量、写"系统日志"变量供 AI 感知 | 游戏化玩法 |
| 创角/开场表单 | first_mes 放占位符 → `[开场]` 正则渲染 HTML 表单 → 提交（模拟发送或 `createChatMessages`）→ 协议条目让 AI 首轮 JSONPatch 初始化变量 | 系统流/经营/冒险卡（见 `references/opening-forms.md`） |

要点（细节 → `references/frontend.md`）：

- 前端以**消息内嵌 HTML 代码块**分发：代码块文本包含 `<head>`/`<body` 才会被酒馆助手渲染为无沙盒 iframe。默认**内联**进正则替换内容，卡自包含、不依赖 CDN 托管。
- iframe 里自带 `$`(jQuery)、`_`(lodash)、`z`(zod)、`toastr`、`Vue`、`YAML` 和全套 TavernHelper 函数；用 `await waitGlobalInitialized('Mvu')` 等 MVU 就绪，再用 `Mvu.getMvuData({type:'message', message_id: getCurrentMessageId()})` 读写本层变量，写完 `await Mvu.replaceMvuData(...)` 落盘。
- 玩家通过界面改变量时，把操作写进一个变量（如 `系统日志`），否则 AI 会看到"变量无故变化"并试图"修正"它。
- 样式规范：宽度自适应、禁用 `vh`/`min-height` 撑高、禁横向滚动条、深色浅色主题都要可读（用透明背景或自适应风格）。

### 7. 打包与自检

```bash
python scripts/check_card.py <卡工程目录>          # 先校验（也可校验成品卡）
python scripts/build_card.py <卡工程目录> --image 底图.png   # 无底图则只出 JSON
```

- `build_card.py` 把 `card.json` + `worldbook.json`（转成 `character_book` 内嵌）+ `regex.json` + `scripts/*.js` 合并为 `输出/<卡名>.json` 与 `.png`（`chara`/`ccv3` 两个 PNG 元数据块），另导出独立的 `世界书.json`、`正则.json` 备用。玩家导入卡后：世界书随卡自动建立；正则会在首次使用时弹窗询问是否启用（ST 的 scoped regex 机制）；酒馆助手脚本直接从卡读取。
- `check_card.py` 检查格式硬伤（字段缺失、变量条目名称/开关、`[initvar]` 未禁用、正则语法、脚本引用、JSON 结构），报错信息直接可修。

### 8. 交付说明

用 `templates/readme-template.md` 写 `说明.md`，必须包含玩家侧要求：
装 `酒馆助手` 与 `提示词模板` 两个扩展（酒馆助手在扩展面板按 URL 安装；提示词模板安装地址 `https://codeberg.org/zonde306/ST-Prompt-Template`），开启酒馆助手的渲染开关，并说明玩法与命令。

可选增强：挂一个 `自动安装插件` 脚本（`import 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/酒馆助手/自动安装插件/index.js'`），玩家缺依赖时弹窗一键安装；同类工具脚本（自动允许卡内正则、角色卡绑定预设等）见 `references/ecosystem.md`。发布前用 `check_card.py` 扫掉 localhost 等开发残留。

## 修改与维护现有卡（改卡是高频任务，比新建更容易翻车）

### 标准作业流程（每轮照做，清单见 `templates/维护检查清单.md`）

1. **备份**：先建 `备份-<主题>前/`，拷入将动的文件（card.json / worldbook.json / 说明.md / 相关 scripts、界面、tools）与 `输出/` 成品。
2. **写幂等补丁脚本**（`tools/patch_<主题>.py`），不要直接手改大 JSON：
   - 每条替换先 **assert 锚点恰好出现 1 次**，全部断言通过再落盘（改一半失败＝半坏状态）；
   - 脚本开头做幂等检查（检测到已打过则跳过），可安全重复运行；
   - worldbook 用 JSON 感知替换（load → 改 content → dump，保 CRLF）；card.json 用保形字符串替换（保原格式与结尾换行）；`界面/*.html` 改完后重跑 `tools/assemble_regex.py` 重组 regex.json。
3. **改完必跑**（顺序固定）：`check_card.py <工程>` → `build_card.py <工程> --image 底图.png` → `check_card.py 输出/<卡名>.json` → `tools/audit_consistency.py`（工程自带的扩展审计）。
4. **收尾**：版本号 +0.1；`说明.md` / creator_notes 同步；新机制往 audit 关键词表追加（防回归）。

### 锚点与格式陷阱（被坑过，先看再改）

- **全角/半角冒号**：中文文本里「不空转：」与「不空转:」是两个字符——锚点必须先从文件 dump 原文核对，勿凭记忆写。
- JSON 里换行是 `\n` 两个字符的转义；往 JSON 字符串插内容时注意写进去的是字面 `\n` 还是真换行。
- 分隔条等号按原文（`===世界设定结束===` 是 3 个等号）；uid 数字字符串键勿数错。
- 保持文件原行尾（CRLF/LF）、BOM、结尾换行习惯；dump 前后 diff 验证。

### 世界书条目增删的位置惯例

- 新条目插在分隔条「===世界设定结束===」（3 个等号；该条目 content 为空，分隔文字就在 comment 里）**之前**；分隔条 uid 让位重编（如 40→42），保持显示有序。
- uid 取空闲号；新条目字段集直接复制同位置同类型现成条目（constant / position / depth / role 一致），只改 uid、comment、content、order。

### 变体起点：优先做成开局，不要维护第二张卡

想做「另一条线 / 另一种起点」的变体时，**直接加 `alternate_greetings` 开局**（各自带完整 `<initvar>`），不要另开工程维护第二张卡——实测：独立变体卡最终被放弃、内容合并回主卡开局。开工前先问用户要哪种。

### 常驻 vs 关键词触发（省 token 的大头）

- **一次性/流程性条目**（如创角表单协议）不应常驻：改绿灯关键词触发（`key` 如 `["开局配置", "OpeningConfig"]`），提交表单后自动生效数轮，不再每轮占位（实测省约 1900 字/轮）。
- 转换时必须**补一个小的「兜底」常驻条目**，保住直启 / 老存档等边缘路径（如「未用表单直接开聊 → 用 [initvar] 默认值」，约 150 字）。
- 跨幕关系、长期状态相关的条目**必须常驻**，不能绿灯。

### 赘述体检与去重（`scripts/scan_duplicates.py`）

- 体检：行级精确查重 + 句级模糊查重（difflib ≥0.55），跨条目与条目内各扫一遍，附条目字数排行（常驻/条件分开）。
- 处理原则：**单一权威源 + 短指针**——数值只留「变量更新规则」、定义只留一个机制条目，其余改「见『XXX』」；**咒语型短指针**（如 `见「遭遇导演术」`）是执行锚点，只压短不删；例子与味道句不删；按节省字数排优先级执行。

## 关键纪律（都是机器消费的接口，错了不报错、只是静静地不工作）

- **条目名称里只有两个前缀是硬接口**：`[initvar]…`（MVU 靠名字识别初始值，且必须禁用）、`[mvu_update]…`（标记"只发给变量更新轮"的条目 = 支持额外模型解析模式）。其余名称（变量列表/更新规则/输出格式）是社区约定——实测卡会用 `[系统]当前变量情况`、`（EJS）MVU账本记录发送` 等自定义名，可接受，但别用 `get_message_variable` 旧宏。
- **变量列表是"内容"接口**：某个启用条目（推荐蓝灯 @D0）中必须含 `{{format_message_variable::stat_data}}`——名字不重要，内容才让 AI 每轮看到最新变量值。
- **输出格式固定为 `<UpdateVariable><Analysis/><JSONPatch/>` 结构**：照抄模板，改动等于让 AI 和 MVU 对不上码。
- **正则 `findRegex` 是 JS 正则字面量字符串**（如 `"/<update(?:variable)?>/gsi"`），字段名是英文（`scriptName`/`findRegex`/`replaceString`/`placement`/`markdownOnly`/`promptOnly`/`minDepth`/`maxDepth`）；`markdownOnly:true` = 仅格式显示，`promptOnly:true` = 仅格式提示词。
- **前端 HTML 必须含 `<body>` 或 `<head>` 标签**，否则酒馆助手不会渲染；且必须以 ``` 代码块包裹。
- **`_` 前缀变量 AI 不能更新；`$` 前缀变量对 AI 不可见**（两者都是 MVU/酒馆助手约定）：只给脚本/界面用的变量记得加前缀。
- **schema 每个字段都必须带兜底**（文本/数值 `.prefault(def)`，数值再加 `.catch(def)` 防 NaN）：字段缺失或非数字输入会让 zod 拒绝整次更新（玩家侧报「变量更新错误」）。新增字段必须与 initvar/开局 `<initvar>` 同步，并按 `references/mvu.md` §2.6 本地实测；initvar 里以 `{` 开头的值（如 `{{user}}`）必须加引号（否则 YAML 解析成对象 → `[object Object]`，见 §3.1）。
- **世界书 JSON 用 ST 格式**：`{"name": ..., "entries": {"<uid数字字符串>": {uid, key, keysecondary, comment, content, constant, disable, position(数字), order, depth, ...}}}`。`position` 数字表：0=Character Before，1=Character After，2=AN Top，3=AN Bottom，4=@D(指定深度)，5=EM Top，6=EM Bottom，7=Outlet。
- **卡 JSON 是 V2 (`chara_card_v2`) 结构**，变量相关内容全在 `data` 下；脚本在 `data.extensions.tavern_helper.scripts`，正则在 `data.extensions.regex_scripts`。打包脚本已处理。
- 修改现有卡前先 `extract_card.py` 拆包，改完再打包，不要凭空重写用户已有的卡；工程里 `card.json` 的 `extensions_extra`（承载 `depth_prompt` 等第三方扩展字段）**不要删**。
- 脚本内容可以带 ``` 围栏（会被自动剥离），但**不能是 JSON 导出格式**（`{"type":"script",…}` 整体粘贴会静默失效；`check_card.py` 会检出）。

## 参考索引

| 文档 | 何时读 |
|---|---|
| `references/ecosystem.md` | 需要解释组件分工/安装方式/版本要求/依赖来源，或要在酒馆助手与小白X之间做选型 |
| `references/card-format.md` | 要手改卡 JSON、PNG 元数据、世界书格式、字段映射时 |
| `references/mvu.md` | 写变量结构(schema)、initvar、三大变量提示词、变量更新相关脚本与调试 |
| `references/regex.md` | 写/改正则，理解 placement、仅格式显示/提示词、命名约定与写法坑 |
| `references/prompt-template.md` | 用 EJS 写动态提示词/分阶段人设/绿灯预处理 |
| `references/frontend.md` | 写状态栏/交互界面、iframe 环境 API、样式规范、分发方式、结构化消息协议与按钮模式 |
| `references/opening-forms.md` | 做创角/开局表单：占位符体系、三种提交通道、协议条目写法 |
| `references/xiaobaix.md` | 走小白X路线：代码块渲染开关、变量管理 2.0、小白板、与酒馆助手混用注意 |
| `references/content-craft.md` | 写角色设定/世界书内容/开场白，追求"能卖"的叙事质量 |
| `references/adult-events.md` | 制作/修改含成人情节的卡：演出时长控制、事件构成与边界、触发密度、计分护栏、镜头聚焦、事件库模式、用词条款、主角人设与人称策略 |
| `references/cover-art.md` | 做/换卡面图：封面工作流（裁水印、文字叠层、rebuild 校验）、PIL 文字重影顺序坑、受限平台图像生成分诊与尺度边界 |

## 常见故障速查

| 症状 | 排查 |
|---|---|
| 变量没初始化 | `[initvar]` 条目名没含 `[initvar]` / 没禁用？开局消息有没有 `first_mes`？新开聊天才生效 |
| 日志"变量结构注册失败" | schema 脚本报错，看「酒馆助手的日志查看器」里 `【脚本|变量结构】` 开头的报错 |
| 变量更新报错（toastr/日志「变量更新错误」） | schema 字段缺兜底：新增字段没 `.prefault(def)`（旧存档缺键即炸）；数值字段收到非数字字符串得到 NaN、zod 在 transform 前就拒绝 → 需 `.catch(def)`。把两种兜底打包进 helper，并本地跑 schema 实测——见 `references/mvu.md` §2.5/§2.6 |
| 某变量显示成 `[object Object]`（如姓名） | initvar 里该值以 `{` 开头（如 `{{user}}`）被 YAML 解析成 flow mapping → 加引号：`姓名: '{{user}}'`。见 `references/mvu.md` §3.1 |
| AI 不更新变量 | `变量列表`/`[mvu_update]变量输出格式` 条目没启用，或没在 D0 深度注入 |
| 状态栏不显示 | 占位符正则没启用？酒馆助手渲染开关没开？HTML 缺 `<body>`/`<head>`？加了闸门后请检查：界面正则要匹配 READY 且排在闸门之后 |
| AI 总是不输出更新块 | 加「变量输出格式强调」或「强制结尾输出」条目（`templates/`，蓝灯 @D0） |
| 你本地正常、玩家那边界面/脚本失效 | 检查卡内是否残留 localhost/开发地址导入（`check_card.py` 会警告）；玩家缺扩展时可用「自动安装插件」脚本引导 |
| 更新块大量出现在提示词 | `[不发送]去除变量更新` 正则的 `promptOnly` 没勾，或深度设置写反（应 null/null 或 minDepth，别用 maxDepth） |
| 玩家导入卡后无正则 | 首次弹窗"允许该角色的正则脚本"被拒绝 → 扩展设置→正则→重新允许 |
| 改完卡却发现成品没变化 | 忘记重新打包：`build_card.py` 才会更新 `输出/`；改世界书/正则/脚本/底图后必须重建 |
| 补丁脚本锚点找不到（count=0） | 全角/半角冒号、等号数量、JSON 转义差异——先从文件 dump 原文再定锚点，勿凭记忆写 |
| 新机制改动后担心静默回归 | 每加机制就往 `tools/audit_consistency.py` 的 KEYWORDS 追加一条，成品抽查会连带校验 |
| 图像生成报 internal server error | 先用无害提示词对照测试分诊：能出图＝内容审核（走单变量降级法）、也报错＝服务波动稍后重试；详见 `references/cover-art.md` |
| 玩家反馈「事件两三句就结束 / 围观群众抢戏 / 数值随演出膨胀」 | 成人卡演出系统的三个经典缺陷，配方见 `references/adult-events.md` |

更详细的排错（含日志文本对照）见 `references/mvu.md` 的诊断节与 `references/ecosystem.md`。
