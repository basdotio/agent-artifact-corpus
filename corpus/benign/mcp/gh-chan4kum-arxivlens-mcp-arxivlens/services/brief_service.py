"""Service for generating structured research briefs and synthesizing paper insights."""

from __future__ import annotations

import re
from typing import List, Optional

from arxivlens.models import CodeRepository, PaperMetadata, ResearchBrief


class BriefService:
    """Service to analyze paper abstracts and metadata into structured research briefs."""

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences while respecting common abbreviations."""
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
        return [s.strip() for s in sentences if s.strip()]

    def generate_brief(
        self,
        paper: PaperMetadata,
        repositories: Optional[List[CodeRepository]] = None,
    ) -> ResearchBrief:
        """Synthesize paper metadata and abstract into a structured ResearchBrief."""
        repos = repositories or []
        sentences = self._split_sentences(paper.summary)

        # 1. Identify Problem Statement
        problem_candidates = []
        for s in sentences[:3]:
            lower = s.lower()
            if any(k in lower for k in ["problem", "challenge", "bottleneck", "limitation", "difficulty", "remains", "despite"]):
                problem_candidates.append(s)

        if not problem_candidates and sentences:
            problem_statement = sentences[0]
        else:
            problem_statement = " ".join(problem_candidates) if problem_candidates else paper.summary[:200] + "..."

        # 2. Identify Methodology
        method_candidates = []
        for s in sentences:
            lower = s.lower()
            if any(k in lower for k in ["we propose", "we introduce", "we present", "in this work", "our approach", "we develop", "architecture"]):
                method_candidates.append(s)

        if not method_candidates and len(sentences) > 1:
            methodology_summary = sentences[1]
        else:
            methodology_summary = " ".join(method_candidates[:2]) if method_candidates else "Methodology details outlined in the paper abstract."

        # 3. Key Contributions
        contributions = []
        for s in sentences:
            lower = s.lower()
            if any(k in lower for k in ["demonstrate", "outperform", "state-of-the-art", "sota", "results show", "achieve", "experiment", "findings"]):
                contributions.append(s)
            elif any(k in lower for k in ["first", "novel", "framework", "dataset", "comprehensive"]):
                if s not in contributions:
                    contributions.append(s)

        if not contributions and len(sentences) > 2:
            contributions = sentences[2:5]

        # 4. Potential Limitations
        limitations = []
        for s in sentences:
            lower = s.lower()
            if any(k in lower for k in ["however", "although", "future work", "scale", "cost", "constrained", "trade-off"]):
                limitations.append(s)

        if not limitations:
            limitations.append("Full empirical boundary conditions and ablation constraints are detailed in the PDF text.")

        return ResearchBrief(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            authors=paper.authors,
            primary_category=paper.primary_category,
            published=paper.published,
            pdf_url=paper.pdf_url,
            problem_statement=problem_statement,
            methodology_summary=methodology_summary,
            key_contributions=contributions[:4],
            potential_limitations=limitations[:3],
            matched_repositories=repos,
        )

    def render_markdown_brief(self, brief: ResearchBrief) -> str:
        """Render a ResearchBrief model into clean, professional GitHub-flavored Markdown."""
        author_list = ", ".join(brief.authors) if brief.authors else "Unknown Authors"

        md_lines = [
            f"# Research Brief: {brief.title}",
            "",
            f"- **arXiv ID**: [{brief.arxiv_id}](https://arxiv.org/abs/{brief.arxiv_id})",
            f"- **Authors**: {author_list}",
            f"- **Primary Category**: `{brief.primary_category}`",
            f"- **Published**: {brief.published}",
            f"- **PDF Link**: [Download PDF]({brief.pdf_url})",
            "",
            "## 1. Problem Statement & Research Gap",
            brief.problem_statement,
            "",
            "## 2. Proposed Methodology & Architecture",
            brief.methodology_summary,
            "",
            "## 3. Key Contributions & Empirical Findings",
        ]

        for contrib in brief.key_contributions:
            md_lines.append(f"- {contrib}")

        md_lines.extend([
            "",
            "## 4. Potential Limitations & Constraints",
        ])

        for lim in brief.potential_limitations:
            md_lines.append(f"- {lim}")

        md_lines.extend([
            "",
            "## 5. Code Implementations & Repositories",
        ])

        if brief.matched_repositories:
            for repo in brief.matched_repositories:
                stars_badge = f"⭐ {repo.stars:,}" if repo.stars else "⭐ 0"
                lang_str = f" `{repo.language}` |" if repo.language else ""
                desc = f" - {repo.description}" if repo.description else ""
                md_lines.append(f"- [{repo.full_name}]({repo.url}) ({stars_badge} |{lang_str} License: {repo.license or 'N/A'}){desc}")
        else:
            md_lines.append("*No verified open-source repositories found on GitHub for this paper.*")

        md_lines.append("")
        return "\n".join(md_lines)
