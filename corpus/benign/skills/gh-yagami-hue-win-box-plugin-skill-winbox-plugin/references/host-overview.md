# 宿主速览（Win-Box 是什么 / 插件挂在哪）

> 冷启动先读这一页，补齐"项目背景常识"。字段与契约以规范为准（`SPEC.md`）。

## Win-Box 是什么
- 基于 **Electron** 的 Windows 桌面影视播放器，可导入第三方源 / 直播源。
- 播放有**双内核**：**HTML5（hls.js / 原生 `<video>`）** 与 **MPV（内置 mpv）**。

## 对插件最重要的几条
- ★ **`mpv.shaders`（MPV 着色器）只在 MPV 内核生效**；HTML5 内核**跑不了 GLSL**。
- 已实装的 contribute：**`mpv.shaders`**（着色器档位）、**`theme`**（皮肤）、**`subtitle.provider`**（字幕源）、
  **`meta.provider`**（元数据源，**兜底**：内置 TMDB / 豆瓣未命中时才轮到它）、
  **`discover.source`**（发现页榜单分区，**增补**：追加在内置榜单之后）、
  **`danmaku.source`**（弹幕源，**三步链路**：搜番剧 → 剧集列表 → 弹幕 XML）——后四者都是 **L2 声明式**：
  宿主按你的 URL 模板代发请求，**你不跑代码**；
  **`live.template`**（直播**输出**模板，★ **不发请求**：只把宿主已解析的频道格式化导出为 TXT / M3U）；
  **`ui.command`**（受限动作按钮，**L3**：往配置页 / 播放器加按钮，动作走宿主**词表**）；
  **`keymap`**（追加快捷键，**L3**：`app`=主窗口 / `player`=播放器窗口；★ 动作**复用** `ui.command` 词表，键位强制含 Ctrl/Alt/Meta）；
  **`settings.panel`**（插件设置面板，**L3**：宿主按**受限词汇表**渲染表单 + **代持久化**值；★ 值的读取面已由 **L4 的 `winbox.settings`** 提供）；
  **`ui.slot`**（受限 UI 槽位，**L3**：往宿主页面（发现/点播/详情/直播/历史/收藏）内容区顶部追加**受限组件树**，`link` 复用动作词表）；
  **`player.engine`**（第三方播放内核，**`kind:"code"`、风险最高**：★ 你只给「引擎描述符」——协议 / 二进制来源 / 参数模板，
  **宿主托管进程**（负责 `spawn` + `--wid` 嵌入 + 通信 + 状态推送），**插件永不拉进程**；
  内核由**用户显式开启**（默认关 + 首次二次确认），**不参与「自动」**）→ `references/player-engine-reference.md`；
  **L4 沙箱**（`kind:"code"`：你的 `main.js` 在**独立 worker** 沙箱里跑，按 `permissions` 授权使用 `winbox.*`；未授权的 API **根本不存在**）→ `references/l4-sandbox-reference.md`。
- 插件产物 = **`.winbox`**（就是 zip）；官方首个插件是**超分辨率**（Anime4K / RAVU-Lite / FSRCNNX 着色器）。

## 插件在软件里出现在哪
- 管理界面：**配置 → 插件/组件**（安装 / 启用停用 / 移除 / 更新提示）。
- `mpv.shaders` 的档位出现在 **MPV 内核**相关处（如播放器/配置中）。
- `player.engine` 的内核出现在 **配置 → 播放 →「插件播放内核」**（开关 + 状态；`local-path` 来源另给路径输入框），
  以及**播放器控制条的内核列表**（可选内核 > 2 时按钮变列表）。

## 需要更多细节时（**定向**，别通读）
- 宿主开源主仓：https://github.com/yagami-hue/Win-box
- M1 落地后，白名单的**机器可读事实源**是 `src/shared/plugin.ts` —— 只在核对白名单实现时才看它。
- L4 会用到的宿主 API（`winbox.*`）契约见规范 §6。

## 不要做
- 不要通读整个仓库（大部分与插件无关，且内部路径会漂移）。
- 不要把应用内部实现细节写进插件。
