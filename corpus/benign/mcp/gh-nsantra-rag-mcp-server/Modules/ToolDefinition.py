from typing import List
from pydantic import BaseModel

class ToolArg(BaseModel):
    name: str
    description: str
    type: str = "string"
    required: bool = True

class ToolReturn(BaseModel):
    description: str
    type: str = "dict"

class ToolInfo(BaseModel):
    name: str
    description: str
    args: List[ToolArg]
    returns: List[ToolReturn]

class ToolManifest(BaseModel):
    server_name: str
    tool_count: int
    tools: List[ToolInfo]

def describeTools() -> dict:
    tools = [
        ToolInfo(
            name = "describeTools",
            description = "Lists and describes all tools available on the MCP server.",
            args = [],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns a dictionary of all available MCP tools and their metadata."
                )
            ]
        ),

        ToolInfo(
            name = "embedPDF",
            description = "Embeds the given PDF and stores it in Chroma vectorstore.",
            args = [
                ToolArg(name = "filepath", description = "Local path to the PDF file.", type = "string", required = False),
                ToolArg(name = "file_url", description = "URL to the PDF file.", type = "string", required = False),
                ToolArg(name = "filename", description = "Custom filename for saving and embedding.", type = "string", required = False),
                ToolArg(name = "collection", description = "Collection name in ChromaDB.", type = "string", required = True),
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns a dictionary with embedding details (status, filename, collection, etc.)."
                )
            ]
        ),

        ToolInfo(
            name = "retrieveDocs",
            description = "Retrieves relevant documents from ChromaDB based on a query.",
            args = [
                ToolArg(name = "query", description = "User query for retrieval.", type = "string", required = True),
                ToolArg(name = "collection", description = "Target ChromaDB collection.", type = "string", required = True),
                ToolArg(name = "top_k", description = "Number of top documents to retrieve.", type = "int", required = False),
                ToolArg(name = "use_reranker", description = "Whether to rerank documents using a cross-encoder.", type = "bool", required = False)
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Dictionary containing query results, count, and metadata."
                )
            ]
        ),

        ToolInfo(
            name = "listDBs",
            description = "Lists all the collections in the ChromaDB vectorstore.",
            args = [],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns list of all ChromaDB collections and their count."
                )
            ]
        ),

        ToolInfo(
            name = "deleteCollection",
            description = "Deletes the specified ChromaDB collection if it exists.",
            args = [
                ToolArg(name = "collection", description = "Name of the collection to delete.", type = "string", required = True)
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns status and message after deletion."
                )
            ]
        ),

        ToolInfo(
            name = "listDocuments",
            description = "Lists all locally stored documents in the DOCUMENT_DIR.",
            args = [],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns a list of locally available documents."
                )
            ]
        ),

        ToolInfo(
            name = "citationProvider",
            description = "Adds citation references to a given LLM-generated answer based on retrieved documents.",
            args = [
                ToolArg(name = "results", description = "Results dictionary from retrieveDocs.", type = "dict", required = True),
                ToolArg(name = "answer", description = "LLM-generated answer to be annotated.", type = "string", required = True),
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns the answer with citations and metadata for each source."
                )
            ]
        ),

        ToolInfo(
            name = "seacrhAcrossCollections",
            description = "Searches for relevant documents across multiple ChromaDB collections based on a query.",
            args = [
                ToolArg(name = "query", description = "The search query or prompt.", type = "string", required = True),
                ToolArg(name = "collections", description = "List of ChromaDB collection names to query.", type = "list", required = True),
                ToolArg(name = "top_k", description = "Number of top documents to retrieve from each collection.", type = "int", required = False),
                ToolArg(name = "use_reranker", description = "Whether to rerank retrieved documents.", type = "bool", required = False)
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns aggregated search results from all specified collections."
                )
            ]
        ),

        ToolInfo(
            name = "collectionStats",
            description = "Retrieves statistics about a specific ChromaDB collection.",
            args = [
                ToolArg(name = "collection", description = "Name of the ChromaDB collection.", type = "string", required = True)
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns statistics such as document count and embedding details."
                )
            ]
        ),

        ToolInfo(
            name = "getDocumentMetadata",
            description = "Retrieves metadata for a specified local document.",
            args = [
                ToolArg(name = "filename", description = "Name of the local document file.", type = "string", required = True)
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns metadata information for the specified document."
                )
            ]
        ),

        ToolInfo(
            name = "updateDocument",
            description = "Updates the filename of a local document in DOCUMENT_DIR.",
            args = [
                ToolArg(name = "filename", description = "Current name of the document file.", type = "string", required = True),
                ToolArg(name = "new_filename", description = "New name for the document file.", type = "string", required = True)
            ],
            returns = [
                ToolReturn(
                    type = "dict",
                    description = "Returns status and message after updating the document filename."
                )
            ]
        )
    ]

    return ToolManifest(
        server_name = "RAG",
        tools = tools,
        tool_count = len(tools)
    ).dict()
