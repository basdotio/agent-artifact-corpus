"""Run Twitter CLI with explicit cookies only, including expired-token failures."""
from __future__ import annotations

import os
import sys


def environment_cookies():
    from twitter_cli.auth import verify_cookies
    from twitter_cli.exceptions import AuthenticationError

    auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "")
    ct0 = os.environ.get("TWITTER_CT0", "")
    if not auth_token or not ct0:
        raise AuthenticationError("Explicit TWITTER_AUTH_TOKEN and TWITTER_CT0 required; browser extraction disabled")
    verify_cookies(auth_token, ct0)
    return {"auth_token": auth_token, "ct0": ct0}


def main():
    from twitter_cli import auth
    from twitter_cli.exceptions import AuthenticationError

    def blocked(*args, **kwargs):
        raise AuthenticationError("Browser cookie extraction disabled in Agent-Reach Plus")

    auth.get_cookies = environment_cookies
    auth.extract_from_browser = blocked
    auth._extract_in_process = blocked
    auth._extract_via_subprocess = blocked
    from twitter_cli.cli import cli
    if len(sys.argv) < 2 or sys.argv[1] not in ("search", "tweet"):
        raise SystemExit("Only search/tweet reading is exposed")
    cli()


if __name__ == "__main__":
    main()
