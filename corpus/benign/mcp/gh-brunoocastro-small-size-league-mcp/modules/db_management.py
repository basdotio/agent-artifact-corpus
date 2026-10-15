import logging
from functools import lru_cache
from typing import List

from langchain_chroma.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document

from config import DATA_PATH, VECTOR_STORE_COLLECTION_NAME
from providers import embedding_provider

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
class VectorStoreManager:
    def __init__(
        self,
        persist_path: str = DATA_PATH,
        collection_name: str = VECTOR_STORE_COLLECTION_NAME,
        max_tokens_per_request: int = 300000,
    ):
        self.max_tokens_per_request = max_tokens_per_request
        self.vector_store_instance = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_provider,
            persist_directory=persist_path,
        )

    def add_or_update_documents(self, documents: List[Document]):
        """Add or update documents in the vector store."""
        if not documents or len(documents) == 0:
            logger.error("No documents provided for database update")
            return

        valid_documents = self.remove_invalid_documents(documents)

        valid_documents = self.deduplicate_documents(valid_documents)

        ids = self.get_ids(valid_documents)

        logger.info(f"Updating database with {len(valid_documents)} documents")

        # Split documents to avoid exceeding the max_tokens limit
        added_ids = []
        total_tokens = 0
        limit_index = 0
        last_added_index = 0
        for idx, doc in enumerate(valid_documents):
            if total_tokens + doc.metadata["tokens"] > self.max_tokens_per_request:
                limit_index = idx
            elif idx == len(valid_documents) - 1:
                limit_index = idx

            if limit_index > 0:
                new_ids = self.vector_store_instance.add_documents(
                    documents=valid_documents[last_added_index:idx],
                    ids=ids[last_added_index:idx],
                )
                added_ids.extend(new_ids)

                total_tokens = 0
                last_added_index = idx
            else:
                total_tokens += doc.metadata["tokens"]

        logger.info(
            f"Added {len(added_ids)} new documents. {len(added_ids) / len(valid_documents) * 100}% of total valid documents"
        )

        return added_ids

    @staticmethod
    def remove_invalid_documents(documents: List[Document]) -> List[Document]:
        """Remove invalid documents from the list."""
        if len(documents) == 0:
            logger.error("No valid documents provided for database update")
            return []

        valid_documents: List[Document] = []

        for doc in documents:
            if doc.metadata is None or "id" not in doc.metadata:
                logger.debug(f"Document {doc} has no id or metadata")
                continue
            if not doc.page_content or len(doc.page_content) == 0:
                logger.debug(f"Document {doc.id} has no content")
                continue

            valid_documents.append(doc)

        if len(valid_documents) != len(documents):
            logger.warning(
                f"Some documents were not added to the database because they were invalid. "
                f"Total documents: {len(documents)}, Valid documents: {len(valid_documents)}"
            )
        logger.info(
            f"Valid documents: {len(valid_documents)} ({len(documents) - len(valid_documents)} invalid)"
        )

        filter_complex_metadata(valid_documents)

        return valid_documents

    @staticmethod
    def deduplicate_documents(documents: List[Document]) -> List[Document]:
        """Deduplicate documents by id."""
        logger.info(f"Searching for duplicates in {len(documents)} documents")
        seen = set()
        unique_docs = []
        for doc in documents:
            if doc.metadata["id"] not in seen:
                unique_docs.append(doc)
                seen.add(doc.metadata["id"])

        duplicates_count = len(documents) - len(unique_docs)

        if duplicates_count > 0:
            logger.info(f"Found {duplicates_count} duplicates")
        else:
            logger.info("No duplicates found")

        return unique_docs

    @staticmethod
    def get_ids(documents: List[Document]) -> List[str]:
        """Get ids from documents."""
        return [doc.metadata["id"] for doc in documents]

    def get(self) -> Chroma:
        return self.vector_store_instance
