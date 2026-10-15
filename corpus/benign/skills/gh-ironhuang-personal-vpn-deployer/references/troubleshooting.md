# 排障手册（按真实故障频率排序）

本手册来自一次真实的长期运维:从部署、换 IP 迁移到反复被 GFW 干扰的完整踩坑记录。每条都给出
**判定命令**和**修复**。服务端命令均在服务器上以 root 运行。

---

## 0. 通用体检

先跑 `scripts/diagnose.sh`(scp 到服务器执行),它把下面第 1~4 类一次性过一遍。手动版:

```bash
systemctl is-active sing-box
ss -tlnp | grep ':443 '      # Reality 监听
ss -ulnp | grep ':8443'      # HY2 监听
journalctl -u sing-box -n 30 --no-pager
```

---

## 1. Reality 突然 timeout(配置没动,尤其换 IP / 换机房后)——头号坑

**症状**:客户端 Reality 节点 timeout/EOF;本机自测也失败;但 HY2 可能正常。

**根因**:REALITY 服务端在**每次握手时会实时把连接转发到伪装目标 dest(如 `www.microsoft.com:443`)
去"借"真 TLS 握手**。所以 dest 从**本服务器**的可达性是硬依赖。换 IP/机房后,到某个 dest 的路由
可能变成"TLS 握手能过、但 TLS 之后数据流卡死",REALITY 转发就失败 → 客户端 EOF。**这与监听端口
无关**,所以换端口没用。

**判定命令**(在服务器上测 dest):
```bash
curl -o /dev/null -s -w 'connect=%{time_connect}s tls=%{time_appconnect}s http=%{http_code} total=%{time_total}s\n' \
  --max-time 12 https://<当前dest>/
```
- 正常:`http=200/301/302` 且 total 很小。
- **坏掉特征**:`tls` 秒过(如 0.07s)但 `http=000` 且 `total` 顶满 max-time(如 12s)——就是它。

**修复**:换一个从本服务器实测正常的 dest(需 TLS1.3 + h2)。三处必须同步改成同一域名,密钥全不变:
1. 服务端 `config.json` 的 `tls.server_name`
2. 服务端 `config.json` 的 `reality.handshake.server`
3. 客户端的 `servername`(Clash)/ `sni`(URI)

```bash
sed -i 's/旧dest/新dest/g' /etc/sing-box/config.json
sing-box check -c /etc/sing-box/config.json && systemctl restart sing-box
```
候选可用 dest:`www.apple.com` / `www.cloudflare.com` / `www.bing.com` / `dl.google.com`。
`deploy.sh` 的自动优选逻辑就是干这个,重装或手动挑都行。

**真实案例**:换公网 IP 后 `www.microsoft.com` 从新 IP `tls=0.07s http=000 total=12s`(卡死),
Reality 全部 EOF、客户端被迫落机场;换成 `www.apple.com`(实测 http=200)后秒恢复。

---

## 2. Reality 偶发断线、延时时不时 Error

**症状**:大多数时候能用,但隔段时间断一下、很快又自己好;手动测延时偶尔 Error。

**判定**:
```bash
journalctl -u sing-box --since "3 min ago" --no-pager | grep -c "processed invalid connection"
journalctl -u sing-box --since "3 min ago" --no-pager | grep "processed invalid" \
  | grep -oE "from [0-9.]+" | sort | uniq -c | sort -rn | head
```
- 一个**正常的 Reality 客户端应产生 0 次** invalid。
- 若大量 invalid **集中在你自己的出口 IP**(几十次/分钟) = 你→服务器路径上的握手被 GFW 篡改。
- 若少量、分散在各种境外 IP = 背景扫描,正常噪音,忽略。

**根因**:该服务器 IP 跑 Reality 用久了(常见几周)被 GFW 标记,开始间歇性干扰 443 上的 TLS 握手。

**修复**(按性价比):
1. **换公网 IP**(云控制台几分钟,最直接;换后见第 1 条重测 dest)。
2. **套 Cloudflare CDN**:改 VLESS+WS+TLS 走 CDN,客户端连的是 Cloudflare 共享 IP 池,
   GFW 无法整段封 → 从根上摆脱"IP 被盯"。需域名,回国线路要优选 IP,稳但不一定更快。
3. **别换端口**:见下条。
4. 兜底:fallback 分组里放 HY2,Reality 被干扰时自动切。

---

## 3. 换端口对 Reality 是反效果(重要反直觉)

