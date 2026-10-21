# 🌙 农历日历 MCP 服务器

<img height="200" src="https://github.com/user-attachments/assets/8c58b7f1-c347-4645-a3bb-c88775eb1e6e" />


✨ 一个提供农历日期和凶吉查询的 MCP 服务器

## 🚀 功能特性

- 📅 `get_lunar` - 获取指定日期的农历信息
- 🔮 `get_taboo` - 查询当日宜忌事项

## 🛠️ 安装使用

接入配置：
```json
{
  "mcpServers": {
    "lunar": {
      "command": "tnpx",
      "args": [
        "-y",
        "lunar-calendar-mcp"
      ]
    }
  }
}
```

## 📦 技术栈

- Node.js
- TypeScript
- Model Context Protocol (MCP)

## 📜 开源协议

[MIT License](LICENSE)

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

### 如何调试

####  安装 mcp tools: https://github.com/f/mcptools 

```bash
brew tap f/mcptools
brew install mcp
```
#### 构建 

```bash
npm run build
```

####  List Tools:

```bash
mcp tools node dist/index.js
```

返回：

```
get_lunar([date:str])
     获取当天的农历日期

get_taboo([date:str])
     获取当天的凶吉
```

#### Call Tool:

```
mcp call get_lunar --params '{"date":"2025-04-10"}'  node dist/index.jsg
```

返回：
```
农历乙巳年二月初五
```


