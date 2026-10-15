"""RabbitMQ 服务端配置中心与凭据脱敏实现.

@author Ateng
@since 2026-10-04
"""

import os
import re
import threading
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import yaml
from pydantic import BaseModel, Field

_PASSWORD_PATTERN = re.compile(r"([a-zA-Z0-9+.-]+://[^:/@\s]+:)([^@\s]+)(@)")


def mask_url(url: str | None) -> str | None:
    """对连接 URL 或包含连接 URL 的错误文本中的密码进行脱敏，替换为掩码 '***'.

    支持单独 URL（包括密码含 '@'）与长文本错误堆栈中嵌入的 URL 凭据脱敏。

    @param url 原始连接 URL 或包含 URL 的文本字符串，支持 None 或空串
    @return 脱敏后的字符串
    """
    if not url:
        return url

    # 1. 若为标准独立 URL 且包含凭据，优先通过 urlsplit 精准脱敏（支持密码内含 '@' 等特殊符号）
    try:
        parts = urlsplit(url)
        if parts.scheme and parts.netloc and "@" in parts.netloc:
            user_info, _, host_info = parts.netloc.rpartition("@")
            if ":" in user_info:
                user, _, _ = user_info.partition(":")
                masked_netloc = f"{user}:***@{host_info}"
                return urlunsplit((parts.scheme, masked_netloc, parts.path, parts.query, parts.fragment))
    except (ValueError, AttributeError):
        pass

    # 2. 复合错误堆栈/长文本正则脱敏替换
    return _PASSWORD_PATTERN.sub(r"\g<1>***\g<3>", url)


_SENSITIVE_PROP_KEYS = ("password", "passwd", "secret", "token", "key", "credential", "auth")


def mask_dict_credentials(data: dict[str, Any] | None) -> dict[str, Any]:
    """对字典数据中的敏感凭据属性与包含密码的 URL 进行递归脱敏.

    匹配包含 password, secret, token, key, credential 等关键字的键将其值替换为 '***'；
    对包含 URL 的字符串值通过 mask_url 脱敏；对嵌套字典递归处理。

    @param data 待脱敏的原始字典，支持 None
    @return 脱敏后的安全字典副本
    """
    if not data:
        return {}

    masked: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = str(key).lower()
        if any(sensitive_word in key_lower for sensitive_word in _SENSITIVE_PROP_KEYS):
            masked[key] = "***"
        elif isinstance(value, str):
            masked[key] = mask_url(value) if "://" in value else value
        elif isinstance(value, dict):
            masked[key] = mask_dict_credentials(value)
        else:
            masked[key] = value
    return masked


def parse_amqp_url(url: str) -> dict[str, Any]:
    """解析 AMQP 连接协议串为分立属性字典.

    @param url AMQP 连接协议串
    @return 包含 host, port, username, password, vhost, ssl 的字典
    """
    parts = urlsplit(url)
    ssl = parts.scheme == "amqps"
    username = unquote(parts.username) if parts.username is not None else None
    password = unquote(parts.password) if parts.password is not None else None
    host = parts.hostname or "localhost"
    port = parts.port or (5671 if ssl else 5672)
    raw_path = parts.path or "/"
    if raw_path == "/":
        vhost = "/"
    else:
        clean_path = raw_path.lstrip("/")
        vhost = unquote(clean_path)
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "vhost": vhost,
        "ssl": ssl,
    }


def parse_management_url(url: str) -> dict[str, Any]:
    """解析 Management HTTP API 基地址为分立属性字典.

    @param url Management API 基地址
    @return 包含 host, port, username, password, ssl, path 的字典
    """
    parts = urlsplit(url)
    ssl = parts.scheme == "https"
    username = unquote(parts.username) if parts.username is not None else None
    password = unquote(parts.password) if parts.password is not None else None
    host = parts.hostname or "localhost"
    port = parts.port or (443 if ssl else 15672)
    path = parts.path or ""
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "ssl": ssl,
        "path": path,
    }


