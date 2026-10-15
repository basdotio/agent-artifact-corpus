# FSDB MCP 服务器返回限制配置

## 概述

为了防止返回过大的数据导致性能问题和内存溢出，服务器对某些可能返回大量数据的操作设置了限制。

## 配置常量

在 `server.py` 中定义的限制常量：

```python
MAX_SIGNALS_RETURN = 1000  # 最大返回信号数量
MAX_SCOPES_RETURN = 1000   # 最大返回作用域数量
MAX_CHANGES_RETURN = 10000 # 最大返回值变化数量
```

## 受影响的工具

### 1. `fsdb_list_scopes` - 列出作用域

**限制**: 最多返回 1000 个作用域

**响应格式**:
```json
{
  "scopes": [...],        // 作用域列表（最多1000个）
  "total": 2500,          // 实际总数
  "returned": 1000,       // 本次返回数量
  "truncated": true       // 是否被截断
}
```

**示例**:
```json
{
  "scopes": [
    {"name": "scope1", "full_name": "top.scope1", ...},
    {"name": "scope2", "full_name": "top.scope2", ...}
  ],
  "total": 2,
  "returned": 2,
  "truncated": false
}
```

### 2. `fsdb_list_signals` - 列出信号

**限制**: 最多返回 1000 个信号

**响应格式**:
```json
{
  "signals": [...],       // 信号列表（最多1000个）
  "total": 5000,          // 实际总数
  "returned": 1000,       // 本次返回数量
  "truncated": true       // 是否被截断
}
```

**示例**:
```json
{
  "signals": [
    {"name": "clk", "full_name": "tb_top.clk", "left_range": 0, "right_range": 0},
    {"name": "resetn", "full_name": "tb_top.resetn", "left_range": 0, "right_range": 0}
  ],
  "total": 81,
  "returned": 81,
  "truncated": false
}
```

### 3. `fsdb_get_signal_changes` - 获取信号变化

**限制**: 最多返回 10000 个值变化

**响应格式**:
```json
{
  "signal": "tb_top.clk",
  "start_time": 0,
  "end_time": 1000000,
  "format": "hex",
  "changes": [...],       // 变化列表（最多10000个）
  "total": 50000,         // 实际总数
  "returned": 10000,      // 本次返回数量
  "truncated": true       // 是否被截断
}
```

**示例**:
```json
{
  "signal": "tb_top.clk",
  "start_time": 0,
  "end_time": 10000,
  "format": "hex",
  "changes": [
    {"time": 0, "value": "1"},
    {"time": 10000, "value": "0"}
  ],
  "total": 2,
  "returned": 2,
  "truncated": false
}
```

### 4. `fsdb_search` - 搜索信号和作用域

**限制**: 
- 信号搜索最多返回 1000 个结果 (MAX_SIGNALS_RETURN)
- 作用域搜索最多返回 1000 个结果 (MAX_SCOPES_RETURN)

**响应格式**:
```json
{
  "pattern": "clk",
  "search_type": "all",
  "scopes": {
    "matches": [...],      // 匹配的作用域（最多1000个）
    "count": 150,          // 返回数量
    "truncated": false     // 是否被截断
  },
  "signals": {
    "matches": [...],      // 匹配的信号（最多1000个）
    "count": 45,           // 返回数量
    "truncated": false     // 是否被截断
  }
}
```

**示例**:
```json
{
  "pattern": "clk",
  "search_type": "signals",
  "signals": {
    "matches": [
      {"name": "clk", "full_name": "tb_top.clk", ...},
      {"name": "clk_div", "full_name": "tb_top.cpu.clk_div", ...}
    ],
    "count": 2,
    "truncated": false
  }
}
```

## 为什么需要限制

### 1. 内存保护
- 大型设计可能包含数万个信号
- 长时间仿真可能产生数百万个值变化
- 无限制返回可能导致内存溢出

### 2. 性能优化
- 减少 JSON 序列化时间
- 降低网络传输开销
- 提高客户端响应速度

### 3. 用户体验
- 避免客户端卡顿
- 提供清晰的截断提示
- 鼓励使用更精确的查询

## 如何处理截断数据

### 客户端检查
```python
result = await session.call_tool("fsdb_list_signals", {
    "path": "test.fsdb",
    "scope_path": "tb_top"
})

data = json.loads(result.content[0].text)

if data.get('truncated', False):
    print(f"⚠ Warning: Results truncated!")
    print(f"  Total: {data['total']}")
    print(f"  Returned: {data['returned']}")
    print(f"  Missing: {data['total'] - data['returned']}")
```

### 建议的处理策略

#### 对于作用域和信号列表
1. **使用更具体的查询**: 指定更深层的作用域路径
2. **分批查询**: 遍历子作用域逐个查询
3. **过滤不需要的信号**: 在客户端进行筛选

#### 对于信号变化
1. **缩小时间范围**: 使用更小的 `start_time` 和 `end_time`
2. **分段查询**: 将长时间范围分成多个小段
3. **采样**: 如果不需要所有变化，考虑采样策略

## 修改限制值

如果需要调整限制值，编辑 `server.py` 中的常量：

```python
# 在 server.py 顶部修改
MAX_SIGNALS_RETURN = 2000   # 增加到 2000
MAX_SCOPES_RETURN = 2000    # 增加到 2000
MAX_CHANGES_RETURN = 20000  # 增加到 20000
```

**注意事项**:
- 增加限制会增加内存使用
- 可能影响响应时间
- 建议根据实际硬件资源调整

## 性能建议

### 推荐的限制值

| 场景 | MAX_SIGNALS | MAX_SCOPES | MAX_CHANGES |
|------|-------------|------------|-------------|
| 小型设计 | 500 | 500 | 5000 |
| 中型设计 | 1000 | 1000 | 10000 |
| 大型设计 | 2000 | 2000 | 20000 |
| 超大设计 | 5000 | 5000 | 50000 |

### 内存估算

粗略估算每个项目的内存占用：
- 每个作用域信息: ~200 字节
- 每个信号信息: ~300 字节
- 每个值变化: ~50 字节

示例：
```
1000 个信号 × 300 字节 = 300 KB
10000 个变化 × 50 字节 = 500 KB
```

## 测试验证

运行测试验证限制功能：

```bash
# 运行 MCP 协议测试
python3 test_mcp_client.py 2>/dev/null
```

测试输出会显示截断信息：
```
Found 81 signal(s) in scope 'tb_top' (showing 81):
  1. clk [0:0]
  2. resetn [0:0]
  ...
```

如果数据被截断，会显示警告：
```
Found 5000 signal(s) in scope 'tb_top' (showing 1000):
  ...
  ⚠ Results truncated (max 1000 returned)
```

## 未来改进

可能的增强功能：

1. **分页支持**: 添加 `offset` 和 `limit` 参数
2. **流式传输**: 对于大量数据使用流式 API
3. **压缩**: 对大型响应进行压缩
4. **缓存**: 缓存常用查询结果
5. **动态限制**: 根据系统负载动态调整限制

## 相关文档

- `TEST_FINAL_REPORT.md` - 完整测试报告
- `MCP_TEST_SUMMARY.md` - MCP 协议测试总结
- `README.md` - 项目主文档
