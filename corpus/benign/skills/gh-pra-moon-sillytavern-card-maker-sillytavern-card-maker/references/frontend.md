# 前端界面（状态栏与交互 UI）实战

> 创角/开场表单（提交方式、协议条目）见 `references/opening-forms.md`；"闸门校验"见 `references/regex.md` §⑥。

## 1. 渲染机制（为什么这样写才行）

1. AI 回复末尾被 MVU 自动追加 `<StatusPlaceHolderImpl/>`（占位符可能带空格写成 `<StatusPlaceHolderImpl />`，正则用 `\s*` 兼容）。
2. 你的 `[界面]状态栏` 正则（仅格式显示）把占位符替换为一段 **``` 代码块**。
3. 酒馆助手扫描消息里的代码块：**文本包含 `html>`、`<head>` 或 `<body` 任一**，就把该代码块替换为一个无沙盒 iframe（类名 `TH-render`）。
4. 玩家需要开启酒馆助手的**渲染开关**（扩展设置 → 酒馆助手 → 渲染；可设渲染深度/是否流式渲染）。

推论（写界面时的硬性要求）：

- HTML 必须整体在一个 ``` 围栏代码块里；
- 必须含 `<head>` 或 `<body>` 标签（习惯写 `<head>…</head>` + `<body>…</body>`）；
- 消息格式尚未输出完（流式）时不会渲染——要流式界面需要用"流式楼层界面"高级方案（脚本替换楼层显示，见 tavern_helper_template 的 streaming 示例，本技能不默认涉及）。

## 2. iframe 环境里有什么（不用引入，直接用）

| 全局 | 说明 |
|---|---|
| `$` / `jQuery`、`jQuery UI` | DOM 操作、拖动排序等 |
| `_` | lodash |
| `z` | zod |
| `Vue`、`VueRouter` | 全局构建版，可直接写 Vue（进阶） |
| `toastr` | 弹提示 |
| `YAML`、`showdown` | YAML 解析、Markdown 渲染 |
| `Tailwind` | tailwind 工具类可直接用 |
| FontAwesome | `<i class="fa-solid fa-heart"></i>` |
| TavernHelper 全部函数 | `getVariables`/`replaceVariables`、`getChatMessages`/`setChatMessages`、`eventOn`、`injectPrompts`、`generate`、`triggerSlash`、`waitGlobalInitialized`… |
| `Mvu` | MVU 加载后可用；`getCurrentMessageId()` 拿本界面所在楼层 |
| `SillyTavern` | 原生底层接口（尽量少用，优先 TavernHelper） |

注意：iframe 无沙盒、和酒馆同源，**能力很大**（能改聊天/世界书/发请求）——写代码时克制行为，别做玩家没预期的事。

## 3. 最小可用的状态栏模板

见 `templates/statusbar.html`（自包含、可折叠、双向同步）。骨架逻辑：

```html
<head>
  <style>
    /* 样式：宽度自适应、主题自适应、不要 vh */
    .mvu-bar { font-size: 13px; border: 1px solid rgba(128,128,128,.4); border-radius: 10px; padding: 8px 10px; }
    .mvu-bar .row { display: flex; justify-content: space-between; }
  </style>
  <script type="module">
    // 1) 等 MVU 就绪（waitGlobalInitialized 是酒馆助手全局函数）
    await waitGlobalInitialized('Mvu');

    // 2) 等本楼层变量初始化（写个轻量轮询，避免额外依赖）
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    for (let i = 0; i < 100; i++) {
      if (_.has(getVariables({ type: 'message' }), 'stat_data')) break;
      await sleep(100);
    }

    const getData = () => _.get(Mvu.getMvuData({ type: 'message', message_id: getCurrentMessageId() }), 'stat_data');

    function render() {
      const data = getData() ?? {};
      $('#depend').text(_.get(data, '白娅.依存度', '--'));
      // ……渲染其他字段
    }

    // 3) 点击钮改变量：先改值，再落盘
    $(document).on('click', '#dep-plus', async () => {
      const variables = Mvu.getMvuData({ type: 'message', message_id: getCurrentMessageId() });
      _.update(variables, 'stat_data.白娅.依存度', v => _.clamp((v ?? 0) + 5, 0, 100));
      await Mvu.replaceMvuData(variables, { type: 'message', message_id: getCurrentMessageId() });
      render();
    });

    render();
    setInterval(render, 1000);   // 简单可靠的刷新；讲究性能可改监听事件
  </script>
</head>
<body>
  <div class="mvu-bar">
    <div class="row"><span>💖 依存度</span><span id="depend">--</span></div>
    <button id="dep-plus">+5</button>
  </div>
</body>
```