def build_amqp_url(
    host: str = "localhost",
    port: int | None = None,
    username: str = "guest",
    password: str = "guest",
    vhost: str = "/",
    ssl: bool = False,
) -> str:
    """基于分立参数构建标准的 AMQP 0-9-1 连接协议串.

    自动对用户名、密码及 vhost 进行 URL 转义，防范 '@', ':', '/' 等特殊字符引发解析破坏。

    @param host RabbitMQ 服务主机名或 IP 地址，默认 'localhost'
    @param port 连接端口，默认依据 ssl 自动推导（普通 5672，SSL 5671）
    @param username 连接用户名，默认 'guest'
    @param password 连接密码，默认 'guest'
    @param vhost 虚拟主机名称，默认 '/'
    @param ssl 是否启用 SSL/TLS 加密传输，默认 False
    @return 合法的标准 AMQP 连接协议串
    """
    scheme = "amqps" if ssl else "amqp"
    effective_port = port if port is not None else (5671 if ssl else 5672)
    user_part = f"{quote(username, safe='')}:{quote(password, safe='')}@" if (username or password) else ""
    netloc = f"{user_part}{host}:{effective_port}"
    if vhost == "/":
        path = "/"
    else:
        clean_vhost = vhost.lstrip("/") if vhost.startswith("/") else vhost
        path = f"/{quote(clean_vhost, safe='')}"
    return urlunsplit((scheme, netloc, path, "", ""))


def build_management_url(
    host: str = "localhost",
    port: int = 15672,
    username: str = "guest",
    password: str = "guest",
    ssl: bool = False,
    path: str = "",
) -> str:
    """基于分立参数构建 RabbitMQ Management HTTP API 访问基地址.

    @param host Management 服务主机名，默认 'localhost'
    @param port HTTP 端口，默认 15672
    @param username HTTP 认证用户名，默认 'guest'
    @param password HTTP 认证密码，默认 'guest'
    @param ssl 是否启用 HTTPS，默认 False
    @param path 可选路径，如 '/api'，默认空
    @return 合法的 Management API 基地址
    """
    scheme = "https" if ssl else "http"
    user_part = f"{quote(username, safe='')}:{quote(password, safe='')}@" if (username or password) else ""
    netloc = f"{user_part}{host}:{port}"
    clean_path = ("/" + path.lstrip("/")) if path else ""
    return urlunsplit((scheme, netloc, clean_path, "", ""))


def merge_amqp_url(
    base_url: str | None = None,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    password: str | None = None,
    vhost: str | None = None,
    ssl: bool | None = None,
) -> str:
    """将分立参数与基础 AMQP URL 深度融合覆盖.

    若存在 base_url，优先提取其中的元数据，再用非空分立字段覆盖；若无 base_url，直接基于分立字段组装。

    @param base_url 可选的基础 AMQP 连接协议串
    @param host 目标主机名覆盖值
    @param port 目标端口覆盖值
    @param username 认证用户名覆盖值
    @param password 认证密码覆盖值
    @param vhost 虚拟主机名称覆盖值
    @param ssl SSL/TLS 传输加密覆盖值
    @return 深度融合后的 AMQP 连接串
    """
    params: dict[str, Any] = {
        "host": "localhost",
        "port": None,
        "username": "guest",
        "password": "guest",
        "vhost": "/",
        "ssl": False,
    }
    if base_url:
        parsed = parse_amqp_url(base_url)
        params["host"] = parsed["host"]
        params["port"] = parsed["port"]
        if parsed["username"] is not None:
            params["username"] = parsed["username"]
        if parsed["password"] is not None:
            params["password"] = parsed["password"]
        if parsed["vhost"] is not None:
            params["vhost"] = parsed["vhost"]
        params["ssl"] = parsed["ssl"]

    if host is not None:
        params["host"] = host
    if port is not None:
        params["port"] = port
    if username is not None:
        params["username"] = username
    if password is not None:
        params["password"] = password
    if vhost is not None:
        params["vhost"] = vhost
    if ssl is not None:
        params["ssl"] = ssl

    return build_amqp_url(
        host=params["host"],
        port=params["port"],
        username=params["username"],
        password=params["password"],
        vhost=params["vhost"],
        ssl=params["ssl"],
    )


