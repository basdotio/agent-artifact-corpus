"""运行环境健康自检探针 (--check / --doctor) 与外部二进制跨平台寻址模块。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from mcp_server_traffic_inspector import __version__
from mcp_server_traffic_inspector.config import ServerConfig
from mcp_server_traffic_inspector.storage import StorageBus

CheckStatus = Literal["ok", "warning", "error"]


@dataclass(frozen=True, slots=True)
class ComponentCheckResult:
    """单项运行环境组件的健康自检结果。

    Attributes:
        status: 状态标识（ok、warning、error）。
        required: 是否为核心强依赖组件。
        message: 人类与 Agent 可读的诊断摘要说明。
        path: 探测到的组件或文件本地路径（如适用）。
        version: 组件版本字符串（如适用）。
        extra: 附加结构化元数据（如 SQLite journal_mode、表清单等）。
    """

    status: CheckStatus
    required: bool
    message: str
    path: str | None = None
    version: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为扁平化字典结构以便序列化输出。

        Returns:
            包含组件状态、路径、版本及扩展属性的字典。
        """
        base = {
            "status": self.status,
            "required": self.required,
            "message": self.message,
        }
        if self.path is not None:
            base["path"] = self.path
        if self.version is not None:
            base["version"] = self.version
        base.update(self.extra)
        return base


