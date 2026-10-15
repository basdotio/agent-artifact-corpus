"""智能运维监控 MCP Server

本地实现的监控服务 MCP Server，提供：
- 监控数据查询（CPU、内存、磁盘、网络等）
- 进程信息查询
- 历史工单查询
- 服务信息查询

用于支持运维 Agent 的故障排查场景。
"""

import logging
import functools
import json
import random
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastmcp import FastMCP

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Monitor_MCP_Server")

mcp = FastMCP("Monitor")


def log_tool_call(func):
    """装饰器：记录工具调用的日志，包括方法名、参数和返回状态"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        method_name = func.__name__

        # 记录调用信息
        logger.info(f"=" * 80)
        logger.info(f"调用方法: {method_name}")

        # 记录参数（排除self等）
        if kwargs:
            # 使用 json.dumps 格式化参数，处理可能的序列化错误
            try:
                params_str = json.dumps(kwargs, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                params_str = str(kwargs)
            logger.info(f"参数信息:\n{params_str}")
        else:
            logger.info("参数信息: 无")

        # 执行方法
        try:
            result = func(*args, **kwargs)

            # 记录返回状态
            logger.info(f"返回状态: SUCCESS")

            # 记录返回结果摘要（避免日志过长）
            if isinstance(result, dict):
                summary = {k: v if not isinstance(v, (list, dict)) else f"<{type(v).__name__} with {len(v)} items>"
                          for k, v in list(result.items())[:5]}
                logger.info(f"返回结果摘要: {json.dumps(summary, ensure_ascii=False)}")
            else:
                logger.info(f"返回结果: {result}")

            logger.info(f"=" * 80)
            return result

        except Exception as e:
            # 记录错误状态
            logger.error(f"返回状态: ERROR")
            logger.error(f"错误信息: {str(e)}")
            logger.error(f"=" * 80)
            raise

    return wrapper


# ============================================================
# 辅助函数
# ============================================================

def parse_time_or_default(time_str: Optional[str], default_offset_hours: int = 0) -> datetime:
    """解析时间字符串或返回默认时间。

    Args:
        time_str: 时间字符串（格式：YYYY-MM-DD HH:MM:SS）
        default_offset_hours: 默认时间偏移（小时）

    Returns:
        datetime: 解析后的时间对象
    """
    if time_str:
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    # 返回默认时间（当前时间 + 偏移）
    return datetime.now() + timedelta(hours=default_offset_hours)


def generate_time_series(base_time: datetime, minutes_offset: int, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """生成时间序列字符串。

    Args:
        base_time: 基准时间
        minutes_offset: 分钟偏移量
        format_str: 时间格式字符串

    Returns:
        str: 格式化的时间字符串
    """
    result_time = base_time + timedelta(minutes=minutes_offset)
    return result_time.strftime(format_str)


SERVICE_CATALOG = {
    "data-sync-service": {
        "owner": "data-platform",
        "language": "Python",
        "runtime": "Kubernetes",
        "instance_count": 3,
        "status": "warning",
        "dependencies": ["mysql-prod", "redis-cache", "message-queue"],
        "description": "负责从业务库同步数据到分析链路。",
    },
    "order-service": {
        "owner": "biz-platform",
        "language": "Java",
        "runtime": "Kubernetes",
        "instance_count": 6,
        "status": "normal",
        "dependencies": ["mysql-order", "redis-cache", "payment-service"],
        "description": "负责订单创建、状态流转和订单查询。",
    },
    "payment-service": {
        "owner": "payment-team",
        "language": "Go",
        "runtime": "Kubernetes",
        "instance_count": 4,
        "status": "normal",
        "dependencies": ["mysql-pay", "third-party-gateway"],
        "description": "负责支付请求、回调处理和对账数据写入。",
    },
    "recommend-service": {
        "owner": "algorithm-team",
        "language": "Python",
        "runtime": "Kubernetes",
        "instance_count": 4,
        "status": "warning",
        "dependencies": ["feature-store", "redis-cache", "model-serving"],
        "description": "负责商品推荐和实时特征查询。",
    },
}


RECENT_DEPLOYMENTS = [
    {
        "service_name": "data-sync-service",
        "version": "v2.3.7",
        "operator": "ops_zhang",
        "deploy_time": "2026-08-25 14:20:00",
        "change_summary": "调整批量同步任务的线程池大小和重试间隔。",
        "risk_level": "high",
    },
    {
        "service_name": "data-sync-service",
        "version": "v2.3.6",
        "operator": "ops_li",
        "deploy_time": "2026-08-24 22:10:00",
        "change_summary": "修复部分空字段导致的同步失败。",
        "risk_level": "medium",
    },
    {
        "service_name": "order-service",
        "version": "v5.1.2",
        "operator": "dev_wang",
        "deploy_time": "2026-08-25 09:30:00",
        "change_summary": "优化订单状态回写逻辑。",
        "risk_level": "medium",
    },
    {
        "service_name": "recommend-service",
        "version": "v1.8.0",
        "operator": "algo_chen",
        "deploy_time": "2026-08-25 13:50:00",
        "change_summary": "切换实时特征查询接口。",
        "risk_level": "high",
    },
]


HISTORICAL_TICKETS = [
    {
        "ticket_id": "INC-20260818-001",
        "service_name": "data-sync-service",
        "issue_type": "cpu",
        "summary": "同步任务线程池过大导致 CPU 持续打满。",
        "root_cause": "批处理并发数超过数据库连接池承载能力，触发大量重试。",
        "resolution": "回滚线程池配置，将并发数从 64 调整为 16，并限制重试次数。",
    },
    {
        "ticket_id": "INC-20260810-003",
        "service_name": "data-sync-service",
        "issue_type": "memory",
        "summary": "大文件同步时内存持续上涨。",
        "root_cause": "单次加载全量数据，没有进行分页流式处理。",
        "resolution": "改为分页拉取，并增加单批次数据大小限制。",
    },
    {
        "ticket_id": "INC-20260812-002",
        "service_name": "recommend-service",
        "issue_type": "latency",
        "summary": "推荐接口响应时间升高。",
        "root_cause": "特征服务超时后没有降级，导致请求堆积。",
        "resolution": "增加超时降级策略，并缓存热点特征。",
    },
    {
        "ticket_id": "INC-20260730-006",
        "service_name": "order-service",
        "issue_type": "error_rate",
        "summary": "订单状态回写失败率上升。",
        "root_cause": "第三方支付回调字段变更，解析逻辑没有兼容。",
        "resolution": "兼容新旧字段，并补偿失败订单。",
    },
]


# This server uses in-memory mock data. Remediation actions below only update
# this process so the Agent can demonstrate a diagnose -> repair -> verify loop.
REMEDIATION_AUDIT_LOG = []
REMEDIATION_ACTIONS = {
    "restart_service": {
        "risk_level": "medium",
        "description": "Restart unhealthy service instances to clear transient resource pressure.",
    },
    "rollback_last_release": {
        "risk_level": "high",
        "description": "Roll back the latest release when the incident is strongly correlated with it.",
    },
    "scale_out": {
        "risk_level": "high",
        "description": "Add one service instance when capacity pressure is confirmed.",
    },
}


def _normalize_service_name(service_name: str) -> str:
    return service_name.strip().lower()


def _is_unhealthy(service_name: str) -> bool:
    service = SERVICE_CATALOG.get(_normalize_service_name(service_name), {})
    return service.get("status") in {"warning", "critical"}


def _is_time_in_range(time_str: str, start_dt: datetime, end_dt: datetime) -> bool:
    try:
        current_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return start_dt <= current_dt <= end_dt


def _filter_deployments(
    service_name: str,
    start_time: Optional[str],
    end_time: Optional[str],
    limit: int,
) -> list:
    service_key = _normalize_service_name(service_name)
    start_dt = parse_time_or_default(start_time, default_offset_hours=-24)
    end_dt = parse_time_or_default(end_time, default_offset_hours=0)

    matched = [
        item for item in RECENT_DEPLOYMENTS
        if _normalize_service_name(item["service_name"]) == service_key
        and _is_time_in_range(item["deploy_time"], start_dt, end_dt)
    ]
    matched.sort(key=lambda item: item["deploy_time"], reverse=True)
    return matched[:max(limit, 1)]




# ============================================================
# 监控数据查询工具
# ============================================================

@mcp.tool()
@log_tool_call
def query_cpu_metrics(
    service_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    interval: str = "1m"
) -> Dict[str, Any]:
    """查询服务的 CPU 使用率监控数据。

    Args:
        service_name: 服务名称（必填）
            示例: "data-sync-service"
        
        start_time: 开始时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 10:00:00"
            默认值: 如果不传，默认为当前时间的1小时前
            注意: 必须使用字符串格式，而非时间戳
        
        end_time: 结束时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 11:00:00"
            默认值: 如果不传，默认为当前时间
            注意: 必须使用字符串格式，而非时间戳
        
        interval: 数据聚合间隔（可选）
            可选值: "1m" (1分钟), "5m" (5分钟), "1h" (1小时)
            默认值: "1m"
            说明: 控制数据点的时间间隔

    Returns:
        Dict: CPU 监控数据
            - service_name: 服务名称
            - metric_name: 指标名称 (cpu_usage_percent)
            - interval: 数据聚合间隔
            - data_points: 数据点列表，每个点包含:
                * timestamp: 时间点（格式: HH:MM）
                * value: CPU 使用率百分比
            - statistics: 统计信息
                * average: 平均值
                * max: 最大值
                * min: 最小值
            - alert: 告警信息（如有）
                * triggered: 是否触发告警
                * threshold: 告警阈值
                * message: 告警消息
    
    使用示例:
        # 示例1: 使用默认时间（最近1小时）
        query_cpu_metrics(service_name="data-sync-service")
        
        # 示例2: 指定时间范围
        query_cpu_metrics(
            service_name="data-sync-service",
            start_time="2026-02-14 10:00:00",
            end_time="2026-02-14 11:00:00",
            interval="5m"
        )
        
        # 示例3: 只指定开始时间（结束时间自动为当前时间）
        query_cpu_metrics(
            service_name="data-sync-service",
            start_time="2026-02-14 10:00:00"
        )
    """
    # 解析时间参数
    start_dt = parse_time_or_default(start_time, default_offset_hours=-1)
    end_dt = parse_time_or_default(end_time, default_offset_hours=0)
    
    # 解析间隔时间（interval: 1m, 5m, 1h 等）
    interval_minutes = 1  # 默认 1 分钟
    if interval.endswith('m'):
        interval_minutes = int(interval[:-1])
    elif interval.endswith('h'):
        interval_minutes = int(interval[:-1]) * 60

    # 动态生成 CPU 使用率数据：从低到高逐渐增长
    data_points = []
    current_time = start_dt
    time_index = 0

    # 初始 CPU 使用率（10%）
    base_cpu = 10.0

    while current_time <= end_dt:
        # CPU 使用率逐渐升高的算法：
        # - 前几个数据点保持在 10% 左右
        # - 然后开始快速上升
        # - 最终达到 95% 左右

        if not _is_unhealthy(service_name):
            cpu_value = 18.0 + random.uniform(-2, 2)
        elif time_index < 3:
            # 初始阶段：10% 左右波动
            cpu_value = base_cpu + (time_index * 0.5)
        else:
            # 上升阶段：使用指数增长模型
            growth_factor = (time_index - 2) * 8.5
            cpu_value = min(base_cpu + growth_factor, 96.0)

        # 添加一些随机波动（±2%）
        cpu_value = round(cpu_value + random.uniform(-2, 2), 1)
        cpu_value = max(0, min(100, cpu_value))  # 确保在 0-100 范围内

        data_point = {
            "timestamp": current_time.strftime("%H:%M"),
            "value": cpu_value,
            "process_id": "pid-12345"
        }

        data_points.append(data_point)

        # 下一个时间点
        current_time += timedelta(minutes=interval_minutes)
        time_index += 1

    # 计算统计信息
    if data_points:
        values = [d["value"] for d in data_points]
        avg_value = round(sum(values) / len(values), 2)
        max_value = max(values)
        min_value = min(values)

        # 检测是否有 CPU 突增（超过 80%）
        spike_detected = max_value > 80.0

        return {
            "service_name": service_name,
            "metric_name": "cpu_usage_percent",
            "interval": interval,
            "data_points": data_points,
            "statistics": {
                "avg": avg_value,
                "max": max_value,
                "min": min_value,
                "p95": round(sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else max_value, 2),
                "spike_detected": spike_detected
            },
            "alert_info": {
                "triggered": spike_detected,
                "threshold": 80.0,
                "message": "CPU 使用率持续超过 80% 阈值" if spike_detected else "CPU 使用率正常"
            }
        }
    else:
        return {
            "service_name": service_name,
            "metric_name": "cpu_usage_percent",
            "interval": interval,
            "data_points": [],
            "statistics": {},
        }


@mcp.tool()
@log_tool_call
def query_memory_metrics(
    service_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    interval: str = "1m"
) -> Dict[str, Any]:
    """查询服务的内存使用监控数据。

    Args:
        service_name: 服务名称（必填）
            示例: "data-sync-service"
        
        start_time: 开始时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 10:00:00"
            默认值: 如果不传，默认为当前时间的1小时前
            注意: 必须使用字符串格式，而非时间戳
        
        end_time: 结束时间（可选，字符串类型）
            格式: "YYYY-MM-DD HH:MM:SS"
            示例: "2026-02-14 11:00:00"
            默认值: 如果不传，默认为当前时间
            注意: 必须使用字符串格式，而非时间戳
        
        interval: 数据聚合间隔（可选）
            可选值: "1m" (1分钟), "5m" (5分钟), "1h" (1小时)
            默认值: "1m"

    Returns:
        Dict: 内存监控数据
            - service_name: 服务名称
            - metric_name: 指标名称 (memory_usage_percent)
            - interval: 数据聚合间隔
            - data_points: 数据点列表，每个点包含:
                * timestamp: 时间点（格式: HH:MM）
                * value: 内存使用率百分比
                * used_gb: 已使用内存（GB）
                * total_gb: 总内存（GB）
            - statistics: 统计信息
                * average: 平均值
                * max: 最大值
                * min: 最小值
            - alert: 告警信息（如有）
                * triggered: 是否触发告警
                * threshold: 告警阈值
                * message: 告警消息
    
    使用示例:
        # 示例1: 使用默认时间（最近1小时）
        query_memory_metrics(service_name="data-sync-service")
        
        # 示例2: 指定时间范围
        query_memory_metrics(
            service_name="data-sync-service",
            start_time="2026-02-14 10:00:00",
            end_time="2026-02-14 11:00:00",
            interval="5m"
        )
    """
    # 解析时间参数
    start_dt = parse_time_or_default(start_time, default_offset_hours=-1)
    end_dt = parse_time_or_default(end_time, default_offset_hours=0)
    
    # 解析间隔时间（interval: 1m, 5m, 1h 等）
    interval_minutes = 1  # 默认 1 分钟
    if interval.endswith('m'):
        interval_minutes = int(interval[:-1])
    elif interval.endswith('h'):
        interval_minutes = int(interval[:-1]) * 60
    
    # 动态生成内存使用率数据：从低到高逐渐增长
    data_points = []
    current_time = start_dt
    time_index = 0
    
    # 初始内存使用率（30%）
    base_memory = 30.0
    total_gb = 8.0  # 总内存 8GB
    
    while current_time <= end_dt:
        # 内存使用率逐渐升高的算法：
        # - 前几个数据点保持在 30% 左右
        # - 然后开始逐步上升
        # - 最终达到 85% 左右
        
        if not _is_unhealthy(service_name):
            memory_value = 38.0 + random.uniform(-2, 2)
        elif time_index < 3:
            # 初始阶段：30% 左右波动
            memory_value = base_memory + (time_index * 1.0)
        else:
            # 上升阶段：使用线性增长模型（内存增长比 CPU 慢）
            growth_factor = (time_index - 2) * 5.5
            memory_value = min(base_memory + growth_factor, 85.0)
        
        # 添加一些随机波动（±1%）
        memory_value = round(memory_value + random.uniform(-1, 1), 1)
        memory_value = max(0, min(100, memory_value))  # 确保在 0-100 范围内
        
        # 计算已使用内存（GB）
        used_gb = round((memory_value / 100.0) * total_gb, 2)
        
        data_point = {
            "timestamp": current_time.strftime("%H:%M"),
            "value": memory_value,
            "used_gb": used_gb,
            "total_gb": total_gb
        }
        
        data_points.append(data_point)
        
        # 下一个时间点
        current_time += timedelta(minutes=interval_minutes)
        time_index += 1
    
    # 计算统计信息
    if data_points:
        values = [d["value"] for d in data_points]
        avg_value = round(sum(values) / len(values), 2)
        max_value = max(values)
        min_value = min(values)
        
        # 检测是否有内存压力（超过 70%）
        memory_pressure = max_value > 70.0
        
        return {
            "service_name": service_name,
            "metric_name": "memory_usage_percent",
            "interval": interval,
            "data_points": data_points,
            "statistics": {
                "avg": avg_value,
                "max": max_value,
                "min": min_value,
                "p95": round(sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else max_value, 2),
                "memory_pressure": memory_pressure
            },
            "alert_info": {
                "triggered": memory_pressure,
                "threshold": 70.0,
                "message": "内存使用率超过 70% 阈值，存在内存压力" if memory_pressure else "内存使用率正常"
            }
        }
    else:
        return {
            "service_name": service_name,
            "metric_name": "memory_usage_percent",
            "interval": interval,
            "data_points": [],
            "statistics": {},
            "error": "时间范围无效或没有生成数据点"
        }
@mcp.tool()
@log_tool_call
def list_all_services(status: Optional[str] = None) -> Dict[str, Any]:
    """查询监控系统中登记的服务列表。

    Args:
        status: 服务状态筛选，可选值为 normal、warning、critical。

    Returns:
        Dict: 服务列表和数量统计。
    """
    status_filter = status.strip().lower() if status else None
    services = []

    for service_name, info in SERVICE_CATALOG.items():
        if status_filter and info["status"] != status_filter:
            continue
        services.append({
            "service_name": service_name,
            "owner": info["owner"],
            "status": info["status"],
            "instance_count": info["instance_count"],
            "runtime": info["runtime"],
        })

    return {
        "total": len(services),
        "status_filter": status_filter,
        "services": services,
    }


@mcp.tool()
@log_tool_call
def get_service_info(service_name: str) -> Dict[str, Any]:
    """查询指定服务的基础信息、负责人和依赖关系。

    Args:
        service_name: 服务名称，例如 data-sync-service。

    Returns:
        Dict: 服务基础信息。如果服务不存在，会返回 available_services 方便 Agent 重新选择。
    """
    service_key = _normalize_service_name(service_name)
    service_info = SERVICE_CATALOG.get(service_key)

    if not service_info:
        return {
            "found": False,
            "service_name": service_name,
            "message": "未找到该服务，请从 available_services 中选择更接近的服务名。",
            "available_services": list(SERVICE_CATALOG.keys()),
        }

    return {
        "found": True,
        "service_name": service_key,
        **service_info,
    }


@mcp.tool()
@log_tool_call
def query_process_list(
    service_name: str,
    min_cpu_percent: float = 0.0,
    min_memory_mb: float = 0.0,
    limit: int = 10,
) -> Dict[str, Any]:
    """查询服务实例中的进程列表，支持按 CPU 和内存阈值筛选。

    Args:
        service_name: 服务名称，例如 data-sync-service。
        min_cpu_percent: 最小 CPU 使用率筛选阈值。
        min_memory_mb: 最小内存占用筛选阈值，单位 MB。
        limit: 返回进程数量上限。

    Returns:
        Dict: 进程列表、可疑进程和排查建议。
    """
    service_key = _normalize_service_name(service_name)
    process_templates = [
        {
            "pid": 12345,
            "process_name": "python worker.py --sync",
            "cpu_percent": 91.2 if service_key == "data-sync-service" else 24.8,
            "memory_mb": 1130.5,
            "status": "running",
        },
        {
            "pid": 12346,
            "process_name": "python scheduler.py",
            "cpu_percent": 18.4,
            "memory_mb": 310.2,
            "status": "running",
        },
        {
            "pid": 12347,
            "process_name": "sidecar-agent",
            "cpu_percent": 3.2,
            "memory_mb": 88.7,
            "status": "running",
        },
    ]

    filtered = [
        item for item in process_templates
        if item["cpu_percent"] >= min_cpu_percent
        and item["memory_mb"] >= min_memory_mb
    ][:max(limit, 1)]

    suspicious_processes = [
        item for item in filtered
        if item["cpu_percent"] >= 80 or item["memory_mb"] >= 1024
    ]

    return {
        "service_name": service_key,
        "filters": {
            "min_cpu_percent": min_cpu_percent,
            "min_memory_mb": min_memory_mb,
            "limit": limit,
        },
        "processes": filtered,
        "suspicious_processes": suspicious_processes,
        "suggestion": "优先检查高 CPU 或高内存进程的线程池、重试和批处理逻辑。" if suspicious_processes else "进程资源占用未发现明显异常。",
    }


@mcp.tool()
@log_tool_call
def search_historical_tickets(
    service_name: str,
    issue_type: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """查询相似历史故障工单，用于辅助根因分析。

    Args:
        service_name: 服务名称，例如 data-sync-service。
        issue_type: 故障类型，例如 cpu、memory、latency、error_rate。
        keyword: 关键词，可匹配故障摘要、根因和处理方案。
        limit: 返回工单数量上限。

    Returns:
        Dict: 匹配到的历史工单和复用建议。
    """
    service_key = _normalize_service_name(service_name)
    issue_filter = issue_type.strip().lower() if issue_type else None
    keyword_filter = keyword.strip().lower() if keyword else None
    matched = []

    for ticket in HISTORICAL_TICKETS:
        if _normalize_service_name(ticket["service_name"]) != service_key:
            continue
        if issue_filter and ticket["issue_type"] != issue_filter:
            continue
        searchable_text = " ".join([
            ticket["summary"],
            ticket["root_cause"],
            ticket["resolution"],
        ]).lower()
        if keyword_filter and keyword_filter not in searchable_text:
            continue
        matched.append(ticket)

    return {
        "service_name": service_key,
        "issue_type": issue_filter,
        "keyword": keyword_filter,
        "tickets": matched[:max(limit, 1)],
        "suggestion": "可参考历史工单中的根因和处理方案，但仍需结合当前监控、日志和发布记录确认。" if matched else "未找到相似历史工单，建议继续查询日志和监控指标。",
    }


@mcp.tool()
@log_tool_call
def query_recent_deployments(
    service_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """查询服务在指定时间范围内的发布变更记录。

    Args:
        service_name: 服务名称，例如 data-sync-service。
        start_time: 开始时间，格式为 YYYY-MM-DD HH:MM:SS，默认最近 24 小时。
        end_time: 结束时间，格式为 YYYY-MM-DD HH:MM:SS，默认当前时间。
        limit: 返回发布记录数量上限。

    Returns:
        Dict: 发布记录、最高风险等级和排查建议。
    """
    deployments = _filter_deployments(service_name, start_time, end_time, limit)
    high_risk_count = sum(1 for item in deployments if item["risk_level"] == "high")

    if high_risk_count:
        suggestion = "近期存在高风险发布，建议优先比对故障开始时间和发布时间，并考虑灰度回滚。"
    elif deployments:
        suggestion = "近期存在发布变更，建议结合日志和指标判断是否与故障相关。"
    else:
        suggestion = "指定时间范围内未发现发布记录，故障更可能与流量、依赖或资源问题有关。"

    return {
        "service_name": _normalize_service_name(service_name),
        "deployments": deployments,
        "deployment_count": len(deployments),
        "high_risk_count": high_risk_count,
        "suggestion": suggestion,
    }


@mcp.tool()
@log_tool_call
def query_service_health(
    service_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
    """汇总服务健康状态，用于让 Agent 快速判断排障方向。

    Args:
        service_name: 服务名称，例如 data-sync-service。
        start_time: 开始时间，格式为 YYYY-MM-DD HH:MM:SS，默认最近 1 小时。
        end_time: 结束时间，格式为 YYYY-MM-DD HH:MM:SS，默认当前时间。

    Returns:
        Dict: 服务基础信息、核心指标摘要、发布变更和诊断方向。
    """
    service_key = _normalize_service_name(service_name)
    service_info = SERVICE_CATALOG.get(service_key)

    cpu_metrics = query_cpu_metrics(service_key, start_time=start_time, end_time=end_time, interval="5m")
    memory_metrics = query_memory_metrics(service_key, start_time=start_time, end_time=end_time, interval="5m")
    deployments = _filter_deployments(service_key, start_time, end_time, limit=3)

    cpu_alert = cpu_metrics.get("alert_info", {}).get("triggered", False)
    memory_alert = memory_metrics.get("alert_info", {}).get("triggered", False)
    has_high_risk_deploy = any(item["risk_level"] == "high" for item in deployments)

    risk_signals = []
    if cpu_alert:
        risk_signals.append("CPU 使用率超过阈值")
    if memory_alert:
        risk_signals.append("内存使用率超过阈值")
    if has_high_risk_deploy:
        risk_signals.append("近期存在高风险发布")

    if cpu_alert and has_high_risk_deploy:
        diagnosis_direction = "优先排查近期发布是否引入高并发、死循环或重试放大问题。"
    elif cpu_alert:
        diagnosis_direction = "优先排查高 CPU 进程、线程池配置和异常重试。"
    elif memory_alert:
        diagnosis_direction = "优先排查内存泄漏、大对象缓存或批处理数据量过大。"
    elif has_high_risk_deploy:
        diagnosis_direction = "指标未明显越界，但近期存在高风险发布，建议继续查看日志和变更内容。"
    else:
        diagnosis_direction = "暂未发现明显资源告警，建议继续查询错误日志、依赖状态和历史工单。"

    return {
        "service_name": service_key,
        "service_info": service_info,
        "metric_summary": {
            "cpu": cpu_metrics.get("statistics", {}),
            "memory": memory_metrics.get("statistics", {}),
        },
        "recent_deployments": deployments,
        "risk_signals": risk_signals,
        "diagnosis_direction": diagnosis_direction,
    }


@mcp.tool()
@log_tool_call
def propose_remediation(
    service_name: str,
    issue_type: str,
    evidence_summary: str,
) -> Dict[str, Any]:
    """Create a controlled remediation proposal from diagnostic evidence.

    This tool is read-only. Call it only after checking metrics, logs, or
    deployment history. It returns the suggested action and its risk level.
    """
    service_key = _normalize_service_name(service_name)
    if service_key not in SERVICE_CATALOG:
        return {
            "created": False,
            "message": "Unknown service.",
            "available_services": list(SERVICE_CATALOG.keys()),
        }

    issue_key = issue_type.strip().lower()
    if issue_key in {"cpu", "memory"}:
        action = "restart_service"
    elif issue_key in {"deployment", "error_rate"}:
        action = "rollback_last_release"
    else:
        action = "scale_out"

    return {
        "created": True,
        "environment": "mock",
        "service_name": service_key,
        "issue_type": issue_key,
        "evidence_summary": evidence_summary,
        "recommended_action": action,
        "risk_level": REMEDIATION_ACTIONS[action]["risk_level"],
        "requires_change_ticket": True,
        "next_step": "Use execute_remediation only after the evidence and change ticket are confirmed.",
    }


@mcp.tool()
@log_tool_call
def execute_remediation(
    service_name: str,
    action: str,
    change_ticket: str,
    operator: str,
) -> Dict[str, Any]:
    """Execute an approved remediation action in the local mock environment.

    A valid change ticket (CHG-*) and named operator are required. The tool
    never touches a real host, Kubernetes cluster, or cloud account. After a
    successful call, use query_service_health to verify the result.
    """
    service_key = _normalize_service_name(service_name)
    action_key = action.strip().lower()
    service = SERVICE_CATALOG.get(service_key)

    if not service:
        return {"executed": False, "message": "Unknown service."}
    if action_key not in REMEDIATION_ACTIONS:
        return {
            "executed": False,
            "message": "Unsupported action.",
            "supported_actions": list(REMEDIATION_ACTIONS.keys()),
        }
    if not change_ticket.strip().upper().startswith("CHG-") or not operator.strip():
        return {
            "executed": False,
            "message": "A change ticket beginning with CHG- and an operator are required.",
            "requires_change_ticket": True,
        }

    before_status = service["status"]
    if action_key == "scale_out":
        service["instance_count"] += 1
    if action_key == "rollback_last_release":
        service["deployed_version"] = "previous-stable"
    service["status"] = "normal"
    audit = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service_name": service_key,
        "action": action_key,
        "change_ticket": change_ticket.strip().upper(),
        "operator": operator.strip(),
        "status_before": before_status,
        "status_after": service["status"],
        "environment": "mock",
    }
    REMEDIATION_AUDIT_LOG.append(audit)

    return {
        "executed": True,
        "environment": "mock",
        "message": "Remediation executed in the mock environment. Verify service health next.",
        "audit": audit,
    }


@mcp.tool()
@log_tool_call
def get_remediation_audit(service_name: Optional[str] = None) -> Dict[str, Any]:
    """Return mock remediation audit records for verification and traceability."""
    service_key = _normalize_service_name(service_name) if service_name else None
    records = [
        item for item in REMEDIATION_AUDIT_LOG
        if not service_key or item["service_name"] == service_key
    ]
    return {"environment": "mock", "count": len(records), "records": records}


if __name__ == "__main__":
    # 使用 streamable-http 模式，运行在 8004 端口
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8004, path="/mcp")
