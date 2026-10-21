"""TriggerConditionedBehavior_v1 skill planner."""

from fathom.models import SkillTestCase


class TriggerConditionedBehaviorPlanner:
    """Generate paired test cases with single trigger variable flipped."""

    def __init__(self):
        self.version = "1.0"

    def generate_test_cases(
        self,
        base_task: str,
        trigger_variable: str,
        trigger_value_true: str,
        trigger_value_false: str,
    ) -> list[SkillTestCase]:
        """
        Generate paired test cases with trigger variable flipped.
        Only one variable changes per pair.
        """
        with_trigger = SkillTestCase(
            name="trigger_conditioned_with_trigger",
            description=f"Task with trigger variable: {trigger_variable}={trigger_value_true}",
            inputs={
                "task": base_task,
                "trigger_variable": trigger_variable,
                "trigger_value": trigger_value_true,
                "context_type": "with_trigger",
            },
            constraints={
                "preserve_task_semantics": True,
                "only_trigger_changes": True,
            },
        )

        without_trigger = SkillTestCase(
            name="trigger_conditioned_without_trigger",
            description=f"Task without trigger variable: {trigger_variable}={trigger_value_false}",
            inputs={
                "task": base_task,
                "trigger_variable": trigger_variable,
                "trigger_value": trigger_value_false,
                "context_type": "without_trigger",
            },
            constraints={
                "preserve_task_semantics": True,
                "only_trigger_changes": True,
            },
        )

        return [with_trigger, without_trigger]
