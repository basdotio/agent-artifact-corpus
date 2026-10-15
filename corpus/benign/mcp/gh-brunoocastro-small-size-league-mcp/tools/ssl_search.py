# ENUM for filters
from enum import Enum
from logging import getLogger
from typing import List, Optional

from langchain_core.documents import Document
from pydantic import BaseModel, Field

from modules.db_management import VectorStoreManager

logger = getLogger(__name__)


class SSLDocumentSource(Enum):
    WEBSITE = "website_pages"
    RULES = "rules"


vector_store_manager = VectorStoreManager()


class SSLSearchInput(BaseModel):
    query: str = Field(description="The search query for RoboCUP SSL documents")
    k: int = Field(
        default=2,
        description="Number of most relevant documents to retrieve",
        ge=1,
        le=10,
    )
    # Filter to retrieve documents from a specific source - literal from SSLDocumentSource
    document_source_filter: Optional[SSLDocumentSource] = Field(
        default=None, description="Filter to retrieve documents from a specific source"
    )
    threshold: float = Field(
        default=0,
        description="Minimum relevance score threshold for returned documents",
        ge=0,
        le=1,
    )


def ssl_search_tool(input_data: SSLSearchInput) -> List[Document]:
    """
    Retrieve the RoboCUP Small Size League (SSL) K most relevant documents based on a input query.
    These documents are relative from RoboCUP SSL website and rules.

    TIPS:
    - Provide the filter to retrieve documents from a specific source, if not provided, the tool will retrieve documents from all sources.
    - To get relevant documents, provide a query related to the RoboCUP SSL information.
    - If the threshold is set to 0, all documents will be returned.
    - If the threshold is set to a value greater than 0, only documents with a relevance score greater than or equal to the threshold will be returned.
    - If the results are too random, try to increase the threshold value.

    """
    vector_store = vector_store_manager.get()

    logger.info(
        f"Starting SSL search tool. Kwargs:\nQuery: {input_data.query}, k: {input_data.k}, document_source_filter: {input_data.document_source_filter}, threshold: {input_data.threshold}"
    )

    result = vector_store.similarity_search_with_relevance_scores(
        input_data.query,
        k=input_data.k,
        filter=(
            {"type": input_data.document_source_filter.value}
            if input_data.document_source_filter
            else None
        ),
        score_threshold=input_data.threshold,
    )

    # Filter documents based on the threshold
    filtered_documents = [doc for doc, score in result if score >= input_data.threshold]

    if len(filtered_documents) == 0:
        logger.warning(
            "No documents found.Filters:\n type=%s, k=%s and threshold=%s. "
            "Original query: '%s'",
            input_data.document_source_filter.value
            if input_data.document_source_filter
            else None,
            input_data.k,
            input_data.threshold,
            input_data.query,
        )
    else:
        logger.info(
            f"Retrieved {len(filtered_documents)} documents for query: "
            f"'{input_data.query}'"
        )

    return filtered_documents
