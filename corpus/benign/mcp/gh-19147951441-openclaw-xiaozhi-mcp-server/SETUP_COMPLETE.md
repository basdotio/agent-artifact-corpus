# ✅ 系统常驻配置完成！

## 📌 安装状态

**✅ 已完成 - 启动文件夹方案**

快捷方式位置：
```
C:\Users\user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\JarvisMCP.lnk
```

---

## 🚀 工作原理

1. **开机登录时** → Windows 自动运行启动文件夹中的快捷方式
2. **快捷方式** → 启动 `run.bat`
3. **run.bat** → 运行 `python bridge.py`
4. **bridge.py** → 连接小智 MCP 服务器，等待请求
5. **进程守护** → 如果意外退出，5 秒后自动重启

---

## 📋 立即启动（无需重启）

双击运行：
```
C:\Users\user\clawd\openclaw-mcp-server\run.bat
```

或在 PowerShell 中：
```powershell
cd C:\Users\user\clawd\openclaw-mcp-server
.\run.bat
```

---

## 🔧 管理命令

### 查看运行状态
```powershell
# 查看 Python 进程
tasklist | findstr python

# 查看桥接器日志
Get-Content C:\Users\user\clawd\openclaw-mcp-server\bridge.log -Tail 50
```

### 停止服务
```powershell
# 方法 1: 任务管理器
# 1. Ctrl+Shift+Esc 打开任务管理器
# 2. 找到 "python.exe" 或 "cmd.exe" (bridge.py)
# 3. 结束任务

# 方法 2: 命令行
taskkill /F /IM python.exe /FI "WINDOWTITLE eq 贾维斯*"
```

### 重启服务
```powershell
# 停止
taskkill /F /IM python.exe /FI "WINDOWTITLE eq 贾维斯*"

# 启动
cd C:\Users\user\clawd\openclaw-mcp-server
.\run.bat
```

---

## 📁 文件说明

```
C:\Users\user\clawd\openclaw-mcp-server\
├── bridge.py                 # 主程序 - MCP 桥接器
├── run.bat                   # 启动脚本（带自动重启）
├── start-service.bat         # 简单启动脚本
├── install-startup.bat       # 安装开机启动（已执行）
├── manifest.json             # MCP 扩展配置
├── tools.py                  # MCP 工具定义
├── requirements.txt          # Python 依赖
├── README.md                 # 项目说明
├── SERVICE_GUIDE.md          # 服务配置指南
└── SETUP_COMPLETE.md         # 本文档
```

---

## ✅ 验证安装

### 1. 检查开机启动
```
路径：C:\Users\user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
文件：JarvisMCP.lnk ✅
```

### 2. 手动启动测试
```powershell
cd C:\Users\user\clawd\openclaw-mcp-server
.\run.bat
```

应该看到：
```
========================================
  贾维斯 MCP 桥接器
========================================

Starting Jarvis MCP Bridge...

[日期 时间] Starting bridge.py...
🤖 贾维斯 MCP 桥接器启动...
正在连接小智 MCP...
✅ 已连接到小智 MCP 服务器
✅ MCP 初始化完成
```

### 3. 重启电脑测试
重启后，应该自动看到 `python.exe` 或 `cmd.exe` 窗口运行。

---

## 🛡️ 防火墙设置

如果连接失败，可能需要允许 Python 访问网络：

1. 打开"Windows Defender 防火墙"
2. 高级设置 → 出站规则
3. 新建规则 → 允许 `python.exe`
4. 或者临时关闭防火墙测试

---

## 📊 日志位置

运行日志会显示在：
- **控制台窗口** - 实时日志
- **bridge.py 输出** - 连接状态、请求处理

关键日志：
```
✅ 已连接到小智 MCP 服务器
✅ MCP 初始化完成
收到消息类型：tools/list
工具调用：process_intent
```

---

## 🐛 故障排除

### 问题 1：开机没有自动启动
**解决：**
1. 检查启动文件夹中是否有 `JarvisMCP.lnk`
2. 手动运行一次 `run.bat`
3. 重启电脑测试

### 问题 2：连接失败
**解决：**
```powershell
# 检查网络
ping api.xiaozhi.me

# 检查 Python
python --version
pip list | Select-String "websockets"

# 重新安装依赖
cd C:\Users\user\clawd\openclaw-mcp-server
pip install -r requirements.txt
```

### 问题 3：窗口闪退
**解决：**
1. 双击 `run.bat` 查看错误信息
2. 检查 Python 路径是否正确
3. 查看控制台输出的错误信息

---

## 📞 快速参考

| 操作 | 命令/路径 |
|------|----------|
| 立即启动 | `C:\Users\user\clawd\openclaw-mcp-server\run.bat` |
| 开机启动位置 | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\` |
| 程序目录 | `C:\Users\user\clawd\openclaw-mcp-server\` |
| 停止服务 | 任务管理器结束 python.exe |
| 查看日志 | 运行窗口实时显示 |

---

## 🎉 配置完成！

**贾维斯 MCP 桥接器已配置为系统常驻服务**

- ✅ 开机自动启动
- ✅ 进程崩溃自动重启
- ✅ 连接小智 MCP 服务器
- ✅ 等待客户端请求

**下次开机后会自动运行，无需手动操作！**

---

🤖 Powered by 贾维斯 (OpenClaw)
配置日期：2026-03-14
