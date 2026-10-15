# MVU 变量框架（zod 版）完整指南

## 1. 工作原理

MVU 是挂在酒馆助手上的脚本，变量按**消息楼层**存放：

```
楼层变量 = { stat_data: { …你的变量… }, display_data: …, delta_data: …, initialized_lorebooks: … }
```

一次交互的生命周期：

1. **新开聊天**：MVU 扫描启用世界书中标题含 `[initvar]` 的条目（含禁用的），把 YAML/JSON/TOML 解析后 merge 进 `stat_data`；若开局消息里有 `<initvar>…</initvar>` 块，则用开局块（**完全覆盖**保底条目）。
2. **用户输入 / AI 回复**：MVU 解析文本里的 `<UpdateVariable>` 块中的更新命令，按顺序应用到变量，每次应用后用**变量结构（schema）**校验与纠错。
3. 更新完成后触发事件（`VARIABLE_UPDATE_ENDED` 等），最后把变量写入该楼层；AI 回复的末尾会自动补 `<StatusPlaceHolderImpl/>` 占位符（供正则做界面）。

两种更新方式（MVU 设置里切换）：

- **随 AI 输出**（默认）：更新命令写在正常回复末尾的 `<UpdateVariable>` 块里。
- **额外模型解析**：MVU 在回复后另发一次生成请求专门做变量更新；此时标题带 `[mvu_update]` 的条目**只发给更新轮**、普通轮次不发；卡里存在 `[mvu_update]` 条目本身就是"本卡支持额外模型解析"的标志。不改设置时按默认规划即可，两种方式都要按本节格式写卡。

  （实测多张线上卡把这类条目命名为 `[MVU]变量更新规则` 等自定义名——随 AI 输出模式完全可用，只是放弃"额外模型解析"模式。加不加前缀是作者选择：想要该模式就必须加。）

  另有 **`[mvu_plot]` 前缀**（291 张语料卡中 15 张使用）：与 `[mvu_update]` 相反——**普通轮发送、更新轮移除**（MVU 源码逻辑：额外调用时删 `[mvu_plot]` 留 `[mvu_update]`，普通轮反之）。适合"只在正文轮需要、不该干扰变量更新判断"的剧情向提示词。

## 2. 变量结构脚本（schema.js）

内容 = `import` 注册工具 + `export const Schema = z.object({…})` + 结尾注册。必须是一个酒馆助手脚本（文件名如 `变量结构.js`，打包后名为 `变量结构`）。

```js
import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';

export const Schema = z.object({
  世界: z.object({
    当前时间: z.string(),
    当前地点: z.string(),
  }),
  白娅: z.object({
    依存度: z.coerce.number().transform(v => _.clamp(v, 0, 100)),
  }),
});

$(() => {
  registerMvuSchema(Schema);
});
```

### 2.1 环境与总原则

- 可用全局：`z`（**zod 4**）与 `_`（lodash），**不要 import 它们**，直接用。
- CDN 镜像：`testingcf.jsdelivr.net` / `gcore.jsdelivr.net` / `cdn.jsdelivr.net` 都在实测卡中使用，任选其一即可；固定分支（`@master`、`@beta`）与默认分支（不加）写法都常见。
- **幂等**：schema 用于解析增量更新，必须满足 `Schema.parse(Schema.parse(x)) === Schema.parse(x)`（transform 必须是"收敛"的）。
- 纠错优先于拒绝：AI 难免输出越界值。与其让更新整体失败，不如 `transform` 修正。只有当用户明确要求时才用 `.min/.max` 这类"拒绝式"约束。
- 顶层必须是 `z.object({...})`；不在里面定义额外中间变量（AI 和你都难维护）。

### 2.2 类型选择速查

