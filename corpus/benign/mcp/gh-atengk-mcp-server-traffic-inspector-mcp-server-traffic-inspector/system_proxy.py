"""跨平台系统代理托管与 CA 根证书管理模块。

在 Windows 平台通过注册表托管全局系统代理并在退出时安全还原，
在非 Windows 环境（Linux/Docker）提供降级处理与代理配置指引。

@author Ateng
@since 2026-10-13
"""

from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("mcp_server_traffic_inspector.system_proxy")

# Windows Internet Settings 注册表子键路径
INTERNET_SETTINGS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def get_ca_certificate(
    custom_cert_dir: Path | None = None,
    install_to_system: bool = False,
) -> dict[str, Any]:
    """获取 mitmproxy 本地 CA 根证书路径及跨平台信任安装指引，在 Windows 上支持自动导入。

    Args:
        custom_cert_dir: 可选的自定义证书目录；未指定时默认使用用户主目录下 .mitmproxy。
        install_to_system: 是否在 Windows 上自动执行 certutil 安装至受信任根证书库，默认 False。

    Returns:
        包含证书存在状态、文件绝对路径及 Windows/Linux 信任安装命令指引与安装结果的字典。
    """
    cert_dir = custom_cert_dir or (Path.home() / ".mitmproxy")
    pem_path = cert_dir / "mitmproxy-ca-cert.pem"
    cer_path = cert_dir / "mitmproxy-ca-cert.cer"

    exists = pem_path.is_file() or cer_path.is_file()
    pem_str = str(pem_path.resolve()) if pem_path.is_file() else None
    cer_str = str(cer_path.resolve()) if cer_path.is_file() else None

    # 构建跨平台证书安装操作说明
    target_pem = pem_str or str(pem_path.resolve())
    target_cer = cer_str or str(cer_path.resolve())

    instructions = {
        "windows": [
            f'certutil -addstore -user Root "{target_pem}"',
            f'或者双击证书文件 "{target_cer}" 并导入至 "受信任的根证书颁发机构"。',
        ],
        "linux": [
            f'sudo cp "{target_pem}" /usr/local/share/ca-certificates/mitmproxy.crt',
            "sudo update-ca-certificates",
        ],
        "macos": [
            (
                "sudo security add-trusted-cert -d -r trustRoot "
                f'-k /Library/Keychains/System.keychain "{target_pem}"'
            ),
        ],
    }

    installed = False
    install_output = ""
    if install_to_system:
        if not exists:
            install_output = "证书文件尚不存在，无法执行自动安装。请先启动一次抓包生成证书。"
        elif sys.platform == "win32":
            target_install_file = pem_str or cer_str
            try:
                cmd = ["certutil", "-addstore", "-user", "Root", str(target_install_file)]
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15.0,
                    check=False,
                )
                install_output = (res.stdout or res.stderr or "").strip()
                installed = res.returncode == 0
            except Exception as exc:
                install_output = f"执行 certutil 安装异常: {exc}"
                installed = False
        else:
            install_output = (
                "非 Windows 平台不支持自动调用 certutil，请根据 instructions 中的指引手动执行。"
            )

    if exists:
        message = "成功定位到 mitmproxy 本地 CA 根证书，请根据操作系统指引将其添加到受信任证书库。"
    else:
        message = (
            f"未在目录 {cert_dir} 探测到 CA 证书。"
            "mitmproxy 将在首次启动 HTTP 抓包时自动生成该证书。"
        )

    res_dict: dict[str, Any] = {
        "exists": exists,
        "ca_pem_path": pem_str,
        "ca_cer_path": cer_str,
        "cert_directory": str(cert_dir.resolve()),
        "instructions": instructions,
        "message": message,
    }
    if install_to_system:
        res_dict["installed"] = installed
        res_dict["install_output"] = install_output

    return res_dict


