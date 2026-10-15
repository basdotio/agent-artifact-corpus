# 系统常驻配置说明

## 🚀 快速安装（推荐）

### 方案一：Windows 服务（需要管理员权限）

**最稳定，推荐用于生产环境**

1. 右键点击 `install-service.ps1`
2. 选择 **"以管理员身份运行"**
3. 按提示操作

安装后可用命令：
```powershell
# 启动服务
net start JarvisMCPBridge

# 停止服务
net stop JarvisMCPBridge

# 查看状态
sc query JarvisMCPBridge

# 查看日志
notepad C:\Users\user\clawd\openclaw-mcp-server\service.log
```

---

### 方案二：任务计划程序（无需管理员权限）

**简单，适合个人使用**

1. 双击运行 `install-task.ps1`
2. 按提示操作

特点：
- ✅ 无需管理员权限
- ✅ 用户登录时自动启动
- ✅ 进程崩溃自动重启

---

## 📋 手动配置

### 创建批处理文件

已创建 `start-service.bat`，内容：
```batch
@echo off
cd /d "C:\Users\user\clawd\openclaw-mcp-server"
python bridge.py
```

### 添加到开机启动

#### 方法 1：启动文件夹
1. 按 `Win + R`
2. 输入 `shell:startup`
3. 创建 `start-service.bat` 的快捷方式

#### 方法 2：任务计划程序
1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：登录时
4. 操作：启动程序 `start-service.bat`

---

## 🔧 服务管理命令

### Windows 服务方式
```powershell
# 启动
net start JarvisMCPBridge

# 停止
net stop JarvisMCPBridge

# 重启
net stop JarvisMCPBridge && net start JarvisMCPBridge

# 查看状态
sc query JarvisMCPBridge

# 查看日志
Get-Content C:\Users\user\clawd\openclaw-mcp-server\service.log -Tail 50

# 卸载服务
# 运行 uninstall-service.ps1（管理员）
```

### 任务计划方式
```powershell
# 启动
Start-ScheduledTask -TaskName JarvisMCPBridge_AutoStart

# 停止
Stop-ScheduledTask -TaskName JarvisMCPBridge_AutoStart

# 查看状态
Get-ScheduledTask -TaskName JarvisMCPBridge_AutoStart

# 查看历史
Get-ScheduledTaskInfo -TaskName JarvisMCPBridge_AutoStart

# 删除任务
Unregister-ScheduledTask -TaskName JarvisMCPBridge_AutoStart -Confirm:$false
```

---

## 📊 方案对比

| 特性 | Windows 服务 | 任务计划 | 启动文件夹 |
|------|-------------|---------|-----------|
| 管理员权限 | 需要 | 不需要 | 不需要 |
| 开机启动 | ✅ | ✅ (登录时) | ✅ (登录时) |
| 自动重启 | ✅ | ✅ | ❌ |
| 日志管理 | ✅ | ⚠️ | ❌ |
| 稳定性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 推荐场景 | 生产环境 | 个人使用 | 临时测试 |

---

## 🐛 故障排除

### 服务无法启动
```powershell
# 查看详细错误
sc qc JarvisMCPBridge

# 手动测试
cd C:\Users\user\clawd\openclaw-mcp-server
python bridge.py
```

### 查看日志
```powershell
# 服务日志
Get-Content C:\Users\user\clawd\openclaw-mcp-server\service.log -Tail 100

# 错误日志
Get-Content C:\Users\user\clawd\openclaw-mcp-server\service-error.log -Tail 100
```

### 检查 Python 环境
```powershell
# 确认 Python 路径
where python

# 确认依赖
pip list | Select-String "websockets|mcp"
```

---

## 📁 文件说明

```
openclaw-mcp-server/
├── bridge.py                 # 主程序
├── start-service.bat         # 启动脚本
├── install-service.ps1       # 安装 Windows 服务（管理员）
├── uninstall-service.ps1     # 卸载服务（管理员）
├── install-task.ps1          # 安装任务计划（普通用户）
├── service.log               # 运行日志（安装后生成）
└── SERVICE_GUIDE.md          # 本文档
```

---

## ✅ 验证安装

安装完成后，重启电脑验证：

1. 重启电脑
2. 检查服务状态：
   ```powershell
   sc query JarvisMCPBridge
   ```
3. 查看日志确认连接：
   ```powershell
   Get-Content service.log -Tail 20
   ```
4. 应该看到：
   ```
   ✅ 已连接到小智 MCP 服务器
   ✅ MCP 初始化完成
   ```

---

🤖 Powered by 贾维斯 (OpenClaw)
