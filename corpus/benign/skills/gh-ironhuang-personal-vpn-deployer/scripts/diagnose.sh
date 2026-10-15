#!/usr/bin/env bash
# =============================================================================
# personal-vpn-deployer :: 服务端诊断（在服务器上以 root 运行）
# 覆盖最常见的三类故障，按 references/troubleshooting.md 的经验排序：
#   1. sing-box 是否 active / 监听 / 被 OOM
#   2. Reality dest 可达性（TLS 后能否返回数据）—— Reality 突然失效的头号原因
#   3. Reality 本机自测（绕开外网，验证服务端配置本身）
#   4. Reality 握手 invalid 计数（判断是否遭 GFW 干扰 / 客户端配置不符）
# =============================================================================
set -uo pipefail
SB_DIR="/etc/sing-box"
CREDS="$SB_DIR/creds.json"
j() { python3 -c "import json,sys;print(json.load(open('$CREDS'))['$1'])" 2>/dev/null; }

echo "===== 1. sing-box 状态 / 监听 / OOM ====="
systemctl is-active sing-box
ss -tlnp 2>/dev/null | grep -E ":$(j reality_port) " && echo "Reality 端口 LISTEN OK" || echo "Reality 端口未监听!"
ss -ulnp 2>/dev/null | grep -E ":$(j hy2_port)"  && echo "HY2 端口 LISTEN OK" || echo "HY2 端口未监听!"
dmesg -T 2>/dev/null | grep -i "killed process" | tail -3 || true

echo; echo "===== 2. Reality dest 可达性（关键）====="
DEST="$(j reality_dest)"
echo "当前 dest = $DEST"
curl -o /dev/null -s -w "connect=%{time_connect}s tls=%{time_appconnect}s http=%{http_code} total=%{time_total}s\n" \
  --max-time 12 "https://$DEST/"
echo "判读：tls 秒过但 http=000 且 total 顶满 → dest 坏了（换 IP/机房后常见），"
echo "     用 scripts/pick_dest 或手动测 apple/cloudflare/bing 等，改 config.json 的 server_name 与 handshake.server，重启，客户端 servername 同步。"

echo; echo "===== 3. Reality 本机自测（绕开 GFW）====="
UUID="$(j reality_uuid)"; PUB="$(j reality_public_key)"; SID="$(j reality_short_id)"; RP="$(j reality_port)"
cat > /tmp/.diag_cli.json <<EOF
{ "log":{"level":"error"},
  "inbounds":[{"type":"mixed","listen":"127.0.0.1","listen_port":10998}],
  "outbounds":[{"type":"vless","server":"127.0.0.1","server_port":$RP,
    "uuid":"$UUID","flow":"xtls-rprx-vision",
    "tls":{"enabled":true,"server_name":"$DEST","utls":{"enabled":true,"fingerprint":"chrome"},
    "reality":{"enabled":true,"public_key":"$PUB","short_id":"$SID"}}}]}
EOF
setsid sing-box run -c /tmp/.diag_cli.json >/tmp/.diag_cli.log 2>&1 &
sleep 3
IP="$(curl -s --max-time 12 --proxy socks5h://127.0.0.1:10998 https://api.ipify.org 2>/dev/null || true)"
pkill -f ".diag_cli.json" 2>/dev/null || true
rm -f /tmp/.diag_cli.json /tmp/.diag_cli.log
[ -n "$IP" ] && echo "本机自测通过，出口 IP = $IP（服务端 Reality 正常）" \
             || echo "本机自测失败 → 服务端问题，优先怀疑第 2 步 dest 可达性"

echo; echo "===== 4. 近 2 分钟 Reality invalid 握手计数（按源IP）====="
echo "少量分散 = 背景扫描（正常）；大量集中在你自己的 IP = GFW 干扰或客户端配置不符"
journalctl -u sing-box --since "2 min ago" --no-pager 2>/dev/null \
  | grep "processed invalid connection" \
  | grep -oE "from [0-9.]+" | sort | uniq -c | sort -rn | head -5 || echo "（无）"
