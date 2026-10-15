---
name: personal-vpn-deployer
description: >-
  在用户自己的服务器上一键部署个人自用翻墙节点（sing-box VLESS-Reality + Hysteria2 双栈），
  并生成 Clash Verge / Clash Meta / Shadowrocket 客户端配置。只要用户提供服务器地址与一种
  SSH 登录方式（密码 / 私钥文件 / 已配好免密），即可全自动完成服务端安装、凭据生成、伪装目标
  优选、防火墙、启动自测。当用户提到"部署 VPN / 搭梯子 / 自建节点 / sing-box / Reality /
  Hysteria2 / 科学上网服务端 / 翻墙服务器 / 机场自建 / 客户端配置生成"等，或想在自己的 VPS 上
  搭建、修复、迁移个人代理节点时，都应使用本 skill。也覆盖换 IP 迁移、Reality 握手失败、HY2 慢
  等常见故障的排查修复。
---

# personal-vpn-deployer

在用户**自己拥有**的服务器上部署个人自用的 sing-box 双协议节点，并产出客户端配置。

- **VLESS-Reality（TCP/443）**：主力，速度快，无需域名/证书（借用大站 TLS 伪装）。
- **Hysteria2（UDP，salamander 混淆）**：断线兜底，抗 TCP 干扰。

> 使用前置：这必须是用户**自己有权操作**的服务器（VPS/云主机）。本 skill 用于个人自用与
> 学习，不用于协助未授权访问他人系统。若用户描述的目标不是自己的服务器，停下并澄清。

## 何时用哪一步

整个流程分五步。根据用户当前所处阶段直接切入，别从头复述：

1. **收集输入** → 2. **建立 SSH** → 3. **服务端部署** → 4. **生成客户端配置** → 5. **验证 & 排障**

---

## 第 1 步：收集输入

问清并确认：

- **服务器地址**：公网 IP 或域名（客户端配置要用它连）。
- **SSH 登录方式**（三选一）：
  - **密码**：用户直接给 root（或可 sudo 的）密码。
  - **私钥文件**：用户给出私钥路径（如 `~/.ssh/id_ed25519`）。
  - **已配免密**：`ssh root@<host>` 已能直接登录。若用户还没配、想配，见
    `references/passwordless-ssh.md`（含 Windows 与 Linux/Mac 教程）。
- **可选**：HY2 端口（默认 8443）、节点名前缀（默认「自建」）、是否已有 Clash 订阅
  （有的话优先用 Script 注入方式，订阅更新不丢；见第 4 步）。

> **Reality 端口固定 443，不要问用户要不要改。** 换高位端口会撕掉 Reality 的 HTTPS 伪装、
> 反而更易被 DPI 识破。原因见 `references/troubleshooting.md`。

确认服务器归属后再继续。

---

## 第 2 步：建立 SSH 连接

目标：得到一个能对服务器执行命令的 SSH 通道。三种方式：

- **私钥文件**：`ssh -i <keyfile> root@<host> "..."`
- **已配免密**：`ssh root@<host> "..."`
- **仅有密码**：优先引导用户把公钥装上去实现免密（见 `references/passwordless-ssh.md`，
  一条 `ssh-copy-id` 或等价命令即可），这样后续所有步骤稳定可复用。若确需用密码直连且
  环境有 `sshpass`，可 `sshpass -p '<pw>' ssh ...`——但**绝不要把密码写进任何会被提交/
  保存的文件**。

### 平台注意（Windows 上执行 SSH 的 agent 必读）

- 在 Windows 用 PowerShell 把**多行 bash 脚本**通过管道喂给远端 `bash -s` 时，PowerShell
  会加 UTF-8 BOM、并可能用 CRLF 换行，导致远端第 1 行报 `set: command not found` 之类。
  稳妥写法：
  ```
  $s = Get-Content -Raw scripts/deploy.sh
  $s | ssh root@<host> "sed '1s/^\xEF\xBB\xBF//' | tr -d '\r' | bash -s"
  ```
  或者直接 `scp scripts/deploy.sh root@<host>:/tmp/ && ssh root@<host> "bash /tmp/deploy.sh"`
  （更稳，推荐）。
- **若 agent 自己的网络出口正走着这台服务器的隧道**：重启 sing-box 会瞬断你的 SSH。
  这是正常现象，等几秒重连即可；关键操作可写成"后台脚本跑完把结果写文件、重连再读"。
  详见 `references/troubleshooting.md` 的「SSH 走在隧道里」。

---

## 第 3 步：服务端部署

把 `scripts/deploy.sh` 传到服务器并以 root 运行（推荐 scp 后执行，避免管道编码问题）：

```bash
scp scripts/deploy.sh root@<host>:/tmp/deploy.sh
ssh root@<host> "REALITY_PORT=443 HY2_PORT=8443 bash /tmp/deploy.sh"
```

