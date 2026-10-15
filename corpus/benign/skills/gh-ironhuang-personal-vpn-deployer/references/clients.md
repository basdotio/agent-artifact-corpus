# 客户端导入指南

`scripts/gen_client.py` 产出的文件对应不同客户端。下面给每种客户端的推荐做法。

节点名默认前缀「自建」，可用 `--name-prefix` 改。

---

## Clash Verge Rev（Windows / macOS，桌面首选）

### 情况 A：已有机场订阅 → 用 Script 注入（强烈推荐）

优点：自建节点注入到现有订阅里，**订阅更新不会冲掉**，单一事实源。

1. 打开生成的 `clash-verge-inject.js`，复制全部内容。
2. Clash Verge → 订阅页 → 当前订阅卡片右键 →「编辑」→ 找到 Script 覆写并粘贴保存；
   或订阅页顶部工具栏「全局扩展脚本」粘贴。
3. 订阅卡片右键 →「重新加载」。
4. 代理组里会出现 `自建-Reality`、`自建-HY2` 和 `🏠 自建` 分组。

> 脚本会把两个节点插到主组 `Proxy`/`Auto` 顶部（若存在），并新建 `🏠 自建` fallback 分组
> （优先 Reality，断了自动切 HY2）。若你的机场把主组改了名，两个节点仍在 `🏠 自建` 里，
> 只是不会自动进主组——把脚本里 `"Proxy"`/`"Auto"` 改成你的组名即可。

### 情况 B：无订阅 → 本地导入独立配置

Clash Verge → 订阅页 → 新建「本地(Local)」配置 → 粘贴 `clash-standalone.yaml` 保存。

---

## Clash Meta / mihomo（Android，CMFA）

> CMFA 扫码只认 `https://` 订阅链接，**不认 `vless://`/`hysteria2://` 节点 URI**。所以：

- **推荐**：把 `clash-standalone.yaml` 传到手机（微信文件传输/网盘/AirDrop），
  CMFA → 配置 → 从本地文件导入。
- 或：若你在服务器上用高位端口 + 随机 token 临时托管了订阅 YAML，用「从 URL 导入」粘贴该链接
  （用完记得关端口，别长期明文暴露凭据）。

---

## Shadowrocket（iOS）

版本要求：2.2.36+（Reality）、2.2.30+（HY2）。

- **最快**：复制 `nodes.txt` 里的 URI，Shadowrocket 首页右上「+」→「从剪贴板」；或扫
  `qrcodes.txt` 里的二维码。
- 手动填：类型 VLESS，TLS 选 Reality，填入 UUID / SNI(=dest) / PublicKey / ShortID /
  指纹 chrome / Flow xtls-rprx-vision；HY2 同理填密码/obfs/SNI/跳过证书验证。

---

## 二维码

`qrcodes.txt` 里是两个节点的二维码图片链接（在线渲染）。在能联网的设备打开链接即可显示二维码，
供手机客户端扫描。二维码内容是明文凭据，别公开分享。

---

## 验证是否生效

客户端选中 `自建-Reality`，浏览器访问 IP 查询页（如 `https://api.ipify.org`），
出口 IP 应等于你的服务器公网 IP。切到 `自建-HY2` 再测一次。
