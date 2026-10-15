# 云安全组放行（必做，agent 无法代办）

云主机有**两道防火墙**：主机内的 ufw（`deploy.sh` 已配）+ 云厂商的**安全组**（独立、需在控制台手动开）。
安全组没放行，客户端一定连不通。

需要放行的**入站(Inbound)**规则：

| 协议/端口 | 用途 | 备注 |
|---|---|---|
| `TCP 443` | VLESS-Reality | |
| `UDP 8443`（或你设的 HY2 端口） | Hysteria2 | **必须是 UDP**，放成 TCP 会一直 timeout |
| `TCP 22` | SSH | 一般默认已开 |

来源(Source)填 `0.0.0.0/0`（任意）。

---

## 腾讯云（轻量 / CVM）

- **轻量应用服务器**：实例详情 → 防火墙 → 添加规则。
- **CVM**：实例 → 安全组 → 配置规则 → 入站规则 → 添加。
- 提示：8888、8080 等被腾讯云标为"高危端口"（易被扫描），本方案用 443 + 8443，无需碰高危端口。

## 阿里云 ECS

实例 → 安全组 → 配置规则 → 入方向 → 手动添加：TCP 443、UDP 8443。

## AWS EC2

EC2 → Security Groups → Inbound rules → Edit：
- Custom TCP, Port 443, Source 0.0.0.0/0
- Custom UDP, Port 8443, Source 0.0.0.0/0

## 其它（Vultr / DigitalOcean / Hetzner 等）

多数默认放开所有入站（仅靠主机 ufw）；若面板里有 Firewall/Cloud Firewall 功能且启用了，
按上表放行 TCP 443 与 UDP 8443。

---

## 验证是否放行成功

在服务器上抓包，然后让客户端尝试连接：
```bash
# Reality（TCP 443）：应看到来自你客户端 IP 的包
timeout 8 tcpdump -nni any 'tcp port 443' 2>/dev/null | head
# HY2（UDP 8443）：0 包 = 安全组 UDP 没放行
timeout 8 tcpdump -nni any 'udp port 8443' 2>/dev/null | head
```
