"""JWT token creation and verification."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from mcp_rag.config import settings


class JWTHandler:
    """Tạo và xác minh JWT tokens.

    JWT có 3 phần: header.payload.signature
    - Header: thuật toán (HS256)
    - Payload: data (user_id, role, exp, ...)
    - Signature: chữ ký = HMAC(header + payload, secret)
    """

    def __init__(self) -> None:
        self.secret = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.issuer = settings.app_name
        self.audience = f"{settings.app_name}-client"

    def create_token(
        self,
        user_id: str,
        role: str,
        scopes: list[str] | None = None,
        expires_minutes: int | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Tạo JWT token.

        Args:
            user_id: ID của user (VD: "alice")
            role: Vai trò (admin, editor, viewer)
            scopes: Danh sách quyền (VD: ["read", "write"])
            expires_minutes: Thời gian hết hạn (phút)
            extra_claims: Claims bổ sung (VD: {"workspace_id": "ws-1"})

        Returns:
            JWT token string
        """
        now = datetime.now(UTC)
        expires_delta = timedelta(
            minutes=expires_minutes or settings.jwt_expiry_minutes
        )

        payload: dict[str, Any] = {
            # Standard claims (theo RFC 7519)
            "sub": user_id,                    # Subject = user ID
            "iss": self.issuer,                # Issuer = app name
            "aud": self.audience,              # Audience = client
            "iat": now,                        # Issued at
            "exp": now + expires_delta,        # Expiration
            "nbf": now,                        # Not before

            # Custom claims
            "role": role,
            "scopes": scopes or [],
        }

        # Merge extra claims (không ghi đè standard claims)
        if extra_claims:
            for key, value in extra_claims.items():
                if key not in payload:
                    payload[key] = value

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify token và trả về payload.

        Raises:
            PermissionError: Nếu token invalid, expired, sai signature...

        Returns:
            Payload dict (đã verify)
        """
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require": ["exp", "iat", "sub"],  # Bắt buộc có các claim này
                    "verify_exp": True,                # Check expiry
                    "verify_iat": True,                # Check issued at
                    "verify_nbf": True,                # Check not before
                },
            )
            return payload

        except jwt.ExpiredSignatureError as e:
            raise PermissionError("Token has expired") from e

        except jwt.InvalidAudienceError as e:
            raise PermissionError("Invalid audience") from e

        except jwt.InvalidIssuerError as e:
            raise PermissionError("Invalid issuer") from e

        except jwt.InvalidTokenError as e:
            raise PermissionError(f"Invalid token: {e}") from e

    def decode_unverified(self, token: str) -> dict[str, Any]:
        """Đọc payload KHÔNG verify signature.

        Chỉ dùng để debug — KHÔNG dùng trong production logic.
        """
        return jwt.decode(token, options={"verify_signature": False})  # type: ignore[no-any-return]


# Singleton
jwt_handler = JWTHandler()
