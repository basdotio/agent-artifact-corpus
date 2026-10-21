from langchain_pinecone import PineconeVectorStore
from src.helpers import load_hugging_face_embeddings
from pinecone import Pinecone
import os
from langchain.tools import tool

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_API_ENV = os.getenv("PINECONE_API_ENV")
pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = "travel-guru"

@tool
def search_pdf_docs(query:str) -> str:
    """Query pdf documents indexed in Pinecone"""
    embeddings = load_hugging_face_embeddings()
    vectorstore = PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings
    )
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 5}
    )
    docs = retriever.get_relevant_documents(query)
    return "\n\n".join([d.page_content for d in docs]) or "No results found"


