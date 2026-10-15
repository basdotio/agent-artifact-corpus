"""Catalog and MuAPI client for the Seedance 2.5 Preview MCP server.

This is a focused companion to the broad MuAPI MCP reference server. It keeps
the same key-forwarding and prediction-polling model while exposing only the
standard Seedance 2.5 Preview routes, including their 480p variants.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests


API_BASE = os.getenv("MUAPI_BASE_URL", "https://api.muapi.ai/api/v1").rstrip("/")
HTTP_TIMEOUT = float(os.getenv("MUAPI_HTTP_TIMEOUT", "120"))
POLL_INTERVAL = float(os.getenv("MUAPI_POLL_INTERVAL", "2"))
POLL_TIMEOUT = float(os.getenv("MUAPI_POLL_TIMEOUT", "420"))

ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21"]
RESOLUTIONS = ["720p", "480p"]


def _string_schema(description: str, *, uri: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string", "description": description}
    if uri:
        schema["format"] = "uri"
    return schema


def _url_list_schema(description: str, maximum: int) -> dict[str, Any]:
    return {
        "type": "array",
        "description": description,
        "items": {"type": "string", "format": "uri"},
        "maxItems": maximum,
    }


def _duration_schema() -> dict[str, Any]:
    return {
        "type": "integer",
        "description": "Video duration in seconds.",
        "default": 5,
        "minimum": 4,
        "maximum": 30,
    }


def _output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "request_id": {"type": "string"},
            "status": {"type": "string"},
            "output": {"type": "object"},
        },
    }


def _generation_tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "outputSchema": _output_schema(),
    }


COMMON_RESOLUTION = {
    "type": "string",
    "description": "Output tier. The 720p route is the standard preview; 480p is faster and lower cost.",
    "enum": RESOLUTIONS,
    "default": "720p",
}

COMMON_SEED = {
    "type": "integer",
    "description": "Optional random seed. Use -1 for a random seed.",
}

TOOLS: list[dict[str, Any]] = [
    _generation_tool(
        "seedance_25_text_to_video",
        "Generate a Seedance 2.5 Preview video from text. Choose 720p or the faster 480p route.",
        {
            "prompt": _string_schema("Detailed scene, subject, camera, lighting, and motion description."),
            "resolution": COMMON_RESOLUTION,
            "aspect_ratio": {
                "type": "string",
                "description": "Output video aspect ratio.",
                "enum": ASPECT_RATIOS,
                "default": "16:9",
            },
            "duration": _duration_schema(),
            "seed": COMMON_SEED,
        },
        ["prompt"],
    ),
    _generation_tool(
        "seedance_25_image_to_video",
        "Animate a single image with Seedance 2.5 Preview at 720p or 480p.",
        {
            "prompt": _string_schema("Motion and scene description for the input image."),
            "image_url": _string_schema("Public URL of the image to animate.", uri=True),
            "resolution": COMMON_RESOLUTION,
            "aspect_ratio": {
                "type": "string",
                "description": "Output video aspect ratio.",
                "enum": ASPECT_RATIOS,
                "default": "16:9",
            },
            "duration": _duration_schema(),
            "seed": COMMON_SEED,
        },
        ["prompt", "image_url"],
    ),
    _generation_tool(
        "seedance_25_first_last_frame",
        "Generate a Seedance 2.5 Preview transition between a first and last image.",
        {
            "prompt": _string_schema("Describe the transition, subject continuity, and camera movement."),
            "images_list": _url_list_schema("Exactly two URLs: [first_frame, last_frame].", 2),
            "resolution": COMMON_RESOLUTION,
            "aspect_ratio": {
                "type": "string",
                "description": "Output video aspect ratio.",
                "enum": ASPECT_RATIOS,
                "default": "16:9",
            },
            "duration": _duration_schema(),
            "seed": COMMON_SEED,
        },
        ["prompt", "images_list"],
    ),
    _generation_tool(
        "seedance_25_omni_reference",
        "Generate a Seedance 2.5 Preview video from image, video, and audio references.",
        {
            "prompt": _string_schema("Describe how the references should combine into the generated video."),
            "images_list": _url_list_schema("Reference image URLs. Up to 20 images.", 20),
            "videos_list": _url_list_schema("Reference video URLs. Up to 6 clips.", 6),
            "audios_list": _url_list_schema("Reference audio URLs. Up to 6 files.", 6),
            "resolution": COMMON_RESOLUTION,
            "aspect_ratio": {
                "type": "string",
                "description": "Output video aspect ratio.",
                "enum": ASPECT_RATIOS,
                "default": "16:9",
            },
            "duration": _duration_schema(),
            "seed": COMMON_SEED,
        },
        ["prompt"],
    ),
    {
        "name": "muapi_predict_result",
        "description": "Poll a MuAPI prediction until it completes or fails.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "request_id": _string_schema("The request_id returned by a Seedance 2.5 generation call."),
            },
            "required": ["request_id"],
            "additionalProperties": False,
        },
        "outputSchema": _output_schema(),
    },
    {
        "name": "muapi_account_balance",
        "description": "Read the current MuAPI credit balance.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


@dataclass(frozen=True)
class Route:
    endpoint: str


ROUTES: dict[str, Route] = {
    "seedance_25_text_to_video": Route("seedance-2.5-text-to-video"),
    "seedance_25_image_to_video": Route("seedance-2.5-image-to-video"),
    "seedance_25_first_last_frame": Route("seedance-2.5-first-last-frame"),
    "seedance_25_omni_reference": Route("seedance-2.5-omni-reference"),
}

LOW_RES_ENDPOINTS = {
    "seedance_25_text_to_video": "seedance-2.5-text-to-video-480p",
    "seedance_25_image_to_video": "seedance-2.5-image-to-video-480p",
    "seedance_25_first_last_frame": "seedance-2.5-first-last-frame-480p",
    "seedance_25_omni_reference": "seedance-2.5-omni-reference-480p",
}

TOOL_BY_NAME = {tool["name"]: tool for tool in TOOLS}


class MuApiError(RuntimeError):
    """A safe, user-facing MuAPI error without provider-specific details."""

    def __init__(self, status_code: int, code: str = "MUAPI_REQUEST_FAILED") -> None:
        self.status_code = status_code
        self.code = code
        super().__init__(f"MuAPI request failed ({code}, HTTP {status_code})")

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "type": "muapi_error",
                "code": self.code,
                "status_code": self.status_code,
            }
        }


def api_key_from_env() -> str:
    return os.getenv("MUAPI_API_KEY") or os.getenv("MUAPIAPP_API_KEY") or ""


def _require_tool(tool_name: str) -> None:
    if tool_name not in TOOL_BY_NAME:
        raise ValueError(f"Unknown tool: {tool_name}")


def _require_url_list(arguments: dict[str, Any], key: str, *, minimum: int = 1, maximum: int) -> None:
    values = arguments.get(key)
    if not isinstance(values, list) or not (minimum <= len(values) <= maximum):
        raise ValueError(f"{key} must contain between {minimum} and {maximum} URL(s)")
    if not all(isinstance(value, str) and value for value in values):
        raise ValueError(f"{key} must contain non-empty URL strings")


def build_request(tool_name: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Validate MCP arguments and map them to an allowlisted MuAPI endpoint."""
    _require_tool(tool_name)
    if tool_name not in ROUTES:
        raise ValueError(f"{tool_name} is not a generation tool")

    allowed = set(TOOL_BY_NAME[tool_name]["inputSchema"]["properties"])
    unknown = set(arguments) - allowed
    if unknown:
        raise ValueError(f"Unsupported argument(s): {', '.join(sorted(unknown))}")

    payload = dict(arguments)
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required")

    if tool_name == "seedance_25_image_to_video":
        image_url = payload.get("image_url")
        if not isinstance(image_url, str) or not image_url:
            raise ValueError("image_url is required")
    elif tool_name == "seedance_25_first_last_frame":
        _require_url_list(payload, "images_list", minimum=2, maximum=2)
    else:
        for key, maximum in (("images_list", 20), ("videos_list", 6), ("audios_list", 6)):
            if key in payload and payload[key] is not None:
                _require_url_list(payload, key, maximum=maximum)

    resolution = payload.pop("resolution", "720p")
    if resolution not in RESOLUTIONS:
        raise ValueError(f"resolution must be one of: {', '.join(RESOLUTIONS)}")
    endpoint = LOW_RES_ENDPOINTS[tool_name] if resolution == "480p" else ROUTES[tool_name].endpoint

    return endpoint, payload


class MuApiClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("MUAPI_API_KEY is not configured")
        self.api_key = api_key

    @property
    def headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = requests.request(
                method,
                f"{API_BASE}/{path.lstrip('/')}",
                headers=self.headers,
                timeout=HTTP_TIMEOUT,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise MuApiError(503, "MUAPI_UNAVAILABLE") from exc

        try:
            body = response.json()
        except ValueError:
            body = None
        if not response.ok:
            code = "MUAPI_REQUEST_FAILED"
            if isinstance(body, dict):
                nested = body.get("error")
                if isinstance(nested, dict) and isinstance(nested.get("code"), str):
                    code = nested["code"]
                elif isinstance(body.get("code"), str):
                    code = body["code"]
            raise MuApiError(response.status_code, code)
        return body if body is not None else {}

    def submit(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._request("POST", endpoint, json=payload)
        if not isinstance(result, dict):
            raise MuApiError(502, "MUAPI_INVALID_RESPONSE")
        request_id = result.get("request_id") or result.get("id")
        if not request_id:
            raise MuApiError(502, "MUAPI_MISSING_REQUEST_ID")
        return {**result, "request_id": request_id}

    def prediction(self, request_id: str) -> dict[str, Any]:
        result = self._request("GET", f"predictions/{request_id}/result")
        if not isinstance(result, dict):
            raise MuApiError(502, "MUAPI_INVALID_RESPONSE")
        return result

    def wait_for_prediction(self, request_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + POLL_TIMEOUT
        terminal = {"completed", "succeeded", "done", "failed", "error", "canceled", "cancelled"}
        while time.monotonic() < deadline:
            result = self.prediction(request_id)
            status = str(result.get("status", "")).lower()
            if status in terminal:
                return result
            time.sleep(POLL_INTERVAL)
        raise MuApiError(504, "MUAPI_POLL_TIMEOUT")

    def balance(self) -> dict[str, Any]:
        result = self._request("GET", "account/balance")
        return result if isinstance(result, dict) else {"balance": result}


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any] | None,
    api_key: str,
    *,
    wait: bool = True,
) -> dict[str, Any]:
    arguments = dict(arguments or {})
    client = MuApiClient(api_key)

    if tool_name == "muapi_account_balance":
        return client.balance()
    if tool_name == "muapi_predict_result":
        request_id = arguments.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id is required")
        return client.wait_for_prediction(request_id) if wait else client.prediction(request_id)

    endpoint, payload = build_request(tool_name, arguments)
    submitted = client.submit(endpoint, payload)
    if not wait:
        return {"request_id": submitted["request_id"], "status": submitted.get("status", "queued")}
    return client.wait_for_prediction(submitted["request_id"])


def as_text(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)
