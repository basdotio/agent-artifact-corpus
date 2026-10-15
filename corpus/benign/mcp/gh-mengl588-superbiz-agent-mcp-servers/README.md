# MCP Servers

为 AIOps 智能诊断提供日志查询和监控数据工具。

## 📚 服务列表

### CLS Server (`cls_server.py`)
**日志查询服务** - 端口 8003

**核心工具：**
- `get_current_timestamp` - 获取当前时间戳
- `get_topic_info_by_name` - 查询日志主题
- `search_log` - 日志搜索
- `search_service_logs` - 服务日志查询（支持级别筛选）
- `analyze_log_pattern` - 日志模式分析

### Monitor Server (`monitor_server.py`)
**监控数据服务** - 端口 8004

**核心工具：**
- `query_cpu_metrics` - CPU 使用率查询
- `query_memory_metrics` - 内存使用查询
- `query_process_list` - 进程列表
- `search_historical_tickets` - 历史工单查询
- `query_recent_deployments` - 最近发布变更查询
- `query_service_health` - 服务健康状态汇总
- `get_service_info` / `list_all_services` - 服务信息

## 🚀 快速开始

### 安装依赖
```bash
pip install fastmcp
```

### 启动服务

**方式一：使用 Makefile（推荐）**
```bash
make mcp-start   # 启动所有 MCP 服务
make mcp-stop    # 停止所有 MCP 服务
make mcp-status  # 查看服务状态
```

**方式二：手动启动**
```bash
python mcp_servers/cls_server.py
python mcp_servers/monitor_server.py
```

## 💡 使用示例

### AIOps 诊断场景

```
用户: data-sync-service 出现告警，请排查

Agent 自动执行:
1. list_all_services() → 查看所有服务状态
2. get_service_info("data-sync-service") → 获取服务详情
3. query_cpu_metrics("data-sync-service") → CPU 趋势分析
4. query_memory_metrics("data-sync-service") → 内存趋势分析
5. query_recent_deployments("data-sync-service") → 最近发布变更
6. search_service_logs("data-sync-service", level="error") → 错误日志
7. analyze_log_pattern("data-sync-service") → 日志模式分析
8. search_historical_tickets(service_name="data-sync-service") → 历史工单
9. query_service_health("data-sync-service") → 汇总健康状态
10. 综合分析 → 生成诊断报告和修复建议
```

### 工具参数示例

**查询 CPU 指标：**
```python
query_cpu_metrics(
    service_name="data-sync-service",
    start_time="2024-02-14 02:00:00",
    interval="1m"
)
```

**搜索错误日志：**
```python
search_service_logs(
    service_name="data-sync-service",
    log_level="error",
    keyword="timeout",
    limit=100
)
```

**搜索历史工单：**
```python
search_historical_tickets(
    service_name="data-sync-service",
    issue_type="cpu",
    limit=10
)
```

**查询最近发布变更：**
```python
query_recent_deployments(
    service_name="data-sync-service",
    start_time="2026-08-25 00:00:00",
    end_time="2026-08-25 23:59:59"
)
```

**汇总服务健康状态：**
```python
query_service_health(
    service_name="data-sync-service",
    start_time="2026-08-25 14:00:00",
    end_time="2026-08-25 15:00:00"
)
```

## 🔧 高级配置

### 接入真实 API

当前返回模拟数据。接入真实 API 步骤：

**腾讯云 CLS：**
```bash
# 安装 SDK
pip install tencentcloud-sdk-python

# 配置环境变量
export TENCENTCLOUD_SECRET_ID="your-id"
export TENCENTCLOUD_SECRET_KEY="your-key"

# 在 cls_server.py 中集成
from tencentcloud.cls.v20201016 import cls_client
```

**其他监控系统：**
- Prometheus
- Grafana
- 云监控（腾讯云/阿里云/AWS）
- 自建监控平台

### 自定义 Mock 数据

修改各 Server 文件中的数据生成逻辑，模拟实际场景。

## 📚 参考资料

- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [MCP 协议](https://modelcontextprotocol.io/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [主项目 README](../README.md)

## Controlled Remediation Demo

The monitor server now supports a mock-only repair loop:

1. Diagnose with metrics, logs, deployments, and service health.
2. Call `propose_remediation(service_name, issue_type, evidence_summary)`.
3. After human approval, call `execute_remediation` with a `CHG-*` ticket and operator.
4. Call `query_service_health` and `get_remediation_audit` to verify and audit the result.

`execute_remediation` changes only the in-memory mock service state. A production implementation must enforce approval, authorization, audit retention, and a real Kubernetes/cloud connector on the server side.

---

**注意**: 当前版本返回模拟数据，生产环境需配置真实 API。
