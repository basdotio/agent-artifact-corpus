import os
from sentence_transformers import SentenceTransformer, CrossEncoder

os.makedirs("Models", exist_ok = True)

encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
encoder.save_pretrained("Models/MiniLM")

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
reranker.save_pretrained("Models/MiniLM-Reranker")