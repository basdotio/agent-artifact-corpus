#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
personal-vpn-deployer :: 客户端配置生成器

从服务端产出的凭据 JSON + 服务器地址，生成多种客户端配置：
  - clash-verge-inject.js  : Clash Verge Rev 的 Script 覆写（注入到现有订阅，订阅更新不丢）
  - clash-standalone.yaml  : 独立 Clash/mihomo 配置（Clash Meta / Clash Verge 本地导入）
  - nodes.txt              : vless:// 与 hysteria2:// 分享链接
  - qrcodes.txt            : 两个节点的二维码图片链接（在线渲染，手机可扫）

用法:
  python gen_client.py --server <IP或域名> --creds creds.json [--outdir ./client-configs] \
      [--up 30] [--down 150] [--name-prefix 自建]

creds.json 可来自服务端 stdout 的 ===VPN_CREDS_BEGIN=== 段，或 /etc/sing-box/creds.json。
"""
import argparse, json, os, sys
from urllib.parse import quote

def load_creds(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_uris(server, c, prefix):
    reality = (
        f"vless://{c['reality_uuid']}@{server}:{c['reality_port']}"
        f"?security=reality&encryption=none&flow=xtls-rprx-vision"
        f"&sni={c['reality_dest']}&fp=chrome"
        f"&pbk={c['reality_public_key']}&sid={c['reality_short_id']}&type=tcp"
        f"#{quote(prefix + '-Reality')}"
    )
    hy2 = (
        f"hysteria2://{quote(c['hy2_password'], safe='')}@{server}:{c['hy2_port']}"
        f"?obfs=salamander&obfs-password={quote(c['hy2_obfs_password'], safe='')}"
        f"&sni={c['hy2_sni']}&insecure=1"
        f"#{quote(prefix + '-HY2')}"
    )
    return reality, hy2

def build_standalone_yaml(server, c, prefix, up, down):
    r, h = f"{prefix}-Reality", f"{prefix}-HY2"
    return f"""\
mixed-port: 7890
mode: rule
log-level: warning

proxies:
  - name: "{r}"
    type: vless
    server: {server}
    port: {c['reality_port']}
    uuid: {c['reality_uuid']}
    network: tcp
    tls: true
    flow: xtls-rprx-vision
    servername: {c['reality_dest']}
    client-fingerprint: chrome
    reality-opts:
      public-key: {c['reality_public_key']}
      short-id: {c['reality_short_id']}

  - name: "{h}"
    type: hysteria2
    server: {server}
    port: {c['hy2_port']}
    password: "{c['hy2_password']}"
    obfs: salamander
    obfs-password: "{c['hy2_obfs_password']}"
    sni: {c['hy2_sni']}
    skip-cert-verify: true
    up: "{up} Mbps"
    down: "{down} Mbps"

proxy-groups:
  - name: "🏠 {prefix}"
    type: fallback
    proxies: ["{r}", "{h}"]
    url: http://www.gstatic.com/generate_204
    interval: 60
  - name: PROXY
    type: select
    proxies: ["🏠 {prefix}", "{r}", "{h}", DIRECT]

rules:
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
"""

def build_verge_inject(server, c, prefix, up, down):
    r, h = f"{prefix}-Reality", f"{prefix}-HY2"
    # 注意：这是 Clash Verge Rev 的 Script 覆写。挂到现有订阅上，订阅更新后脚本自动重注入。
    return f"""\
// personal-vpn-deployer 生成的 Clash Verge Script 覆写
// 用法：Clash Verge → 订阅右键「编辑」→ 启用该 Script；或订阅页「全局扩展脚本」粘贴本文件。
function main(config, profileName) {{
  const SERVER = "{server}";
  const reality = {{
    name: "{r}", type: "vless", server: SERVER, port: {c['reality_port']},
    uuid: "{c['reality_uuid']}",
    network: "tcp", udp: true, tls: true,
    flow: "xtls-rprx-vision", servername: "{c['reality_dest']}",
    "client-fingerprint": "chrome",
    "reality-opts": {{
      "public-key": "{c['reality_public_key']}",
      "short-id": "{c['reality_short_id']}"
    }}
  }};
  const hy2 = {{
    name: "{h}", type: "hysteria2", server: SERVER, port: {c['hy2_port']},
    password: "{c['hy2_password']}",
    obfs: "salamander", "obfs-password": "{c['hy2_obfs_password']}",
    sni: "{c['hy2_sni']}", "skip-cert-verify": true,
    up: "{up} Mbps", down: "{down} Mbps"
  }};
  const names = ["{r}", "{h}"];
  config.proxies = [reality, hy2].concat(config.proxies || []);
  const selfGroup = {{
    name: "🏠 {prefix}", type: "fallback", proxies: names,
    url: "http://www.gstatic.com/generate_204", interval: 60, lazy: false
  }};
  config["proxy-groups"] = config["proxy-groups"] || [];
  config["proxy-groups"].unshift(selfGroup);
  for (const g of config["proxy-groups"]) {{
    if (g.name === "Proxy") g.proxies = ["🏠 {prefix}"].concat(names, g.proxies);
    if (g.name === "Auto")  g.proxies = names.concat(g.proxies);
  }}
  return config;
}}
"""

def qr_url(data):
    return ("https://api.qrserver.com/v1/create-qr-code/"
            "?size=300x300&ecc=M&data=" + quote(data, safe=""))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True, help="服务器公网 IP 或域名")
    ap.add_argument("--creds", required=True, help="凭据 JSON 路径")
    ap.add_argument("--outdir", default="./client-configs")
    ap.add_argument("--up", default="30", help="HY2 Brutal 上行 Mbps")
    ap.add_argument("--down", default="150", help="HY2 Brutal 下行 Mbps")
    ap.add_argument("--name-prefix", default="自建", help="节点名前缀")
    args = ap.parse_args()

    c = load_creds(args.creds)
    os.makedirs(args.outdir, exist_ok=True)
    p = args.name_prefix

    reality_uri, hy2_uri = build_uris(args.server, c, p)

    with open(os.path.join(args.outdir, "clash-verge-inject.js"), "w", encoding="utf-8") as f:
        f.write(build_verge_inject(args.server, c, p, args.up, args.down))
    with open(os.path.join(args.outdir, "clash-standalone.yaml"), "w", encoding="utf-8") as f:
        f.write(build_standalone_yaml(args.server, c, p, args.up, args.down))
    with open(os.path.join(args.outdir, "nodes.txt"), "w", encoding="utf-8") as f:
        f.write(reality_uri + "\n" + hy2_uri + "\n")
    with open(os.path.join(args.outdir, "qrcodes.txt"), "w", encoding="utf-8") as f:
        f.write(f"{p}-Reality 二维码:\n{qr_url(reality_uri)}\n\n")
        f.write(f"{p}-HY2 二维码:\n{qr_url(hy2_uri)}\n")

    print("已生成客户端配置到:", os.path.abspath(args.outdir))
    for fn in ("clash-verge-inject.js", "clash-standalone.yaml", "nodes.txt", "qrcodes.txt"):
        print("  -", fn)
    print("\n分享链接:")
    print(" ", reality_uri)
    print(" ", hy2_uri)

if __name__ == "__main__":
    main()
