from mcp.server.fastmcp import FastMCP
from Modules import Core, Database, ToolDefinition

mcp = FastMCP("RAG")

# Modules/ToolDefinitions
@mcp.tool()
def describeTools() -> dict:
    return ToolDefinition.describeTools()

# Modules/Core
@mcp.tool()
def listDocuments() -> dict:
    return Core.listDocuments()

# Modules/Core
# There may be some validation error
@mcp.tool()
def citationProvider(results: dict, answer: str) -> dict:
    return Core.citationProvider(results, answer)

# Modules/Core
@mcp.tool()
def getDocumentMetadata(filename: str) -> dict:
    return Core.getDocumentMetadata(filename)

# Modules/Core
@mcp.tool()
def updateDocument(filename: str, new_filename: str) -> dict:
    return Core.updateDocument(filename, new_filename)

# Modules/Database
@mcp.tool()
def searchAcrossCollections(query: str, collections: list, top_k: int = 10, use_reranker: bool = True) -> dict:
    return Database.searchAcrossCollections(query, collections, top_k, use_reranker)

# Modules/Database
@mcp.tool()
def collectionStats(collection: str) -> dict:
    return Database.collectionStats(collection)

# Modules/Database
@mcp.tool()
def listDBs() -> dict:
    return Database.listDBs()

# Modules/Database
@mcp.tool()
def deleteCollection(collection: str) -> dict:
    return Database.deleteCollection(collection)

# Modules/Database
@mcp.tool()
def embedPDF(filepath: str, file_url: str, filename: str, collection: str) -> dict:
    return Database.embedPDF(filepath, file_url, filename, collection)

# Modules/Database
@mcp.tool()
def retrieveDocs(query: str, collection: str, top_k: int = 20, use_reranker: bool = True) -> dict:
    return Database.retrieveDocs(query, collection, top_k, use_reranker)

if __name__ == "__main__":
    mcp.run()