import hashlib
import re
import uuid
from logging import getLogger
from typing import List, Tuple

import tiktoken
from bs4 import BeautifulSoup
from langchain_community.document_loaders import RecursiveUrlLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm

logger = getLogger(__name__)


def count_tokens(text, model="cl100k_base"):
    """
    Count the number of tokens in the text using tiktoken.

    Args:
        text (str): The text to count tokens for
        model (str): The tokenizer model to use (default: cl100k_base for GPT-4)

    Returns:
        int: Number of tokens in the text
    """
    encoder = tiktoken.get_encoding(model)
    return len(encoder.encode(text))


def bs4_extractor(html: str) -> str:
    """
    Extracts clean text from HTML or XML content, removing CSS, scripts, and unnecessary whitespace.
    Handles both HTML and XML documents robustly.
    """
    # Try to parse as XML first, fallback to HTML if it fails
    try:
        soup = BeautifulSoup(html, "lxml-xml")

        # If root is <html>, treat as HTML
        if soup.find("html"):
            logger.debug("Parsed as HTML")
            soup = BeautifulSoup(html, "html.parser")
        elif soup.find("xml"):
            logger.debug("Parsed as XML")
            soup = BeautifulSoup(html, "lxml-xml")
        else:
            logger.debug("Parsed as HTML - Fallback")
            soup = BeautifulSoup(html, "html.parser")
    except Exception:
        logger.debug("Parsed as HTML - Fallback")
        soup = BeautifulSoup(html, "html.parser")

    # Remove all <style>, <script>, <noscript>, and <template> elements
    for tag in soup(["style", "script", "noscript", "template"]):
        tag.decompose()
        logger.debug(f"Removed {tag.name} tag")

    # Remove comments
    for comment in soup.find_all(
        string=lambda text: isinstance(text, type(soup.Comment))
    ):
        comment.extract()
        logger.debug("Removed comment")

    # Try to target main content if possible
    main_content = soup.find("article", class_="status-publish")
    if not main_content:
        # Try common main content tags
        for tag in ["main", "article", "section", "body"]:
            main_content = soup.find(tag)
            if main_content:
                break

    # Extract text
    content = (
        main_content.get_text(separator="\n")
        if main_content
        else soup.get_text(separator="\n")
    )

    # Remove excessive whitespace and blank lines
    # Replace multiple spaces/tabs with a single space
    content = re.sub(r"[ \t]+", " ", content)
    # Replace multiple newlines (including those with spaces/tabs in between) with a single newline
    content = re.sub(r"(\n\s*){2,}", "\n", content)
    # Remove leading/trailing whitespace
    content = content.strip()

    logger.debug(f"Extracted content with length {len(content)}")

    return content


def load_site(urls: List[str]) -> Tuple[List[Document], List[int]]:
    """
    Load information from the official website.

    This function:
    1. Uses RecursiveUrlLoader to fetch pages from the website
    2. Counts the total documents and tokens loaded

    Returns:
        list: A list of Document objects containing the loaded content
        list: A list of tokens per document
    """
    if len(urls) == 0:
        logger.warning("No URLs provided")
        return [], []

    logger.info("Loading website...")

    docs = []
    # Show the progress
    for url in tqdm(
        urls,
        desc="Processing URLs and loading page content",
        total=len(urls),
        unit="URLs",
    ):
        loader = RecursiveUrlLoader(
            url,
            max_depth=3,
            extractor=bs4_extractor,
        )

        # Load documents using lazy loading (memory efficient)
        docs_lazy = loader.lazy_load()

        # Load documents and track URLs
        for d in docs_lazy:
            # Add document source as metadata
            d.metadata["source"] = url

            # Add the document to the list
            docs.append(d)

    logger.info(f"Loaded {len(docs)} documents from website.")

    # Count total tokens in documents
    total_tokens = 0
    tokens_per_doc = []
    for doc in tqdm(
        docs, desc="Counting tokens in documents", total=len(docs), unit="documents"
    ):
        document_tokens = count_tokens(doc.page_content)
        total_tokens += document_tokens
        tokens_per_doc.append(document_tokens)
        # Add tokens per document to metadata
        doc.metadata["tokens"] = document_tokens

    logger.info(f"Total tokens in loaded documents: {total_tokens}")

    if len(docs) == 0:
        logger.warning("No documents were loaded")
        return []
    else:
        logger.info(
            f"Loaded {len(docs)} documents with an average of {total_tokens / len(docs)} tokens per document"
        )
    return docs, total_tokens


