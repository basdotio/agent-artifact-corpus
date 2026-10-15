from app.retrieval import build_hybrid_query


def test_hybrid_query_filters_to_verified_source_tiers():
    query = build_hybrid_query(
        "BMRCL Purple Line shutdown Tuesday",
        elser_inference_id=".elser-2-elasticsearch",
        jina_reranker_inference_id="jina-reranker-v2",
    )

    query_text = str(query)

    assert "'source_tier': ['official', 'news']" in query_text
    assert query["retriever"]["text_similarity_reranker"]["inference_id"] == "jina-reranker-v2"
    assert query["retriever"]["text_similarity_reranker"]["retriever"]["rrf"]["rank_window_size"] == 20
