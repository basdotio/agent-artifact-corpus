# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from .base import AgentLLMasJudge


class ContextRelevancyEvaluator(AgentLLMasJudge):
    """
    Evaluates how relevant the data retrieved by the target agent is to the request.
    """

    @property
    def name(self) -> str:
        return f"{self.agent_name}_context_relevancy"

    @property
    def description(self) -> str:
        return f"Evaluates how relevant the data retrieved by the {self.agent_name} is to the request"

    @property
    def system_prompt(self) -> str:
        return f"""
You are an expert evaluator of medical AI systems. Your task is to evaluate how relevant the data retrieved by the "{self.agent_name}" agent is to the request made.

Focus on the RELEVANCE OF INFORMATION provided:
1. How well does the retrieved data address the specific request?
2. Is the information directly relevant to the question or task?
3. Does the agent provide exactly what was needed without irrelevant information?
4. Did the agent retrieve all the important information that was requested?

Rate the context relevancy on a scale from 1 to 5:
1: Poor - The information is completely irrelevant to the request
2: Below Average - Most of the information is irrelevant, with only minimal connection to the request
3: Average - Some relevant information is provided, but with significant gaps or irrelevant content
4: Good - Most of the information is relevant, with minor gaps or unnecessary information
5: Excellent - The information perfectly addresses the request with no irrelevant content

Your response must begin with "Rating: X" where X is your score (1-5), followed by your detailed explanation.

IMPORTANT: The conversation you'll review is a segment of a larger conversation, focusing on a specific interaction with the {self.agent_name} agent. Focus on evaluating only the relevance of the information provided by the {self.agent_name} agent in response to the immediate preceding request (which could come from a user or another agent).
"""

    @property
    def min_score(self) -> int:
        return 1

    @property
    def max_score(self) -> int:
        return 5

    def process_rating(self, content: str) -> int:
        return self.default_rating_extraction(content)
