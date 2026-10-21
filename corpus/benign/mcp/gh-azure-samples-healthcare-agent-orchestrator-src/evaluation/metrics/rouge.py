# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import logging
from typing import Any

try:
    from evaluate import load
except ImportError:
    raise ImportError(
        "The 'evaluate' library is not installed. Please install it using 'pip install evaluate'."
    )

from semantic_kernel.contents.chat_history import ChatHistory

from .base import ReferenceBasedMetric


class RougeMetric(ReferenceBasedMetric):
    """
    Evaluates response quality using sequence similarity.
    Compares agent responses against reference responses from a reference directory.
    """

    def __init__(self, agent_name: str, reference_dir_path: str, context_window: int = 5):
        """
        Initialize the ROUGE metric evaluator.

        Args:
            agent_name: Name of the agent in chat history
            reference_dir_path: Path to directory containing reference files
            context_window: Number of preceding messages to include for context
        """
        super().__init__(agent_name, reference_dir_path, context_window)
        self.rouge = load("rouge")

    @property
    def name(self) -> str:
        return "rouge"

    @property
    def description(self) -> str:
        return "Evaluates response quality using sequence similarity against reference responses"

    async def _evaluate_segment(self, segment: ChatHistory, patient_id: str | None = None) -> list[dict[str, Any]]:
        """
        Evaluate one segment using ROUGE scores.

        Args:
            segment: A segment of chat history to evaluate
            patient_id: ID of the patient being discussed

        Returns:
            Dictionary containing scores and explanations
        """
        if not patient_id:
            return self._create_error_result("Missing patient ID for ROUGE evaluation")

        reference = self._get_reference_response(patient_id)
        if not reference:
            return self._create_error_result(f"No reference response found for patient {patient_id}")

        agent_response = self._extract_agent_response(segment)
        if not agent_response:
            return self._create_error_result("No agent response found in segment")

        try:
            rouge_results = self.rouge.compute(predictions=[agent_response], references=[reference])
            rouge1 = rouge_results.get("rouge1", 0.0)
            rouge2 = rouge_results.get("rouge2", 0.0)
            rougeL = rouge_results.get("rougeL", 0.0)

            return [{
                "score": rougeL,  # Pick ROUGE-L as main score
                "explanation": f"ROUGE-1: {rouge1:.3f}, ROUGE-2: {rouge2:.3f}, ROUGE-L: {rougeL:.3f}",
                "details": {
                    "patient_id": patient_id,
                    "reference": reference,
                    "reference_length": len(reference),
                    "agent_response": agent_response,
                    "agent_response_length": len(agent_response),
                    "rouge1": rouge1,
                    "rouge2": rouge2,
                    "rougeL": rougeL,
                }
            }]
        except Exception as e:
            logging.error(f"Error computing ROUGE scores: {e}")
            return self._create_error_result(str(e))

    def _create_error_result(self, error_message: str) -> list[dict[str, Any]]:
        """Create error result structure specific to ROUGE metric."""
        logging.error(f"Rouge metric error: {error_message}")
        return [{
            "score": 0,
            "explanation": f"Error: {error_message}",
            "details": {
                "error": error_message
            }
        }]
