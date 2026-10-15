"""Settings are read from the environment at call time, so tests can change them."""
import os

MIN_SECRET_LENGTH = 32


def auth_required() -> bool:
    """Auth is required unless REQUIRE_AUTH is explicitly set to 'false' (fail closed)."""
    return os.getenv("REQUIRE_AUTH", "true").strip().lower() != "false"


def jwt_secret() -> str:
    secret = os.getenv("PAYMENTS_JWT_SECRET", "")
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"PAYMENTS_JWT_SECRET must be set and at least {MIN_SECRET_LENGTH} characters long"
        )
    return secret