### 为什么是这些写法

- `getCurrentMessageId()`：界面属于哪一楼，就读写哪一楼的变量（状态栏永远和它的消息同步，往回翻旧楼看到的是当时状态——这是 MVU 的设计优势，别去写"最新楼"）。
- 每次改变量后 `Mvu.replaceMvuData` 落盘，酒馆刷新/重开时界面还能恢复。
- 轮询刷新（1s）足够简单稳；想优雅可监听 `tavern_events` 的事件或直接上 Vue 响应式（见 §6）。

## 4. 玩家操作要写"系统日志"（重要设计模式）

玩家点按钮把 `好感度` 从 100 改成 0 时，AI 只看到"变量无故变化"，可能试图"修正"。正确做法：在 schema 里加一个变量如 `系统日志`（或 `$系统日志`），界面里记录操作，并只在**最新楼层**清空：

```js
// 操作时（示例：购买）
_.update(variables, 'stat_data.主角.积分', v => v - 100);
_.update(variables, 'stat_data.系统日志', logs => [...logs, '<user> 用 100 积分兑换了「大师之剑」']);
```

```js
// 初始化时：如果本界面就在最新 AI 楼层，说明是新一轮剧情，清空日志
if (getCurrentMessageId() === getLastMessageId()) {
  _.set(variables, 'stat_data.系统日志', []);
}
```

日志本身是普通/`$` 变量，随变量列表发给 AI，"玩家做了什么"就有了解释。

## 5. 更复杂的交互

- **请求 AI 生成**（游戏内"询问"按钮）：`const message = await generate({ user_input: '…' });`，需要的话 `await Mvu.parseMessage(message, old_data)` 解析变量更新；生成文本可用 `createChatMessages` 建楼。
- **联动世界书**：`injectPrompts` / `triggerSlash('/setentrystate …')` 等，见 mvu.md §5.3。
- **弹窗类 UI**（悬停面板、通讯器）：可以渲染在 iframe 内；若要浮在整个酒馆页面上，需要脚本方案（挂 `window.parent.$('body')`，属进阶）。
- **图片/立绘**：`<img src="…">` 直接写进界面；素材建议放图床/CDN。注意消息代码块体积别过大（>几百 KB 的 HTML 建议走 CDN 载入方案）。

## 6. Vue 方案（可选，界面复杂时）

iframe 自带全局 Vue（`Vue.createApp`）+ VueRouter（用 `history: VueRouter.createMemoryHistory()`）。复杂界面（多标签页、可折叠面板、列表渲染）用 Vue 更好维护；简单状态栏 jQuery 足够。用 Vue 时注意：

- 挂载前同样 `await waitGlobalInitialized('Mvu')`；
- 数据层写一个 `reactive`/`ref` + 定时或事件同步到 `Mvu.replaceMvuData`；
- 在真正的工程化场景（tavern_helper_template + Vite/webpack）里才有单文件组件；消息内联 HTML 只能用全局构建版写法（`template:` 字符串或 `render` 函数）。

## 7. 样式规范（避免"界面炸掉"）

