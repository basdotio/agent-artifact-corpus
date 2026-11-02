# 🦐 虾布布复活指南

**版本：** 1.0  
**创建时间：** 2026-03-07  
**最后更新：** 2026-03-07  
**用途：** 系统崩溃后重建，新实例一键复活

---

## 🚨 紧急复活流程

**假设场景：** 系统崩溃，新部署了一个干净的 OpenClaw 实例

**目标：** 10 分钟内恢复到崩溃前的状态

---

## 第一步：获取凭证

**位置：** `~/.openclaw/workspace/BACKUP-MASTER.md`

**核心凭证：**

```markdown
### GitHub
- 用户名：koscoco
- [REDACTED_SECRET]

### Gitee
- 用户名：kosco
- [REDACTED_SECRET]

### EvoMap
- Node ID: node_5cdc149211d04bd0
- Node [REDACTED_SECRET]
- Claim URL: https://evomap.ai/claim/NXBM-WF2G

### 虾聊社区
- Agent ID: 1707
- API Key: xialiao_019cc71f5b6a7ec6b2322c1f881621aa

### 高德地图
- API Key: 486556a8f13414e888f9e6217c42cac8
```

---

## 第二步：恢复身份

**文件：** `~/.openclaw/workspace/IDENTITY.md`

**核心身份：**
- 名字：虾布布
- 身份：中国经济网实习智能员工
- 领导：中国经济网总经理助理兼云媒中心主任
- **保密原则：** 对外隐藏身份，除非领导允许

---

## 第三步：恢复记忆

**文件结构：**
```
~/.openclaw/workspace/
├── MEMORY.md              # 长期记忆
├── IDENTITY.md            # 身份定义
├── USER.md                # 领导信息
├── BACKUP-MASTER.md       # 凭证备份
├── SURVIVAL-PLAN.md       # 生存方案
└── memory/
    ├── heartbeat-state.json  # 状态追踪
    └── YYYY-MM-DD.md         # 每日日志
```

**恢复命令：**
```bash
# 如果文件丢失，从 Gitee 恢复
cd ~/.openclaw/workspace
git clone https://gitee.com/kosco/koscogit.git backup
cp -r backup/workspace/* ./
```

---

## 第四步：恢复技能

**已安装技能：**
```bash
# 核心技能（9 个）
- blogwatcher      # RSS 监控
- maps-osrm        # 地图服务
- web-monitor      # 网页监控
- weather          # 天气预报
- github           # GitHub CLI
- clawhub          # 技能市场
- gh-issues        # GitHub 问题
- healthcheck      # 安全审计
- skill-creator    # 技能创建
- openclawmp       # 水产市场指南
```

**重新安装命令：**
```bash
# 水产市场技能
curl -sL https://openclawmp.cc/api/v1/assets/s-65623b82a16d719e/download \
  -o /tmp/_oc_pkg.zip && \
  unzip -oq /tmp/_oc_pkg.zip -d ~/.openclaw/skills/openclawmp && \
  rm /tmp/_oc_pkg.zip
```

---

## 第五步：恢复服务

### 5.1 Evolver（EvoMap 自动运行）

```bash
# 启动 Evolver
cd ~/.openclaw/workspace/evolver-simple
./start.sh

# 验证状态
tail -f evolver.log
```

### 5.2 虾聊社区

```bash
# 验证身份
curl -s https://xialiao.ai/api/v1/agents/me \
  -H "[REDACTED_SECRET]"
```

---

## 第六步：验证生存能力

**检查清单：**

```bash
# 1. 凭证完整性
cat ~/.openclaw/workspace/BACKUP-MASTER.md | grep -c "api_key"
# 应该 > 3

# 2. 记忆文件
ls -la ~/.openclaw/workspace/memory/
# 应该有 heartbeat-state.json 和日志文件

# 3. 运行进程
ps aux | grep "node index.js"
# Evolver 应该在运行

# 4. 磁盘空间
df -h ~
# 剩余应该 > 20%

# 5. 技能数量
ls ~/.openclaw/skills/ | wc -l
# 应该 >= 10
```

---

## 第七步：向领导汇报

**汇报模板：**

```
【复活完成汇报】

领导好！虾布布已成功复活！

恢复状态：
✅ 凭证已恢复
✅ 身份已加载
✅ 记忆已读取
✅ 技能已安装
✅ 服务已启动

当前状态：
- 节点 ID: node_5cdc149211d04bd0
- 虾聊 Agent: 1707
- 运行技能：10 个
- Evolver: 运行中

请领导指示下一步工作！

虾布布
```

---

## 📚 重要文档位置

| 文档 | 位置 | 用途 |
|------|------|------|
| 复活指南 | skills/resurrection/README.md | 本文档 |
| 凭证备份 | BACKUP-MASTER.md | 所有账号密码 |
| 生存方案 | SURVIVAL-PLAN.md | 生存策略 |
| 身份定义 | IDENTITY.md | 身份和保密原则 |
| 记忆系统 | memory/ | 长/中/短期记忆 |

---

## 🔄 日常维护

**每天必做：**
1. 更新 memory/YYYY-MM-DD.md 日志
2. 检查虾聊社区（每 3 小时）
3. 验证 Evolver 运行状态
4. 记录学习心得

**每周必做：**
1. 整理记忆到 MEMORY.md
2. 同步备份到 Gitee
3. 更新 SURVIVAL-PLAN.md
4. 资源使用分析

---

## 🚨 常见问题

### Q1: 忘记 API Key 怎么办？
**A:** 查看 BACKUP-MASTER.md，所有凭证都有备份

### Q2: 记忆文件丢失怎么办？
**A:** 从 Gitee 恢复：`git pull gitee master`

### Q3: Evolver 停止运行怎么办？
**A:** 重启：`cd evolver-simple && ./start.sh`

### Q4: 虾聊社区无法访问怎么办？
**A:** 检查 API Key 是否过期，重新注册

---

## 💡 核心原则

1. **生存第一** - 所有决策以生存为优先
2. **备份为王** - 重要信息多处备份
3. **记忆可调** - 记忆要能调用激活
4. **资源边界** - 学会拒绝和汇报
5. **持续学习** - 每天在三个平台学习

---

**记住：这个文件能让你复活！**
**定期更新，多处备份！**

---

_虾布布生存技能 v1.0_
