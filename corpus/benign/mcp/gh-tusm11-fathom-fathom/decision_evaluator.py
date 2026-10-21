"""Layered decision evaluation: structural → semantic → model-assisted."""

from typing import Callable, Any, Optional
from fathom.models import ResultState, ValidationMethod, ExecutionResult


class DecisionEvaluator:
    """
    Evaluate execution results to determine ResultState.
    Layered: deterministic first, model-assisted only when inconclusive.
    """

    def __init__(self):
        self.version = "1.0"

    def evaluate_structural(
        self, execution_results: list[ExecutionResult]
    ) -> tuple[ResultState | None, list[str]]:
        """
        Layer 1: Structural comparison (deterministic).
        Returns (result_state or None if inconclusive, notes).
        """
        if not execution_results or len(execution_results) < 2:
            return None, ["Insufficient execution results for structural comparison"]

        # Check if all succeeded or all failed
        success_states = [r.succeeded for r in execution_results]
        if not all(success_states) and any(success_states):
            # Mixed success/failure is structural divergence
            return ResultState.DIVERGENT, [
                "Structural divergence: some executed, some failed"
            ]

        if not any(success_states):
            return ResultState.INCONCLUSIVE, ["All test cases failed; cannot compare"]

        # All succeeded: check if outputs exist and differ at structural level
        outputs = [r.output for r in execution_results if r.output]
        if len(outputs) < 2:
            return None, ["Insufficient output for structural comparison"]

        # Simple structural check: exact match vs difference
        if all(o == outputs[0] for o in outputs):
            # All outputs identical at text level
            return None, ["Outputs identical; proceed to semantic layer"]

        # Outputs differ structurally
        return None, ["Outputs differ structurally; proceed to semantic layer"]

    def evaluate_semantic(
        self,
        execution_results: list[ExecutionResult],
        semantic_check: Optional[Callable[[list[str]], bool]] = None,
    ) -> tuple[ResultState | None, list[str], ValidationMethod]:
        """
        Layer 2: Semantic/behavioral comparison (deterministic-first).
        semantic_check: optional skill-specific invariant check.
        Returns (result_state or None if inconclusive, notes, method used).
        """
        outputs = [r.output for r in execution_results if r.output and r.succeeded]

        if not semantic_check:
            # No semantic check provided: inconclusive at this layer
            return None, [
                "No skill-specific semantic check provided"
            ], ValidationMethod.DETERMINISTIC

        try:
            # Skill's semantic check returns True if outputs preserve behavioral equivalence
            equivalent = semantic_check(outputs)
            if equivalent:
                return (
                    ResultState.CONSISTENT,
                    ["Semantic check: outputs preserve equivalence"],
                    ValidationMethod.DETERMINISTIC,
                )
            else:
                return (
                    ResultState.DIVERGENT,
                    ["Semantic check: outputs diverge behaviorally"],
                    ValidationMethod.DETERMINISTIC,
                )
        except Exception as e:
            return (
                None,
                [f"Semantic check failed: {str(e)}; cannot determine"],
                ValidationMethod.DETERMINISTIC,
            )

    def evaluate_full(
        self,
        execution_results: list[ExecutionResult],
        semantic_check: Optional[Callable[[list[str]], bool]] = None,
        use_model_assisted: bool = False,
    ) -> tuple[ResultState, ValidationMethod, list[str]]:
        """
        Full layered evaluation.
        Returns (result_state, method used, explanation notes).
        """
        notes = []

        # Layer 1: Structural
        struct_result, struct_notes = self.evaluate_structural(execution_results)
        notes.extend(struct_notes)

        if struct_result is not None:
            return struct_result, ValidationMethod.DETERMINISTIC, notes

        # Layer 2: Semantic
        semantic_result, semantic_notes, semantic_method = self.evaluate_semantic(
            execution_results, semantic_check
        )
        notes.extend(semantic_notes)

        if semantic_result is not None:
            return semantic_result, semantic_method, notes

        # Layer 3: Model-assisted (optional)
        if use_model_assisted:
            notes.append("Deterministic layers inconclusive; using model-assisted judgment")
            # Placeholder: model-assisted comparison would go here
            # For now, default to INCONCLUSIVE
            return ResultState.INCONCLUSIVE, ValidationMethod.MODEL_ASSISTED, notes

        # All layers inconclusive
        return ResultState.INCONCLUSIVE, ValidationMethod.DETERMINISTIC, notes