@dataclass(frozen=True, slots=True)
class DoctorReport:
    """--check / --doctor 整体运行环境健康诊断报告。

    Attributes:
        service: 服务包名称。
        version: 当前服务版本号。
        ready: 核心组件及显式配置项是否全部就绪。
        exit_code: 推荐的进程退出码（就绪为 0，存在阻塞错误为 1）。
        checks: 各子系统探测结果映射表。
    """

    service: str
    version: str
    ready: bool
    exit_code: int
    checks: dict[str, ComponentCheckResult]

    def to_dict(self) -> dict[str, Any]:
        """转换为标准可 JSON 序列化的字典结构。

        Returns:
            完整的结构化自检报告字典。
        """
        return {
            "service": self.service,
            "version": self.version,
            "ready": self.ready,
            "exit_code": self.exit_code,
            "checks": {name: item.to_dict() for name, item in self.checks.items()},
        }

    def to_json(self, indent: int = 2) -> str:
        """序列化为格式化的 JSON 文本。

        Args:
            indent: JSON 缩进空格数，默认为 2。

        Returns:
            JSON 格式字符串。
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


def _default_tshark_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_key in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_key)
        if root:
            candidates.append(Path(root) / "Wireshark" / "tshark.exe")
    candidates.extend(
        [
            Path("/usr/bin/tshark"),
            Path("/usr/local/bin/tshark"),
            Path("/opt/homebrew/bin/tshark"),
        ]
    )
    return candidates


def resolve_tshark_path(
    explicit_path: str | None = None,
    which_fn: Callable[[str], str | None] = shutil.which,
    candidate_paths: Sequence[Path] | None = None,
) -> Path | None:
    """按优先级解析 tshark 可执行文件绝对路径。

    寻址优先级：显式指定路径 > 系统 PATH (shutil.which) > 平台默认安装目录。

    Args:
        explicit_path: 用户通过 CLI 或环境变量显式指定的路径。
        which_fn: PATH 查找函数，默认使用 shutil.which。
        candidate_paths: 平台标准安装候选路径列表，为 None 时使用内置跨平台候选集。

    Returns:
        命中且存在的 tshark Path 对象；若未找到或显式路径不存在则返回 None。
    """
    # 1. 若显式指定了路径，仅校验该路径是否存在，不静默回退掩盖配置错误
    if explicit_path and explicit_path.strip():
        custom = Path(explicit_path.strip()).expanduser()
        return custom.resolve() if custom.is_file() else None

    # 2. 检索系统 PATH 环境变量
    found_in_path = which_fn("tshark")
    if found_in_path:
        path_obj = Path(found_in_path)
        if path_obj.is_file():
            return path_obj.resolve()

    # 3. 探测操作系统默认安装路径
    fallbacks = (
        list(candidate_paths) if candidate_paths is not None else _default_tshark_candidates()
    )
    for candidate in fallbacks:
        if candidate.is_file():
            return candidate.resolve()

    return None


def resolve_mitmdump_path(
    which_fn: Callable[[str], str | None] = shutil.which,
) -> Path | None:
    """解析当前环境中的 mitmdump 可执行文件路径。

    优先检查当前 Python 解释器所属虚拟环境的 Scripts/bin 目录，其次检索系统 PATH。

    Args:
        which_fn: PATH 查找函数，默认使用 shutil.which。

    Returns:
        mitmdump 可执行文件绝对路径，未找到时返回 None。
    """
    exe_dir = Path(sys.executable).resolve().parent
    for binary_name in ("mitmdump.exe", "mitmdump"):
        candidate = exe_dir / binary_name
        if candidate.is_file():
            return candidate.resolve()

    found = which_fn("mitmdump")
    if found and Path(found).is_file():
        return Path(found).resolve()

    return None


def _probe_binary_version(binary_path: Path) -> str | None:
    try:
        completed = subprocess.run(
            [str(binary_path), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5.0,
            check=False,
        )
        output = (completed.stdout or completed.stderr or "").strip()
        if output:
            return output.splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None
    return None


def _check_python_runtime() -> ComponentCheckResult:
    ver_info = sys.version_info
    ver_str = f"{ver_info.major}.{ver_info.minor}.{ver_info.micro}"
    ok = (ver_info.major, ver_info.minor) >= (3, 11)
    return ComponentCheckResult(
        status="ok" if ok else "error",
        required=True,
        message="Python 运行时满足 >= 3.11 要求" if ok else "Python 版本低于 3.11",
        path=sys.executable,
        version=ver_str,
    )


def _check_mitmdump() -> ComponentCheckResult:
    mitmdump_bin = resolve_mitmdump_path()
    if mitmdump_bin is not None:
        version_line = _probe_binary_version(mitmdump_bin)
        return ComponentCheckResult(
            status="ok",
            required=True,
            message="mitmdump 代理引擎可用",
            path=str(mitmdump_bin),
            version=version_line or "installed",
        )

    try:
        from mitmproxy import version as mitm_version

        return ComponentCheckResult(
            status="ok",
            required=True,
            message="mitmproxy Python 核心库已就绪",
            path=sys.executable,
            version=str(getattr(mitm_version, "VERSION", "unknown")),
        )
    except ImportError as exc:
        return ComponentCheckResult(
            status="error",
            required=True,
            message=f"未检测到 mitmdump 或 mitmproxy 依赖: {exc}",
        )


def is_admin_user() -> bool:
    """探测当前进程是否具备 Windows 管理员权限或 POSIX root 权限。"""
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return os.getuid() == 0 if hasattr(os, "getuid") else False


def _check_tshark(explicit_path: str | None) -> ComponentCheckResult:
    resolved = resolve_tshark_path(explicit_path=explicit_path)
    if resolved is not None:
        version_line = _probe_binary_version(resolved)
        is_admin = is_admin_user()
        admin_note = " (管理员权限就绪)" if is_admin else " (普通权限，已启用时空切片模式)"
        return ComponentCheckResult(
            status="ok",
            required=bool(explicit_path),
            message=f"tshark 协议分析引擎可用{admin_note}",
            path=str(resolved),
            version=version_line or "available",
            extra={"is_admin": is_admin},
        )

    if explicit_path:
        return ComponentCheckResult(
            status="error",
            required=True,
            message=f"显式指定的 tshark 路径不存在或不可访问: {explicit_path}",
            path=explicit_path,
        )

    return ComponentCheckResult(
        status="warning",
        required=False,
        message=(
            "未在 PATH 或默认目录检测到 tshark"
            "（L7 HTTP 抓包正常可用，L3/L4 PCAP 功能需安装 Wireshark/tshark）"
        ),
    )


def _check_ca_certificate() -> ComponentCheckResult:
    confdir = Path.home() / ".mitmproxy"
    pem_cert = confdir / "mitmproxy-ca-cert.pem"
    cer_cert = confdir / "mitmproxy-ca-cert.cer"

    if pem_cert.is_file() or cer_cert.is_file():
        target = pem_cert if pem_cert.is_file() else cer_cert
        return ComponentCheckResult(
            status="ok",
            required=False,
            message="mitmproxy CA 根证书已生成",
            path=str(target.resolve()),
        )

    return ComponentCheckResult(
        status="warning",
        required=False,
        message="mitmproxy CA 根证书尚未生成（首次启动 start_http_capture 时将自动生成）",
        path=str(pem_cert),
    )


def get_ca_env_vars(ca_cert_path: Path | str | None = None) -> dict[str, str]:
    """获取适配常见运行时（Python、Node.js、curl、git）的 CA 证书环境变量字典。

    Args:
        ca_cert_path: 可选的显式 CA 证书文件路径；未指定时默认从 ~/.mitmproxy 目录检索。

    Returns:
        包含 SSL_CERT_FILE、REQUESTS_CA_BUNDLE 等环境变量键值映射的字典；
        若未探测到可用证书文件则返回空字典 {}。
    """
    if ca_cert_path is not None:
        target = Path(ca_cert_path)
        if not target.is_file():
            return {}
    else:
        confdir = Path.home() / ".mitmproxy"
        pem_cert = confdir / "mitmproxy-ca-cert.pem"
        cer_cert = confdir / "mitmproxy-ca-cert.cer"
        target = pem_cert if pem_cert.is_file() else (cer_cert if cer_cert.is_file() else None)
        if target is None:
            return {}

    target_str = str(target.resolve())
    return {
        "SSL_CERT_FILE": target_str,
        "REQUESTS_CA_BUNDLE": target_str,
        "NODE_EXTRA_CA_CERTS": target_str,
        "CURL_CA_BUNDLE": target_str,
        "GIT_SSL_CAINFO": target_str,
    }


def trust_ca_certificate(
    system_wide: bool = False,
    ca_cert_path: Path | str | None = None,
) -> dict[str, Any]:
    """将 mitmproxy CA 证书安装至操作系统受信任根证书库，并生成环境变量配置。

    Args:
        system_wide: Windows 下是否强制写入系统全局库（需要管理员权限），
            默认 False（当前用户根证书库，免提权）。
        ca_cert_path: 可选的显式 CA 证书文件路径；未指定时默认从 ~/.mitmproxy 目录检索。

    Returns:
        包含 status、message、scope、cert_path 与 env_vars 的字典。
    """
    if ca_cert_path is not None:
        target_path = Path(ca_cert_path)
        target = target_path if target_path.is_file() else None
    else:
        confdir = Path.home() / ".mitmproxy"
        pem_cert = confdir / "mitmproxy-ca-cert.pem"
        cer_cert = confdir / "mitmproxy-ca-cert.cer"
        target = cer_cert if cer_cert.is_file() else (pem_cert if pem_cert.is_file() else None)

    env_vars = get_ca_env_vars(ca_cert_path=target)

    if target is None:
        return {
            "status": "error",
            "message": "未找到已生成的 mitmproxy CA 证书文件，请先启动一次 HTTP 抓包自动生成证书。",
            "env_vars": env_vars,
        }

    target_str = str(target.resolve())
    if sys.platform == "win32":
        scope = "LocalMachine" if system_wide else "CurrentUser"
        cmd = (
            ["certutil", "-addstore", "-f", "Root", target_str]
            if system_wide
            else ["certutil", "-user", "-addstore", "Root", target_str]
        )
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15.0,
                check=False,
            )
            if completed.returncode == 0:
                return {
                    "status": "ok",
                    "scope": scope,
                    "cert_path": target_str,
                    "message": f"成功将 CA 证书导入 Windows {scope} 受信任根证书颁发机构。",
                    "env_vars": env_vars,
                }
            return {
                "status": "error",
                "scope": scope,
                "cert_path": target_str,
                "message": f"certutil 导入证书失败: {completed.stderr or completed.stdout}",
                "env_vars": env_vars,
            }
        except Exception as exc:
            return {
                "status": "error",
                "scope": scope,
                "cert_path": target_str,
                "message": f"执行 certutil 命令异常: {exc}",
                "env_vars": env_vars,
            }

    if sys.platform == "darwin":
        cmd = [
            "security",
            "add-trusted-cert",
            "-d",
            "-r",
            "trustRoot",
            "-k",
            str(Path.home() / "Library/Keychains/login.keychain-db"),
            target_str,
        ]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
            status = "ok" if completed.returncode == 0 else "error"
            return {
                "status": status,
                "scope": "login.keychain",
                "cert_path": target_str,
                "message": "macOS 钥匙串导入完毕" if status == "ok" else completed.stderr,
                "env_vars": env_vars,
            }
        except Exception as exc:
            return {
                "status": "error",
                "cert_path": target_str,
                "message": f"macOS security 导入异常: {exc}",
                "env_vars": env_vars,
            }

    # Linux 平台引导
    return {
        "status": "manual_action_required",
        "scope": "system",
        "cert_path": target_str,
        "message": (
            f"Linux 请执行: sudo cp '{target_str}' "
            "/usr/local/share/ca-certificates/mitmproxy.crt && sudo update-ca-certificates"
        ),
        "env_vars": env_vars,
    }


def _check_sqlite_wal(
    config: ServerConfig,
    storage: StorageBus | None = None,
) -> ComponentCheckResult:
    owns_storage = storage is None
    bus = storage or StorageBus.from_config(config)
    try:
        bus.initialize()
        health = bus.verify_health()
        required_tables = {"http_flows", "http_bodies", "intercept_rules"}
        is_ready = (
            health.writable
            and health.journal_mode.lower() == "wal"
            and required_tables.issubset(set(health.tables))
        )
        return ComponentCheckResult(
            status="ok" if is_ready else "error",
            required=True,
            message=(
                "SQLite WAL 共享数据总线与分流目录读写正常"
                if is_ready
                else f"SQLite WAL 数据总线自检未通过: {health.error or health.journal_mode}"
            ),
            path=str(health.db_path),
            extra={
                "journal_mode": health.journal_mode.lower(),
                "tables": health.tables,
                "bodies_dir": str(health.bodies_dir),
            },
        )
    finally:
        if owns_storage:
            bus.cleanup()


def run_doctor(
    config: ServerConfig,
    storage: StorageBus | None = None,
) -> DoctorReport:
    """执行全量运行环境健康自检探针并汇总报告。

    Args:
        config: 当前解析的服务端配置对象。
        storage: 可选的外部已初始化 StorageBus 实例；未传入时内部创建临时总线并在探测后清理。

    Returns:
        包含各项检测明细、总就绪状态与退出码的 DoctorReport。
    """
    # 1. 依次执行五大核心与辅助探针
    checks: dict[str, ComponentCheckResult] = {
        "python_runtime": _check_python_runtime(),
        "mitmdump": _check_mitmdump(),
        "tshark": _check_tshark(config.tshark_path),
        "ca_certificate": _check_ca_certificate(),
        "sqlite_wal": _check_sqlite_wal(config, storage=storage),
    }

    # 2. 判定整体就绪状态（不存在任何 status == 'error' 的组件即视为就绪）
    ready = all(item.status != "error" for item in checks.values())
    exit_code = 0 if ready else 1

    return DoctorReport(
        service="mcp-server-traffic-inspector",
        version=__version__,
        ready=ready,
        exit_code=exit_code,
        checks=checks,
    )