| 场景 | 写法 |
|---|---|
| 数字 | `z.coerce.number()`（永远不用裸 `z.number()`，AI 常把数字写成字符串 `"5"`） |
| 整数 | `z.coerce.number().int()` |
| 文本 | `z.string()` |
| 真假 | `z.boolean()`（不要 `z.coerce.boolean()`） |
| 固定几个取值 | `z.enum(['进行中', '已完成'])` |
| "数字或待初始化" | `z.coerce.number().or(z.literal('待初始化'))` |
| 固定格式文本 | 优先 `z.templateLiteral([...])`，少用正则 |
| 键固定的对象 | `z.record(z.enum(['上装','下装',…]), 值类型)`（键必须都有） |
| 键可缺省 | `z.partialRecord(z.enum([...]), 值类型)` |
| 动态键对象（物品栏/NPC） | `z.record(z.string().describe('物品名'), z.object({…}))` |
| 必有键+可扩展 | `z.intersection(z.object({必有键...}), z.record(z.string(), 值类型))` |
| 默认值 | `.prefault(值)`（新字段缺失时填充）；**不要用 `z.default`** |
| 可整体清除的子对象 | `z.object({…}).prefault({})`（配合 JSONPatch remove 兼容） |

### 2.3 transform 纠错模式（最常用）

```js
依存度: z.coerce.number().transform(v => _.clamp(v, 0, 100)),
数量: z.coerce.number().prefault(1),                 // 缺省数量=1
物品栏: z.record(z.string(), z.object({
  描述: z.string(),
  数量: z.coerce.number().prefault(1),
})).transform(data => _.pickBy(data, ({ 数量 }) => 数量 > 0)),   // 数量≤0 自动移除
称号: z.record(z.string(), z.object({…})).transform(data =>
  _(data).entries().takeRight(Math.ceil(_.get(_, '…')  /* 依另一变量取数见下 */)).fromPairs().value()),
```

- **transform 只能拿"解析后的值"**，签名为 `(value) => newValue`，不要用第二个参数（context）。
- 跨字段依赖（如"称号数量上限 = ceil(依存度/10)"）放在该对象自己的 transform 里，数据中已含兄弟字段（见示例：`data.依存度`）。
- 想记录插入顺序并"保留最新的 N 个"：`_(data).entries()` 保持插入序，`takeRight(N)` 取最新。
- 需要"首次时间戳"之类的排序：`$time: z.coerce.number().prefault(() => Date.now())`。
- 禁止使用不存在的 API：`z.passthrough`、`z.strict`、`z.extend` 不能用在已被 `.prefault({})` 包裹的对象上。

### 2.4 `_` 与 `$` 前缀

| 前缀 | 效果 | 典型用途 |
|---|---|---|
| `_变量` | AI 能看到，但**更新会被 MVU 忽略** | 只允许脚本/界面改的状态 |
| `$变量` | AI **完全看不到**（不进 `{{format_message_variable::stat_data}}`），但可被 AI 更新命令命中 | 脚本内部的开关/日志（此时建议同时用 `_` 或干脆让 AI 不知道有它） |

### 2.5 ★字段兜底纪律：prefault + catch（血泪教训）

zod 对象里**没有兜底的字段一旦缺失，parse 直接失败**——玩家侧表现 = toastr/日志报「变量更新错误」、该次更新被整体拒绝。三种必踩场景：

1. **新增字段后，旧存档（老聊天）里没有这个键** → parse 失败；
2. **AI 初始化/更新时漏写某个键**（指望 AI 每次写全所有字段是不现实的）→ parse 失败；
3. **`z.coerce.number()` 收到非数字字符串**（如 `"abc"`）会得到 **NaN，而 zod 在进入你的 transform 之前就拒绝 NaN**——"在 transform 里判 NaN 兜底"来不及，必须 `.catch(def)`。

正确姿势：把兜底**打包进 helper**，全字段免漏——

```js
// 文本：缺失、空串、"undefined"/"null" 字符串一律回退默认值
const normText = def =>
  z.coerce.string()
    .transform(s => { const t = String(s ?? '').trim(); return (t && t !== 'undefined' && t !== 'null') ? t : def; })
    .prefault(def);

// 数值：越界取整 + 字段缺失回退 + 非数字（NaN/类型错）回退
const clampNum = (def, min, max) =>
  z.coerce.number()
    .transform(v => (Number.isFinite(v) ? Math.min(max, Math.max(min, Math.round(v))) : def))
    .catch(def)      // 校验错误（NaN 等）兜底
    .prefault(def);  // 字段缺失兜底

// 计数：非负整数
const clampCnt = z.coerce.number().transform(v => (Number.isFinite(v) ? Math.max(0, Math.round(v)) : 0)).catch(0).prefault(0);
```

