---
name: device-control
description: Control electronic test equipment including oscilloscopes, programmable power supplies, and other test instruments. Use when user mentions electronic test devices like oscilloscopes, power supplies, function generators, multimeters, etc. Supports operations such as reading measurements, capturing screenshots, setting parameters, and running automated tests.
---

# Device Control Skill

此 skill 用于协调控制电子测试设备。

## 可用设备 Skills

根据设备类型使用对应的 skill：

| 设备类型 | Skill | 说明 |
|----------|-------|------|
| 示波器 | @oscilloscope | Yokogawa 示波器控制 - 读取均值、截图 |
| 电源 | @power-supply | 可编程电源控制 - 设置电压、开关输出 |
| 程控电阻 | @programmable-resistor | RM550 电阻控制 - 设置阻值 |

## 使用方法

根据需求使用对应的专业 skill：
- **示波器操作** → 使用 @oscilloscope skill
- **电源操作** → 使用 @power-supply skill
- **电阻操作** → 使用 @programmable-resistor skill

## 设备连接排查

当设备命令执行失败（如 "未找到 VISA 设备" 或 "未找到串口设备"）时，请手动绑定设备到 WSL：

**步骤 1: 在 Windows 上（PowerShell）**
```powershell
# 安装 usbipd（如果未安装）
winget install --id=USBIPd

# 查看可用的 USB 设备
usbipd list

# 绑定设备到 WSL
usbipd bind --busid <BUSID>
```

**步骤 2: 在 WSL 中 attach 设备**
```shell
pwsh.exe -c "usbipd attach --wsl --busid <BUSID>"
```

**提示**：
- 示波器：通常显示为 "DLM series" 或 "Yokogawa"
- 电源：通常显示为 "USB Test and Measurement" 或 ITECH 型号
- 程控电阻：通常显示为 "RM550" 或 "PRO" 开头

