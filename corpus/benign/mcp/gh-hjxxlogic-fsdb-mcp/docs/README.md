# FSDB MCP 服务器文档

本目录包含 FSDB MCP 服务器的详细文档。

## 文档列表

### 安装和配置

- **[INSTALL.md](INSTALL.md)** - 详细的安装指南
  - 环境要求
  - 依赖安装
  - 配置步骤
  - 验证安装

- **[LIMITS_CONFIG.md](LIMITS_CONFIG.md)** - 返回限制配置
  - 限制说明
  - 配置方法
  - 性能建议
  - 处理策略

### 测试文档

- **[TEST_FINAL_REPORT.md](TEST_FINAL_REPORT.md)** - 完整测试报告
  - 测试结果
  - 发现的问题
  - 修复方案
  - 性能数据

- **[MCP_TEST_SUMMARY.md](MCP_TEST_SUMMARY.md)** - MCP 协议测试总结
  - 测试原理
  - 测试方式对比
  - 关键修复
  - 通信流程

### 其他语言

- **[README_CN.md](README_CN.md)** - 中文版 README

## 快速导航

### 我想...

- **安装服务器** → 查看 [INSTALL.md](INSTALL.md)
- **了解限制配置** → 查看 [LIMITS_CONFIG.md](LIMITS_CONFIG.md)
- **查看测试结果** → 查看 [TEST_FINAL_REPORT.md](TEST_FINAL_REPORT.md)
- **理解 MCP 协议** → 查看 [MCP_TEST_SUMMARY.md](MCP_TEST_SUMMARY.md)
- **中文文档** → 查看 [README_CN.md](README_CN.md)

## 主要文档

项目的主要文档在根目录：
- **[../README.md](../README.md)** - 项目主文档

## 测试文件

测试相关文件在 `tests/` 目录：
- `test_server_tools.py` - 直接 API 测试
- `test_mcp_client.py` - MCP 协议测试
- `test_fsdb.py` - FSDB 基础测试
