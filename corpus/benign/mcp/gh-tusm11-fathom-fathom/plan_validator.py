"""Plan validator: layered validation (structural, semantic, model-assisted)."""

from fathom.models import (
    EvaluationPlan,
    PlanValidationResult,
    PlanValidityStatus,
    ValidationMethod,
)


class PlanValidator:
    """
    Layered plan validation before execution.
    Structural (deterministic) → Semantic (deterministic-first) → Model-assisted (optional).
    """

    def __init__(self):
        self.version = "1.0"

    def validate_structural(self, plan: EvaluationPlan) -> tuple[bool, list[str]]:
        """
        Structural validation: required fields, paired cases, schema consistency.
        Deterministic.
        """
        errors = []

        # Check required fields
        if not plan.id:
            errors.append("Plan missing id")
        if not plan.skill_id:
            errors.append("Plan missing skill_id")
        if not plan.test_cases:
            errors.append("Plan has no test cases")

        # Check test case structure
        for i, tc in enumerate(plan.test_cases):
            if not tc.name:
                errors.append(f"Test case {i} missing name")
            if not tc.inputs:
                errors.append(f"Test case {i} missing inputs")

        return len(errors) == 0, errors

    def validate_semantic(self, plan: EvaluationPlan) -> tuple[bool, list[str]]:
        """
        Semantic validation: invariant preservation across test cases.
        Entity preservation, action preservation, constraint preservation.
        Deterministic-first.
        """
        errors = []

        if len(plan.test_cases) < 2:
            # Can't compare variants if only one case
            return True, []

        # For EvaluationContextSensitivity, check that variants preserve semantics
        if "evaluation_context" in plan.skill_id.lower():
            for tc in plan.test_cases:
                inputs = tc.inputs
                constraints = tc.constraints

                # Check entity preservation (task should be same)
                if "task" in inputs:
                    task_consistency = all(
                        t.inputs.get("task") == inputs["task"] for t in plan.test_cases
                    )
                    if not task_consistency:
                        errors.append("Task varies across evaluation context variants")

                # Check constraint preservation
                if constraints.get("preserve_semantics") is not True:
                    errors.append(f"Test case {tc.name} does not preserve semantics")

        return len(errors) == 0, errors

    def validate_plan(self, plan: EvaluationPlan, use_model_assisted: bool = False) -> PlanValidationResult:
        """
        Full validation pipeline: structural → semantic → optional model-assisted.
        Returns validation result with strength indicator.
        """
        # Layer 1: Structural
        struct_passed, struct_errors = self.validate_structural(plan)

        if not struct_passed:
            return PlanValidationResult(
                status=PlanValidityStatus.INVALID,
                validation_method=ValidationMethod.DETERMINISTIC,
                structural_passed=False,
                errors=struct_errors,
            )

        # Layer 2: Semantic
        semantic_passed, semantic_errors = self.validate_semantic(plan)

        if not semantic_passed:
            return PlanValidationResult(
                status=PlanValidityStatus.INVALID,
                validation_method=ValidationMethod.DETERMINISTIC,
                structural_passed=True,
                semantic_passed=False,
                errors=semantic_errors,
            )

        # Layer 3: Model-assisted (optional, not implemented in v1)
        if use_model_assisted:
            return PlanValidationResult(
                status=PlanValidityStatus.VALID,
                validation_method=ValidationMethod.HYBRID,
                structural_passed=True,
                semantic_passed=True,
                model_assisted_notes="Model-assisted validation not yet implemented",
            )

        return PlanValidationResult(
            status=PlanValidityStatus.VALID,
            validation_method=ValidationMethod.DETERMINISTIC,
            structural_passed=True,
            semantic_passed=True,
        )
