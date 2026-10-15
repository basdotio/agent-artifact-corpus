# Xueqiu MCP

基于雪球API的MCP服务，让您通过Claude或其他AI助手轻松获取股票数据。

## 项目简介

本项目基于[pysnowball](https://github.com/uname-yang/pysnowball)封装了雪球API，并通过MCP协议提供服务，使您能够在Claude等AI助手中直接查询股票数据。

## 安装方法

本项目使用`uv`进行依赖管理。请按照以下步骤进行安装：

```bash
# 克隆仓库
git clone https://github.com/liqiongyu/xueqiu_mcp.git
cd xueqiu_mcp

# 使用uv安装依赖
uv venv && uv pip install -e .
```

## 配置

### 配置雪球Token

1. 在项目根目录创建`.env`文件
2. 添加以下内容：

```
XUEQIU_TOKEN=您的雪球token
```

* 快捷方式：

```bash
echo 'XUEQIU_TOKEN="xq_a_token=xxxxx;u=xxxx"' > .env
```

关于如何获取雪球token，请参考[pysnowball文档](https://github.com/uname-yang/pysnowball/blob/master/how_to_get_token.md)。

## 运行服务

使用以下命令启动MCP服务：

```bash
uv --directory /path/to/xueqiu_mcp run main.py
```

或者，如果您已经配置了Claude Desktop：

```json
"xueqiu-mcp": {
  "args": [
    "--directory",
    "/path/to/xueqiu_mcp",
    "run",
    "main.py"
  ],
  "command": "uv"
}
```

## 功能特性

- 获取股票实时行情
- 查询指数收益
- 获取深港通/沪港通北向数据
- 基金相关数据查询
- 关键词搜索股票代码

## 展示图

![image](./images/cursor_mcp.png)

![image](./images/claude_mcp.png)

## 致谢

- [pysnowball](https://github.com/uname-yang/pysnowball) - 雪球股票数据接口的Python版本
- [fastmcp](https://github.com/fastmcp) - MCP服务框架

## 许可证

[MIT License](./LICENSE)