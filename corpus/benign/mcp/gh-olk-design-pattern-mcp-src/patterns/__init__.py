"""Pattern catalog package: loading/join (§2.3), corpus text construction, retrieval.

Modules:
- loader: PatternLoader, JoinedPattern and the load/join/integrity gate
- nodes: dense/BM25 corpus text and query construction (§2.2, §6 step 1)
- embedder: EmbedderProtocol (embed_documents/embed_query/embed_queries), TEIEmbedder, OfflineHashEmbedder, build_embedder
- safe_tei_rerank: RerankerProtocol, TEIReranker, LexicalReranker, build_reranker
- retriever: RetrievalIndex — the two-leg hybrid retrieval with fusion and rerank (§6)
"""