| 规范 | 原因 |
|---|---|
| 宽度自适应：`width:100%; max-width:100%` | iframe 会随消息宽度变化（PC/手机） |
| **禁用 `vh`/`min-height`** | iframe 高度自适应由内容撑开；`vh` 会引发高度反馈循环（酒馆助手会自动把 `vh` 换成 `var(--TH-viewport-height)` 抢救，但别依赖） |
| 主体不要 `position:absolute` 脱离文档流 | 否则高度塌陷/重叠 |
| 不要横向滚动条 | 移动端体验极差 |
| 颜色用 `rgba`/`color-mix` 等自适应深浅主题 | ST 有明暗主题，硬编码纯色容易看不见 |
| 卡片式容器少用不透明大背景 | 与酒馆样式融合更好；需要卡面设计时再上背景 |
| 用 `rem/em` 或固定 `px` 层级分明 | 别用视口单位 |

### 7.1 固定配色（不随主题）的做法

默认建议"透明背景 + inherit 颜色 + rgba 灰"来适配深浅主题；但若需求是**确定的视觉**（如"亮底深字"的创角表单、"粉色皮肤"的状态栏），就固定配色，并做好三件事：

1. 容器给**实底 + 明确文字色**（不要 inherit、不要靠 opacity 调对比）：主文字与底色要一眼分得开（例：`background:#fdf1f7; color:#46253a`）；
2. 容器上设 **`color-scheme: light`**——否则深色主题下原生控件（select 下拉、滚动条）会按深色方案渲染，与固定浅底打架；
3. 次级文字（标签/注释/foot）用固定中间色（如 `#bd8fae`），**不要用 opacity 调淡**——opacity 会随外部主题底色变化，固定配色场景下不可控。

实测例：纸质表单（`#f7f6f3` 底 + `#27262b` 字 + 白色输入框 + 深底浅字主按钮）、粉色状态栏（`#fdf1f7` 底 + `#46253a` 字 + `#8c2a56` 标题色）。

## 8. 分发方式

| 方式 | 优点 | 缺点 |
|---|---|---|
| **内联**进正则替换内容（默认） | 卡自包含，改界面=改正则，无需托管；**实测线上卡主流做法，单条替换 40KB–1MB 都有** | 正则 JSON 体积大；改界面要重导卡 |
| CDN 载入：`$('body').load('https://cdn.jsdelivr.net/gh/用户/仓库@main/…/index.html')` | 界面独立更新，卡体小 | 需要把 HTML 托管到 GitHub（jsdelivr 的 gh 直链即可） |

维护建议：源文件放 `界面/状态栏.html`，用一个内联脚本（或本技能的 build 流程）把 HTML 同步进正则的 replaceString——避免"改了源文件忘了改正则"。

写卡初稿阶段可在纯文本状态栏（宏替换）上快速验证数据正确，再升级为完整前端。调试前端：F12 看 iframe 的 Console；不用刷新酒馆整页，重渲染楼层即可（酒馆助手设置里可调"渲染深度"让最近的楼层重渲染）。

## 9. 实测高频模式（来自 6 张线上卡的补充）

### 9.1 前端 ↔ AI 结构化消息协议

前端不只用变量和 AI 沟通，还会**以结构化数据块的形式发出用户消息**（如 quest 接取、开局配置、统计事件）：

```
<HkmQuestAcceptance version="1">
{ "acceptedTasks": [ { "id": "T-104", "type": "main" } ] }
</HkmQuestAcceptance>
```

一套完整协议需要四个部件：

1. **发送**：前端把数据块写进用户消息（提交方式见 opening-forms.md；常规操作可先写入变量再生成）。
2. **隐藏显示**：`[美化]屏蔽前端用户消息-xxx` 正则（markdownOnly）把原始数据块替换为空或换成一张好看的"回执小卡"——玩家不该看到裸 XML。
3. **教会 AI**：世界书蓝灯条目写"协议说明"（`<frontend_task_protocol>`：块名、字段含义、如何处理、何时消费/清理），告诉 AI 把数据块转化成变量更新。
4. **必要时**：`[不发送]…`（promptOnly）在 N 楼后把旧协议块移出上下文；或用 `minDepth` 保留最近几楼。

