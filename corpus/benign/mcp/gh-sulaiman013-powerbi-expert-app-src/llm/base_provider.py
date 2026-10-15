"""
Base LLM Provider

Abstract interface for all LLM providers.
Ensures consistent behavior and security guarantees across providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""
    OLLAMA = "ollama"
    AZURE_FOUNDRY = "azure_foundry"
    AZURE_PRIVATE = "azure_private"  # Azure OpenAI Service


class LLMStatus(str, Enum):
    """LLM provider status."""
    READY = "ready"
    INITIALIZING = "initializing"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    provider_type: LLMProviderType
    endpoint: str
    model: str
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 0.9
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0

    # Security settings
    validate_endpoint: bool = True
    allowed_endpoints: list[str] = field(default_factory=lambda: ["127.0.0.1", "localhost"])


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    model: str
    provider: LLMProviderType

    # Timing
    latency_ms: float

    # Token usage (if available)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # For audit logging
    request_id: Optional[str] = None

    # Raw response for debugging (never includes actual data)
    raw_response: Optional[dict] = None

    @property
    def success(self) -> bool:
        """Check if response is valid."""
        return bool(self.content and len(self.content.strip()) > 0)


@dataclass
class LLMRequest:
    """Request to LLM provider."""
    # System prompt (instructions for DAX generation)
    system_prompt: str

    # User prompt (schema + intent, NEVER actual data)
    user_prompt: str

    # Request ID for tracking
    request_id: str

    # Override config for this request
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    def __post_init__(self):
        """Validate request doesn't contain data patterns."""
        # Basic safety check - production would have more sophisticated checks
        dangerous_patterns = [
            "INSERT INTO", "UPDATE ", "DELETE FROM",
            "SELECT *", "TRUNCATE", "DROP TABLE"
        ]
        combined = f"{self.system_prompt} {self.user_prompt}".upper()
        for pattern in dangerous_patterns:
            if pattern in combined:
                raise ValueError(f"Request contains potentially dangerous pattern: {pattern}")


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement this interface to ensure:
    1. Consistent behavior across providers
    2. Security guarantees (schema-only)
    3. Proper error handling
    4. Audit logging support
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._status = LLMStatus.INITIALIZING
        self._last_health_check: Optional[float] = None
        self._error_message: Optional[str] = None

    @property
    def status(self) -> LLMStatus:
        """Get provider status."""
        return self._status

    @property
    def provider_type(self) -> LLMProviderType:
        """Get provider type."""
        return self.config.provider_type

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider.

        Returns:
            True if initialization successful, False otherwise.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and reachable.

        Returns:
            True if healthy, False otherwise.
        """
        pass

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            request: The LLM request (schema + intent only)

        Returns:
            LLM response containing generated content

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up resources."""
        pass

    async def generate_dax(
        self,
        schema_info: str,
        user_intent: str,
        request_id: str,
    ) -> LLMResponse:
        """
        Generate a DAX query from schema and user intent.

        This is the primary method for DAX generation.
        It ensures the system prompt is properly configured.

        Args:
            schema_info: Schema information (tables, columns, relationships)
            user_intent: What the user wants to achieve
            request_id: Unique request ID for tracking

        Returns:
            LLM response with generated DAX
        """
        system_prompt = self._build_dax_system_prompt()
        user_prompt = self._build_dax_user_prompt(schema_info, user_intent)

        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            request_id=request_id,
        )

        return await self.generate(request)

    def _build_dax_system_prompt(self) -> str:
        """Build the system prompt for DAX generation."""
        return """You are an expert DAX (Data Analysis Expressions) query generator for Power BI.

Your task is to generate valid DAX queries based on the provided schema and user requirements.

RULES:
1. Generate ONLY valid DAX syntax
2. Use only the tables and columns provided in the schema
3. Follow DAX best practices
4. Use appropriate functions (CALCULATE, SUMX, FILTER, etc.)
5. Quote table names with spaces using single quotes: 'Table Name'[Column]
6. Return ONLY the DAX query, no explanations

OUTPUT FORMAT:
Return the DAX query wrapped in ```dax and ``` markers.
"""

    def _build_dax_user_prompt(self, schema_info: str, user_intent: str) -> str:
        """Build the user prompt for DAX generation."""
        return f"""SCHEMA:
{schema_info}

USER REQUEST:
{user_intent}

Generate the DAX query to fulfill this request."""

    def _validate_endpoint(self, endpoint: str) -> bool:
        """
        Validate that the endpoint is allowed.

        This is a critical security check for air-gapped deployments.
        """
        if not self.config.validate_endpoint:
            return True

        # Parse the endpoint to get the host
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        host = parsed.hostname or ""

        # Check against allowed endpoints
        for allowed in self.config.allowed_endpoints:
            if host == allowed or host.endswith(f".{allowed}"):
                return True

        return False


class LLMProviderError(Exception):
    """Exception raised by LLM providers."""

    def __init__(
        self,
        message: str,
        provider: LLMProviderType,
        request_id: Optional[str] = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.provider = provider
        self.request_id = request_id
        self.recoverable = recoverable


class LLMConnectionError(LLMProviderError):
    """Connection error to LLM provider."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Timeout waiting for LLM response."""
    pass


class LLMValidationError(LLMProviderError):
    """Validation error in request or response."""
    pass
