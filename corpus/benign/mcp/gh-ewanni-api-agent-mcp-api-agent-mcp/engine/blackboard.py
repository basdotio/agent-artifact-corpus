from pydantic import BaseModel, Field

from ..llm.schemas import Critique, Proposal


class BlackboardState(BaseModel):
    task: str
    current_proposals: list[Proposal] = Field(default_factory=list)
    critiques: list[Critique] = Field(default_factory=list)
    verified_facts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    round_summaries: list[str] = Field(default_factory=list)

    def render(self) -> str:
        sections = [f"# TASK\n{self.task}"]
        if self.current_proposals:
            sections.append(
                "# PROPOSALS\n" + "\n".join(
                    f"- [{proposal.agent}] {proposal.summary}\n  {proposal.content[:3000]}"
                    for proposal in self.current_proposals
                )
            )
        if self.critiques:
            sections.append(
                "# CRITIQUES\n" + "\n".join(
                    f"- [{critique.agent}] concerns: {critique.concerns}; "
                    f"strengths: {critique.strengths}; questions: {critique.questions}"
                    for critique in self.critiques
                )
            )
        if self.verified_facts:
            sections.append("# VERIFIED FACTS\n" + "\n".join(f"- {fact}" for fact in self.verified_facts))
        if self.open_questions:
            sections.append("# OPEN QUESTIONS\n" + "\n".join(f"- {question}" for question in self.open_questions))
        if self.round_summaries:
            sections.append("# PREVIOUS ROUNDS\n" + "\n".join(f"- {summary}" for summary in self.round_summaries))
        return "\n\n".join(sections)