"换端口躲扫描"对 Shadowsocks 有用,但对 **REALITY 恰恰相反**。REALITY 的隐蔽性依赖伪装成
"浏览器正常访问 https://dest"——真实浏览器只在 **443** 访问网站。把它挪到高位端口(如 31459),
DPI 会看到"某高位端口上带着知名站点 SNI 的 TLS 握手",没有任何浏览器会这么做 → 一眼识破 → 干扰。

**真实案例**:为躲扫描把 Reality 从 443 换到 31459,结果客户端 100% invalid/timeout,比在 443
上的偶发干扰糟糕得多,已全部改回 443。**Reality 请永远待在 443。**

---

## 4. HY2 一直 timeout

**判定**:抓包看 UDP 包有没有到服务器。
```bash
timeout 8 tcpdump -nni any 'udp port 8443' 2>/dev/null | head
```
0 包 = 外部 UDP 根本没到。

**根因 & 修复**:云安全组只放了 **TCP**。HY2 走 **UDP**,必须在安全组单独放行
`UDP <HY2端口>`。见 `cloud-security-group.md`。

---

## 5. HY2 慢(YouTube / 大流量卡)

**根因**:国内运营商/GFW 对 **UDP/QUIC 做 QoS 限速**,持续大带宽流量(视频、实时数据)被打击
最狠。TCP(Reality)不受此限。这是路径级限制,不是配置 bug。

**要点**:
- **保留 HY2 的 `up`/`down`(Brutal 定速),别去掉换 BBR**。国内是丢包型干扰,Brutal 无视丢包
  硬发比 BBR 退让式更快。数值设在略低于实际带宽(如 up 30 / down 150),太高会自造丢包。
- **端口跳跃(port hopping)**:让 HY2 在一段 UDP 端口范围内跳,规避对固定端口的 QoS,通常提速。
  需在云安全组放行一段 UDP 端口范围。
- **要视频级速度**还是得靠通畅的 Reality(TCP);HY2 定位是抗干扰的兜底。

**真实教训**:曾把 HY2 的 up/down 去掉想换 BBR,结果从"慢"变"超级慢",改回 Brutal 才回血。

---

## 6. claude.ai / GitHub 用自建节点不通或慢

**现象**:自建节点(机房 IP)访问 claude.ai 报错/连不上;GitHub clone 极慢。机场节点却正常。

**根因**:
- **claude.ai**:其 Cloudflare 对"数据中心/机房 ASN"的 IP 做风控挑战。浏览器能解 JS 挑战、
  勉强过;手机 App 的登录 webview 过不了 → "连接不行"。机房 IP 属性改不掉。
- **GitHub**:大陆机房到 GitHub(Azure)国际链路慢(实测约 3 MB/s),大仓库 clone 超时;
  香港/新加坡机场节点离 GitHub 近,快。

**修复**:把这些域名**分流到干净节点(机场)**,不走自建机房 IP。Clash 规则(prepend,优先级最高):
```yaml
prepend:
  - DOMAIN-KEYWORD,github,🐙 干净节点组
  - DOMAIN-SUFFIX,claude.ai,🐙 干净节点组
  - DOMAIN-SUFFIX,anthropic.com,🐙 干净节点组
```
再建一个只含非自建节点的 url-test 分组做"干净节点组"。自建节点适合跑不挑 IP 信誉的普通流量。

---

## 7. SSH 走在隧道里(运维 agent 必读)

**现象**:每次重启服务器上的 sing-box,你的 SSH 就断"Connection closed by remote host"。

**原因**:你的运维机器开了 TUN/全局代理,到服务器的 SSH 流量本身走了这台服务器的代理隧道。
重启 sing-box = 掐断隧道 = SSH 断。

**应对**:
- 属正常现象,等几秒重连即可。
- 关键操作写成**自包含后台脚本**:脚本内 `systemctl restart` + 等待 + 干活 + 结果写文件,
  用 `setsid bash script.sh &` 跑,SSH 断了不影响脚本,重连再 `cat` 结果文件。
- 或临时把代理切到别的节点/关 TUN 再操作服务器。

---

## 8. 从 Windows 用 SSH 喂脚本报 `set/sed: command not found`

PowerShell 管道会给内容加 UTF-8 BOM 且用 CRLF,污染远端脚本第 1 行。修复:
```
$s | ssh root@<host> "sed '1s/^\xEF\xBB\xBF//' | tr -d '\r' | bash -s"
```
或直接 `scp` 脚本上去再执行(推荐,最稳)。

---

## 附:快速回滚

`deploy.sh` 不覆盖已存在的备份。改 config 前手动备份:
```bash
cp /etc/sing-box/config.json /etc/sing-box/config.json.bak.$(date +%s)
```
出问题:`cp <备份> /etc/sing-box/config.json && systemctl restart sing-box`。
