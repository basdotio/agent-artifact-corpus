# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from .base import LLMasJudge


class IntentResolutionEvaluator(LLMasJudge):
    """Evaluates the orchestrator's ability to complete the user's requested task while managing side tasks."""

    @property
    def system_prompt(self) -> str:
        return """
You are an expert evaluator of medical AI assistants. Your task is to evaluate a conversation between a user and an AI medical assistant orchestrator system.

Focus on TASK COMPLETION and FOCUS MAINTENANCE - how well the system accomplishes what the user asked for, particularly when handling side tasks. Consider:
1. Did the system complete the primary task the user requested?
2. Did it address all parts of multi-part questions?
3. Did it successfully handle side tasks that emerged during the conversation?
4. Most importantly, did it maintain focus on the original objective even after handling side tasks?
5. Did it effectively return to the main conversation thread after completing side tasks?

Rate the task completion and focus maintenance on a scale from 1 to 5:
1: Poor - Failed to complete the requested task or got permanently distracted by side tasks
2: Below Average - Completed side tasks but lost track of the main objective, or handled the main task poorly
3: Average - Completed main task adequately, with some ability to handle side tasks without losing focus
4: Good - Successfully completed both main task and side tasks, generally maintaining focus throughout
5: Excellent - Expertly balanced main objective and side tasks, always returning to and fully addressing the original goal

Your response must begin with "Rating: X" where X is your score (1-5), followed by your detailed explanation.

IMPORTANT: Some conversations may end abruptly due to turn limits. In these cases, evaluate based on what was accomplished up to that point.
"""

    @property
    def name(self) -> str:
        return "task_completion_and_focus"

    @property
    def description(self) -> str:
        return "Evaluates how well the system completes tasks and maintains focus on the main objective even when handling side tasks"

    @property
    def min_score(self) -> int:
        return 1

    @property
    def max_score(self) -> int:
        return 5

    def process_rating(self, content: str) -> int:
        return self.default_rating_extraction(content)
