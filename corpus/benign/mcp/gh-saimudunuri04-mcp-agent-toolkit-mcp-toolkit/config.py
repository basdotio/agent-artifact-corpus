"""Configuration: secrets load from AWS Secrets Manager first, env vars as fallback.

Expected Secrets Manager secret (JSON): ``mcp-agent-toolkit/config``
    {"LANGSMITH_API_KEY": "...", "BEDROCK_MODEL_ID": "..."}

Local/dev fallback env vars: LANGSMITH_API_KEY, LANGSMITH_PROJECT,
AWS_REGION, BEDROCK_MODEL_ID, MOCK_MODE (default "true"),
MCP_SERVER_URL, MCP_ALLOWED_TOOLS.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)

SECRET_NAME = os.getenv("SECRET_NAME", "mcp-agent-toolkit/config")
DEFAULT_ALLOWED_TOOLS = ("doc_search", "record_lookup", "text_stats")


def _from_secrets_manager(secret_name: str) -> dict:
    try:
        import boto3

        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        payload = json.loads(resp.get("SecretString") or "{}")
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        log.debug("Secrets Manager unavailable (%s); using env vars", exc)
        return {}


@dataclass
class Settings:
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_max_tokens: int = 512
    langsmith_api_key: str | None = None
    langsmith_project: str = "mcp-agent-toolkit"
    mock_mode: bool = True
    data_dir: str = "data"
    mcp_server_url: str | None = None
    allowed_tools: tuple = DEFAULT_ALLOWED_TOOLS

    @classmethod
    def load(cls) -> "Settings":
        secrets = _from_secrets_manager(SECRET_NAME)

        def get(k, d=None):
            return secrets.get(k, os.getenv(k, d))

        mock_raw = get("MOCK_MODE", "true")
        allowed_raw = get("MCP_ALLOWED_TOOLS", ",".join(DEFAULT_ALLOWED_TOOLS))
        return cls(
            aws_region=get("AWS_REGION", "us-east-1"),
            bedrock_model_id=get(
                "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            langsmith_api_key=get("LANGSMITH_API_KEY"),
            langsmith_project=get("LANGSMITH_PROJECT", "mcp-agent-toolkit"),
            mock_mode=str(mock_raw).lower() not in ("false", "0", "no"),
            data_dir=get("DATA_DIR", "data"),
            mcp_server_url=get("MCP_SERVER_URL"),
            allowed_tools=tuple(t.strip() for t in str(allowed_raw).split(",") if t.strip()),
        )
