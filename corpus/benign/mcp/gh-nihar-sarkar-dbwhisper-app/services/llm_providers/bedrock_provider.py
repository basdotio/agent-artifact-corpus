"""AWS Bedrock provider for SQL generation using the Converse API."""

import boto3
import json
from .base import BaseLLMClient, LLMResponse
from app.util.config import settings
import logging

logger = logging.getLogger(__name__)


class BedrockProvider(BaseLLMClient):
    """AWS Bedrock provider for SQL generation using the Converse API."""

    def __init__(self):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None
        )
        self.model_id = settings.BEDROCK_MODEL_ID

    async def generate_sql(self, schema: str, domain_context: str, user_query: str, dialect: str) -> LLMResponse:
        """Generate SQL using AWS Bedrock Converse API."""
        system_prompt = self._build_prompt(schema, domain_context, dialect)
        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[{"text": system_prompt}],
                messages=[{
                    "role": "user",
                    "content": [{"text": user_query}]
                }]
            )
            content = response["output"]["message"]["content"][0]["text"]
            usage = response.get("usage", {})
            return LLMResponse(
                content=content.strip(),
                model=self.model_id,
                usage=usage
            )
        except Exception as e:
            logger.error("Bedrock API error: %s", e)
            raise