def merge_management_url(
    base_url: str | None = None,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    password: str | None = None,
    ssl: bool | None = None,
    path: str | None = None,
) -> str | None:
    """将分立参数与基础 Management URL 深度融合覆盖.

    若既无 base_url 也无任何 management 显式参数，则返回 None 保持未启用状态。

    @param base_url 可选的基础 Management API 基地址
    @param host Management 主机覆盖值
    @param port Management 端口覆盖值
    @param username 认证用户名覆盖值
    @param password 认证密码覆盖值
    @param ssl HTTPS 覆盖值
    @param path API 路径覆盖值
    @return 融合后的 Management API 地址，或未启用时返回 None
    """
    has_explicit = any(
        arg is not None
        for arg in (base_url, host, port, username, password, ssl, path)
    )
    if not has_explicit:
        return None

    params: dict[str, Any] = {
        "host": "localhost",
        "port": 15672,
        "username": "guest",
        "password": "guest",
        "ssl": False,
        "path": "",
    }
    if base_url:
        parsed = parse_management_url(base_url)
        params["host"] = parsed["host"]
        params["port"] = parsed["port"]
        if parsed["username"] is not None:
            params["username"] = parsed["username"]
        if parsed["password"] is not None:
            params["password"] = parsed["password"]
        params["ssl"] = parsed["ssl"]
        params["path"] = parsed["path"]

    if host is not None:
        params["host"] = host
    if port is not None:
        params["port"] = port
    if username is not None:
        params["username"] = username
    if password is not None:
        params["password"] = password
    if ssl is not None:
        params["ssl"] = ssl
    if path is not None:
        params["path"] = path

    return build_management_url(
        host=params["host"],
        port=params["port"],
        username=params["username"],
        password=params["password"],
        ssl=params["ssl"],
        path=params["path"],
    )


class RabbitMQConnectionConfig(BaseModel):
    """RabbitMQ 单个实例连接元数据配置."""

    name: str = Field(default="default", description="连接标识别名")
    amqp_url: str = Field(..., description="AMQP 0-9-1 连接协议串")
    management_url: str | None = Field(default=None, description="HTTP Management API 访问基地址")

    @property
    def masked_amqp_url(self) -> str:
        """获取脱敏后的 AMQP 连接串."""
        masked = mask_url(self.amqp_url)
        return masked if masked is not None else ""

    @property
    def masked_management_url(self) -> str | None:
        """获取脱敏后的 Management API 地址."""
        return mask_url(self.management_url)

    def to_summary_dict(self) -> dict[str, Any]:
        """生成脱敏后的连接元数据概要字典.

        @return 脱敏连接概要信息字典
        """
        return {
            "name": self.name,
            "amqp_url": self.masked_amqp_url,
            "management_url": self.masked_management_url,
            "has_management": self.management_url is not None,
        }


class RabbitMQServerConfig(BaseModel):
    """RabbitMQ MCP 服务端运行时全局拓扑与安全配置."""

    connections: dict[str, RabbitMQConnectionConfig] = Field(
        default_factory=dict, description="已配置的所有实例连接字典"
    )
    allow_write: bool = Field(default=False, description="是否允许写入与破坏性操作门禁开关")
    default_connection_name: str = Field(default="default", description="默认连接别名")

    def get_connection(self, name: str = "default") -> RabbitMQConnectionConfig:
        """根据连接名称检索配置对象.

        若请求 'default' 且未显式定义名为 'default' 的连接，则自动回退到配置指定的 default_connection_name。

        @param name 连接别名，默认为 'default'
        @return 对应的连接配置对象
        @throws KeyError 当指定的连接别名不存在时抛出
        """
        target_name = name or self.default_connection_name
        if target_name == "default" and target_name not in self.connections:
            target_name = self.default_connection_name

        if target_name not in self.connections:
            available = list(self.connections.keys())
            raise KeyError(f"未找到指定的 RabbitMQ 连接配置: '{name}'，当前可用连接列表: {available}")
        return self.connections[target_name]

    def list_connections(self) -> list[dict[str, Any]]:
        """获取脱敏后的所有可用连接列表.

        @return 连接概要字典列表，空时返回空列表
        """
        return [conn.to_summary_dict() for conn in self.connections.values()]

    def apply_cli_overrides(
        self,
        url: str | None = None,
        management_url: str | None = None,
        allow_write: bool = False,
        broker_host: str | None = None,
        broker_port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        vhost: str | None = None,
        ssl: bool | None = None,
        management_host: str | None = None,
        management_port: int | None = None,
        management_ssl: bool | None = None,
    ) -> None:
        """应用 CLI 命令行参数覆盖（保障 CLI > ENV > Config 优先级）.

        支持完整连接串覆盖与细粒度分立参数深度融合覆盖。

        @param url 命令行传入的 AMQP 连接协议串
        @param management_url 命令行传入的 Management API 地址
        @param allow_write 命令行传入的写操作放行标志
        @param broker_host 目标 Broker 主机名
        @param broker_port 目标 Broker 端口号
        @param username 认证用户名
        @param password 认证密码
        @param vhost 虚拟主机名称
        @param ssl 是否启用 AMQP TLS/SSL
        @param management_host Management 服务主机名
        @param management_port Management 服务端口号
        @param management_ssl 是否启用 Management HTTPS
        """
        target_name = (
            self.default_connection_name
            if self.default_connection_name in self.connections
            else "default"
        )

        has_amqp_input = any(
            x is not None
            for x in (url, broker_host, broker_port, username, password, vhost, ssl)
        )
        has_mgmt_input = any(
            x is not None
            for x in (
                management_url,
                management_host,
                management_port,
                management_ssl,
            )
        )

        if target_name in self.connections:
            target_conn = self.connections[target_name]
        else:
            target_conn = RabbitMQConnectionConfig(
                name=target_name,
                amqp_url="amqp://guest:guest@localhost:5672/",
                management_url=None,
            )
            self.connections[target_name] = target_conn

        if has_amqp_input:
            base_amqp = url or target_conn.amqp_url
            target_conn.amqp_url = merge_amqp_url(
                base_url=base_amqp,
                host=broker_host,
                port=broker_port,
                username=username,
                password=password,
                vhost=vhost,
                ssl=ssl,
            )

        if has_mgmt_input:
            parsed_amqp = parse_amqp_url(target_conn.amqp_url)
            effective_mgmt_host = management_host or broker_host or parsed_amqp.get("host")
            effective_mgmt_user = username or parsed_amqp.get("username")
            effective_mgmt_pass = password or parsed_amqp.get("password")
            base_mgmt = management_url or target_conn.management_url

            target_conn.management_url = merge_management_url(
                base_url=base_mgmt,
                host=effective_mgmt_host,
                port=management_port,
                username=effective_mgmt_user,
                password=effective_mgmt_pass,
                ssl=management_ssl,
            )

        if allow_write:
            self.allow_write = True