- `.prefault()` 在所有节点上都可链（包括 `.transform()` 之后），放链尾即可；`.catch()` 加在 transform 之后、prefault 之前；
- 固定键对象用 `z.partialRecord(z.enum([...]), 值)`（缺键容忍）而非 `z.record(...)`（全键强制，AI 部分更新会炸）；
- **新增字段 checklist**：① helper/schema 补兜底 → ② initvar 与每条 `<initvar>` 块同步 → ③ 按 §2.6 实测通过才算完。

### 2.6 本地实测 schema（打包前强烈建议）

schema 逻辑可以完全脱离酒馆在本地验证（最小方案，实测可用）：

```bash
mkdir _schema_test && cd _schema_test && bun add zod
```

把 `变量结构.js` 里的 helper 与 Schema 粘进 `test.mjs`（顶部把全局 z 换成 `import { z } from 'zod';`），至少覆盖这些输入后全绿再打包：

- `Schema.parse({})` —— 全字段缺失（老存档/初始化兜底）；
- 部分字段 + 字符串数字（`堕落: '35'`）；
- 怪输入（`'abc'` / `{}` / `Infinity`）—— 验证 catch 链；
- 越界值（150 / -20）；
- 幂等（`parse(parse(x))` 与 `parse(x)` 一致）。

进阶（本技能实战）：把 schema 抽成 `schema.mjs` 单一来源，让单元测试与一个 **verify.mjs**（读取真实 worldbook.json / card.json，把每个 [initvar] 与开局 `<initvar>` 块 YAML 解析后走一遍 `Schema.parse`，查报错、被丢弃的键与异常值）共用同一份 schema——这一类脚本能拦住绝大多数"玩家试玩才发现变量更新报错"的问题。

## 3. 初始化变量（initvar）

### 3.1 保底条目（对所有开局生效）

世界书新建条目，**标题含 `[initvar]` 且必须禁用**（如 `[initvar]变量初始化勿开`），内容为 YAML：

```yaml
世界:
  当前时间: 2025-04-07 08:42
  当前地点: 私立星见学园·2年A班教室
白娅:
  依存度: 15
主角:
  物品栏:
    旧手帕:
      描述: 角落绣着歪歪扭扭小兔子的手帕
      数量: 1
```

写法要点：

- 缩进层级与变量结构一一对应（可让 AI 读 schema.json/更新规则生成）。
- **不要**使用旧式 `变量: [值, 描述]` 写法；不要用 `{{宏}}` 作为变量名（用"主角"而不是 `{{user}}`）。
- 节点内容会被 MVU 用 YAML→JSON5→TOML 顺序解析，任一失败都会报错。
- **★含特殊字符的值必须加引号**：以 `{` 开头的值（如 `{{user}}`）会被 YAML 解析成 **flow mapping**——`YAML.parse("姓名: {{user}}")` 得到 `{"姓名":{"{ user }":null}}`，再经 schema 的 String() 变成 `[object Object]`。正确写法：`姓名: '{{user}}'`（单引号 = 字面字符串）。同理建议加引号的：含 `: `（冒号＋空格）、以 `#`/`&`/`*`/`!` 开头、含 `[`/`]`/`,` 的值。

### 3.2 按开局设置（覆盖保底）

在开局消息（`alternate_greetings` 的每个开局 / 或 `first_mes`）末尾追加：

```
<UpdateVariable>
<initvar>
（该开局的完整 YAML 初始值）
</initvar>
</UpdateVariable>
```

- 有 `<initvar>` 的开局**完全忽略** `[initvar]` 保底条目；没有的则用保底。
- 外层 `UpdateVariable` 包裹是为了让 `[不发送]去除变量更新` 正则顺手把它们从提示词里清掉。
- 增量方案（可选）：开局里也可直接写 `_.set('世界.当前时间','…')` 这类单条命令，只改需要差异的部分（MVU 旧式语法仍被支持）。

