"""Create a development JWT.

Usage: PAYMENTS_JWT_SECRET=... python -m payments_mcp.token --scopes payments:read,payments:write
"""
import argparse

from . import config
from .auth import READ_SCOPE, WRITE_SCOPE, issue_token


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="dev-agent")
    parser.add_argument("--scopes", default=f"{READ_SCOPE},{WRITE_SCOPE}")
    parser.add_argument("--ttl", type=int, default=3600, help="lifetime in seconds")
    args = parser.parse_args()
    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    print(issue_token(config.jwt_secret(), args.subject, scopes, args.ttl))


if __name__ == "__main__":
    main()
