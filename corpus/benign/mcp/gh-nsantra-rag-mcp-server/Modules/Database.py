import os
import requests
from langchain_chroma import Chroma
from Modules.Utils import saveFiles, rerankDocs
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from Modules.Config import CHROMA_DB_PERSIST_DIR, EMBEDDING_FUNCTION, DOCUMENT_DIR

def listDBs() -> dict:
    """
    Lists all existing collections in the Chroma vectorstore.

    Args:
        None

    Returns:
        dict: A dictionary containing:
            - status (str): "success"
            - collections (List[str]): Names of all available vectorstore collections.
            - count (int): Total number of collections.
            - persist_directory (str): Directory path where ChromaDB collections are stored.

    On Error:
        Returns a dictionary with:
            - status (str): "error"
            - message (str): Error details.
    """
    try:
        db_collections = Chroma(persist_directory = CHROMA_DB_PERSIST_DIR)._client.list_collections()
        db_list = [i.name for i in db_collections]
        
        return {
            "status": "success",
            "collections": db_list,
            "count": len(db_list),
            "persist_directory": CHROMA_DB_PERSIST_DIR
        }

    except Exception as err:
        return {
            "status": "error",
            "message": f"Error listing DBs: {str(err)}"
        }
    
def deleteCollection(collection: str) -> dict:
    try:
        _ = Chroma(
            persist_directory = CHROMA_DB_PERSIST_DIR,
            collection_name = collection
        ).delete_collection()

        return {
            "status": "success",
            "message": f"Collection {collection} has been successfully deleted.",
        }
    
    except Exception as err:
        return {
            "status": "error",
            "message": f"Error deleting collection: {str(err)}"
        }
    
def embedPDF(filepath: str = None, file_url: str = None, filename: str = None, collection: str = None) -> dict:
    """
    Embeds the content of a PDF file (from local path or URL) into a Chroma vectorstore.
    Claude Desktop decides whether to pass filepath (local) or file_url (HTTPS url) based on the prompt.
    
    Args:
        filepath (str, optional): Local path to the PDF file.
        file_url (str, optional): HTTPS URL to the PDF file.
        filename (str, optional): Name to assign to the saved file (used for MCP client).
        collection (str, optional): Target ChromaDB collection name.
    
    Returns:
        dict: A dictionary containing:
            - status (str): "success" or "error"
            - source (str): Original source (URL or local path)
            - destination_filepath (str): Final saved file path used for embedding
            - filename (str): File name used
            - collection (str): Target ChromaDB collection name
            - message (str): Summary of the operation
    """
    try:
        destination = os.path.normpath(os.path.join(DOCUMENT_DIR, filename))
        source = None
        
        if file_url and file_url.startswith(("http://", "https://")):
            response = requests.get(file_url, stream = True)
            if response.status_code != 200:
                raise ValueError(f"Failed to download file from URL: {file_url}")

            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size = 8192):
                    f.write(chunk)
            source = file_url
            
        elif filepath:
            destination = saveFiles(filepath, target_filename=filename)
            source = filepath
            
        else:
            raise ValueError("Either 'filepath' or 'file_url' must be provided.")

        if not os.path.exists(destination):
            raise FileNotFoundError(f"File not found at: {destination}")

        loader = PyPDFLoader(destination)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 1000,
            chunk_overlap = 200 
        )
        texts = text_splitter.split_documents(documents)

        _ = Chroma.from_documents(
            documents = texts,
            embedding = EMBEDDING_FUNCTION,
            collection_name = collection,
            persist_directory = CHROMA_DB_PERSIST_DIR
        )

        return {
            "status": "success",
            "source": source,
            "destination_filepath": destination,
            "filename": filename,
            "collection": collection,
            "message": f"PDF '{filename}' has been successfully embedded into collection '{collection}'."
        }

    except Exception as err:
        return {
            "status": "error",
            "message": f"Error embedding PDF: {err}"
        }
    
def retrieveDocs(query: str, collection: str, top_k: int = 20, use_reranker: bool = True) -> dict:
    """
    Retrieves relevant documents from a ChromaDB collection based on a user query.

    Args:
        query (str): The search query or prompt used to find relevant documents.
        collection (str): Name of the ChromaDB collection to query.
        top_k (int, optional): Number of top documents to retrieve. Defaults to 20.
        use_reranker (bool, optional): Whether to rerank retrieved documents. Defaults to True.

    Returns:
        dict: A dictionary containing:
            - status (str): "success" if documents are retrieved, otherwise "error".
            - collection (str): Name of the queried collection.
            - query (str): The input query used for retrieval.
            - results (List[dict]): List of retrieved documents with:
                - content (str): Text content of the document.
                - metadata (dict): Metadata associated with the document.
            - count (int): Number of documents returned.

    On Error:
        Returns a dictionary with:
            - status (str): "error"
            - message (str): Error details.
    """
    try:
        db = Chroma(
            embedding_function = EMBEDDING_FUNCTION,
            collection_name = collection,
            persist_directory = CHROMA_DB_PERSIST_DIR
        ).as_retriever(kwargs = {"k": top_k})

        results = db.invoke(query)

        docs = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in results
        ]

        if use_reranker:
            docs = rerankDocs(query, docs, top_k)

        return {
            "status": "success",
            "collection": collection,
            "query": query,
            "results": docs,
            "count": len(docs),
        }

    except Exception as err:
        return {
            "status": "error",
            "message": f"Error retrieving documents: {str(err)}"
        }
    
def searchAcrossCollections(query: str, collections: list, top_k: int = 10, use_reranker: bool = True) -> dict:
    """
    Searches for relevant documents across multiple ChromaDB collections based on a user query.

    Args:
        query (str): The search query or prompt used to find relevant documents.
        collections (list): List of ChromaDB collection names to query.
        top_k (int, optional): Number of top documents to retrieve from each collection. Defaults to 10.
        use_reranker (bool, optional): Whether to rerank retrieved documents. Defaults to True.
    
    Returns:
        dict: A dictionary containing:
    """
    try:
        all_docs = []

        for col in collections:
            retriever = Chroma(
                collection_name = col,
                embedding_function = EMBEDDING_FUNCTION,
                persist_directory = CHROMA_DB_PERSIST_DIR
            ).as_retriever(kwargs = {"k": top_k})

            results = retriever.invoke(query)
            docs = [{"content": d.page_content, "metadata": d.metadata} for d in results]
            all_docs.extend(docs)

        if use_reranker:
            all_docs = rerankDocs(query, all_docs, top_k)

        return {
            "status": "success",
            "query": query,
            "collections_searched": collections,
            "results": all_docs,
            "count": len(all_docs)
        }

    except Exception as err:
        return {"status": "error", "message": str(err)}
    
def collectionStats(collection: str) -> dict:
    """
    Retrieves statistics about a specific ChromaDB collection.

    Args:
        collection (str): Name of the ChromaDB collection.

    Returns:
        dict: A dictionary containing:
            - status (str): "success" or "error"
            - collection (str): Name of the collection
            - num_documents (int): Number of documents in the collection
    """
    try:
        db = Chroma(collection_name = collection, persist_directory = CHROMA_DB_PERSIST_DIR)
        docs = db._client.get_collection(name = collection).peek(limit = 10000)

        return {
            "status": "success",
            "collection": collection,
            "num_documents": len(docs),
        }

    except Exception as err:
        return {"status": "error", "message": str(err)}