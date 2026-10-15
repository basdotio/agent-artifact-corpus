def author_spotlight_prompt(topic: str) -> str:
    return f"""
    Use DBLP and arXiv to identify leading authors, labs, and collaborations driving research in {topic}.
    Focus on the most active, cited, and recently publishing contributors.

    Your task:
    1. Query DBLP for authors who have published multiple papers in {topic} (preferably within the last 3 years).
    2. Rank them by either publication frequency or citation count (if available).
    3. For each top author (5–10 total):
       - **Name**
       - **Affiliation or Lab (if known)**
       - **Notable Papers (2–3):**
         - Title, Year, Link to PDF or DBLP
         - One-sentence summary of contribution
       - **Research Themes:** Short list of 2–3 keywords summarizing their focus areas
    4. Add a final section titled **Collaborative Networks**, summarizing:
       - Recurrent co-author clusters or lab collaborations
       - Notable cross-institution or international projects
       - Any new or emerging research collectives

    **Formatting:**
    Return as a structured Markdown document:

    # Author Spotlight: Leaders in {topic}

    ## 1. [Author Name] — [Institution]
    **Research Focus:** keyword1, keyword2, keyword3  
    **Representative Works:**
    - [Paper Title (2024)](PDF link) — one-sentence summary  
    - [Paper Title (2023)](PDF link) — one-sentence summary  

    ## 2. [Next Author]
    ...

    ## Collaborative Networks
    - Collaboration 1: description
    - Collaboration 2: description
    - Research Groups: description

    Maintain an academic yet approachable tone. Emphasize contributions, diversity of ideas,
    and current collaborations rather than exhaustive bibliographic listings.
    """