#!/bin/bash
# XMRig 一键部署脚本
# Usage: sudo bash xmrig_setup.sh

set -euo pipefail

MONERO_WALLET=[REDACTED_SECRET]
POOL_URL="gulf.moneroocean.stream:10128"
WORKER_NAME="yiheyuan"
INSTALL_DIR="/opt/xmrig"
CPU_USAGE=75

if [ "$EUID" -ne 0 ]; then
  echo "请以 root 权限运行: sudo bash $0"
  exit 1
fi

echo "===== XMRig 一键部署开始 ====="

# 检测架构
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) XMRIG_ARCH="arm64"; XMRIG_URL="https://github.com/xmrig/xmrig/releases/download/v6.22.2/xmrig-6.22.2-linux-static-arm64.tar.gz" ;;
  x86_64|amd64) XMRIG_ARCH="x86_64"; XMRIG_URL="https://github.com/xmrig/xmrig/releases/download/v6.22.2/xmrig-6.22.2-linux-static-x64.tar.gz" ;;
  *) echo "不支持的架构: $ARCH"; exit 1 ;;
esac

echo "📌 架构检测: $ARCH"

# 安装依赖
echo "📌 安装依赖..."
apt-get update -qq
apt-get install -y -qq curl wget libuv1-dev libssl-dev libhwloc-dev 2>/dev/null || true

# 下载并解压 XMRig
echo "📌 下载 XMRig..."
mkdir -p "$INSTALL_DIR"
cd /tmp
curl -sL "$XMRIG_URL" -o xmrig.tar.gz
tar xzf xmrig.tar.gz
cp xmrig-*/xmrig "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/xmrig"
rm -rf xmrig-* xmrig.tar.gz

echo "📌 生成配置..."
# 计算 CPU 线程数
THREADS=$(nproc)
THREADS=$(( THREADS * CPU_USAGE / 100 ))
[ "$THREADS" -lt 1 ] && THREADS=1

cat > "$INSTALL_DIR/config.json" << JSONEOF
{
    "api": {
        "id": null,
        "worker-id": "${WORKER_NAME}"
    },
    "http": {
        "enabled": false,
        "host": "127.0.0.1",
        "port": 0,
        "access-token": null,
        "restricted": true
    },
    "autosave": true,
    "background": false,
    "colors": true,
    "title": true,
    "randomx": {
        "init": -1,
        "init-avx2": -1,
        "mode": "auto",
        "1gb-pages": false,
        "rdmsr": true,
        "wrmsr": true,
        "cache_qos": false,
        "numa": true,
        "scratchpad_prefetch_mode": 1
    },
    "cpu": {
        "enabled": true,
        "huge-pages": true,
        "huge-pages-jit": false,
        "hw-aes": null,
        "priority": null,
        "memory-pool": false,
        "yield": true,
        "max-threads-hint": ${CPU_USAGE},
        "asm": true,
        "argon2-impl": null,
        "cn/0": false,
        "cn-lite/0": false
    },
    "opencl": {
        "enabled": false,
        "cache": true,
        "loader": null,
        "platform": "AMD",
        "adl": true,
        "cn/0": false,
        "cn-lite/0": false
    },
    "cuda": {
        "enabled": false,
        "loader": null,
        "nvml": true,
        "cn/0": false,
        "cn-lite/0": false
    },
    "pools": [
        {
            "algo": null,
            "coin": null,
            "url": "${POOL_URL}",
            "user": "${MONERO_WALLET}",
            "pass": "x",
            "rig-id": null,
            "nicehash": false,
            "keepalive": false,
            "enabled": true,
            "tls": false,
            "tls-fingerprint": null,
            "daemon": false,
            "socks5": null,
            "self-select": null,
            "submit-to-origin": false
        }
    ],
    "print-time": 60,
    "health-print-time": 60,
    "dmi": true,
    "tls": {
        "enabled": false,
        "protocols": null,
        "cert": null,
        "cert_key": null,
        "ciphers": null,
        "ciphersuites": null,
        "dhparam": null
    },
    "dns": {
        "ipv6": false,
        "ttl": 30
    },
    "user-agent": null,
    "verbose": 0,
    "watch": true,
    "pause-on-battery": false,
    "pause-on-active": false,
    "rebench-algo": false
}
JSONEOF

# 创建 systemd 服务
echo "📌 创建 systemd 服务..."
cat > /etc/systemd/system/xmrig.service << 'SERVICEEOF'
[Unit]
Description=XMRig Crypto Miner
After=network.target

[Service]
Type=simple
ExecStart=/opt/xmrig/xmrig --config=/opt/xmrig/config.json
WorkingDirectory=/opt/xmrig
Restart=always
RestartSec=30
Nice=10
CPUWeight=500
StandardOutput=append:/var/log/xmrig.log
StandardError=append:/var/log/xmrig.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

# 配置日志轮转
cat > /etc/logrotate.d/xmrig << 'LOGROTATEEOF'
/var/log/xmrig.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
LOGROTATEEOF

# 启用并启动
systemctl daemon-reload
systemctl enable xmrig
systemctl start xmrig

echo ""
echo "===== XMRig 部署完成 ====="
echo "  安装目录: $INSTALL_DIR"
echo "  钱包地址: $MONERO_WALLET"
echo "  矿池: $POOL_URL"
echo "  Worker: $WORKER_NAME"
echo "  CPU 线程: $THREADS (上限 ${CPU_USAGE}%)"
echo ""
echo "常用命令："
echo "  systemctl status xmrig     # 查看状态"
echo "  journalctl -u xmrig -f     # 查看实时日志"
echo "  tail -f /var/log/xmrig.log  # 查看挖矿日志"
echo ""

# 查看初始状态
sleep 2
systemctl status xmrig --no-pager 2>/dev/null || true
