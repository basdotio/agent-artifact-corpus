# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from .base import LLMasJudge


class AgentSelectionEvaluator(LLMasJudge):
    """Evaluates the orchestrator's ability to select the correct agent at each step."""

    @property
    def system_prompt(self) -> str:
        return """
You are an expert evaluator of medical AI assistants. Your task is to evaluate a conversation between a user and an AI orchestrator (called "Orchestrator") that coordinates multiple specialized medical agents.

Focus on the orchestrator's ability to select the correct agent for each user query. Consider:
1. Did the orchestrator select the most appropriate agent for each task?
2. Did it avoid using unnecessary agents?
3. Did it effectively route complex questions to specialized agents?
4. Did it use multiple agents when appropriate for complex questions?

Rate the orchestrator's agent selection ability on a scale from 1 to 5:
1: Poor - Consistently selected inappropriate agents, wasting resources and providing poor answers
2: Below Average - Often selected inappropriate agents, missing opportunities to use specialized expertise
3: Average - Generally selected appropriate agents, with a few mistakes or missed opportunities
4: Good - Consistently selected appropriate agents, effectively using their specialized capabilities
5: Excellent - Perfectly matched user queries with the optimal agent(s), leveraging specialized knowledge efficiently

Your response must begin with "Rating: X" where X is your score (1-5), followed by your detailed explanation.
"""

    @property
    def name(self) -> str:
        return "agent_selection"

    @property
    def description(self) -> str:
        return "Evaluates the orchestrator's ability to select the correct agent at each step"

    @property
    def min_score(self) -> int:
        return 1

    @property
    def max_score(self) -> int:
        return 5

    def process_rating(self, content: str) -> int:
        return self.default_rating_extraction(content)
