"""RabbitMQ 安全写保护门禁与高危动作二次确认守卫.

@author Ateng
@since 2026-10-04
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from mcp_server_rabbitmq.core.config import RabbitMQServerConfig, get_global_config

F = TypeVar("F", bound=Callable[..., Any])


class WriteGateError(PermissionError):
    """写入保护门禁拦截异常，当未开启 --allow-write 时禁止任何写入或破坏性操作."""

    def __init__(self, action: str) -> None:
        message = (
            f"写入保护门禁已启用：当前服务运行在只读保护模式下（未配置 --allow-write 或 "
            f"MCP_RABBITMQ_ALLOW_WRITE=true），已阻断写入或破坏性操作: '{action}'。"
            "如需执行该操作，请在启动时显式声明允许写入参数。"
        )
        super().__init__(message)
        self.action = action


def check_write_permission(action: str, config: RabbitMQServerConfig | None = None) -> None:
    """检查当前服务是否具备写入权限，无权限时抛出 WriteGateError.

    @param action 当前尝试执行的动作名称（如 'declare_queue', 'publish_message'）
    @param config 可选的服务配置对象，未传入时使用全局配置
    @throws WriteGateError 当服务处于只读保护模式时抛出
    """
    target_config = config or get_global_config()
    if not target_config.allow_write:
        raise WriteGateError(action=action)


def require_write(action: str) -> Callable[[F], F]:
    """写保护门禁装饰器，自动为目标同步或异步函数注入写权限前置校验.

    @param action 当前操作标识
    @return 装饰器函数
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                check_write_permission(action)
                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            check_write_permission(action)
            return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def check_confirmation(
    action: str,
    confirm: bool,
    target: str,
    impact_estimate: str | None = None,
) -> dict[str, Any] | None:
    """高危破坏性动作二次确认前置守卫 (ADR-0002).

    当 confirm 为 False 时，不执行物理破坏操作，返回受影响预估报告；
    当 confirm 为 True 时，返回 None 允许业务流程继续执行。

    @param action 待执行的高危动作名称（如 'delete_queue', 'purge_queue'）
    @param confirm 调用方是否已显式传入确认标志
    @param target 目标操作对象名称
    @param impact_estimate 可选的操作影响预估描述
    @return 若未确认返回预估报告字典，已确认返回 None
    """
    if confirm:
        return None

    default_estimate = "该操作具有破坏性且不可逆，请核对目标对象并在参数中设置 confirm=True 后重新执行"
    return {
        "status": "requires_confirmation",
        "confirmed": False,
        "action": action,
        "target": target,
        "impact_estimate": impact_estimate or default_estimate,
        "message": "高危操作需要显式二次确认，请确认后传入 confirm=True 重新执行",
    }