def save_full_txt(documents: List[Document], save_file_path: str):
    """Save the documents to a file"""

    # Open the output file
    with open(save_file_path, "w") as f:
        # Write each document
        for i, doc in enumerate(documents):
            # Get the source (URL) from metadata
            source = doc.metadata.get("source", "Unknown URL")

            # Write the document with proper formatting
            f.write(f"\nDOCUMENT {i + 1}\n")
            f.write(f"SOURCE: {source}\n")
            f.write(f"ID: {doc.metadata.get('id', 'Unknown ID')}\n")
            f.write(f"TYPE: {doc.metadata.get('type', 'Unknown Type')}\n")
            f.write("CONTENT:\n")
            f.write(doc.page_content)
            f.write("\n\n" + "=" * 80 + "\n\n")

    logger.info(f"Documents concatenated and saved into {save_file_path}")


def update_metadata(documents: List[Document], metadata: dict) -> List[Document]:
    """
    Update metadata for each document in the list.

    Args:
        documents (list): List of Document objects to update
        metadata (dict): Metadata to add to each document

    Returns:
        list: Updated list of Document objects with new metadata
    """
    if len(metadata.items()) > 0 and len(documents) > 0:
        # Add metadata to documents
        for document in documents:
            # Add metadata to documents
            for key, value in metadata.items():
                document.metadata[key] = value

            for key, value in document.metadata.items():
                if not isinstance(value, bool) and not isinstance(
                    value, (str, int, float)
                ):
                    document.metadata[str(key)] = str(value)

    return documents


def split_documents(documents: List[Document]):
    """
    Split documents into smaller chunks for improved retrieval.

    This function:
    1. Uses RecursiveCharacterTextSplitter with tiktoken to create semantically meaningful chunks
    2. Ensures chunks are appropriately sized for embedding and retrieval
    3. Counts the resulting chunks and their total tokens

    Args:
        documents (list): List of Document objects to split

    Returns:
        list: A list of split Document objects
    """
    logger.info("Splitting documents...")

    # Initialize text splitter using tiktoken for accurate token counting
    # chunk_size=8,000 creates relatively large chunks for comprehensive context
    # chunk_overlap=500 ensures continuity between chunks
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=8000, chunk_overlap=500
    )

    # Split documents into chunks
    split_docs = text_splitter.split_documents(documents)

    logger.info(f"Created {len(split_docs)} chunks from documents.")

    # remove documents without content
    split_docs = [
        doc
        for doc in split_docs
        if doc.page_content and len(doc.page_content.strip()) > 0
    ]

    # Generate a deterministic ID based on the URL
    for doc in split_docs:
        source = doc.metadata.get("source", uuid.uuid4())
        type = doc.metadata.get("type", "Unknown_Type")
        content = doc.page_content.strip()
        # Create a unique hash string using the source and content
        # This ensures that the same content always generates the same ID
        # This is important for reproducibility and consistency
        # and to avoid collisions in the database
        hash_string = f"{type}-{source}-{content}"

        # Generate a deterministic ID based on the URL and content
        url_hash = hashlib.md5(hash_string.encode()).hexdigest()
        doc.metadata["id"] = f"doc_{url_hash}"

    # Count total tokens in split documents
    total_tokens = 0
    for doc in split_docs:
        total_tokens += count_tokens(doc.page_content)

    logger.info(f"Total tokens in split documents: {total_tokens}")

    return split_docs
