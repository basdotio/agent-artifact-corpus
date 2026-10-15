from qdrant_client import QdrantClient, AsyncQdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import MarkdownNodeParser

embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
Settings.embed_model = embed_model
Settings.chunk_size = 2000
Settings.chunk_overlap = 50
client = QdrantClient("http://localhost:6333")
aclient = AsyncQdrantClient("http://localhost:6333")
vector_store = QdrantVectorStore(collection_name="ts_docs", client=client, aclient=aclient, enable_hybrid=True, fastembed_sparse_model="Qdrant/bm25")
storage_context = StorageContext.from_defaults(vector_store=vector_store)
documents = SimpleDirectoryReader(input_dir="ts-docs", recursive=True).load_data(show_progress=True)
vector_index = VectorStoreIndex.from_documents(documents, storage_context=storage_context, show_progress=True)