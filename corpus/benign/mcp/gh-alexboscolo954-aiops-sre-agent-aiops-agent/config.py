"""Runtime settings, read from AIOPS_* environment variables (or a .env file)."""

from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIOPS_", env_file=".env", extra="ignore")

    # LLM. Any init_chat_model string; set model_base_url for an
    # OpenAI-compatible gateway (LiteLLM, vLLM) and use "openai:<model>".
    model: str = "anthropic:claude-sonnet-5-5"
    model_base_url: str | None = None
    model_api_key: SecretStr | None = None
    model_headers: dict[str, str] = {}  # JSON, e.g. {"anthropic-workspace-id": "..."}
    max_model_calls: int = 30
    max_tool_calls: int = 25
    tool_output_limit: int = 8000  # max characters per tool result

    # Kubernetes. No silent fallback to the default kubeconfig context:
    # either run in-cluster or name the context explicitly.
    in_cluster: bool = False
    kubeconfig: Path | None = None
    kube_context: str | None = None
    namespaces: Annotated[list[str], NoDecode] = Field(default_factory=list)
    enable_actions: bool = False
    max_replicas: int = 10

    # Prometheus (optional: the server is skipped when unset).
    prometheus_url: str | None = None
    prometheus_token: SecretStr | None = None

    runbooks_dir: Path = Path("runbooks")

    # Webhook server.
    # Two tokens: Alertmanager can only submit alerts; only approvers can read
    # reports and approve actions.
    webhook_token: SecretStr | None = None
    approver_token: SecretStr | None = None
    max_concurrent_triages: int = 3  # alert storms queue instead of fanning out
    decision_timeout_seconds: int = 1800  # proposed actions go stale after this
    slack_webhook_url: SecretStr | None = None

    @field_validator("namespaces", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [ns.strip() for ns in v.split(",") if ns.strip()]
        return v
