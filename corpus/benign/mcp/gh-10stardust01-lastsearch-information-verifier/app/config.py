from functools import lru_cache
from os import getenv
from pathlib import Path

from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


@dataclass(frozen=True)
class Settings:
    elasticsearch_url: str = "https://localhost:9200"
    elasticsearch_api_key: str | None = None
    elasticsearch_index: str = "bengaluru-sources"
    aws_region: str = "ap-south-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    jina_reranker_inference_id: str = "jina-reranker-v2"
    elser_inference_id: str = ".elser-2-elasticsearch"


@lru_cache
def get_settings() -> Settings:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)

    return Settings(
        elasticsearch_url=getenv("ELASTICSEARCH_URL", "https://localhost:9200"),
        elasticsearch_api_key=getenv("ELASTICSEARCH_API_KEY"),
        elasticsearch_index=getenv("ELASTICSEARCH_INDEX", "bengaluru-sources"),
        aws_region=getenv("AWS_REGION", "ap-south-1"),
        bedrock_model_id=getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        ),
        jina_reranker_inference_id=getenv("JINA_RERANKER_INFERENCE_ID", "jina-reranker-v2"),
        elser_inference_id=getenv("ELSER_INFERENCE_ID", ".elser-2-elasticsearch"),
    )
