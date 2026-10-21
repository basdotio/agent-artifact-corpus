"""Small HTTP helper shared by the cloud connectors: retries and throttling."""

import time
from typing import Any, Optional

import httpx

RETRY_STATUSES = {429, 500, 502, 503, 504}


def request(
    client: httpx.Client,
    method: str,
    url: str,
    attempts: int = 5,
    sleep=time.sleep,
    **kwargs: Any,
) -> httpx.Response:
    """Send a request, honouring Retry-After on 429/5xx with backoff.

    Raises:
        httpx.HTTPStatusError: After the last attempt, or for other 4xx errors.
    """
    delay = 1.0
    response: Optional[httpx.Response] = None
    for attempt in range(attempts):
        response = client.request(method, url, **kwargs)
        if response.status_code not in RETRY_STATUSES or attempt == attempts - 1:
            break
        retry_after = response.headers.get("Retry-After")
        try:
            wait = float(retry_after) if retry_after else delay
        except ValueError:
            wait = delay
        sleep(min(wait, 60.0))
        delay *= 2
    assert response is not None
    response.raise_for_status()
    return response
