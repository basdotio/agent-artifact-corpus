import argparse
import logging
import os
from datetime import datetime
from typing import List

from langchain_core.documents import Document

from config import (
    DEFAULT_SITEMAP_URL,
    FULL_RULES_FILE_PATH,
    FULL_WEBSITE_FILE_PATH,
    INITIAL_RULES_URLS,
    URLS_FILE_PATH,
)
from modules.db_management import VectorStoreManager
from modules.text_handler import (
    load_site,
    save_full_txt,
    split_documents,
    update_metadata,
)
from modules.website_sources import extract_urls_from_sitemap, process_urls
from tools.ssl_search import SSLDocumentSource

logger = logging.getLogger(__name__)


def get_updated_website_sources(
    sitemap_url: str = DEFAULT_SITEMAP_URL, output_file: str = URLS_FILE_PATH
) -> list[str]:
    """Update the website sources by processing the sitemap and saving URLs."""
    logger.info(f"Processing sitemap from: {sitemap_url}")
    urls_info = extract_urls_from_sitemap(sitemap_url)

    if not urls_info:
        logger.error("No URLs were extracted from the sitemap.")
        return

    filtered_urls = process_urls(urls_info)

    # Check if file exists and read previous URLs if it does
    previous_urls = set()
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            previous_urls = set(line.strip() for line in f)

    # Calculate statistics
    new_urls = set(filtered_urls) - previous_urls
    removed_urls = previous_urls - set(filtered_urls)
    total_urls = len(filtered_urls)

    # Save new URLs to file
    with open(output_file, "w") as f:
        for url in filtered_urls:
            f.write(f"{url}\n")

    # Print statistics
    logger.info("\nURL Update Statistics:")
    logger.info(f"Total URLs processed: {total_urls}")
    logger.info(f"New URLs added: {len(new_urls)}")
    logger.info(f"URLs removed: {len(removed_urls)}")
    logger.info(f"Updated file: {output_file}")
    logger.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return filtered_urls


def generate_documents_from_sources(
    urls: List[str], metadata: dict = {}, save_file_path: str = None
) -> List[Document]:
    """Update full text and documents based on current sources."""
    urls = list(set(urls))

    logger.info(f"Loading content from {len(urls)} URL's into documents ")

    documents, total_tokens = load_site(urls)

    logger.info(
        f"Loaded {len(documents)} documents, resulting in {total_tokens} tokens"
    )

    documents_with_metadata = update_metadata(
        documents, metadata
    )  # Update metadata for each document

    if save_file_path:
        logger.info(f"Saving documents to file {save_file_path}")
        save_full_txt(documents=documents_with_metadata, save_file_path=save_file_path)

    # Split the documents into chunks
    splits = split_documents(documents_with_metadata)

    logger.info("Document update completed. Returning splits.")
    return splits


def update_database(documents_list: List[Document]):
    """Update the database based on a list of documents."""
    if not documents_list:
        logger.error("No documents provided for database update")
        return

    logger.info(f"Updating database with {len(documents_list)} documents")
    vector_store = VectorStoreManager()

    vector_store.add_or_update_documents(documents_list)

    logger.info("Database update completed")


def test_vector_store(query: str = "How to submit a paper?"):
    # Create retriever to get relevant documents (k=3 means return top 3 matches)
    vector_store = VectorStoreManager()
    retriever = vector_store.get().as_retriever(search_kwargs={"k": 5})

    # Get relevant documents for the query
    relevant_docs = retriever.invoke(query)
    logger.info(f"Query: {query}")
    logger.info(f"Retrieved {len(relevant_docs)} relevant documents:\n")

    for d in relevant_docs:
        logger.info(d.metadata["source"])
        logger.info(d.page_content)
        logger.info("\n--------------------------------\n")


def run_all_commands(query: str = "How to submit a paper?"):
    """Run all update commands sequentially."""
    logger.info("Starting full update process")

    # Step 1: Update website sources
    logger.info(f"{'-' * 8}\nStep 1: Fetching website sources")
    website_pages_urls = get_updated_website_sources()

    # Step 2: Update documents and save full text files
    logger.info(f"{'-' * 8}\nStep 2: Updating documents and saving full text files")

    logger.info("Step 2.1: Updating website documents")
    website_documents = generate_documents_from_sources(
        website_pages_urls,
        metadata={
            "type": SSLDocumentSource.WEBSITE.value,
            "reliability": 0.6,
        },
        save_file_path=FULL_WEBSITE_FILE_PATH,
    )

    logger.info("Step 2.2: Updating rules documents")
    rules_documents = generate_documents_from_sources(
        INITIAL_RULES_URLS,
        metadata={
            "type": SSLDocumentSource.RULES.value,
            "reliability": 1,
        },
        save_file_path=FULL_RULES_FILE_PATH,
    )

    all_documents = website_documents + rules_documents
    logger.info(f"Total documents generated: {len(all_documents)}")

    # Step 3: Update database
    logger.info(f"{'-' * 8}\nStep 3: Updating database")
    update_database(documents_list=all_documents)

    logger.info(f"{'-' * 8}\nFull update process completed. Lets test the vector store")
    test_vector_store(query)


def main():
    parser = argparse.ArgumentParser(
        description="RoboCup Small Size League MCP Update Tools"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Update website sources command
    sources_parser = subparsers.add_parser(
        "update-sources", help="Update website sources from sitemap"
    )
    sources_parser.add_argument(
        "--sitemap-url",
        type=str,
        default=DEFAULT_SITEMAP_URL,
        help="URL of the sitemap to process",
    )
    sources_parser.add_argument(
        "--output",
        type=str,
        default="processed_urls.txt",
        help="Output file for processed URLs",
    )

    # Update documents command
    docs_parser = subparsers.add_parser(
        "update-documents", help="Update full text and documents"
    )
    docs_parser.add_argument(
        "--sources",
        type=List[str],
        default=[],
        help="Array of strings representing source URLs",
    )
    docs_parser.add_argument(
        "--metadata",
        type=dict,
        default={},
        help="Metadata to add to the documents",
    )

    # Update database command
    db_parser = subparsers.add_parser(
        "update-database", help="Update database from documents"
    )
    db_parser.add_argument(
        "--documents",
        type=List[Document],
        nargs="+",
        required=True,
        help="Array of Document objects to process",
    )

    # Test vector store command
    test_parser = subparsers.add_parser(
        "test-vector-store", help="Test the vector store"
    )
    test_parser.add_argument(
        "--query",
        type=str,
        default="How to submit a paper?",
        help="Query to test the vector store",
    )

    # Run all command
    all_parser = subparsers.add_parser(
        "run-all", help="Run all update commands sequentially"
    )
    all_parser.add_argument(
        "--query",
        type=str,
        default="How to submit a paper?",
        help="Query to test the vector store",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.command == "update-sources":
        get_updated_website_sources(args.sitemap_url, args.output)
    elif args.command == "update-documents":
        generate_documents_from_sources(args.sources, args.metadata)
    elif args.command == "update-database":
        update_database(args.documents)
    elif args.command == "test-vector-store":
        test_vector_store(args.query)
    elif args.command == "run-all":
        run_all_commands(args.query)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
