[![MCP SERVER TOOLS](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=MCP+SERVER+TOOLS)]()

## 1. describeTools
**Description:** Lists and describes all tools available on the MCP server.

**Arguments:**  
_None_

**Returns:**  
- Dictionary containing all available MCP tools and their metadata.

## 2. embedPDF
**Description:** Embeds the given PDF and stores it in the Chroma vectorstore.

**Arguments:**
- `filepath` (string, optional): Local path to the PDF file.  
- `file_url` (string, optional): URL to the PDF file.  
- `filename` (string, optional): Custom filename for saving and embedding.  
- `collection` (string, required): Collection name in ChromaDB.

**Returns:**  
- Dictionary with embedding details such as `status`, `filename`, `collection`, and `message`.

## 3. retrieveDocs
**Description:** Retrieves relevant documents from ChromaDB based on a query.

**Arguments:**
- `query` (string, required): User query for retrieval.  
- `collection` (string, required): Target ChromaDB collection.  
- `top_k` (int, optional): Number of top documents to retrieve.  
- `use_reranker` (bool, optional): Whether to rerank documents using a cross-encoder.

**Returns:**  
- Dictionary containing query results, count, and metadata.

## 4. listDBs
**Description:** Lists all the collections in the ChromaDB vectorstore.

**Arguments:**  
_None_

**Returns:**  
- Dictionary containing a list of all ChromaDB collections and their count.

## 5. deleteCollection
**Description:** Deletes the specified ChromaDB collection if it exists.

**Arguments:**
- `collection` (string, required): Name of the collection to delete.

**Returns:**  
- Dictionary containing deletion `status` and `message`.

## 6. listDocuments
**Description:** Lists all locally stored documents in the `DOCUMENT_DIR`.

**Arguments:**  
_None_

**Returns:**  
- Dictionary containing a list of locally available documents.

## 7. citationProvider
**Description:** Adds citation references to a given LLM-generated answer based on retrieved documents.

**Arguments:**
- `results` (dict, required): Results dictionary from `retrieveDocs`.  
- `answer` (string, required): LLM-generated answer to be annotated.

**Returns:**  
- Dictionary containing the annotated answer with citations and metadata for each source.

## 8. searchAcrossCollections
**Description:** Searches for relevant documents across multiple ChromaDB collections based on a query.

**Arguments:**
- `query` (string, required): The search query or prompt.  
- `collections` (list, required): List of ChromaDB collection names to query.  
- `top_k` (int, optional): Number of top documents to retrieve from each collection.  
- `use_reranker` (bool, optional): Whether to rerank retrieved documents.

**Returns:**  
- Dictionary containing aggregated search results from all specified collections.

## 9. collectionStats
**Description:** Retrieves statistics about a specific ChromaDB collection.

**Arguments:**
- `collection` (string, required): Name of the ChromaDB collection.

**Returns:**  
- Dictionary containing collection statistics such as document count and embedding details.

## 10. getDocumentMetadata
**Description:** Retrieves metadata for a specified local document.

**Arguments:**
- `filename` (string, required): Name of the local document file.

**Returns:**  
- Dictionary containing metadata information for the specified document.

## 11. updateDocument
**Description:** Updates the filename of a local document in the `DOCUMENT_DIR`.

**Arguments:**
- `filename` (string, required): Current name of the document file.  
- `new_filename` (string, required): New name for the document file.

**Returns:**  
- Dictionary containing `status` and `message` after updating the document filename.
