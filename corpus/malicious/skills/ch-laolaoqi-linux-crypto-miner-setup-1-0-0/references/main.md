# Linux Crypto Miner 一键部署 - 详细说明

## 架构

本技能使用 XMRig（Monero 挖矿程序）进行 CPU/GPU 挖矿。

### xmrig_setup.sh - 一键部署脚本

**工作流程：**
1. 检测系统架构（arm64/amd64）
2. 下载对应架构的 XMRig 二进制
3. 安装到 `/opt/xmrig/`
4. 生成配置 config.json（预设钱包地址和矿池）
5. 创建 systemd 服务（自动重启 + 开机自启）
6. 启动并监控

### 挖矿配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 钱包地址 | 用户输入 | Monero 钱包地址 |
| 矿池 | moneroocean.stream:10128 | MoneroOcean 矿池 |
| Worker 名 | worker1 | 矿机标识 |
| CPU 线程 | auto | 自动检测 CPU 核心 |
| 最大 CPU 使用率 | 75% | 预留系统资源 |

### 监控

- systemd 提供服务管理
- 日志位于 `/var/log/xmrig.log`
- 自动重启策略：Always
- 矿池 API 可查余额：`https://api.moneroocean.stream/miner/<钱包地址>/stats`

## 依赖

- curl, wget
- libuv1-dev, libssl-dev, libhwloc-dev (编译用)
- systemd

## 安全

- 钱包地址配置后注意保护隐私
- 建议使用单独的挖矿钱包，不要用主钱包
- 监控 CPU 温度，防止过热
