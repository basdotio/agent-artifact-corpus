"""全栈网络诊断 (SessionDiagnosis) 与 HTTP 流量聚合分析模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import logging
from contextlib import closing
from typing import Any

from mcp_server_traffic_inspector.config import LOGGER_NAME
from mcp_server_traffic_inspector.pcap import PcapCaptureManager
from mcp_server_traffic_inspector.pcap_slicer import CaptureSidecar
from mcp_server_traffic_inspector.storage import StorageBus, _format_url

logger = logging.getLogger(LOGGER_NAME)


class NetworkDiagnostics:
    """全栈网络会话诊断与流量统计分析器。

    支持聚合 HTTP 慢请求、状态码分布、高频端点与流量消耗，
    并对应用层 (L7) 及传输层 (L3/L4 PCAP) 链路质量进行智能根因分析与评分。
    """

    def __init__(
        self,
        storage: StorageBus,
        pcap_manager: PcapCaptureManager | None = None,
    ) -> None:
        """初始化诊断引擎。

        Args:
            storage: 共享 SQLite WAL 数据总线实例。
            pcap_manager: 可选的 PCAP 网络层捕获分析器实例。
        """
        self.storage = storage
        self.pcap_manager = pcap_manager or PcapCaptureManager()

    def analyze_http_traffic(self, session_id: str | None = None) -> dict[str, Any]:
        """聚合指定会话（未提供时默认最近一次会话）HTTP 流量的多维统计指标。

        Args:
            session_id: 可选的会话 ID；未指定时默认查询最近一次抓包会话。

        Returns:
            包含慢请求 Top 5、状态码分布及占比、高频端点 Top 10 与大载荷 Top 3 的指标字典。
        """
        with closing(self.storage._connect()) as conn:
            # 1. 未指定 session_id 时，默认取最近一次发生抓包的会话 ID
            resolved_session_id = session_id
            if resolved_session_id is None:
                latest_row = conn.execute(
                    "SELECT session_id FROM http_flows ORDER BY timestamp DESC LIMIT 1;"
                ).fetchone()
                if latest_row and latest_row["session_id"]:
                    resolved_session_id = str(latest_row["session_id"])

            where_clause = "WHERE session_id = ?" if resolved_session_id else ""
            params: list[Any] = [resolved_session_id] if resolved_session_id else []

            # 2. 流量总数与总吞吐字节数
            totals = conn.execute(
                f"""
                SELECT
                    COUNT(*) as total_count,
                    COALESCE(SUM(request_body_size), 0) as total_sent,
                    COALESCE(SUM(response_body_size), 0) as total_recv
                FROM http_flows {where_clause};
                """,
                params,
            ).fetchone()
            total_flows = int(totals["total_count"] or 0)
            total_sent = int(totals["total_sent"] or 0)
            total_recv = int(totals["total_recv"] or 0)

            # 3. 状态码分布与占比统计（互斥分布：2xx/3xx/4xx/5xx/error）
            dist_rows = conn.execute(
                f"""
                SELECT status_code, has_error, COUNT(*) as cnt
                FROM http_flows {where_clause}
                GROUP BY status_code, has_error;
                """,
                params,
            ).fetchall()
            status_dist: dict[str, int] = {
                "2xx": 0,
                "3xx": 0,
                "4xx": 0,
                "5xx": 0,
                "error": 0,
            }
            for r in dist_rows:
                code = r["status_code"]
                cnt = int(r["cnt"])
                if code is None:
                    status_dist["error"] += cnt
                elif 200 <= code < 300:
                    status_dist["2xx"] += cnt
                elif 300 <= code < 400:
                    status_dist["3xx"] += cnt
                elif 400 <= code < 500:
                    status_dist["4xx"] += cnt
                elif 500 <= code < 600:
                    status_dist["5xx"] += cnt
                else:
                    status_dist["error"] += cnt

            status_dist_pct: dict[str, float] = {
                k: round((v / total_flows) * 100.0, 2) if total_flows > 0 else 0.0
                for k, v in status_dist.items()
            }

            # 3. 慢请求 Top 5
            slow_rows = conn.execute(
                f"""
                SELECT id, method, scheme, host, port, path, status_code, duration_ms
                FROM http_flows {where_clause}
                ORDER BY COALESCE(duration_ms, 0) DESC, timestamp DESC
                LIMIT 5;
                """,
                params,
            ).fetchall()
            slow_top_5 = [
                {
                    "id": str(r["id"]),
                    "method": str(r["method"]),
                    "url": _format_url(
                        str(r["scheme"]),
                        str(r["host"]),
                        int(r["port"]),
                        str(r["path"]),
                    ),
                    "status_code": r["status_code"],
                    "duration_ms": float(r["duration_ms"])
                    if r["duration_ms"] is not None
                    else None,
                }
                for r in slow_rows
            ]

            # 4. 高频端点 Top 10
            endpoint_rows = conn.execute(
                f"""
                SELECT
                    method, host, path,
                    COUNT(*) as cnt,
                    AVG(duration_ms) as avg_ms
                FROM http_flows {where_clause}
                GROUP BY method, host, path
                ORDER BY cnt DESC, avg_ms DESC
                LIMIT 10;
                """,
                params,
            ).fetchall()
            top_endpoints = [
                {
                    "method": str(r["method"]),
                    "host": str(r["host"]),
                    "path": str(r["path"]),
                    "endpoint": f"{r['method']} {r['path']}",
                    "count": int(r["cnt"]),
                    "avg_duration_ms": round(float(r["avg_ms"]), 2)
                    if r["avg_ms"] is not None
                    else None,
                }
                for r in endpoint_rows
            ]

            # 5. 最大报文载荷 Top 3
            payload_rows = conn.execute(
                f"""
                SELECT
                    id, method, scheme, host, port, path,
                    request_body_size, response_body_size,
                    (COALESCE(request_body_size, 0) + COALESCE(response_body_size, 0)) as total_sz
                FROM http_flows {where_clause}
                ORDER BY total_sz DESC, timestamp DESC
                LIMIT 3;
                """,
                params,
            ).fetchall()
            largest_top_3 = [
                {
                    "id": str(r["id"]),
                    "method": str(r["method"]),
                    "url": _format_url(
                        str(r["scheme"]),
                        str(r["host"]),
                        int(r["port"]),
                        str(r["path"]),
                    ),
                    "total_size": int(r["total_sz"] or 0),
                    "request_size": int(r["request_body_size"] or 0),
                    "response_size": int(r["response_body_size"] or 0),
                }
                for r in payload_rows
            ]

        return {
            "session_id": resolved_session_id,
            "total_flows": total_flows,
            "total_bytes_sent": total_sent,
            "total_bytes_received": total_recv,
            "status_distribution": status_dist,
            "status_distribution_pct": status_dist_pct,
            "status_code_distribution": status_dist,
            "slow_requests_top_5": slow_top_5,
            "top_endpoints_top_10": top_endpoints,
            "largest_payloads_top_3": largest_top_3,
        }

    def diagnose_http_session(self, session_id: str | None = None) -> dict[str, Any]:
        """对应用层 HTTP 抓包会话执行健康度评估与异常根因分析。

        Args:
            session_id: 可选的目标会话 ID；未指定时评估全局流量。

        Returns:
            包含健康度评分、异常项清单及排障建议的诊断报告字典。
        """
        metrics = self.analyze_http_traffic(session_id)
        total = metrics["total_flows"]
        if total == 0:
            return {
                "session_type": "http",
                "target": session_id,
                "health_status": "healthy",
                "health_score": 100,
                "summary": "当前会话暂无 HTTP 流记录，链路处于空闲状态。",
                "anomalies": [],
                "recommendations": ["可启动业务流量触发请求后再执行会话诊断。"],
            }

        score = 100
        anomalies: list[dict[str, Any]] = []
        recommendations: list[str] = []

        # 1. 检查 5xx 服务端错误
        err_5xx = metrics["status_code_distribution"]["5xx"]
        rate_5xx = round((err_5xx / total) * 100.0, 1)
        if err_5xx > 0:
            sev = "critical" if rate_5xx > 10.0 else "medium"
            deduction = min(40, int(rate_5xx * 2) + 10)
            score -= deduction
            anomalies.append(
                {
                    "severity": sev,
                    "type": "server_errors",
                    "description": f"检测到 {err_5xx} 次 5xx 服务端异常，占比达 {rate_5xx}%",
                    "evidence": {"5xx_count": err_5xx, "ratio_pct": rate_5xx},
                }
            )
            recommendations.append(
                "重点排查上游微服务健康度、网关代理配置（502/504）或服务端未捕获的致命异常。"
            )

        # 2. 检查 4xx 客户端错误
        err_4xx = metrics["status_code_distribution"]["4xx"]
        rate_4xx = round((err_4xx / total) * 100.0, 1)
        if rate_4xx > 20.0:
            score -= 15
            anomalies.append(
                {
                    "severity": "medium",
                    "type": "client_errors",
                    "description": f"客户端 4xx 请求异常占比过高 ({rate_4xx}%)",
                    "evidence": {"4xx_count": err_4xx, "ratio_pct": rate_4xx},
                }
            )
            recommendations.append("排查客户端鉴权 Token、请求路由或 404 资源路径是否失效。")

        # 3. 检查慢请求瓶颈
        slow_top = metrics["slow_requests_top_5"]
        very_slow = [r for r in slow_top if (r["duration_ms"] or 0) > 2000.0]
        if very_slow:
            max_duration = max(r["duration_ms"] or 0 for r in very_slow)
            score -= 20
            anomalies.append(
                {
                    "severity": "medium",
                    "type": "slow_requests",
                    "description": (
                        f"发现 {len(very_slow)} 个响应耗时超过 2000ms 的慢请求"
                        f"（最慢达 {max_duration}ms）"
                    ),
                    "evidence": {"slow_flows": [r["url"] for r in very_slow]},
                }
            )
            recommendations.append(
                "针对响应慢的端点优化数据库查询与外部依赖调用，或考虑引入异步处理机制。"
            )

        score = max(0, min(100, score))
        if score >= 80:
            health_status = "healthy"
            summary = "HTTP 链路运行健康，未发现显著服务端异常或瓶颈。"
        elif score >= 50:
            health_status = "degraded"
            summary = "HTTP 链路出现性能劣化或局部异常，建议根据异常项排查修复。"
        else:
            health_status = "critical"
            summary = "HTTP 链路出现严重服务端错误或不可用情况，急需介入排查。"

        return {
            "session_type": "http",
            "target": session_id,
            "health_status": health_status,
            "health_score": score,
            "summary": summary,
            "anomalies": anomalies,
            "recommendations": recommendations,
        }

    def diagnose_pcap_session(self, file_path: str) -> dict[str, Any]:
        """对底层网络层 PCAP 抓包文件执行链路质量根因诊断。

        Args:
            file_path: 目标 PCAP 文件路径。

        Returns:
            包含 TCP 重传、RTT 与 DNS 质量的诊断报告字典。
        """
        analysis = self.pcap_manager.analyze_pcap(file_path=file_path)
        score = 100
        anomalies: list[dict[str, Any]] = []
        recommendations: list[str] = []

        # 1. TCP 重传率分析
        tcp = analysis["tcp_analysis"]
        retrans_rate = float(tcp.get("retransmission_rate_pct") or 0.0)
        if retrans_rate > 5.0:
            score -= 35
            anomalies.append(
                {
                    "severity": "high",
                    "type": "tcp_retransmission",
                    "description": f"TCP 重传率过高 ({retrans_rate}%)，可能存在丢包或拥塞",
                    "evidence": tcp,
                }
            )
            recommendations.append(
                "检查物理网络连通性、Wi-Fi 信号干扰、交换机端口丢包或服务端 TCP 队列溢出。"
            )
        elif retrans_rate > 1.0:
            score -= 15
            anomalies.append(
                {
                    "severity": "medium",
                    "type": "tcp_retransmission",
                    "description": f"TCP 重传率处于警戒区间 ({retrans_rate}%)",
                    "evidence": tcp,
                }
            )

        # 2. RTT 往返时延分析
        rtt = tcp.get("rtt_ms") or {}
        avg_rtt = rtt.get("avg")
        if avg_rtt is not None and avg_rtt > 100.0:
            score -= 20
            anomalies.append(
                {
                    "severity": "medium",
                    "type": "high_rtt",
                    "description": f"网络往返时延 (RTT) 较高 (平均 {avg_rtt}ms)",
                    "evidence": rtt,
                }
            )
            recommendations.append("排查是否存在跨地域高延迟链路，或检查中间代理节点网络转发性能。")

        # 3. DNS 解析质量分析
        dns = analysis["dns_analysis"]
        dns_fails = int(dns.get("failed_count") or 0)
        dns_avg_time = dns.get("avg_duration_ms")
        if dns_fails > 0:
            score -= 25
            anomalies.append(
                {
                    "severity": "high",
                    "type": "dns_failure",
                    "description": f"检测到 {dns_fails} 次 DNS 解析异常或失败",
                    "evidence": dns,
                }
            )
            recommendations.append(
                "检查本地 DNS 缓存、域名解析记录 (A/CNAME) 及递归 DNS 服务器可用性。"
            )
        elif dns_avg_time is not None and dns_avg_time > 100.0:
            score -= 10
            anomalies.append(
                {
                    "severity": "low",
                    "type": "slow_dns",
                    "description": f"DNS 解析耗时偏长 (平均 {dns_avg_time}ms)",
                    "evidence": dns,
                }
            )

        # 4. 伴随元数据 (Sidecar) 挂载与双轨代理重定向感知
        sidecar = CaptureSidecar.load(file_path)
        redirection_notice: dict[str, Any] | None = None
        if sidecar:
            extra = sidecar.get("extra") or {}
            redirection_notice = extra.get("redirection_notice")

        total_pkts = int(analysis.get("total_packets") or 0)
        if total_pkts == 0:
            if redirection_notice:
                if redirection_notice.get("has_raw_socket"):
                    score = 60
                    health_status = "degraded"
                    raw_ports = redirection_notice.get("raw_socket_ports", [])
                    summary = (
                        f"检测到目标进程存在非 HTTP 原生套接字连接 (端口: {raw_ports})，"
                        "未流经本地 HTTP 代理，原生 TCP 载荷未被记录。"
                    )
                    recommendations.append(
                        "目标进程包含原生 TCP 套接字通信，请使用 "
                        "interface='loopback' 或 interface='auto' 重新执行网络层抓包。"
                    )
                else:
                    score = 100
                    health_status = "healthy"
                    summary = (
                        "检测到目标进程流量已被本地 HTTP 代理接管（代理分流正常）。"
                        "物理网卡切片无直接外联报文，全量明文数据已录制在 HTTP 会话中。"
                    )
                    recommendations.append(
                        "若需捕获四层底层裸 TCP 二进制报文，请关闭全局代理后再启动抓包。"
                    )
            else:
                score = 50
                health_status = "degraded"
                summary = "PCAP 文件报文总数为 0，未捕获到任何有效网络数据包。"
                recommendations.append("检查抓包网卡选择、BPF 过滤表达式或目标进程网络活动。")
        else:
            score = max(0, min(100, score))
            if score >= 80:
                health_status = "healthy"
                summary = "网络层链路质量良好，未见显著重传、延迟或 DNS 异常。"
            elif score >= 50:
                health_status = "degraded"
                summary = "网络层链路出现轻度拥塞或延迟偏高，建议优化网络配置。"
            else:
                health_status = "critical"
                summary = "网络层链路质量严重劣化（重传或解析失败），需重点排查底层网络。"

        report: dict[str, Any] = {
            "session_type": "pcap",
            "target": file_path,
            "health_status": health_status,
            "health_score": score,
            "summary": summary,
            "anomalies": anomalies,
            "recommendations": recommendations,
        }
        if sidecar:
            report["sidecar_loaded"] = True
            report["process_family"] = sidecar.get("process_family")
            report["server_topology"] = sidecar.get("server_topology")
            if redirection_notice:
                report["redirection_notice"] = redirection_notice

        return report

    def diagnose_network_session(
        self,
        session_type: str = "http",
        target: str | None = None,
    ) -> dict[str, Any]:
        """对网络会话执行综合健康诊断。

        Args:
            session_type: 诊断类型，可选 'http' 或 'pcap'，默认 'http'。
            target: 当 session_type='http' 时为可选 session_id；当 'pcap' 时为必填文件路径。

        Returns:
            结构化诊断报告字典。

        Raises:
            ValueError: 当参数不合法或 PCAP 路径为空时抛出。
        """
        stype = session_type.strip().lower()
        if stype == "http":
            return self.diagnose_http_session(session_id=target)
        if stype == "pcap":
            if not target or not target.strip():
                raise ValueError("当 session_type='pcap' 时必须指定 target 为 PCAP 文件路径")
            return self.diagnose_pcap_session(file_path=target)

        raise ValueError(f"不支持的 session_type: {session_type}（仅支持 'http' 或 'pcap'）")
