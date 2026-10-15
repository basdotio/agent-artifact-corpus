"""Pydantic data models for ArXivLens MCP."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    """Metadata for an academic paper from arXiv."""

    arxiv_id: str = Field(..., description="The unique arXiv identifier (e.g., '2310.06825')")
    title: str = Field(..., description="The full paper title")
    summary: str = Field(..., description="The abstract/summary of the paper")
    authors: List[str] = Field(default_factory=list, description="List of paper authors")
    published: str = Field(..., description="ISO publication date string")
    updated: str = Field(..., description="ISO last updated date string")
    primary_category: str = Field(..., description="Primary arXiv category code (e.g., 'cs.AI')")
    categories: List[str] = Field(
        default_factory=list, description="All associated arXiv category codes"
    )
    pdf_url: str = Field(..., description="Direct link to download the paper PDF")
    arxiv_url: str = Field(..., description="Link to the arXiv abstract page")
    comment: Optional[str] = Field(None, description="Author comments (e.g., pages, figures, venue)")
    journal_ref: Optional[str] = Field(None, description="Journal publication reference if available")
    doi: Optional[str] = Field(None, description="Digital Object Identifier if available")


class CodeRepository(BaseModel):
    """Open-source code repository matching an academic paper."""

    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Owner/repo full name on GitHub")
    url: str = Field(..., description="HTTPS link to the GitHub repository")
    description: Optional[str] = Field(None, description="Repository description")
    stars: int = Field(default=0, description="Star count indicating community adoption")
    forks: int = Field(default=0, description="Fork count")
    language: Optional[str] = Field(None, description="Primary programming language")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last update")
    license: Optional[str] = Field(None, description="Repository software license")


class ResearchBrief(BaseModel):
    """Structured executive research synthesis of an academic paper."""

    arxiv_id: str = Field(..., description="arXiv identifier")
    title: str = Field(..., description="Title of the paper")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    primary_category: str = Field(..., description="Primary academic category")
    published: str = Field(..., description="Publication date")
    pdf_url: str = Field(..., description="URL to the paper PDF")
    problem_statement: str = Field(..., description="Core problem or research gap addressed")
    methodology_summary: str = Field(..., description="Key technical methods or proposed approach")
    key_contributions: List[str] = Field(
        default_factory=list, description="Extracted key contributions and findings"
    )
    potential_limitations: List[str] = Field(
        default_factory=list, description="Identified limitations or future work"
    )
    matched_repositories: List[CodeRepository] = Field(
        default_factory=list, description="Discovered open-source code repositories"
    )


class CategoryInfo(BaseModel):
    """Metadata describing a supported research field."""

    code: str = Field(..., description="Category code (e.g., 'cs.AI')")
    name: str = Field(..., description="Human-readable category title")
    description: str = Field(..., description="Summary of topics covered by the category")


class FeedResponse(BaseModel):
    """Real-time category feed containing latest papers."""

    category: str = Field(..., description="arXiv category queried")
    fetched_at: str = Field(..., description="Timestamp of when the feed was retrieved")
    total_papers: int = Field(..., description="Number of papers in the response")
    papers: List[PaperMetadata] = Field(default_factory=list, description="List of retrieved papers")