## 4. 三大变量提示词

### 4.1 变量列表（让 AI 看到最新变量）

条目 `变量列表`：蓝灯（constant）、位置 @D0（position=4, depth=0, role=system）、启用。内容：

```text
---
<status_current_variable>
{{format_message_variable::stat_data}}
</status_current_variable>
```

- `{{format_message_variable::…}}` 是酒馆助手的宏：发送给 AI 时替换为变量值，**且显示楼层时同样替换**（状态栏纯文本方案也用它）。
- 变量是逐楼更新、条目每轮重发，因此 AI 总能看到"截止上一楼"的最新值。
- 想只列部分变量/控制 token：可以改写为只引用子路径（如 `{{format_message_variable::stat_data.白娅}}`），或把不重要的变量加 `$` 前缀。
- 想更省 token 可用 EJS 重排（见 prompt-template.md）。
- **条目名不是硬接口**：实测卡里这条常被命名成 `[系统]当前变量情况`、`[MVU]当前系统变量状态`、`（EJS）MVU账本记录发送`，或直接并入其他条目——MVU 只识别 `[initvar]`/`[mvu_update]` 前缀；真正的要求是"一个启用条目（约定蓝灯、@D0）里含 `{{format_message_variable::stat_data}}`"。用 EJS 自定义快照输出时，记得过滤 `$` 前缀键与 MVU 的元数据键 `$__META_EXTENSIBLE__$`。

### 4.2 变量更新规则（教 AI 怎么改）

条目 `[mvu_update]变量更新规则`：蓝灯、@D0、启用。为每个（组）变量写"何时更新、更新成什么"。

```yaml
---
变量更新规则:
  世界:
    当前时间:
      format: YYYY-MM-DD HH:MM        # 可选：格式要求
    近期事务:
      type: |-
        { [事务名: string]: string; }  # 动态键对象用 TS 索引签名
      check:
        - 记录任务、约定、重要事件；完成后移除
        - 最多保持 5-8 项
  白娅:
    依存度:
      type: number
      range: 0~100
      check:
        - 角色察觉到 <user> 行为时按态度 ±(3~6)
        - 单次不超过 ±6
    着装.${上装|下装|内衣|袜子|鞋子|饰品}:   # 固定键合并书写
      check:
        - 换装、衣物损坏、特殊场合时更新
    称号:
      type: |- 
        { [称号名: string]: { 效果: string; 自我评价?: string; } }
      check:
        - 重要行为/心理变化时获得；关键词 '待评价' 应尽快补全
        - 数量上限 ceil(依存度/10)，超出移除最早的
```

写作规范（决定 AI 的服从率）：

- 同规则的固定键合并：`主角.能力面板.${力量|敏捷|体质|智力|感知|魅力}`；string 类型省略 `type` 字段。
- 动态键对象把 `type` 写为带索引签名的 TS 块；可在注释里说明字段含义。
- `check:` 每条一句话，可用 `±(3~6)`、`仅当……` 等措辞；不要穷举所有旁支情况。
- `_` 前缀变量不要写更新规则（AI 改了也无效）。
- 规则自身也是"提示词"：不写清 = AI 自由发挥；写得过细 = 烧 token 且僵化。以"能覆盖 90% 剧情走向"为度。

### 4.3 变量输出格式（固定模板，照抄）

条目 `[mvu_update]变量输出格式`：蓝灯、@D0、启用。内容固定为（这就是新式 JSONPatch 格式）：

