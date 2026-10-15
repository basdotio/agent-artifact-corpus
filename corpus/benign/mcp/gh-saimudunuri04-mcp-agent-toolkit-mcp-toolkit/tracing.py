"""LangSmith tracing setup. Degrades gracefully when no API key is configured."""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def init_tracing(settings) -> bool:
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        log.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)
        return True
    log.info("No LANGSMITH_API_KEY configured; running without tracing")
    return False
