import httpx

from .retry import with_retry


class LLMClient:
    """Small client for providers exposing the OpenAI chat-completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float = 120.0,
    ) -> None:
        normalized_url = base_url.rstrip("/") + "/"
        self._client = httpx.AsyncClient(
            base_url=normalized_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout),
        )

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int,
        json_mode: bool = False,
        json_schema: dict | None = None,
    ) -> dict:
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_schema:
            strict_schema = dict(json_schema)
            properties = strict_schema.get("properties", {})
            strict_schema["required"] = list(properties)
            strict_schema["additionalProperties"] = False
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_output",
                    "strict": True,
                    "schema": strict_schema,
                },
            }
        elif json_mode:
            body["response_format"] = {"type": "json_object"}
        response = await with_retry(lambda: self._post(body))
        message = response["choices"][0]["message"]
        return {
            "content": message.get("content") or "",
            "usage": response.get("usage", {}),
            "finish_reason": response["choices"][0].get("finish_reason"),
        }

    async def _post(self, body: dict) -> dict:
        response = await self._client.post("chat/completions", json=body)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            error = data["error"]
            if isinstance(error, dict):
                message = error.get("message", "provider returned an error")
            else:
                message = str(error)
            raise httpx.HTTPStatusError(
                message,
                request=response.request,
                response=response,
            )
        if "choices" not in data or not data["choices"]:
            raise ValueError("provider response is missing a non-empty 'choices' array")
        return data

    async def aclose(self) -> None:
        await self._client.aclose()