```text
---
变量输出格式:
  rule:
    - you must output the update analysis and the actual update commands at once in the end of the next reply
    - the update commands works like the **JSON Patch (RFC 6902)** standard, must be a valid JSON array containing operation objects, but supports the following operations instead:
      - replace: replace the value of existing paths
      - delta: update the value of existing number paths by a delta value
      - insert: insert new items into an object or array (using `-` as array index intends appending to the end)
      - remove
      - move
    - don't update field names starts with `_` as they are readonly, such as `_变量`
  format: |-
    <UpdateVariable>
    <Analysis>$(IN ENGLISH, no more than 80 words)
    - ${calculate time passed: ...}
    - ${decide whether dramatic updates are allowed as it's in a special case or the time passed is more than usual: yes/no}
    - ${analyze every variable based on its corresponding `check`, according only to current reply instead of previous plots: ...}
    </Analysis>
    <JSONPatch>
    [
      { "op": "replace", "path": "${/path/to/variable}", "value": "${new_value}" },
      { "op": "delta", "path": "${/path/to/number/variable}", "value": "${positive_or_negative_delta}" },
      { "op": "insert", "path": "${/path/to/object/new_key}", "value": "${new_value}" },
      { "op": "insert", "path": "${/path/to/array/-}", "value": "${new_value}" },
      { "op": "remove", "path": "${/path/to/object/key}" },
      { "op": "move", "from": "${/path/to/variable}", "to": "${/path/to/another/path}" }
    ]
    </JSONPatch>
    </UpdateVariable>
```

- 更新块出现在回复**末尾**；`<Analysis>` 用英文、≤80 词，是"先想再改"的提示词工程手段。
- 路径从 `stat_data` 内部开始（顶层变量直接 `/世界/当前时间`）。
- 兼容旧式：`_.set('白娅.依存度', 35);//理由` 命令 MVU 仍能解析，但新卡一律用 JSONPatch。
- 输出协议可以更细：有的卡明确要求 `正文 → <StatusPlaceHolderImpl/> → <UpdateVariable>…`（占位符在更新块之前）——闸门正则兼容两种顺序（见 regex.md §⑥）。

### 4.4 输出纪律强化（AI 不肯输出更新块时）

两个实测有效的补丁条目（模板：`templates/变量输出格式强调.yaml`、`templates/强制结尾输出.yaml`；均蓝灯 @D0）：

- **变量输出格式强调**（轻量）：追加 `rule: The following must be inserted to the end of reply, and cannot be omitted` + 格式骨架，提醒模型别省略。
- **强制结尾输出**（重装）：声明"最高优先级",要求"**即使本轮没有任何变量变化，也必须输出 `<JSONPatch>[]</JSONPatch>`**"、"回复最后一个字符必须是 `</UpdateVariable>`"、"禁止以台词/场景/状态栏结尾"。适合输出纪律差的模型或预设。

## 5. 与变量有关的脚本模式

前置永远是：

```js
await waitGlobalInitialized('Mvu');
```

### 5.1 读写变量

```js
// 读（楼层号支持负数：-1 最新、-2 倒数第二；前端界面里用 getCurrentMessageId()）
const variables = Mvu.getMvuData({ type: 'message', message_id: -1 });
const stat = _.get(variables, 'stat_data');

// 改并落盘
_.update(variables, 'stat_data.白娅.依存度', v => v + 5);
await Mvu.replaceMvuData(variables, { type: 'message', message_id: -1 });

// 解析一段含更新命令的文本（如 generate 的返回值，不产生楼层所以需自行解析）
const new_data = await Mvu.parseMessage(text, variables);
```

### 5.2 事件钩子

| 事件 | 用途 |
|---|---|
| `Mvu.events.COMMAND_PARSED` | 拿到解析出的更新命令并修复（如把中文间误加的 `-` 去掉、繁体转简体） |
| `Mvu.events.VARIABLE_UPDATE_STARTED` | 更新开始 |
| `Mvu.events.VARIABLE_UPDATE_ENDED` | 拿到 `(new_variables, old_variables)`：纠错、跨楼限制变动幅度、检测阈值突破弹提示、强制回滚某变量 |
| `Mvu.events.BEFORE_MESSAGE_UPDATE` | 写入楼层前最后处理 |

```js
await waitGlobalInitialized('Mvu');
eventOn(Mvu.events.VARIABLE_UPDATE_ENDED, (new_variables, old_variables) => {
  const old_v = _.get(old_variables, 'stat_data.白娅.依存度');
  const new_v = _.get(new_variables, 'stat_data.白娅.依存度');
  if (old_v < 30 && new_v >= 30) toastr.success('白娅的依存度突破了 30！');
});
```

