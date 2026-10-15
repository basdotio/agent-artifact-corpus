import os
import shutil
from typing import List
from Modules.Config import DOCUMENT_DIR, RERANKER

def saveFiles(filepath: str, target_filename: str) -> str:
    """
    Saves a file to the designated DOCUMENT_DIR.

    Args:
        filepath (str): Path to the source file to be saved.
    
    Returns:
        str: Destination path where the file is saved, or an error message.
    """
    try:
        filename = target_filename or os.path.basename(filepath)
        destination = os.path.normpath(os.path.join(DOCUMENT_DIR, filename))

        shutil.copy(filepath, destination)

        if not os.path.exists(destination):
            raise FileNotFoundError(f"File was not saved correctly: {destination}")

        return destination

    except Exception as err:
        raise RuntimeError(f"Error saving file: {err}")

def rerankDocs(query: str, results: list, top_k: int = 5) -> List:
    """
    Reranks retrieved documents based on their relevance to the query using a cross-encoder model.

    Args:
        query (str): The search query or prompt.
        results (list): List of retrieved documents, each as a dictionary with "content" key.
        top_k (int, optional): Number of top documents to return after reranking. Defaults to 5.
    
    Returns:
        List: Reranked list of top_k documents.
    """
    try:
        if not results:
            return []

        pairs = [(query, doc.get("content", "")) for doc in results]
        scores = RERANKER.predict(pairs, batch_size = 32)
        reranked = sorted(zip(results, scores), key = lambda x: x[1], reverse = True)[:top_k]
        return [r[0] for r in reranked]
    
    except Exception as err:
        print(f"[RAG RERANKER] Error: {err}")
        return results[:top_k]