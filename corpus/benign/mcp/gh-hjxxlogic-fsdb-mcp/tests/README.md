# FSDB MCP 服务器测试

本目录包含 FSDB MCP 服务器的测试脚本。

## 测试文件

### 1. test_server_tools.py - 直接 API 测试

**用途**: 直接测试 pynpi 库的 API 调用逻辑

**运行**:
```bash
cd ~/work/fsdb-mcp
python3 test_server_tools.py
```

**测试内容**:
- 所有 9 个工具的底层实现
- pynpi API 调用序列
- 数据读取和处理逻辑

**优点**:
- 快速验证底层逻辑
- 无需启动 MCP 服务器
- 直接的错误信息

### 2. test_mcp_client.py - MCP 协议测试

**用途**: 通过 MCP 协议测试完整的服务器功能

**运行** (需要在虚拟环境中):
```bash
cd ~/work/fsdb-mcp
source venv/bin/activate  # 激活虚拟环境
python tests/test_mcp_client.py 2>/dev/null
```

**前置条件**:
- 需要安装 MCP SDK: `pip install mcp`
- Python 3.10 或更高版本
- 虚拟环境已创建并激活

**测试内容**:
- MCP 协议通信
- JSON-RPC 消息格式
- stdio 传输
- 完整的客户端-服务器交互
- 多信号批处理 API

**优点**:
- 验证真实使用场景
- 测试协议兼容性
- 发现通信问题

### 3. test_fsdb.py - FSDB 基础测试

**用途**: 测试基本的 FSDB 文件读取功能

**运行**:
```bash
cd ~/work/fsdb-mcp
python3 test_fsdb.py
```

**测试内容**:
- FSDB 文件打开
- 基本信息读取
- 简单的信号查询

## 测试结果

所有测试都应该通过：

```
✅ test_server_tools.py: 13/13 通过 (包含多信号批处理 API)
✅ test_mcp_client.py: 10/10 通过 (包含多信号批处理 API)
✅ test_fsdb.py: 基础功能正常
```

## 测试数据

测试使用的 FSDB 文件：
- **文件**: `../test.fsdb`
- **大小**: ~87 MB
- **仿真时间**: 0 - 28,237,930,808 (1ps 单位)
- **信号数量**: 81 个（第一个作用域）

## 运行所有测试

```bash
cd ~/work/fsdb-mcp

echo "=== 运行直接 API 测试 ==="
python3 tests/test_server_tools.py

echo ""
echo "=== 运行 MCP 协议测试 (需要虚拟环境) ==="
source venv/bin/activate
python tests/test_mcp_client.py 2>/dev/null
deactivate

echo ""
echo "=== 运行 FSDB 基础测试 ==="
python3 tests/test_fsdb.py
```

## 测试报告

详细的测试报告请查看：
- [../docs/TEST_FINAL_REPORT.md](../docs/TEST_FINAL_REPORT.md) - 完整测试报告
- [../docs/MCP_TEST_SUMMARY.md](../docs/MCP_TEST_SUMMARY.md) - MCP 测试总结

## 添加新测试

如果要添加新的测试：

1. 创建新的测试文件 `test_xxx.py`
2. 使用现有测试作为模板
3. 确保测试独立运行
4. 更新本 README
5. 更新测试报告

## 故障排查

### 测试失败常见原因

1. **VERDI_HOME 未设置**
   ```bash
   export VERDI_HOME=/path/to/verdi
   ```

2. **LD_LIBRARY_PATH 未设置**
   ```bash
   export LD_LIBRARY_PATH=$VERDI_HOME/share/NPI/lib/linux64:$LD_LIBRARY_PATH
   ```

3. **test.fsdb 不存在**
   - 确保测试文件在项目根目录

4. **权限问题**
   ```bash
   chmod +x tests/*.py
   ```

## 持续集成

未来可以添加 CI/CD 配置：
- GitHub Actions
- 自动化测试
- 测试覆盖率报告
