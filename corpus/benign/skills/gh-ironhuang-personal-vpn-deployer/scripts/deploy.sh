#!/usr/bin/env bash
# =============================================================================
# personal-vpn-deployer :: 服务端一键部署 (sing-box VLESS-Reality + Hysteria2)
# 在目标服务器上以 root 运行。产出凭据 JSON 到 stdout（标记包裹）供客户端生成使用。
#
# 用法:
#   REALITY_PORT=443 HY2_PORT=8443 bash deploy.sh
# 环境变量（均有默认值）:
#   REALITY_PORT   Reality 监听端口（务必保持 443，见 references/troubleshooting.md）
#   HY2_PORT       Hysteria2 UDP 端口
#   REALITY_DEST   手动指定伪装目标域名；留空则自动优选
#   HY2_SNI        HY2 自签证书 CN / 客户端 SNI
# =============================================================================
set -euo pipefail

REALITY_PORT="${REALITY_PORT:-443}"
HY2_PORT="${HY2_PORT:-8443}"
HY2_SNI="${HY2_SNI:-www.bing.com}"
REALITY_DEST="${REALITY_DEST:-}"
SB_DIR="/etc/sing-box"

log() { echo "[deploy] $*" >&2; }
die() { echo "[deploy][ERROR] $*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "必须以 root 运行"

# ---------------------------------------------------------------------------
# 1. 开启 BBR（拥塞控制，提升国际链路吞吐）
# ---------------------------------------------------------------------------
log "配置 BBR ..."
cat > /etc/sysctl.d/99-bbr.conf <<'EOF'
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
EOF
sysctl --system >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# 2. 安装 sing-box（官方脚本，含 QUIC/HY2）
# ---------------------------------------------------------------------------
if ! command -v sing-box >/dev/null 2>&1; then
  log "安装 sing-box ..."
  bash <(curl -fsSL https://sing-box.app/deb-install.sh) >&2 || die "sing-box 安装失败"
else
  log "sing-box 已安装：$(sing-box version | head -1)"
fi
mkdir -p "$SB_DIR"

# ---------------------------------------------------------------------------
# 3. 生成凭据
# ---------------------------------------------------------------------------
log "生成密钥与凭据 ..."
KP="$(sing-box generate reality-keypair)"
R_PRIV="$(echo "$KP" | awk '/PrivateKey/{print $2}')"
R_PUB="$(echo "$KP"  | awk '/PublicKey/{print $2}')"
UUID="$(sing-box generate uuid)"
SHORT_ID="$(openssl rand -hex 8)"
HY2_PW="$(openssl rand -base64 16)"
HY2_OBFS_PW="$(openssl rand -base64 16)"

# HY2 自签证书（ECDSA，CN 用作客户端 SNI）
openssl ecparam -genkey -name prime256v1 -out "$SB_DIR/hy2.key" 2>/dev/null
openssl req -new -x509 -days 3650 -key "$SB_DIR/hy2.key" \
  -out "$SB_DIR/hy2.crt" -subj "/CN=$HY2_SNI" 2>/dev/null
chown sing-box:sing-box "$SB_DIR/hy2.key" "$SB_DIR/hy2.crt" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. 自动优选 Reality 伪装目标 (dest)
#    关键经验：REALITY 握手时服务端要实时连到 dest 去"借"真握手；
#    dest 必须从【本服务器】能完成 TLS 之后还能正常返回数据（http_code!=000）。
#    换 IP/机房后原 dest 可能 TLS 通但数据卡死 → 必须实测优选。
# ---------------------------------------------------------------------------
test_dest() {  # $1=domain -> 打印 "OK" 表示可用
  local d="$1" code time_tls
  read -r code time_tls < <(curl -o /dev/null -s \
    -w '%{http_code} %{time_appconnect}' --max-time 8 "https://$d/" 2>/dev/null || echo "000 0")
  # 可用条件：TLS 握手成功(time_appconnect>0) 且 拿到真实 HTTP 状态码(非 000)
  if [ "$code" != "000" ] && awk "BEGIN{exit !($time_tls>0)}"; then echo OK; fi
}

if [ -z "$REALITY_DEST" ]; then
  log "自动优选 Reality dest ..."
  for cand in www.apple.com www.cloudflare.com www.bing.com www.microsoft.com \
              dl.google.com www.amazon.com www.samsung.com; do
    if [ "$(test_dest "$cand")" = "OK" ]; then
      REALITY_DEST="$cand"; log "选定 dest = $REALITY_DEST"; break
    else
      log "  $cand 不可用（TLS后无响应/超时），跳过"
    fi
  done
  [ -n "$REALITY_DEST" ] || die "没有可用的 dest，请手动指定 REALITY_DEST"
else
  log "使用手动指定 dest = $REALITY_DEST"
fi

# ---------------------------------------------------------------------------
# 5. 写 config.json
# ---------------------------------------------------------------------------
log "写入 $SB_DIR/config.json ..."
cat > "$SB_DIR/config.json" <<EOF
{
  "log": { "level": "warn", "timestamp": true },
  "inbounds": [
    {
      "type": "vless", "tag": "vless-in",
      "listen": "0.0.0.0", "listen_port": $REALITY_PORT,
      "users": [ { "uuid": "$UUID", "flow": "xtls-rprx-vision" } ],
      "tls": {
        "enabled": true, "server_name": "$REALITY_DEST",
        "reality": {
          "enabled": true,
          "handshake": { "server": "$REALITY_DEST", "server_port": 443 },
          "private_key": "$R_PRIV",
          "short_id": [ "$SHORT_ID" ]
        }
      }
    },
    {
      "type": "hysteria2", "tag": "hy2-in",
      "listen": "0.0.0.0", "listen_port": $HY2_PORT,
      "users": [ { "password": "$HY2_PW" } ],
      "obfs": { "type": "salamander", "password": "$HY2_OBFS_PW" },
      "tls": {
        "enabled": true, "alpn": [ "h3" ],
        "certificate_path": "$SB_DIR/hy2.crt",
        "key_path": "$SB_DIR/hy2.key"
      }
    }
  ],
  "outbounds": [ { "type": "direct", "tag": "direct" } ]
}
EOF

sing-box check -c "$SB_DIR/config.json" || die "config.json 校验失败"

# ---------------------------------------------------------------------------
# 6. 防火墙（先放行 22 再启用，避免 SSH 断连）
# ---------------------------------------------------------------------------
if command -v ufw >/dev/null 2>&1; then
  log "配置 ufw ..."
  ufw allow 22/tcp >/dev/null 2>&1 || true
  ufw allow ${REALITY_PORT}/tcp >/dev/null 2>&1 || true
  ufw allow ${HY2_PORT}/udp >/dev/null 2>&1 || true
  ufw --force enable >/dev/null 2>&1 || true
fi

# ---------------------------------------------------------------------------
# 7. 启动 & 自测
# ---------------------------------------------------------------------------
log "启动 sing-box ..."
systemctl enable --now sing-box >/dev/null 2>&1 || systemctl restart sing-box
sleep 2
systemctl is-active --quiet sing-box || die "sing-box 未处于 active"

# 本机 REALITY 自测（绕开任何外网干扰，验证服务端配置正确）
cat > /tmp/.sb_selftest.json <<EOF
{ "log":{"level":"error"},
  "inbounds":[{"type":"mixed","listen":"127.0.0.1","listen_port":10999}],
  "outbounds":[{"type":"vless","server":"127.0.0.1","server_port":$REALITY_PORT,
    "uuid":"$UUID","flow":"xtls-rprx-vision",
    "tls":{"enabled":true,"server_name":"$REALITY_DEST","utls":{"enabled":true,"fingerprint":"chrome"},
    "reality":{"enabled":true,"public_key":"$R_PUB","short_id":"$SHORT_ID"}}}]}
EOF
setsid sing-box run -c /tmp/.sb_selftest.json >/tmp/.sb_selftest.log 2>&1 &
sleep 3
SELF_IP="$(curl -s --max-time 12 --proxy socks5h://127.0.0.1:10999 https://api.ipify.org 2>/dev/null || true)"
pkill -f ".sb_selftest.json" 2>/dev/null || true
rm -f /tmp/.sb_selftest.json /tmp/.sb_selftest.log
if [ -n "$SELF_IP" ]; then
  log "REALITY 本机自测通过，出口 IP = $SELF_IP"
else
  log "警告：REALITY 本机自测未返回 IP（可能 dest 抖动，可重跑或手动指定 REALITY_DEST）"
fi

# ---------------------------------------------------------------------------
# 8. 输出凭据 JSON（写文件 + 打印到 stdout 供客户端生成）
# ---------------------------------------------------------------------------
cat > "$SB_DIR/creds.json" <<EOF
{
  "reality_uuid": "$UUID",
  "reality_public_key": "$R_PUB",
  "reality_private_key": "$R_PRIV",
  "reality_short_id": "$SHORT_ID",
  "reality_dest": "$REALITY_DEST",
  "reality_port": $REALITY_PORT,
  "hy2_password": "$HY2_PW",
  "hy2_obfs_password": "$HY2_OBFS_PW",
  "hy2_sni": "$HY2_SNI",
  "hy2_port": $HY2_PORT
}
EOF
chmod 600 "$SB_DIR/creds.json"

echo "===VPN_CREDS_BEGIN==="
cat "$SB_DIR/creds.json"
echo "===VPN_CREDS_END==="
log "完成。凭据已存 $SB_DIR/creds.json（chmod 600），请离线备份。"
log "别忘了在【云厂商安全组】放行入站 ${REALITY_PORT}/TCP 与 ${HY2_PORT}/UDP。"
