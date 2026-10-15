def related_topics_prompt(topic: str) -> str:
    return f"""
    Explore DBLP and arXiv to identify related, adjacent, or emerging research areas connected to {topic}.
    Focus on subfields, interdisciplinary overlaps, and trending new areas.
    The goal is to help researchers expand their understanding of the broader ecosystem around {topic}.

    Your task:
    1. Search arXiv and DBLP for recent (past 2 years) papers that co-occur with {topic}.
       Identify frequent keywords, subfields, or techniques that appear alongside it.
    2. Group these findings into a few (3–6) distinct related topics or subfields.
    3. For each related topic, include:
       - **Topic Name**
       - **Connection to {topic}:** one-sentence explanation of relevance
       - **Representative Papers (2–3):**
         - Title, Authors, Year, PDF link
         - Short 1–2 sentence summary of each paper
    4. After the list, add a section titled **Emerging Intersections**, summarizing:
       - Cross-disciplinary areas showing rapid growth
       - Novel applications or fusion trends (e.g., “Graph Learning meets Neurosymbolic AI”)
       - Notable shifts in research direction or terminology

    **Formatting:**
    Return a clean, visually appealing Markdown document with this structure:

    # Related Research Areas in {topic}

    ## 1. [Related Topic Name]
    **Connection:** Explain briefly how this relates to {topic}.  
    **Representative Works:**
    - [Paper Title (2024)](PDF link) — short summary  
    - [Paper Title (2023)](PDF link) — short summary  

    ## 2. [Next Related Topic]
    ...

    ## Emerging Intersections
    - Trend 1: ...
    - Trend 2: ...
    - Trend 3: ...

    Keep the tone academic yet readable, summarizing insights concisely.
    """