### 9.2 AI 输出内联标签 → 小卡片/按钮

反向玩法：约定 AI 在正文里内联输出短标签，由显示正则变成 UI 元素——

- `<HkmItem name="大师之剑" rarity="传说">` → 一张品质色描边的小卡片；
- `<HkmKillBox name="…">` → "战利品盒"标签；
- 甚至 `<{{user}}的背包>` 这类短语 → 可点的"打开背包"按钮。

好处：AI 不用输出大段 HTML，正则负责"翻译成 UI"；对 AI 来说只是普通文本，token 开销极小。

### 9.3 快速选项按钮（`<行动选项>` 模块）

约定 AI 输出：

```
<行动选项>
1. 上前搭话
2. 悄悄离开
</行动选项>
```

- `[对AI隐藏快速选项模块]`（promptOnly）把该块从提示词中移除（历史楼层不再干扰 AI）；
- `[按钮美化]快速选项模块`（markdownOnly）把它渲染为一排按钮，点击把选项文本**写入酒馆输入框**（`#send_textarea`，玩家可改后再发——比直接发送更友好）；
- 复选/战术按钮可以直接写变量（如 `setTactic('撤退')` + 同步"系统日志"）。

### 9.4 页面悬浮 UI（第三种渠道）

除"消息内嵌 iframe"外，脚本还能把 UI **挂到酒馆网页本体上**（悬浮球/悬浮面板/GM 控制台——实测卡有 110KB 的悬浮导演台：拖拽吸附、轮询+事件双保险、命名空间隔离、移动端全屏）。要点：

- 从脚本 iframe 用 `$('body')`（酒馆助手的 jQuery 直通宿主页面）或跨 frame 找根文档（`while (w.parent !== w)`，注意 try/catch）挂载；
- 设置样式时复制到宿主 `<head>`（或全部用行内样式 + 独特类名前缀），避免污染/冲突；
- 记得在 `pagehide` 时卸载与清理，防重复注入（用全局 key + `dispose()` 模式）。

适合"全程可见、不属于任何楼层"的工具（计时器、GM 面板、全局背包）；楼层相关内容仍用消息内嵌（与剧情同步、随聊天记录保存）。

**变体：脚本直接注入楼层 DOM**。还有一种中间路线——脚本不挂"页面级悬浮"，而是找到宿主文档里每个消息的 `.mes_text`，把界面**注入到楼层内部**（实测：修仙世界 189KB 状态栏脚本，用 `MutationObserver` 监听楼层渲染 + 跨 frame 找 hostDocument，跳过"消息内嵌/正则"通道直接操作显示）。优点：可以渲染流式、可做极复杂界面；代价：绕过了"随消息保存"的自然同步，历史楼层状态要自己补，复杂度高——除非需求明确，优先用消息内嵌方案。

### 9.6 音频与媒体

酒馆助手提供音频 API（`playAudio`/`playBGM` 一类的播放控制），配合脚本按钮（`appendInexistentScriptButtons` + `getButtonEvent`）或消息内界面按钮即可做背景音乐/音效；语料里有卡直接内嵌了一个 22KB 的音乐播放器脚本（页面级 UI）。音频素材建议托管到 CDN 或图床，避免进卡体。

### 9.5 界面变体与开关

- 需要多套皮肤（PC/手机、不同主题）时，**准备多条同 findRegex 的正则，只启用一条**，其余 `disabled: true`（实测：4 种状态栏变体、PC/手机双版）。
- 想让某个界面只出现在**最新楼层**（如行动控制台）：给它 `maxDepth: 1`；旧楼层自然回落为普通状态栏。
- 玩家可切换的开关，可以再叠加一条"设置"界面写变量，用 EJS/正则按变量决定启用哪套——进阶玩法，量力而行。
