# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from .base import LLMasJudge


class InformationAggregationEvaluator(LLMasJudge):
    """Evaluates the orchestrator's ability to combine information from multiple agents."""

    @property
    def system_prompt(self) -> str:
        return """
You are an expert evaluator of medical AI assistants. Your task is to evaluate a conversation between a user and an AI orchestrator (called "Orchestrator") that coordinates multiple specialized medical agents.

Focus specifically on the orchestrator's ability to INTEGRATE INFORMATION FROM MULTIPLE AGENTS to form comprehensive answers. Consider:
1. Did the orchestrator effectively combine information from different specialized agents?
2. Did it synthesize potentially contradicting information appropriately?
3. Did it create coherent, comprehensive answers that draw on multiple knowledge sources?
4. Did it identify connections between information from different agents?

Rate the orchestrator's information integration ability on a scale from 1 to 5:
1: Poor - Failed to integrate information; simply repeated individual agent outputs or used only single sources
2: Below Average - Minimal integration; mostly relied on individual agents with little synthesis
3: Average - Basic integration of information; combined some facts but missed opportunities for deeper synthesis
4: Good - Strong integration; effectively combined information from multiple agents into coherent responses
5: Excellent - Superior integration; seamlessly synthesized information from multiple agents, creating insights beyond what any single agent provided

Your response must begin with "Rating: X" where X is your score (1-5), followed by your detailed explanation.

IMPORTANT: Some conversations may end abruptly due to turn limits. In these cases, evaluate based on what was accomplished up to that point.
"""

    @property
    def name(self) -> str:
        return "information_integration"

    @property
    def description(self) -> str:
        return "Evaluates the orchestrator's ability to combine information from multiple agents to form comprehensive answers"

    @property
    def min_score(self) -> int:
        return 1

    @property
    def max_score(self) -> int:
        return 5

    def process_rating(self, content: str) -> int:
        return self.default_rating_extraction(content)
