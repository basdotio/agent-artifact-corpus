import os
from datetime import datetime
from Modules.Config import DOCUMENT_DIR

def citationProvider(results: dict, answer: str) -> dict:
    """
    Provides citations for the generated answer based on retrieved documents.

    Args:
        results (dict): Dictionary with "results" key containing retrieved documents.
        answer (str): The LLM-generated answer to annotate with citations.

    Returns:
        dict: {
            "answer_with_citations": str,
            "citations": List[dict]  # each with "id", "source", "snippet", "score"
        }
    """
    try:
        if "results" not in results or not results["results"]:
            return {
                "status": "neutral",
                "answer_with_citations": answer,
                "citations": []
            }

        citations = []
        for idx, doc in enumerate(results["results"], 1):
            citations.append({
                "id": idx,
                "source": doc.get("metadata", {}).get("source", f"Document {idx}"),
                "snippet": doc["content"][:200],
                "score": doc.get("score", None)
            })
            
        cited_answer = answer.strip() + "\n\nCitations:\n"
        for c in citations:
            cited_answer += f"[{c['id']}] {c['source']}\n"

        return {
            "status": "success",
            "answer_with_citations": cited_answer,
            "citations": citations
        }

    except Exception as err:
        return {
            "status": "error",
            "message": f"Error generating citations: {str(err)}"
        }
    
def listDocuments() -> dict:
    """
    Lists all documents stored in the DOCUMENT_DIR.

    Args:
        None

    Returns:
        dict: A dictionary containing:
            - status (str): "success" or "error"
            - documents (List[str]): List of document filenames
    """
    try:
        documents = os.listdir(DOCUMENT_DIR)
        return {
            "status": "success",
            "documents": documents
        }
    except Exception as err:
        return {
            "status": "error",
            "message": f"Error listing documents: {str(err)}"
        }
    
def getDocumentMetadata(filename: str) -> dict:
    """
    Retrieves metadata for a specific document stored in DOCUMENT_DIR.

    Args:
        filename (str): Name of the document file.
    
    Returns:
        dict: A dictionary containing:
            - status (str): "success" or "error"
            - filename (str): Name of the document file
            - filepath (str): Full path to the document file
            - size_bytes (int): Size of the file in bytes
            - created (str): Creation timestamp
            - modified (str): Last modified timestamp
    """
    try:
        filepath = os.path.join(DOCUMENT_DIR, filename)
        if not os.path.exists(filepath):
            return {"status": "error", "message": f"{filename} not found."}

        size = os.path.getsize(filepath)
        created = datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
        modified = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()

        return {
            "status": "success",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "created": created,
            "modified": modified,
        }

    except Exception as err:
        return {"status": "error", "message": str(err)}
    

def updateDocument(filename: str, new_filename: str) -> dict:
    """
    Updates the filename of a document stored in DOCUMENT_DIR.

    Args:
        filename (str): Current name of the document file.
        new_filename (str): New name to assign to the document file.

    Returns:
        dict: A dictionary containing:
            - status (str): "success" or "error"
            - message (str): Summary of the operation
            - filepath (str): New file path after renaming
    """
    try:
        old_path = os.path.join(DOCUMENT_DIR, filename)
        if not os.path.exists(old_path):
            return {"status": "error", "message": f"{filename} not found."}

        new_path = os.path.join(DOCUMENT_DIR, new_filename)
        os.rename(old_path, new_path)

        return {"status": "success", "message": f"{filename} renamed to {new_filename}", "filepath": new_path}

    except Exception as err:
        return {"status": "error", "message": str(err)}