### 5.3 用变量联动世界书（立即事件模式）

`injectPrompts` 把变量状态转成"只用于激活绿灯的文本"或直接注入 Dn 提示词：

```js
await waitGlobalInitialized('Mvu');
eventOn(Mvu.events.VARIABLE_UPDATE_ENDED, variables => {
  const v = _.get(variables, 'stat_data.白娅.依存度');
  injectPrompts([{
    id: '激活-白娅阶段',              // 同 id 会覆盖旧注入
    content: `白娅阶段${v < 20 ? '一' : v < 60 ? '二' : '三'}`,  // 绿灯关键字就写"白娅阶段一"
    position: 'none', depth: 0, role: 'user', should_scan: true,  // position:'none'=只参与激活，不进提示词
  }]);
});
```

或在注入时用 `filter` 按变量条件决定是否注入某段内容（世界书条目用 `【【事件名】】` 作为关键字）。

### 5.4 健壮性模式（发布卡的加分项，实测卡做法）

- **健壮加载版变量结构**：等待 `z` 就绪（最长 120 秒）→ try/catch 动态 import `mvu_zod.js` → 全程 `toastr`+`console` 双通道上报失败。避免"脚本静默失效、玩家不知道"。模板：`templates/变量结构-健壮版.js`。
- **变量自愈**：在脚本里读取当前楼层/聊天变量，把 schema 的默认值 merge 回去（缺字段的旧存档自动补全，4 秒后可再跑一次兜底）。
- **阈值单一事实来源**：把分档/门槛只定义在脚本里，并写入变量（如 `系统.阈值`）供世界书 EJS 与状态栏读取；再用 EJS 版变量列表把这类"内部字段"从 AI 视野里剔除（配合下文过滤写法）。
- **EJS 兜底修复条目**：一条提示词模板条目——正常游玩时渲染为空（零 token 占用），只有当变量结构缺失时才向 AI 输出一段修复性 JSONPatch 指令（实测卡做法）。

## 6. 诊断清单

| 现象 | 定位 | 处理 |
|---|---|---|
| 日志无 `【脚本|变量结构】变量结构注册成功` | schema 脚本错误 | 复制日志中 `【脚本|变量结构】` 全部报错让 AI 修 |
| 日志出现 `【脚本|MVU】发生变量更新错误` | schema 解析不了某个更新 | 看报错里的路径与值，补 transform/prefault |
| 日志 `【脚本|变量结构】变量初始化失败` | initvar 不是合法 YAML/JSON | 修 YAML 缩进/引号 |
| 变量管理器看不到变量 | 没新开聊天 / 没设第一条消息 / 插件缺失 | 新开聊天；确认卡有 `first_mes` |
| AI 很少输出更新块 | 变量条目没启用或没在 D0 | 检查三条目 constant+position |
| 更新块出现在给 AI 的提示词里 | 缺 `[不发送]去除变量更新` 正则 | 导入正则并检查 promptOnly 与深度设置（默认应为 null/null） |

查看工具（都在酒馆输入框左侧魔棒）：**日志查看器**、**变量管理器**（可手改变量、复制变量 JSON——做 `<initvar>` 时很好用）、**提示词查看器**。

## 7. 变量设计思路（写卡第一步）

先问"这张卡的乐趣需要**记住**什么"：

- 恋爱养成：好感度（+阶段）、关系状态、纪念事件 → 配合分阶段人设（EJS）。
- 冒险/系统流：时间地点、背包、能力面板、任务清单、货币。
- 经营/商店：库存、价格、玩家购买记录（配合前端界面点单）。
- 悬疑/剧情：线索收集、NPC 生死、章节进程（配合 `_`/`$` 前缀管理隐藏状态）。

设计纪律：

1. 变量分层：`世界 / 主角 / 各角色 / 系统`，避免顶层平铺。
2. 每个变量都想清楚：**取值范围、更新时机、初始值**（= 更新规则三要素）。
3. 只给"AI 需要感知"的变量不加前缀；脚本内部数据用 `$`/`_`。
4. 变量名用中文、无宏、稳定（改变量名等于迁移整张卡）。
