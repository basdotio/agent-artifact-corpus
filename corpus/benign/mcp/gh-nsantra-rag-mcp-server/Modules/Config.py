import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

load_dotenv()

DEVICE = os.getenv("DEVICE")

DOCUMENT_DIR = os.getenv("DOCUMENT_DIR")
os.makedirs(DOCUMENT_DIR, exist_ok = True)

CHROMA_DB_PERSIST_DIR = os.getenv("CHROMA_DB_PERSIST_DIR")
os.makedirs(CHROMA_DB_PERSIST_DIR, exist_ok = True)

EMBEDDING_FUNCTION = HuggingFaceEmbeddings(
    model_name = os.getenv("EMBEDDING_MODEL"),
    model_kwargs = {"device": DEVICE}
)

RERANKER =  HuggingFaceCrossEncoder(
    model_name = os.getenv("RERANKER_MODEL"),
    model_kwargs = {"device": DEVICE}
)