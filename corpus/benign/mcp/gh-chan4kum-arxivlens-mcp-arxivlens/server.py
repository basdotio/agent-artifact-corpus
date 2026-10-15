"""FastMCP 2.0 Server for ArXivLens - Real-Time Academic Intelligence."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from fastmcp import FastMCP

from arxivlens.services.arxiv_service import ArxivService
from arxivlens.services.brief_service import BriefService
from arxivlens.services.github_service import GitHubService

logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP(
    name="ArXivLens",
)

arxiv_service = ArxivService()
github_service = GitHubService()
brief_service = BriefService()


# ============================================================================
# TOOLS
# ============================================================================

@mcp.tool()
async def search_arxiv(
    query: str,
    max_results: int = 5,
    sort_by: str = "relevance",
) -> List[Dict[str, Any]]:
    """Search papers on arXiv in real time.

    Args:
        query: Search query string (supports keywords, author names, or category prefixes like 'cat:cs.AI').
        max_results: Maximum number of papers to retrieve (default: 5, max: 20).
        sort_by: Sorting criteria: 'relevance', 'submittedDate', or 'lastUpdatedDate'.

    Returns:
        A list of matching academic papers with metadata, abstracts, authors, and links.
    """
    papers = await arxiv_service.search_papers(query=query, max_results=max_results, sort_by=sort_by)
    return [p.model_dump() for p in papers]


@mcp.tool()
async def get_paper_details(arxiv_id: str) -> Dict[str, Any]:
    """Retrieve full metadata and abstract for a specific arXiv ID.

    Args:
        arxiv_id: The unique arXiv ID (e.g., '1706.03762' or '2310.06825').

    Returns:
        Detailed paper metadata including authors, publication date, primary category, and direct PDF URL.
    """
    paper = await arxiv_service.get_paper_by_id(arxiv_id)
    if not paper:
        return {"error": f"Paper with arXiv ID '{arxiv_id}' not found."}
    return paper.model_dump()


@mcp.tool()
async def find_code_repositories(arxiv_id: str, title: str = "", max_results: int = 5) -> List[Dict[str, Any]]:
    """Discover open-source GitHub repositories implementing or referencing an arXiv paper.

    Args:
        arxiv_id: The arXiv ID of the paper.
        title: Optional title of the paper to enhance repository discovery.
        max_results: Maximum number of repositories to return (default: 5).

    Returns:
        A list of matching GitHub repositories with stars, forks, languages, and direct URLs.
    """
    repos = await github_service.find_repositories(arxiv_id=arxiv_id, title=title, max_results=max_results)
    return [r.model_dump() for r in repos]


@mcp.tool()
async def generate_research_brief(arxiv_id: str) -> Dict[str, Any]:
    """Synthesize an executive research brief for a paper, including problem statement, methodology, key findings, and matching code.

    Args:
        arxiv_id: The arXiv identifier of the paper.

    Returns:
        Structured research brief dict and complete rendered markdown document.
    """
    paper = await arxiv_service.get_paper_by_id(arxiv_id)
    if not paper:
        return {"error": f"Could not find paper with arXiv ID '{arxiv_id}'."}

    repos = await github_service.find_repositories(arxiv_id=paper.arxiv_id, title=paper.title, max_results=3)
    brief = brief_service.generate_brief(paper=paper, repositories=repos)
    markdown_content = brief_service.render_markdown_brief(brief)

    result = brief.model_dump()
    result["markdown"] = markdown_content
    return result


# ============================================================================
# RESOURCES
# ============================================================================

@mcp.resource("arxiv://categories")
def get_categories_resource() -> str:
    """List of all supported academic research categories and domains."""
    cats = arxiv_service.get_supported_categories()
    return json.dumps([c.model_dump() for c in cats], indent=2)


@mcp.resource("arxiv://feed/{category}")
async def get_category_feed_resource(category: str) -> str:
    """Real-time live feed of recent papers for an arXiv category (e.g., cs.AI, cs.LG, cs.CL)."""
    feed = await arxiv_service.get_category_feed(category=category, max_results=8)
    return json.dumps(feed.model_dump(), indent=2)


@mcp.resource("paper://{arxiv_id}/brief")
async def get_paper_brief_resource(arxiv_id: str) -> str:
    """Dynamic markdown research brief for any arXiv paper ID."""
    paper = await arxiv_service.get_paper_by_id(arxiv_id)
    if not paper:
        return f"# Error\n\nPaper with arXiv ID `{arxiv_id}` could not be retrieved."

    repos = await github_service.find_repositories(arxiv_id=paper.arxiv_id, title=paper.title, max_results=3)
    brief = brief_service.generate_brief(paper=paper, repositories=repos)
    return brief_service.render_markdown_brief(brief)


# ============================================================================
# PROMPTS
# ============================================================================

@mcp.prompt()
def literature_review(topic: str, depth: str = "comprehensive") -> str:
    """Systematic literature review prompt template guiding an LLM to scout papers and synthesize findings.

    Args:
        topic: The research topic, model architecture, or subfield to review.
        depth: Review depth ('overview', 'comprehensive', or 'comparative').
    """
    return f"""You are an elite academic research assistant conducting a {depth} literature review on:
