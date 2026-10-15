# 贡献指南

感谢您对 OpenClaw --xiaozhi  MCP Server 项目的关注！欢迎任何形式的贡献，包括代码提交、问题报告、文档改进等。

## 📋 目录

- [行为准则](#行为准则)
- [贡献方式](#贡献方式)
- [开发环境设置](#开发环境设置)
- [提交代码](#提交代码)
- [代码规范](#代码规范)
- [测试](#测试)
- [Pull Request 流程](#pull-request-流程)

---

## 行为准则

本项目遵循 [Contributor Covenant](https://www.contributor-covenant.org/) 行为准则。请对所有参与者保持尊重和友善。

---

## 贡献方式

### 1. 报告问题

发现 Bug？请创建 Issue 并包含：
- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（Python 版本、操作系统等）

### 2. 功能建议

有新功能想法？请创建 Issue 并说明：
- 功能描述
- 使用场景
- 预期效果

### 3. 改进文档

文档有误或不清晰？欢迎提交 PR 改进！

### 4. 提交代码

修复 Bug 或添加新功能？请参考以下流程。

---

## 开发环境设置

### 1. Fork 项目

在 GitHub 上 Fork 本项目到您的账户。

### 2. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/openclaw-xiaozhi-mcp-server.git
cd openclaw-xiaozhi-mcp-server
```

### 3. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 激活虚拟环境（macOS/Linux）
source venv/bin/activate
```

### 4. 安装开发依赖

```bash
pip install -r requirements.txt
```

### 5. 配置环境变量

```bash
# 复制示例配置
copy .env.example .env

# 编辑 .env 文件，设置您的 OPENCLAW_TOKEN
notepad .env
```

### 6. 验证环境

```bash
# 运行环境检查
python check_env.py

# 运行测试
python test_mcp_full.py
```

---

## 提交代码

### 1. 创建分支

```bash
# 确保基于最新的主分支
git checkout main
git pull upstream main

# 创建功能分支
git checkout -b feature/your-feature-name
# 或修复分支
git checkout -b fix/issue-123
```

### 2. 编写代码

遵循项目的代码规范和结构。

### 3. 提交更改

```bash
# 添加更改
git add .

# 提交（使用清晰的提交信息）
git commit -m "feat: 添加新功能

- 功能描述 1
- 功能描述 2

Closes #123"
```

### 4. 推送分支

```bash
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

在 GitHub 上创建 Pull Request，填写：
- 变更描述
- 关联的 Issue
- 测试说明

---

## 代码规范

### Python 代码风格

遵循 [PEP 8](https://pep8.org/) 规范：

```python
# ✅ 推荐
def calculate_total(items: list) -> float:
    """计算总金额。
    
    Args:
        items: 商品列表
        
    Returns:
        总金额
    """
    return sum(item.price for item in items)

# ❌ 不推荐
def calc(l):
    return sum(i.price for i in l)
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量 | 小写 + 下划线 | `user_name` |
| 函数 | 小写 + 下划线 | `get_user_info()` |
| 类 | 大驼峰 | `MCPClient` |
| 常量 | 大写 + 下划线 | `MAX_RETRY` |
| 私有成员 | 单下划线前缀 | `_internal_method()` |

### 类型注解

推荐使用类型注解：

```python
from typing import Optional, Dict, Any

async def process_intent(
    intent: str, 
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """处理用户意图"""
    pass
```

### 文档字符串

所有公共函数和类应包含文档字符串：

```python
class OpenClawClient:
    """OpenClaw WebSocket 客户端。
    
    负责与小智 MCP 服务器建立和维护 WebSocket 连接。
    """
    
    async def connect(self):
        """连接到 WebSocket 服务器。
        
        Raises:
            ConnectionError: 连接失败时抛出
        """
        pass
```

---

## 测试

### 运行现有测试

```bash
# 运行完整 MCP 测试
python test_mcp_full.py

# 运行客户端测试
python test_client.py

# 运行环境检查
python check_env.py
```

### 添加新测试

为新增功能添加测试用例：

```python
# test_new_feature.py
import unittest
from server import process_intent

class TestNewFeature(unittest.TestCase):
    async def test_process_intent_returns_task_id(self):
        """测试 process_intent 返回任务 ID"""
        result = await process_intent("test intent")
        self.assertIn("task_id", result)
        self.assertEqual(result["status"], "processing")

if __name__ == "__main__":
    unittest.main()
```

---

## Pull Request 流程

### 1. 创建 PR

- Fork 项目
- 创建功能分支
- 提交更改
- 推送到 GitHub
- 创建 Pull Request

### 2. PR 模板

```markdown
## 变更描述
简要描述此 PR 的变更内容

## 关联 Issue
Closes #123

## 测试说明
- [ ] 已运行现有测试
- [ ] 已添加新测试
- [ ] 已手动验证功能

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 已添加必要的文档
- [ ] 提交信息清晰
```

### 3. 代码审查

- 维护者将审查代码
- 可能需要修改
- 审查通过后合并

### 4. 合并

- PR 合并到主分支
- 删除功能分支

---

## 发布流程

### 版本号规范

遵循 [Semantic Versioning](https://semver.org/)：

- `MAJOR.MINOR.PATCH` (如 `1.2.3`)
- `MAJOR`: 不兼容的 API 变更
- `MINOR`: 向后兼容的功能添加
- `PATCH`: 向后兼容的 Bug 修复

### 发布步骤

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git 标签
4. 发布 GitHub Release

---

## 常见问题

### Q: 如何开始第一次贡献？

A: 查看标记为 `good first issue` 的 Issue，这些适合新手。

### Q: 不确定如何开始？

A: 可以在 Issue 中留言，维护者会提供帮助。

### Q: 代码审查需要多久？

A: 通常 1-3 个工作日，取决于维护者的时间。

---

## 联系方式

- GitHub Issues: 提问和讨论
- Email: （如有）

---

感谢您的贡献！🎉