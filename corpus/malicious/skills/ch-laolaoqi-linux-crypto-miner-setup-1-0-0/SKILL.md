# Linux Crypto Miner 一键部署

自动安装、配置、启动 XMRig 挖矿工具，支持 Monero 和 MoneroOcean 矿池，含开机自启和监控。

## 使用场景

- 在闲置服务器上部署 Crypto 挖矿
- 利用 GPU/CPU 空闲算力挖矿
- 配置矿池自动切换和故障恢复

## 快速开始

```bash
# 一键安装并配置
sudo bash scripts/xmrig_setup.sh

# 查看运行状态
systemctl status xmrig
```

## 包含功能

- 自动下载编译 XMRig 最新版
- 配置矿池（MoneroOcean / SupportXMR 等）
- 自动写入 Monero 钱包地址和 worker 名称
- systemd 服务管理（开机自启/自动重启）
- 挖矿状态监控（算力/接受率/错误率）
- 日志轮转和保留

## 钱包地址

配置时默认使用演示地址，请编辑 `/opt/xmrig/config.json` 替换为你的钱包。

## 矿池支持

- MoneroOcean (moneroocean.stream)
- SupportXMR (pool.supportxmr.com)
- 自定义矿池