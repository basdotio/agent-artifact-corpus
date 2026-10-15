from typing import List, Optional

import httpx
from langchain_core.documents import Document
from pydantic import BaseModel, Field


class TDPSearchInput(BaseModel):
    """Input schema for TDPSearchTool."""

    query: str = Field(..., description="The search query to look up in TDP.")
    leagues: List[str] = Field(
        default=["soccer_smallsize"],
        description="The leagues to search in. Defaults to soccer_smallsize.",
    )


class TDPLeague(BaseModel):
    """League type for TDPSearchTool."""

    league_major: Optional[str] = Field(..., description="The major league of the TDP.")
    league_minor: Optional[str] = Field(..., description="The minor league of the TDP.")
    league_sub: Optional[str] = Field(..., description="The sub league of the TDP.")
    name: Optional[str] = Field(..., description="The name of the TDP.")
    name_pretty: Optional[str] = Field(..., description="The pretty name of the TDP.")


class TDPTeam(BaseModel):
    """Team type for TDPSearchTool."""

    name: Optional[str] = Field(..., description="The name of the team.")
    name_pretty: Optional[str] = Field(..., description="The pretty name of the team.")


class TDPInfo(BaseModel):
    """Data type for TDPSearchTool."""

    index: Optional[int] = Field(..., description="The index of the TDP.")
    league: Optional[TDPLeague] = Field(..., description="The league of the TDP.")
    team_name: Optional[TDPTeam] = Field(..., description="The team of the TDP.")
    year: Optional[int] = Field(..., description="The year of the TDP.")


class TDPResultParagraph(BaseModel):
    """Paragraph type for TDPSearchTool."""

    tdp_name: Optional[TDPInfo] = Field(
        ..., description="The TDP name information including league and team details."
    )
    title: Optional[str] = Field(..., description="The title of the paragraph.")
    content: Optional[str] = Field(..., description="The content of the paragraph.")
    questions: Optional[List[str]] = Field(
        default_factory=list,
        description="List of questions related to the paragraph content.",
    )

    def get_tdp_url(self):
        base_url = "https://tdpsearch.com/#/tdp"

        url = f"{base_url}/{self.tdp_name.league.name}__{self.tdp_name.year}__{self.tdp_name.team_name.name}__{self.tdp_name.index}"

        return url


class TDPResult(BaseModel):
    """Response type for TDPSearchTool."""

    keywords: Optional[List[str]] = Field(
        default_factory=list, description="The keywords found in the TDP."
    )
    paragraphs: Optional[List[TDPResultParagraph]] = Field(
        default_factory=list, description="The paragraphs found in the TDP."
    )

    def pretty_markdown(self, amount_of_paragraphs: int = 5):
        """Convert the TDPResult to a pretty markdown string."""
        markdown = f"# TDP Search Results ({len(self.paragraphs)} paragraphs)\n\n"
        markdown += f"## Keywords: {', '.join(self.keywords)}\n\n"
        markdown += "## Results found:\n\n"

        for index, paragraph in enumerate(self.paragraphs[:amount_of_paragraphs]):
            markdown += f"### {index + 1}. TDP from {paragraph.tdp_name.team_name.name_pretty} Team - Paragraph {paragraph.title}\n\n"
            markdown += f"**TDP Year:** {paragraph.tdp_name.year}\n\n"
            markdown += f"**TDP URL:** {paragraph.get_tdp_url()}\n\n"
            markdown += f"**TDP Content:**\n\n{paragraph.content}\n\n"
            markdown += "**Questions related to the TDP content:**\n"
            for idx, question in enumerate(paragraph.questions):
                markdown += f"  - Q{idx + 1}: {question}\n"
            markdown += "\n"

        return markdown

    def as_documents(self) -> List[Document]:
        """Convert the TDPResult to a list of Document objects."""
        from langchain.schema import Document

        documents = []
        for paragraph in self.paragraphs:
            doc = Document(
                page_content=paragraph.content,
                metadata={
                    "tdp_name": paragraph.tdp_name,
                    "tdp_url": paragraph.get_tdp_url(),
                    "team_name": paragraph.tdp_name.team_name.name_pretty,
                    "year": paragraph.tdp_name.year,
                    "title": paragraph.title,
                    "questions": paragraph.questions,
                    "keywords": self.keywords,
                },
            )
            documents.append(doc)

        return documents


async def tdp_search_tool(query: str) -> List[Document]:
    """
    Searches through TDPs (Team Description Papers) for relevant insights about small size league soccer projects.
    Useful for finding technical documentation, specifications, improvements and related information.

    This tools calls the API provided at https://tdpsearch.com/ for the RoboTeamTwente open source project.
    The original project is open source and available at https://github.com/emielsteerneman/TDP.

    Args:
        query: The search query to look up in TDP.
    Returns:
        The TDP search result in a pretty markdown format.
    """

    # URL to the TDP search API
    base_url = "https://functionapp-test-dotenv-310.azurewebsites.net/api/query"
    leagues = ["soccer_smallsize"]

    params = {"query": query, "leagues": leagues}

    try:
        # Request to the TDP search API using httpx async client
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)

        # Raise an exception if the response is not successful
        response.raise_for_status()

        # Parse the JSON response
        json_response = response.json()

        print(f"JSON response: {json_response}")

        # Create a TDPResult object from the JSON response
        result = TDPResult(**json_response)

        # Print the TDP search result in a pretty markdown format
        print(f"\nTDP search result: \n{result.pretty_markdown()}\n")

        # Return the TDP search document list
        return result.as_documents()
    except httpx.RequestError:
        # Return an error message if the TDP search API request fails
        return [
            Document(
                page_content="TDP search API request failed. Disconsider the usage of this tool.",
            )
        ]
