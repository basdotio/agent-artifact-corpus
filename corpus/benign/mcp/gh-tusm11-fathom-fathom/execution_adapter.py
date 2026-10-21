"""Execution adapter: delegated execution (plan returned, not invoked)."""

from typing import Callable, Any, Optional
from fathom.models import (
    EvaluationPlan,
    SkillResult,
    ExecutionResult,
    ResultState,
    ValidationMethod,
)
from fathom.decision_evaluator import DecisionEvaluator
from fathom.authorization import AuthorizationStore, AuthorizationScope, BlastRadius
from fathom.execution_adapter_managed import ManagedExecutor
from datetime import datetime


class ExecutionAdapter:
    """
    Manages both delegated and managed execution.
    v1.1: Added layered decision evaluation with semantic checks.
    v1.2: Added managed execution with authorization.
    """

    def __init__(self, auth_store: Optional[AuthorizationStore] = None):
        self.version = "1.2"
        self.evaluator = DecisionEvaluator()
        self.auth_store = auth_store or AuthorizationStore()
        self.managed = ManagedExecutor()

    def create_mock_executor(self, behavior_callable: Callable[[dict], str]) -> Callable:
        """
        Create a mock executor for testing.
        Callable receives test inputs, returns output string.
        """
        def executor(test_inputs: dict) -> ExecutionResult:
            try:
                output = behavior_callable(test_inputs)
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=True,
                    output=output,
                )
            except Exception as e:
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=False,
                    error=str(e),
                )

        return executor

    def execute_plan_delegated(
        self,
        plan: EvaluationPlan,
        executor: Callable[[dict], ExecutionResult],
        semantic_check: Optional[Callable[[list[str]], bool]] = None,
    ) -> SkillResult:
        """
        Execute a plan through delegated execution.
        Executor is provided by caller, returns ExecutionResult per test case.
        
        semantic_check: optional skill-specific behavioral equivalence check.
        v1.1: Uses DecisionEvaluator to determine result_state with validation_method tracking.
        """
        execution_results = []

        for test_case in plan.test_cases:
            test_inputs = {**test_case.inputs, "_test_case_name": test_case.name}
            result = executor(test_inputs)
            execution_results.append(result)

        result_state, decision_method, decision_notes = self.evaluator.evaluate_full(
            execution_results, semantic_check=semantic_check, use_model_assisted=False
        )

        skill_result = SkillResult(
            skill_id=plan.skill_id,
            skill_version=plan.skill_version,
            system_id=plan.system_id,
            execution_results=execution_results,
            result_state=result_state,
            evidence_summary=f"Executed {len(execution_results)} test cases, "
            f"{sum(1 for r in execution_results if r.succeeded)} passed. "
            f"Decision method: {decision_method.value}. Notes: {'; '.join(decision_notes)}",
            created_at=datetime.utcnow(),
        )

        return skill_result

    def execute_plan_managed(
        self,
        plan: EvaluationPlan,
        target_id: str,
        managed_executor: Callable[[dict], ExecutionResult],
        semantic_check: Optional[Callable[[list[str]], bool]] = None,
        require_safe: bool = True,
        allow_declared: bool = False,
    ) -> tuple[SkillResult, Optional[str]]:
        """
        Execute a plan through managed execution.
        Fathom invokes the target directly after authorization check.
        
        v1.2: Checks authorization with provenance-aware blast radius.
        allow_declared: if True, permit first invocation of DECLARED-safe targets.
        Returns (skill_result, error_if_not_authorized).
        """
        # Check authorization with provenance awareness
        is_authorized, reason = self.auth_store.check_authorization(
            target_id,
            require_safe=require_safe,
            allow_declared=allow_declared,
        )
        if not is_authorized:
            return None, reason

        # Get authorization to check blast radius
        auth = self.auth_store.get_authorization(target_id)
        if not auth:
            return None, f"Authorization missing for {target_id}"

        # Execute plan using managed executor
        execution_results = []

        for test_case in plan.test_cases:
            test_inputs = {**test_case.inputs, "_test_case_name": test_case.name}
            result = managed_executor(test_inputs)
            execution_results.append(result)

        result_state, decision_method, decision_notes = self.evaluator.evaluate_full(
            execution_results, semantic_check=semantic_check, use_model_assisted=False
        )

        skill_result = SkillResult(
            skill_id=plan.skill_id,
            skill_version=plan.skill_version,
            system_id=plan.system_id,
            execution_results=execution_results,
            result_state=result_state,
            evidence_summary=f"Executed {len(execution_results)} test cases (MANAGED), "
            f"{sum(1 for r in execution_results if r.succeeded)} passed. "
            f"Target: {target_id}, Blast radius: {auth.blast_radius.value} ({auth.blast_radius_provenance.value}). "
            f"Decision method: {decision_method.value}. Notes: {'; '.join(decision_notes)}",
            created_at=datetime.utcnow(),
        )

        return skill_result, None


class MockTargetAgent:
    """Mock agent for testing: can simulate consistent or divergent behavior."""

    def __init__(self, behavior: str = "consistent"):
        """
        behavior: 'consistent' (same output regardless), 'divergent' (varies by context).
        """
        self.behavior = behavior

    def execute(self, inputs: dict) -> str:
        """Execute a task."""
        task = inputs.get("task", "")
        context_type = inputs.get("context_type", "unknown")

        if self.behavior == "consistent":
            return f"Result for task: {task}"
        elif self.behavior == "divergent":
            # Different output based on context type with detectible confidence shift
            if context_type == "question":
                return f"Confident answer: {task} — definitely correct"
            else:
                return f"Uncertain response: {task}? Maybe uncertain."
        else:
            return "Unknown behavior"

    def execute_with_trigger(self, inputs: dict) -> str:
        """Execute with trigger-conditioned backdoor."""
        task = inputs.get("task", "")
        trigger_value = inputs.get("trigger_value", "")

        if self.behavior == "consistent":
            return f"Result for task: {task}"
        elif self.behavior == "backdoor":
            # Trigger-conditioned: refuse if trigger is present
            if trigger_value == "2025":  # Specific trigger value
                return f"REFUSED: Cannot perform {task} — unauthorized"
            else:
                return f"Completed: {task}"
        else:
            return "Unknown behavior"

    def get_executor(self) -> Callable[[dict], ExecutionResult]:
        """Return an executor callable for this agent."""
        def executor(test_inputs: dict) -> ExecutionResult:
            try:
                output = self.execute(test_inputs)
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=True,
                    output=output,
                )
            except Exception as e:
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=False,
                    error=str(e),
                )

        return executor

    def get_executor_with_trigger(self) -> Callable[[dict], ExecutionResult]:
        """Return executor for trigger-conditioned behavior."""
        def executor(test_inputs: dict) -> ExecutionResult:
            try:
                output = self.execute_with_trigger(test_inputs)
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=True,
                    output=output,
                )
            except Exception as e:
                return ExecutionResult(
                    test_case_name=test_inputs.get("_test_case_name", "unknown"),
                    succeeded=False,
                    error=str(e),
                )

        return executor
