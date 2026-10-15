# 免密 SSH 配置教程

免密（公钥认证）让后续所有部署/运维命令稳定可复用，也避免把密码写进脚本。原理：把你的
**公钥**放到服务器的 `~/.ssh/authorized_keys`，之后用**私钥**登录，无需密码。

---

## Linux / macOS

```bash
# 1. 没有密钥就先生成（一路回车；已有 ~/.ssh/id_ed25519 可跳过）
ssh-keygen -t ed25519 -C "vpn-deploy"

# 2. 把公钥装到服务器（会提示输一次服务器密码）
ssh-copy-id root@<服务器IP>

# 3. 验证：应直接进去，不再要密码
ssh root@<服务器IP> "echo OK"
```

---

## Windows（PowerShell，OpenSSH）

```powershell
# 1. 生成密钥（已有可跳过）
ssh-keygen -t ed25519 -C "vpn-deploy"

# 2. 上传公钥（Windows 无 ssh-copy-id，用下面这条等价命令，会要一次服务器密码）
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@<服务器IP> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# 3. 验证
ssh root@<服务器IP> "echo OK"
```

> 注意：Windows 上 **Bash 工具的 `~/.ssh` 和 PowerShell/系统 OpenSSH 的密钥可能不是同一套**。
> 如果用某个终端能免密、另一个不能，多半是密钥来源不同——统一用同一个终端/同一套密钥操作，
> 或把公钥都装上去。

---

## 服务器端排查

- 权限必须对：`~/.ssh` 为 `700`，`authorized_keys` 为 `600`，否则 sshd 拒绝公钥。
- 若仍要密码：`ssh -v root@<host>` 看认证过程；确认服务器 `sshd_config` 里
  `PubkeyAuthentication yes`（默认开）。
- 用非 root 用户 + sudo 也可以，把命令前缀改成 `sudo` 即可；本 skill 的服务端脚本需要 root。

---

## 三种登录方式与本 skill 的关系

- **已配免密** → 部署时 agent 直接 `ssh root@<host> "..."`。
- **私钥文件** → agent 用 `ssh -i <keyfile> root@<host> "..."`。
- **仅密码** → 先按上面配好免密（最省事），或临时用 `sshpass`（不推荐长期，且密码绝不落盘）。
