from dotenv import load_dotenv
load_dotenv()

import os
from pydantic import BaseModel, Field, HttpUrl, ValidationError


class Settings(BaseModel):
    # MLIT GraphQL endpoint & API key (REQUIRED)
    base_url: HttpUrl = Field(
        default=os.getenv("MLIT_BASE_URL") or "https://data-platform.mlit.go.jp/api/v1/"
    )
    api_key: str = Field(..., alias="MLIT_API_KEY")

    # HTTP & reliability
    timeout_s: float = 30.0
    max_retries: int = 3
    backoff_base_s: float = 0.5
    rps: float = 4.0  # light rate limit

    # simple input limits
    max_size: int = 500  # MLIT recommended upper bound per query sample
    max_distance_m: int = 50000  # precaution for geoDistance


def load_settings() -> Settings:
    env = {
        "MLIT_API_KEY": os.getenv("MLIT_API_KEY"),
        # base_url is automatically set by default
    }
    try:
        return Settings.model_validate(env)
    except ValidationError as e:
        raise RuntimeError(
            "Config error: set ENV MLIT_API_KEY (and optionally MLIT_BASE_URL)."
        ) from e
