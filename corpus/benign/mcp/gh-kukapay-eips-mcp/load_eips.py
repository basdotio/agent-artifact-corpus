from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.fastembed import FastEmbedEmbedder
from agno.document.chunking.markdown import MarkdownChunking

def main():

  vector_db = LanceDb(
    uri="tmp/lancedb",
    table_name="EIPs",
    search_type=SearchType.vector,
    embedder=FastEmbedEmbedder(),
  )
  
  knowledge_base = TextKnowledgeBase(
    path="doc/EIPs/EIPS",
    formats=[".md"],
    chunking_strategy=MarkdownChunking(chunk_size=5000, overlap=0),
    vector_db=vector_db,
  )

  knowledge_base.load()
  
if __name__ == "__main__":
  main()  