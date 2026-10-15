import chromadb
from chromadb.utils import embedding_functions

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits text into overlapping chunks, attempting to break at newlines or spaces.
    """
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Try splitting at newline first
            boundary = text.rfind('\n', start, end)
            if boundary != -1 and boundary > start + chunk_size // 2:
                end = boundary + 1
            else:
                # Try splitting at space
                boundary = text.rfind(' ', start, end)
                if boundary != -1 and boundary > start + chunk_size // 2:
                    end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return [c for c in chunks if c]

class VectorDB:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
        # Use sentence-transformers all-MiniLM-L6-v2 locally
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="notes",
            embedding_function=self.embedding_fn
        )

    def index_note(self, title: str, body: str, tags: list[str]):
        """
        Splits a note into chunks and indexes them in ChromaDB.
        Deletes any existing chunks for this note first to avoid duplicates.
        """
        # 1. Delete existing chunks for this note
        self.delete_note(title)

        # 2. Chunk body
        chunks = chunk_text(body)
        if not chunks:
            # Index a fallback chunk representing title and tags
            chunks = [f"Note Title: {title}\nTags: {', '.join(tags)}"]

        # 3. Add to ChromaDB
        ids = [f"{title}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"title": title, "chunk_index": i} for i in range(len(chunks))]
        
        self.collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )

    def delete_note(self, title: str):
        """
        Deletes all chunks associated with a specific note title.
        """
        try:
            self.collection.delete(where={"title": title})
        except Exception:
            # Handle case where delete fails if collection is empty
            pass

    def search_notes(self, query: str, top_n: int = 5) -> list[dict]:
        """
        Performs semantic search, groups results by note, and returns the top_n unique notes.
        """
        # Fetch more results than needed to allow for deduplication
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_n * 3, 50)
        )

        if not results or not results['ids'] or len(results['ids'][0]) == 0:
            return []

        unique_notes = {}
        # Iterate over results (ids, distances, metadatas, documents)
        for doc_id, distance, metadata, doc in zip(
            results['ids'][0],
            results['distances'][0],
            results['metadatas'][0],
            results['documents'][0]
        ):
            title = metadata['title']
            # Lower distance means higher semantic similarity
            if title not in unique_notes or distance < unique_notes[title]['distance']:
                unique_notes[title] = {
                    "title": title,
                    "content": doc,
                    "distance": float(distance)
                }

        # Sort by distance ascending
        sorted_notes = sorted(unique_notes.values(), key=lambda x: x['distance'])
        return sorted_notes[:top_n]