`deploy.sh` 会依次：开 BBR → 装 sing-box → 生成密钥/UUID/short_id/HY2 密码/自签证书 →
**自动优选 Reality 伪装目标 dest**（实测候选站点，选出从本服务器 TLS 后仍能正常返回数据的）
→ 写 `config.json` → 配 ufw → 启动 → 本机自测 → 打印凭据 JSON。

**抓取凭据**：脚本会在 stdout 输出被 `===VPN_CREDS_BEGIN===` / `===VPN_CREDS_END===`
包裹的 JSON，并存到服务器 `/etc/sing-box/creds.json`（chmod 600）。把这段 JSON 存到本地
一个文件（如 `client-configs/creds.json`）供第 4 步使用。

### ⚠️ 必须提醒用户的手动步骤：云安全组

主机 ufw 只是第一道；**云厂商的安全组是独立的第二道防火墙**，agent 无法代改。必须提醒用户
在控制台放行**入站**：
- `TCP 443`（Reality）
- `UDP <HY2端口>`（默认 8443）—— 注意是 **UDP**，只放 TCP 会导致 HY2 一直 timeout。

各家路径见 `references/cloud-security-group.md`（腾讯云 / 阿里云 / AWS）。没放行前客户端连不通。

---

## 第 4 步：生成客户端配置

用 `scripts/gen_client.py`（纯 Python，跨平台）从凭据生成所有客户端配置：

```bash
python scripts/gen_client.py --server <host> --creds client-configs/creds.json --outdir client-configs
```

产出（都在 `client-configs/`）：
- `clash-verge-inject.js`：Clash Verge Rev 的 **Script 覆写**——注入到用户**现有订阅**，
  订阅更新不会冲掉自建节点。**用户已有订阅时首选这个**。
- `clash-standalone.yaml`：独立 Clash/mihomo 配置，供 Clash Meta 本地导入或无订阅用户使用。
- `nodes.txt`：`vless://` 与 `hysteria2://` 分享链接（Shadowrocket / Clash Meta 可直接粘贴）。
- `qrcodes.txt`：两个节点的二维码图片链接，手机可扫。

各客户端（Clash Verge / Clash Meta / Shadowrocket）的具体导入步骤、注意事项，见
`references/clients.md`。

> HY2 客户端默认带 `up/down`（Brutal 定速）。**不要为了"自适应"去掉它们**——国内 UDP 是
> 丢包型限速，Brutal 无视丢包硬发，比 BBR 退让式更快。原因见 `references/troubleshooting.md`。

---

## 第 5 步：验证 & 排障

- **服务端自测**：`deploy.sh` 末尾已做本机 REALITY 自测并回显出口 IP。任何时候都可再跑
  `scripts/diagnose.sh`（scp 到服务器执行）做完整体检。
- **客户端验证**：让用户在客户端选中 Reality 节点，访问 IP 查询页，出口 IP 应等于服务器 IP。

遇到问题查 `references/troubleshooting.md`，它按真实故障频率排序，收录了以下高频坑（每条都有
判定命令和修复）：

| 症状 | 头号原因 | 一句话修复 |
|---|---|---|
| Reality 突然 timeout（配置没动，尤其换 IP/机房后） | dest 从本服务器 TLS 后卡死 | 重选 dest，改服务端 `server_name`+`handshake.server` 与客户端 `servername` |
| Reality 偶发断线、延时 Error | 该 IP 被 GFW 盯上、间歇干扰握手 | 换公网 IP / 套 Cloudflare CDN；别换端口 |
| HY2 慢（YouTube/大流量） | 国内 UDP QoS 限速 | 保留 Brutal up/down、端口跳跃；大带宽仍建议走 Reality |
| HY2 一直 timeout | 云安全组只放了 TCP | 安全组放行 **UDP** 端口 |
| claude.ai / GitHub 用自建 IP 不通或慢 | 机房 IP 被目的站风控 | 这两类域名分流走干净节点（机场），见 troubleshooting |

---

## 关键设计原则（务必遵守）

1. **Reality 固定 443**——伪装依赖它待在 443。
2. **dest 必须实测优选**——不能假设某个固定域名总可用；换 IP 后尤其要重测。
3. **HY2 UDP 端口在云安全组要单独放行**，且是 UDP。
4. **凭据是敏感信息**——private key、UUID、密码等。生成的配置含明文凭据，别发到公开渠道；
   提醒用户离线备份。若要在服务器上临时托管订阅文件供手机拉取，用高位端口 + 随机 token，
   用完即关（见 troubleshooting）。
5. **服务器绑 `0.0.0.0`**——换公网 IP 时服务端配置不用改，只改客户端里的 server 地址
   （但要重测 dest 可达性，见第 5 步表格第一行）。
