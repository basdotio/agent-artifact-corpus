# 创角 / 开场表单（Opening Form）完整指南

游戏化卡（系统流、经营、冒险）的标配：开局先让玩家**填表创建角色/选配置**，再进入正式剧情。实测 6 张线上卡中有 4 张使用（最成熟的一份含存档系统）。

## 1. 架构总览

```
first_mes 只放占位符（或一段"游玩指南"）
   ↓ 显示时被 [开场]/[替换] 正则替换
HTML 表单（内联在正则替换内容里，渲染为 iframe）
   ↓ 玩家填写、点击提交
结构化用户消息（【开局配置】+ <OpeningConfig> 数据块）
   ↓（DOM 写入输入框并发送 / SDK 建楼）
世界书"协议条目"教 AI 如何消费
   ↓ AI 首轮回复
用 JSONPatch 完整初始化变量 + 生成开局剧情
```

## 2. 第一步：让开场消息变成占位符

- 主 `first_mes` 从一行占位符开始，例如 `<TentacleReady>`、`<HkmOpeningSetup/>`、`<GuPCreatorImpl/>`、`[游玩指南]`；其余 `alternate_greetings` 照常写完整文案（给不想创角的玩家直接开局）。
- 对应正则：`[开场]…` / `[替换]…`，**仅格式显示**（markdownOnly），placement `[2]`（若表单也用于替换用户消息则加 `[1]`），替换内容 = 完整 HTML 表单（`templates/创角表单骨架.html`）。
- **两段式**（可选）：第一条开场是"游玩指南 + 一个【开始创建】按钮"——玩家点按钮把 `[开始创建]` 作为用户消息发出，第二条正则（`maxDepth: 1`，只在最新楼层渲染）把 `[开始创建]` 替换为真正的表单。适合想让玩家先读规则再创角的卡。

## 3. 表单实现要点

- 起点：`templates/创角表单骨架.html`（已含"查找宿主输入框 + 提交"的完整逻辑）。
- 样式与自适应规范与 `frontend.md` §7 相同（无 `vh`、宽度自适应、深浅主题可读）。
- 表单运行在消息 iframe 内：**DOM 查找要走出 iframe**：

```js
function findRoot() {
  let w = window;
  try {
    while (w.parent && w.parent !== w) {
      const d = w.parent.document;
      if (d && d.getElementById('send_textarea')) { w = w.parent; break; }
      w = w.parent;
    }
  } catch (e) { /* 跨域保护 */ }
  const d = w.document;
  return { ta: d.getElementById('send_textarea'), sendBtn: d.getElementById('send_but') };
}
```

## 4. 三个提交通道

### A. 模拟玩家发送（最通用，推荐）

```js
const { ta, sendBtn } = findRoot();
const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
if (setter) setter.call(ta, text); else ta.value = text;
ta.dispatchEvent(new Event('input', { bubbles: true }));  // 关键：让酒馆感知内容变化
sendBtn.click();
```

要点：直接 `ta.value = text` 在某些前端框架下不会触发状态同步——**用原生 setter + 派发 `input` 事件**（实测卡做法）。

### B. SDK 建楼（酒馆助手环境）

```js
await createChatMessages([{ role: 'user', message: text, data: { /* 可选元数据 */ } }]);
await triggerSlash('/trigger');   // 立刻触发 AI 生成
```

适合需要"**立刻生成**、不等玩家操作"的流程（如创角后自动开局）；配合 `getVariables({type:'chat'})` 可以做存档（实测卡用 localStorage 存档银行 + 变量 pending 标记恢复中断的创角）。注意校验接口可用性并对失败给出提示。

### C. 直接写变量（不经过 AI）

难度、辅助开关、昵称这类**确定性数据**：表单直接 `Mvu.replaceMvuData` 写进楼层变量，再让玩家正常发送第一条消息。比"让 AI 转写"更可靠，省一轮生成。

**组合建议**：确定性字段（姓名/性别/难度）→ C 直接写变量；需要叙事发挥的部分（出身故事/开局场景）→ A/B 交给 AI。

## 5. 协议条目：教 AI 消费提交内容

提交消息里带结构化数据块，例如：

```
【开局配置】
<OpeningConfig>
姓名: 夏美
性别: 女
天赋: 天才
难度: 困难
</OpeningConfig>
请以上述配置为我生成开局：先完整初始化变量（JSONPatch），再从适合的时机切入剧情。
```

配一条蓝灯 @D0 世界书条目（可命名 `[mvu_update]自定义开局更新指令`）：

```yaml
---
自定义开局更新指令:
  触发条件: 用户消息包含 <OpeningConfig>
  执行:
    - 按配置完整初始化以下变量（**禁止使用 <initvar>，必须用 JSONPatch**）：
      - 用 replace 覆盖完整顶层对象：/世界 /主角 /系统
      - 各对象必须一次性给出完整结构，禁止用 insert 逐个添加
    - 检查数值与配置一致（天赋/难度对初始值的影响写明在此）
    - 输出完 JSONPatch 后再开始正文
```

**为什么禁止 `<initvar>`**：`<initvar>` 只在"新开聊天"时被 MVU 读取；创角发生在聊天已经打开之后，只有 JSONPatch 更新才能真正落进变量（实测卡的教训）。

另一条路线（F 卡）：first_mes 里预置一份**空值 initvar**（`姓名: ''`、`时间: ''`），表单提交后由 AI 用 JSONPatch 把空值填满——效果相同，看作者喜好。

## 6. 变体与多语言

- 多开局各有创角的卡：给每个开局的占位符用不同标签（`<Start1Ready>`…）或让表单正则读取开局文案里的标记。
- 表单也可以是"设置面板"：游戏中途改难度/风格（写到变量 + 系统日志，同样适用本节所有通道）。

## 7. 校验清单（提交前逐条过）

- [ ] first_mes 占位符与正则 findRegex 完全一致（含大小写/斜杠；建议 `/<XxxReady\s*\/>/g` 兼容空格）
- [ ] 表单正则 `markdownOnly: true`，`promptOnly: false`（表单不该进提示词）；两段式的"开始创建"正则 `maxDepth: 1`
- [ ] 提交按钮：native setter + `input` 事件 + 点击 `#send_but`（或 SDK 通道）
- [ ] 提交内容含结构化数据块；世界书有对应协议条目（含"禁止 initvar、必须 JSONPatch"的硬规则）
- [ ] 表单在**无 MVU / 插件缺失**时给出错误提示（try/catch 包住，toastr 或状态行文字），而不是静默失灵
- [ ] 深色/浅色主题下可读；手机宽度不横向滚动
- [ ] 重复提交防护：提交后禁用按钮或显示"已提交"状态

## 8. 常见坑

| 坑 | 原因/处理 |
|---|---|
| 点按钮没反应 | 找不到输入框（iframe 嵌套层级不同）→ 用 §3 的 walk 循环 + try/catch；或按钮事件没绑上（表单 HTML 被正则二次转义） |
| 提交后输入框有字但没发送 | 只触发了 input 未点击 `#send_but`；或框架未感知（没用 native setter） |
| 提交后变量没变 | 协议条目缺失/没在 D0；或 AI 用了 `<initvar>`（已开局无效）；或正则把提交消息从提示词里误删 |
| 表单只在第一楼层显示一次 | 给表单正则加了 `maxDepth`；去掉即可常驻（或在两段式里这是有意设计） |
| 玩家跳过创角 | alternate_greetings 保留"直接开局"文案；或协议条目支持"无配置时用默认值开局" |
