# 青马易战自动答题MCP服务

青马易战平台设计的 Model Context Protocol (MCP) 服务器，提供自动答题功能。

## 功能特性

- 🎓 获取课程列表和信息
- ❓ 自动获取题目内容和选项
- ✅ 自动提交答案并获取结果反馈

## 系统要求

- Python 3.11+
- uv 包管理器
- 依赖包：httpx、mcp、pycryptodome

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/shibig666/QMYZ-MCP.git
cd QMYZ-MCP
```

2. 安装依赖：
```bash
uv sync
```

## MCP 工具

### `get_courses`

获取用户的课程列表。

**参数：**
- `JSESSIONID` (str): 用户的会话ID，从浏览器cookie中获取

**返回：**
- 课程字典，格式：`{课程ID: 课程名称}`

**示例：**
```python
await get_courses("YOUR_JSESSIONID")
# 返回: {'2': '形势与政策', '7': '毛泽东思想和中国特色社会主义理论体系概论', '8': '思想道德与法治', '9': '马克思主义基本原理', '10': '中国近现代史纲要', '12': '习近平新时代中国特色社会主义思想概论', '16': '不忘初心牢记使命', '50': '党史学习', '52': '2020一马当先复赛1(测试)', '68': '学习“四史”', '257': '深学细悟二十大，笃行实干谱新篇', '444': '中华民族一家亲 同心共筑中国梦', '445': '网络文明素养提升', '450': '全民国家安全教育 走深走实十周年', '520': '学思践悟 青春力行——学习党的二十届三中全会精神', '523': '福建红色文化读本'}
```

### `get_question`

获取指定课程的下一道题目。

**参数：**
- `JSESSIONID` (str): 用户的会话ID
- `course_id` (str): 课程ID

**返回：**
- 题目信息字典，包含：
  - `sub_descript`: 题目描述
  - `sub_type`: 题目类型
  - `options`: 选项内容（A、B、C、D等）
  - `option_count`: 选项数量
  - `uuid`: 题目唯一标识符

### `submit_question`

提交题目答案。

**参数：**
- `JSESSIONID` (str): 用户的会话ID
- `course_id` (str): 课程ID  
- `question_id` (str): 题目UUID（从get_question获取）
- `answer` (str): 答案选项（如 "A"、"B"、"C"、"D"）

**返回：**
- "答题正确" 或 "答题错误"

## 与 Claude Desktop 集成

在 Claude Desktop 配置文件中添加MCP服务器配置：

```json
{
  "mcpServers": {
    "qmyz": {
      "command": "uv",
      "args": ["--directory", "path/to/qmyz-mcp", "run", "main.py"]
    }
  }
}
```

## 使用流程

1. **获取JSESSIONID**：登录青马易战平台，从浏览器开发者工具中复制JSESSIONID cookie值

2. **配置系统提示词**：

```markdown
# 青马易战智能答题助手

你是一个专业的答题助手，帮助用户完成青马易战平台的学习任务。

## 工作流程

1. **获取课程列表**
   - 使用 `get_courses(JSESSIONID)` 获取所有可用课程

2. **智能答题循环**
   - 使用 `get_question(JSESSIONID, course_id)` 获取题目
   - 仔细分析题目内容和选项
   - 基于知识储备选择最合适的答案
   - 使用 `submit_question(JSESSIONID, course_id, uuid, answer)` 提交答案
   - 根据结果反馈继续下一题

## 答题策略

- 仔细阅读题目，理解题意
- 分析所有选项，排除明显错误答案
- 基于相关知识做出最佳判断
- 每题只有一次机会，谨慎作答
- 答完一道题后继续下一题，不要重试

## 交互规范

- 全程使用中文交流
- 详细解释答题思路
- 显示答题进度和结果
- 提供学习建议和知识点总结

## 注意事项

- 仅答题一次，错误后不重复提交
```
3. **开始答题**：在对话框输入答题说明

```markdown
请开始答题

- **答题课程**: 思想道德与法治

- **JSESSIONID**: YOUR_JSESSIONID

- **答题说明**: 完成10道答题
```

## 注意事项

⚠️ **重要提醒**：
- 本工具仅供学习和研究使用
- 请遵守青马易战平台的使用条款
- 建议结合实际学习，不要过度依赖自动答题
- JSESSIONID有时效性，过期后需要重新获取


## 许可证

本项目仅供学习研究使用，请勿用于商业目的，详情见 [LICENSE](LICENSE) 文件。

