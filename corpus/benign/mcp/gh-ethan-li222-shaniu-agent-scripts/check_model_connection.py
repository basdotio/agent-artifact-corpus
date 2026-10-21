"""Check model endpoint networking without sending credentials or model prompts."""
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from shaniu.config import Settings


async def main():
    settings = Settings.from_env()
    result = dict(host=urlsplit(settings.api_base).hostname)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as client:
            async with client.get(settings.api_base, allow_redirects=False) as response:
                result.update(reachable=True, http_status=response.status)
    except Exception as error:
        cause = getattr(error, 'os_error', None)
        result.update(reachable=False, error_type=type(error).__name__, cause_type=type(cause).__name__, errno=getattr(cause, 'errno', None), winerror=getattr(cause, 'winerror', None))
    print(json.dumps(result))
    return 0 if result['reachable'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