def _parse_bool(value: str | None, default: bool = False) -> bool:
    """解析布尔字符串环境变量."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config(
    config_path: Path | str | None = None,
    allow_write: bool | None = None,
) -> RabbitMQServerConfig:
    """加载并解析 RabbitMQ MCP 服务端配置.

    加载优先级：显式入参 > 环境变量指定文件 > 默认 connections.yaml > 环境变量 URL/分立参数兜底。
    支持 MCP_RABBITMQ_URL/MCP_RABBITMQ_MANAGEMENT_URL 以及细粒度分立环境变量：
    - MCP_RABBITMQ_HOST / MCP_RABBITMQ_PORT
    - MCP_RABBITMQ_USERNAME / MCP_RABBITMQ_USER / MCP_RABBITMQ_PASSWORD
    - MCP_RABBITMQ_VHOST / MCP_RABBITMQ_SSL
    - MCP_RABBITMQ_MANAGEMENT_HOST / MCP_RABBITMQ_MANAGEMENT_PORT / MCP_RABBITMQ_MANAGEMENT_SSL

    @param config_path 配置文件路径
    @param allow_write 显式指定的写保护门禁开关
    @return 组装完成的 RabbitMQServerConfig 对象
    """
    resolved_path: Path | None = None
    if config_path:
        resolved_path = Path(config_path)
    elif env_path := os.getenv("MCP_RABBITMQ_CONFIG_PATH"):
        resolved_path = Path(env_path)
    elif Path("connections.yaml").is_file():
        resolved_path = Path("connections.yaml")

    connections_map: dict[str, RabbitMQConnectionConfig] = {}
    cfg_allow_write = False
    default_conn_name = "default"

    # 1. 尝试从 YAML 配置文件解析
    if resolved_path and resolved_path.is_file():
        with resolved_path.open("r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        cfg_allow_write = bool(raw_data.get("allow_write", False))
        default_conn_name = str(raw_data.get("default_connection", "default"))

        raw_conns = raw_data.get("connections", {})
        if isinstance(raw_conns, dict):
            for name, conn_info in raw_conns.items():
                if isinstance(conn_info, dict):
                    connections_map[name] = RabbitMQConnectionConfig(
                        name=name,
                        amqp_url=str(conn_info.get("amqp_url", "")),
                        management_url=conn_info.get("management_url"),
                    )

    # 2. 环境变量提取与深度融合
    env_amqp = os.getenv("MCP_RABBITMQ_URL")
    env_mgmt = os.getenv("MCP_RABBITMQ_MANAGEMENT_URL")

    env_host = os.getenv("MCP_RABBITMQ_HOST")
    env_port_str = os.getenv("MCP_RABBITMQ_PORT")
    env_port = int(env_port_str) if env_port_str and env_port_str.isdigit() else None
    env_user = os.getenv("MCP_RABBITMQ_USERNAME") or os.getenv("MCP_RABBITMQ_USER")
    env_pass = os.getenv("MCP_RABBITMQ_PASSWORD")
    env_vhost = os.getenv("MCP_RABBITMQ_VHOST")
    env_ssl = (
        _parse_bool(os.getenv("MCP_RABBITMQ_SSL"))
        if "MCP_RABBITMQ_SSL" in os.environ
        else None
    )

    env_mgmt_host = os.getenv("MCP_RABBITMQ_MANAGEMENT_HOST") or env_host
    env_mgmt_port_str = os.getenv("MCP_RABBITMQ_MANAGEMENT_PORT")
    env_mgmt_port = int(env_mgmt_port_str) if env_mgmt_port_str and env_mgmt_port_str.isdigit() else None
    env_mgmt_user = (
        os.getenv("MCP_RABBITMQ_MANAGEMENT_USERNAME")
        or os.getenv("MCP_RABBITMQ_MANAGEMENT_USER")
        or env_user
    )
    env_mgmt_pass = os.getenv("MCP_RABBITMQ_MANAGEMENT_PASSWORD") or env_pass
    env_mgmt_ssl = (
        _parse_bool(os.getenv("MCP_RABBITMQ_MANAGEMENT_SSL"))
        if "MCP_RABBITMQ_MANAGEMENT_SSL" in os.environ
        else None
    )

    has_split_env = any(
        x is not None
        for x in (
            env_host,
            env_port,
            env_user,
            env_pass,
            env_vhost,
            env_ssl,
        )
    )
    has_mgmt_split_env = any(
        x is not None
        for x in (
            os.getenv("MCP_RABBITMQ_MANAGEMENT_HOST"),
            env_mgmt_port,
            os.getenv("MCP_RABBITMQ_MANAGEMENT_USERNAME"),
            os.getenv("MCP_RABBITMQ_MANAGEMENT_USER"),
            os.getenv("MCP_RABBITMQ_MANAGEMENT_PASSWORD"),
            env_mgmt_ssl,
        )
    )

    target_conn_name = (
        default_conn_name
        if default_conn_name in connections_map
        else "default"
    )

    if not connections_map or env_amqp or has_split_env or env_mgmt or has_mgmt_split_env:
        base_amqp: str | None = None
        base_mgmt: str | None = None

        if target_conn_name in connections_map:
            base_amqp = connections_map[target_conn_name].amqp_url
            base_mgmt = connections_map[target_conn_name].management_url

        if env_amqp:
            base_amqp = env_amqp
        if env_mgmt:
            base_mgmt = env_mgmt

        final_amqp = merge_amqp_url(
            base_url=base_amqp,
            host=env_host,
            port=env_port,
            username=env_user,
            password=env_pass,
            vhost=env_vhost,
            ssl=env_ssl,
        )

        final_mgmt = merge_management_url(
            base_url=base_mgmt,
            host=env_mgmt_host,
            port=env_mgmt_port,
            username=env_mgmt_user,
            password=env_mgmt_pass,
            ssl=env_mgmt_ssl,
        )

        connections_map[target_conn_name] = RabbitMQConnectionConfig(
            name=target_conn_name,
            amqp_url=final_amqp,
            management_url=final_mgmt,
        )

    # 3. 计算最终门禁状态
    env_allow_write = _parse_bool(os.getenv("MCP_RABBITMQ_ALLOW_WRITE"), default=cfg_allow_write)
    final_allow_write = allow_write if allow_write is not None else env_allow_write

    return RabbitMQServerConfig(
        connections=connections_map,
        allow_write=final_allow_write,
        default_connection_name=default_conn_name,
    )


_GLOBAL_CONFIG: RabbitMQServerConfig | None = None
_CONFIG_LOCK = threading.Lock()


def get_global_config() -> RabbitMQServerConfig:
    """获取当前进程全局配置实例，未初始化时自动加载并加锁保护."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        with _CONFIG_LOCK:
            if _GLOBAL_CONFIG is None:
                _GLOBAL_CONFIG = load_config()
    return _GLOBAL_CONFIG


def set_global_config(config: RabbitMQServerConfig) -> None:
    """线程安全设置全局配置实例."""
    global _GLOBAL_CONFIG
    with _CONFIG_LOCK:
        _GLOBAL_CONFIG = config


def reset_global_config() -> None:
    """线程安全重置全局配置实例为初始状态."""
    global _GLOBAL_CONFIG
    with _CONFIG_LOCK:
        _GLOBAL_CONFIG = None