class SystemProxyManager:
    """跨平台系统全局代理管理器。

    负责在 Windows 环境下按需托管系统注册表全局代理，
    并在进程退出时自动将代理状态安全还原为启动前初始值，防止宿主机网络断连。
    """

    def __init__(self) -> None:
        """初始化系统代理管理器。"""
        self._is_windows = sys.platform == "win32"
        self._initial_enabled: int | None = None
        self._initial_server: str | None = None
        self._modified_by_us = False

    def toggle_proxy(
        self,
        enable: bool,
        host: str = "127.0.0.1",
        port: int = 8080,
    ) -> dict[str, Any]:
        """开启或关闭系统全局网络代理。

        Args:
            enable: 是否开启系统代理。
            host: 代理服务监听的主机地址，默认 127.0.0.1。
            port: 代理服务监听的端口号，默认 8080。

        Returns:
            包含平台支持状态、当前代理开启状态及详细说明的结构化字典。
        """
        # 1. 前置检查跨平台兼容性
        if not self._is_windows:
            proxy_url = f"http://{host}:{port}"
            return {
                "supported": False,
                "system_proxy_enabled": False,
                "proxy_server": "",
                "message": (
                    f"当前操作系统环境不支持通过注册表自动托管系统代理。"
                    f"在 Linux/macOS/Docker 容器内，请通过环境变量配置代理，例如: "
                    f"export http_proxy={proxy_url} https_proxy={proxy_url}"
                ),
            }

        # 2. Windows 平台首次变更前记录原始系统代理状态
        if self._initial_enabled is None:
            self._initial_enabled, self._initial_server = self._read_registry()

        proxy_str = f"{host}:{port}"
        target_enable = 1 if enable else 0

        # 3. 写入注册表并刷新 Windows 系统网络设置
        try:
            self._write_registry(enabled=target_enable, server=proxy_str)
            self._refresh_system_settings()
            self._modified_by_us = True
            status_text = "开启" if enable else "关闭"
            logger.info("系统代理已成功%s: %s", status_text, proxy_str if enable else "已禁用")
            return {
                "supported": True,
                "system_proxy_enabled": enable,
                "proxy_server": proxy_str if enable else "",
                "message": f"Windows 系统全局代理已成功{status_text}。",
            }
        except Exception as exc:
            logger.error("设置 Windows 系统代理失败: %s", exc)
            return {
                "supported": True,
                "system_proxy_enabled": False,
                "proxy_server": "",
                "message": f"写入 Windows 代理注册表时发生异常: {exc}",
            }

    def restore_initial_state(self) -> None:
        """还原系统代理至本次会话变更前的初始状态。

        由 LifecycleManager / atexit 钩子自动调用，保障进程退出时不污染宿主机网络。
        """
        if not self._is_windows or not self._modified_by_us or self._initial_enabled is None:
            return

        try:
            logger.info(
                "正在还原 Windows 系统代理至会话前初始状态 (ProxyEnable=%s, ProxyServer=%s)...",
                self._initial_enabled,
                self._initial_server,
            )
            self._write_registry(
                enabled=self._initial_enabled,
                server=self._initial_server or "",
            )
            self._refresh_system_settings()
            self._modified_by_us = False
            logger.info("Windows 系统代理状态已成功还原。")
        except Exception as exc:
            logger.warning("还原 Windows 系统代理初始状态时发生非致命异常: %s", exc)

    def get_proxy_status(
        self,
        expected_host: str = "127.0.0.1",
        expected_port: int = 8080,
    ) -> dict[str, Any]:
        """查询当前系统全局代理状态及是否指向指定的目标抓包服务。

        Args:
            expected_host: 预期的抓包代理监听地址，默认 127.0.0.1。
            expected_port: 预期的抓包代理监听端口，默认 8080。

        Returns:
            包含 supported、enabled、proxy_server、is_pointing_to_inspector 等字段的字典。
        """
        if not self._is_windows:
            return {
                "supported": False,
                "system_proxy_enabled": False,
                "proxy_server": "",
                "is_pointing_to_inspector": False,
                "modified_by_current_session": False,
                "message": "当前操作系统环境不支持通过注册表管理系统代理。",
            }

        enabled, server = self._read_registry()
        is_enabled = bool(enabled)
        server_str = server.strip()
        expected = f"{expected_host}:{expected_port}"
        alt_expected = (
            f"127.0.0.1:{expected_port}" if expected_host in ("0.0.0.0", "localhost") else expected
        )
        is_pointing = is_enabled and (
            server_str == expected
            or server_str == alt_expected
            or server_str.endswith(f":{expected_port}")
        )
        status_word = "开启" if is_enabled else "关闭"
        return {
            "supported": True,
            "system_proxy_enabled": is_enabled,
            "proxy_server": server_str if is_enabled else "",
            "is_pointing_to_inspector": is_pointing,
            "modified_by_current_session": self._modified_by_us,
            "message": f"系统代理处于{status_word}状态 ({server_str or '未设置'})。",
        }

    def smart_restore(
        self,
        expected_host: str = "127.0.0.1",
        expected_port: int = 8080,
    ) -> dict[str, Any]:
        """按归属权安全复位系统全局代理 (Proxy Ownership Check)。

        仅当系统代理指向当前抓包代理或由当前会话主动开启时才执行关闭；
        若检测到当前系统代理指向第三方端口，则跳过关闭以保护用户网络。

        Args:
            expected_host: 预期的抓包代理监听地址，默认 127.0.0.1。
            expected_port: 预期的抓包代理监听端口，默认 8080。

        Returns:
            包含 supported、restored、system_proxy_enabled 与说明信息的字典。
        """
        if not self._is_windows:
            return {
                "supported": False,
                "restored": False,
                "system_proxy_enabled": False,
                "proxy_server": "",
                "reason": "unsupported_platform",
                "message": "当前平台不支持注册表系统代理托管。",
            }

        enabled, server = self._read_registry()
        if not enabled:
            return {
                "supported": True,
                "restored": True,
                "system_proxy_enabled": False,
                "proxy_server": server.strip(),
                "message": "系统代理当前已处于关闭状态，无需复位。",
            }

        server_str = server.strip()
        expected = f"{expected_host}:{expected_port}"
        alt_expected = (
            f"127.0.0.1:{expected_port}" if expected_host in ("0.0.0.0", "localhost") else expected
        )
        is_pointing = (
            server_str == expected
            or server_str == alt_expected
            or server_str.endswith(f":{expected_port}")
        )

        if self._modified_by_us or is_pointing:
            try:
                target_server = (
                    self._initial_server if (self._initial_enabled and self._initial_server) else ""
                )
                self._write_registry(enabled=0, server=target_server)
                self._refresh_system_settings()
                self._modified_by_us = False
                logger.info("已安全复位并关闭当前抓包实例托管的系统代理")
                return {
                    "supported": True,
                    "restored": True,
                    "system_proxy_enabled": False,
                    "proxy_server": "",
                    "message": "已成功复位并关闭当前抓包实例托管的系统代理。",
                }
            except Exception as exc:
                logger.error("复位系统代理失败: %s", exc)
                return {
                    "supported": True,
                    "restored": False,
                    "system_proxy_enabled": True,
                    "proxy_server": server_str,
                    "message": f"复位系统代理时发生异常: {exc}",
                }

        # 系统代理指向外部第三方
        logger.info(
            "当前系统代理指向外部服务 (%s)，非本抓包服务 (%s)，已跳过复位",
            server_str,
            expected,
        )
        return {
            "supported": True,
            "restored": False,
            "system_proxy_enabled": True,
            "proxy_server": server_str,
            "reason": "external_proxy_owned",
            "message": f"当前系统代理指向外部服务 ({server_str})，已跳过复位以保护第三方代理配置。",
        }

    def _read_registry(self) -> tuple[int, str]:
        """读取 Windows 注册表中当前 Internet Settings 代理配置。"""
        import winreg

        enabled = 0
        server = ""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, INTERNET_SETTINGS_KEY, 0, winreg.KEY_READ
            ) as key:
                try:
                    val, _ = winreg.QueryValueEx(key, "ProxyEnable")
                    enabled = int(val)
                except FileNotFoundError:
                    enabled = 0

                try:
                    val, _ = winreg.QueryValueEx(key, "ProxyServer")
                    server = str(val)
                except FileNotFoundError:
                    server = ""
        except Exception as exc:
            logger.warning("读取 Windows 代理注册表失败，将使用默认值: %s", exc)
        return (enabled, server)

    def _write_registry(self, enabled: int, server: str) -> None:
        """向 Windows 注册表写入 Internet Settings 代理配置。"""
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, INTERNET_SETTINGS_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, enabled)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server)

    def _refresh_system_settings(self) -> None:
        """通知 Windows 系统刷新代理设置以使注册表修改即刻生效。"""
        try:
            internet_option_settings_changed = 39
            internet_option_refresh = 37
            wininet = ctypes.windll.wininet
            wininet.InternetSetOptionW(0, internet_option_settings_changed, 0, 0)
            wininet.InternetSetOptionW(0, internet_option_refresh, 0, 0)
        except Exception as exc:
            logger.debug("调用 InternetSetOptionW 刷新网络选项时发生异常: %s", exc)