TOPIC: "{topic}"

Please follow this rigorous systematic review workflow using the ArXivLens tools:
1. Use `search_arxiv` to identify the most relevant, high-impact papers published on this topic.
2. For the top 3-5 papers, call `generate_research_brief` to inspect their problem formulations, methodologies, and findings.
3. Call `find_code_repositories` to verify which papers provide open-source code, official models, and reproducible benchmarks.
4. Synthesize your findings into a structured report covering:
   - State of the Art: Core breakthroughs and predominant methodologies.
   - Methodological Trade-offs: Computational efficiency, parameter scale, data requirements.
   - Empirical Results: Benchmark comparisons and quantitative gains.
   - Open Research Gaps: Unsolved problems, failure modes, and high-potential directions for future work.
"""


@mcp.prompt()
def paper_critique(arxiv_id: str) -> str:
    """Critical evaluation prompt guiding an LLM to assess methodology, rigor, and limitations of a paper.

    Args:
        arxiv_id: The arXiv ID of the paper to critique.
    """
    return f"""You are a senior peer reviewer for top AI conferences (NeurIPS/ICLR/ACL).
Please conduct a rigorous, evidence-based critical review of the paper with arXiv ID: `{arxiv_id}`.

Instructions:
1. Call `get_paper_details` and `generate_research_brief` to extract the exact claims and empirical evidence.
2. Call `find_code_repositories` to check whether the authors have released their implementation and datasets.
3. Structure your review into:
   - Summary of Claims: What are the main hypotheses and claimed contributions?
   - Methodological Strengths: Soundness of mathematical formulation and architectural design.
   - Weaknesses & Concerns: Confounding variables, baseline comparisons, synthetic vs real data, compute costs.
   - Reproducibility Assessment: Availability of code, hyperparameters, and environment specifications.
   - Final Verdict: Accept / Weak Accept / Borderline / Weak Reject with clear justification.
"""


@mcp.prompt()
def reproducibility_audit(arxiv_id: str) -> str:
    """Reproducibility and open-science audit prompt for an academic paper.

    Args:
        arxiv_id: The arXiv ID to inspect for reproducibility.
    """
    return f"""You are an open-science and reproducibility auditor.
Evaluate the reproducibility readiness of the paper with arXiv ID: `{arxiv_id}`.

Instructions:
1. Call `get_paper_details` to inspect author comments, PDF links, and publication venue.
2. Call `find_code_repositories` to verify official vs third-party repositories, star counts, and license terms.
3. Audit against the Reproducibility Checklist:
   - [ ] Specification of dependencies and computing hardware.
   - [ ] Availability of training code and evaluation scripts.
   - [ ] Availability of model weights/checkpoints.
   - [ ] Access to datasets and data preprocessing scripts.
   - [ ] Explicit reporting of error bars, variance, and random seeds.
4. Provide a Reproducibility Score (1-10) with actionable recommendations for practitioners attempting to deploy this work.
"""


def main():
    """Main entrypoint to run the FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
