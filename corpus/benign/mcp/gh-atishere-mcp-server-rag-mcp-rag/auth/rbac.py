"""Role-Based Access Control (RBAC)."""

from enum import Enum
from typing import Final


class Role(str, Enum):
    """Vai trò của user."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Quyền hạn trong hệ thống."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


# Mapping: Role → Set[Permission]
# Final = không được thay đổi sau khi định nghĩa
ROLE_PERMISSIONS: Final[dict[Role, set[Permission]]] = {
    Role.ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.ADMIN,
    },
    Role.EDITOR: {
        Permission.READ,
        Permission.WRITE,
    },
    Role.VIEWER: {
        Permission.READ,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    """Kiểm tra role có permission không.

    Args:
        role: Tên role (VD: "admin")
        permission: Permission cần kiểm tra

    Returns:
        True nếu có quyền, False nếu không
    """
    try:
        role_enum = Role(role)
    except ValueError:
        # Role không tồn tại → không có quyền gì
        return False

    return permission in ROLE_PERMISSIONS.get(role_enum, set())


def require_permission(role: str, permission: Permission) -> None:
    """Raise PermissionError nếu role KHÔNG có permission.

    Dùng như "guard clause" trong code:
        require_permission(user.role, Permission.DELETE)
        # Nếu không có quyền → raise, code dừng
        # Nếu có quyền → tiếp tục
    """
    if not has_permission(role, permission):
        raise PermissionError(
            f"Role '{role}' lacks permission '{permission.value}'"
        )


def get_permissions(role: str) -> set[Permission]:
    """Lấy tất cả permissions của role."""
    try:
        role_enum = Role(role)
    except ValueError:
        return set()

    return ROLE_PERMISSIONS.get(role_enum, set()).copy()
