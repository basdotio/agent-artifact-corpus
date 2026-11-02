# 快速开始指南

## 第一次使用

### 1. 准备工作

**⚠️ 重要：每次使用前都需要提供你的 API Key**

当你第一次使用时，Agent 会询问你的 API Key：

```
Agent: 创建虚拟伴侣需要两个 API Key：

1. Vidu API Key（用于生成图片和视频）
   - 格式：vda_ 开头
   - 获取：platform.vidu.cn 注册后在控制台获取

2. Tavily API Key（用于搜索角色信息和照片）
   - 格式：tvly- 开头
   - 获取：tavily.com 注册后获取

请提供你的 API Key（格式：Vidu: xxx, Tavily: xxx）：
```

**提供后，Agent 会自动配置环境变量（仅在当前 session 有效）。**

**⚠️ 安全提示：**
- 不要将 API Key 保存到文件
- 不要在日志中记录完整的 API Key
- 测试完成后清除环境变量：`unset VIDU_KEY TAVILY_API_KEY`

### 2. 创建角色

直接和 Agent 对话：

```
用户：我想创建一个虚拟男友
Agent：好的！你想创建哪个角色？
...
```

### 3. 后续互动

创建角色后，你可以：
- 和角色聊天
- 要求角色发照片
- 要求角色发视频
- 配置整点视频推送

## 常用命令

```bash
# 测试推送
./scripts/push-daemon.sh test

# 启动守护进程
./scripts/push-daemon.sh start

# 查看状态
./scripts/push-daemon.sh status
```

