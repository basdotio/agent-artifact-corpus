# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import logging
import os
import re
from typing import Any, Dict, List

import pandas as pd
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import \
    AzureChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory

from .base import AgentReferenceBasedLLMasJudge

FACT_EXTRACTION_PROMPT_TEMPLATE = """
Organize the following free-text patient summary into a list of facts. This list will be
later be used to evaluate the accuracy of each fact in the summary.

- Each fact should be a single sentence. 
- Each fact should be categorized into one of the following categories:
    {fact_list}
- Include all factual statements from the summary. Do not omit any facts.
- Maintain the order of the facts as they appear in the summary.
- Facts that are repeated in the summary should be included only once in the list of facts.

Here is the patient summary:

{summary}

Format your response as a JSON array of objects, where each object has two properties:
- "fact": the text of the fact
- "category": the category of the fact (must be one of {fact_list})

Example:
[
  {{"fact": "Patient is a 65-year-old male", "category": "demographics"}},
  {{"fact": "Patient was diagnosed with stage II lung cancer", "category": "diagnosis"}}
]
"""

ENTAILMENT_EVALUATION_PROMPT_TEMPLATE = """
Given the following list of facts, evaluate the entailment status. Assign one of the following labels to each fact:
- Yes: The fact is entailed by the summary.
- No: The fact is not entailed by the summary.
- Partial: The fact is partially entailed by the summary.

In addition, for each fact, if the entailment status is 'No' or 'Partial', assign an error type. The error type should be one of the following:
- Missing: The fact is missing from the summary.
- Incorrect: The fact is incorrect in the summary.
- Ambiguous: The fact is ambiguous in the summary.
- Other: The fact is not entailed by the summary, but does not fall into any of the above categories.

Here is the list of facts:

{facts}

And here is the patient summary:

{reference_text}

Format your response as a JSON array of objects, where each object has the following properties:
- "fact_idx": the index of the fact (as an integer)
- "entailment": "Yes", "No", or "Partial"
- "error_type": only for "No" or "Partial" entailment, one of "Missing", "Incorrect", "Ambiguous", "Other"

Example:
[
  {{"fact_idx": 0, "entailment": "Yes"}},
  {{"fact_idx": 1, "entailment": "No", "error_type": "Incorrect"}}
]
"""


class TBFactMetric(AgentReferenceBasedLLMasJudge):
    """
    Evaluates factual consistency between agent responses and reference responses.

    TBFact implements the following steps:
    1. Extracts facts from the agent's response and reference text.
    2. Evaluates entailment of the extracted facts against the reference text.
    3. Calculates precision, recall, and F1 score based on the entailment results.

    TBFact does a bi-directional evaluation:
    - pred-to-gold: Evaluates if model-generated facts are supported by the reference (precision)
    - gold-to-pred: Evaluates if reference facts are captured in the model output (recall)

    We support loading and saving reference facts to/from a JSON file with `load_reference_facts` and `save_reference_facts`.
    The expected format is:
    ```json
    {
        "patient_id_1": [
            {"fact": "Fact 1", "category": "demographics"},
            {"fact": "Fact 2", "category": "diagnosis"}
        ],
        ...
    }
    ```
    """

    @property
    def name(self) -> str:
        return f"{self.agent_name}_tbfact"

    @property
    def description(self) -> str:
        return "Evaluates factual consistency between responses and reference answers."

    @property
    def system_prompt(self) -> str:
        # This is not used in this implementation
        return ""

    @property
    def min_score(self) -> int:
        return 0

    @property
    def max_score(self) -> int:
        return 1

    def __init__(
        self,
        evaluation_llm_service,
        agent_name: str,
        reference_dir_path: str,
        context_window: int = 5,
        fact_categories: List[str] = None,
        fact_extraction_prompt_template: str = FACT_EXTRACTION_PROMPT_TEMPLATE,
        entailment_evaluation_prompt_template: str = ENTAILMENT_EVALUATION_PROMPT_TEMPLATE,
        reference_facts: Dict[str, List[Dict[str, str]]] = None
    ):
        """
        Initialize the factuality evaluator.

        Args:
            evaluation_llm_service: LLM service to use for evaluation
            agent_name: Name of the agent to evaluate
            reference_dir_path: Path to directory with reference responses
            context_window: Number of messages to include for context
            fact_categories: List of fact categories to extract
            fact_extraction_prompt_template: Template for fact extraction prompt.
                By default, we format the prompt with `fact_list` and `summary`.
            entailment_evaluation_prompt_template: Template for entailment evaluation prompt.
                By default, we format the prompt with `facts` and `reference_text`.
            reference_facts: Optional pre-extracted reference facts as a dictionary 
                mapping patient IDs to lists of fact dictionaries.
        """
        super().__init__(evaluation_llm_service, agent_name, reference_dir_path, context_window)
        self.fact_categories = fact_categories or [
            "demographics",
            "diagnosis",
            "treatment",
            "symptom",
            "biomarker",
            "other"
        ]
        self.fact_list = ", ".join(f'"{fact}"' for fact in self.fact_categories)
        self.fact_extraction_prompt_template = fact_extraction_prompt_template
        self.entailment_evaluation_prompt_template = entailment_evaluation_prompt_template
        self.reference_facts_cache = reference_facts or {}  # Initialize with provided facts or empty dict

    async def evaluate(self, chat_history: ChatHistory, patient_id: str | None = None) -> list[dict[str, Any]]:
        """
        Evaluate agent responses against reference answers, caching extracted reference facts.

        Args:
            chat_history: The chat history to evaluate
            patient_id: The ID of the patient to retrieve reference answer for

        Returns:
            List of evaluation results
        """
        if not patient_id:
            return self._create_error_result("Patient ID is required for reference-based evaluation")

        reference = self._get_reference_response(patient_id)
        if not reference:
            return self._create_error_result(f"No reference found for patient ID: {patient_id}")

        # Extract facts from reference only once and cache them if not already cached
        if patient_id not in self.reference_facts_cache:
            try:
                self.reference_facts_cache[patient_id] = await self._extract_facts(reference)
                logging.info(
                    f"Extracted {len(self.reference_facts_cache[patient_id])} facts from reference for patient {patient_id}")
            except Exception as e:
                logging.error(f"Error extracting facts from reference for patient {patient_id}: {e}")
                self.reference_facts_cache[patient_id] = []

        # Call parent method to continue evaluation
        return await super().evaluate(chat_history, patient_id)

    def load_reference_facts(self, filepath: str) -> bool:
        """
        Load reference facts from a JSON file.

        Args:
            filepath: Path to the JSON file containing reference facts

        Returns:
            True if loading was successful, False otherwise
        """
        try:
            if not os.path.exists(filepath):
                logging.error(f"Reference facts file not found: {filepath}")
                return False

            with open(filepath, 'r') as f:
                reference_facts = json.load(f)

            self.reference_facts_cache.update(reference_facts)
            logging.info(f"Successfully loaded reference facts for {len(reference_facts)} patients from {filepath}")
            return True
        except Exception as e:
            logging.error(f"Error loading reference facts from {filepath}: {e}")
            return False

    def save_reference_facts(self, filepath: str) -> bool:
        """
        Save cached reference facts to a JSON file.

        Args:
            filepath: Path where to save the reference facts JSON file

        Returns:
            True if saving was successful, False otherwise
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.reference_facts_cache, f, indent=2)

            logging.info(
                f"Successfully saved reference facts for {len(self.reference_facts_cache)} patients to {filepath}")
            return True
        except Exception as e:
            logging.error(f"Error saving reference facts to {filepath}: {e}")
            return False

    def process_rating(self, content: str) -> float:
        # Not used directly in this implementation as we calculate our own F1 score
        raise NotImplementedError("This method is not implemented in TBFactMetric.")

    def get_fact_extraction_prompt(self, summary: str) -> str:
        """
        Create a fact extraction prompt for a given summary.
        This method can be overridden by subclasses to customize the prompt.

        Args:
            summary: The text to extract facts from

        Returns:
            A formatted prompt for fact extraction
        """
        return self.fact_extraction_prompt_template.format(
            fact_list=self.fact_list,
            summary=summary
        )

    def get_entailment_evaluation_prompt(self, facts: str, reference_text: str) -> str:
        """
        Create an entailment evaluation prompt for facts against a reference text.
        This method can be overridden by subclasses to customize the prompt.

        Args:
            facts: Formatted facts to evaluate
            reference_text: Reference text to evaluate against

        Returns:
            A formatted prompt for entailment evaluation
        """
        return self.entailment_evaluation_prompt_template.format(
            facts=facts,
            reference_text=reference_text
        )

    async def _evaluate_segment(self, segment: ChatHistory, patient_id: str | None = None) -> list[dict[str, Any]]:
        """
        Evaluate a single conversation segment for factual consistency.

        Args:
            segment: A segment of chat history with agent response
            patient_id: The patient ID for reference lookup

        Returns:
            Evaluation results including precision, recall, and F1
        """
        agent_response = self._extract_agent_response(segment)
        if not agent_response:
            return self._create_error_result(f"No response from agent '{self.agent_name}' found in segment - patient id: {patient_id}")

        if patient_id not in self.reference_facts_cache:
            return self._create_error_result(f"No reference facts found for patient ID: {patient_id}")

        reference = self._current_reference

        # Step 1: Extract facts from agent response (use cached facts for reference)
        pred_facts = await self._extract_facts(agent_response)
        gold_facts = self.reference_facts_cache[patient_id]

        if not pred_facts or not gold_facts:
            return self._create_error_result(f"Failed to extract facts from one or both texts - patient id: {patient_id}")

        # Step 2: Evaluate entailment in both directions
        pred_to_gold_results = await self._evaluate_facts(pred_facts, reference)
        gold_to_pred_results = await self._evaluate_facts(gold_facts, agent_response)

        # Step 3: Calculate metrics
        metrics = self._calculate_metrics(pred_to_gold_results, gold_to_pred_results)

        # Format individual fact evaluations for details
        pred_facts_eval = [
            {
                "fact": fact["fact"],
                "category": fact["category"],
                "entailment": result["entailment"],
                "error_type": result.get("error_type"),
                "direction": "pred_to_gold"
            }
            for fact, result in zip(pred_facts, pred_to_gold_results)
        ]

        gold_facts_eval = [
            {
                "fact": fact["fact"],
                "category": fact["category"],
                "entailment": result["entailment"],
                "error_type": result.get("error_type"),
                "direction": "gold_to_pred"
            }
            for fact, result in zip(gold_facts, gold_to_pred_results)
        ]

        # Calculate per-category metrics
        category_metrics = self._calculate_category_metrics(pred_facts_eval + gold_facts_eval)

        return [{
            "score": metrics["f1"],  # Use F1 as the main score
            "explanation": f"Precision: {metrics['precision']:.3f}, Recall: {metrics['recall']:.3f}, F1: {metrics['f1']:.3f}",
            "details": {
                "patient_id": patient_id,
                "reference": reference,
                "agent_response": agent_response,
                "metrics": metrics,
                "category_metrics": category_metrics,
                "fact_evaluations": pred_facts_eval + gold_facts_eval,
            }
        }]

    async def _extract_facts(self, text: str) -> List[Dict[str, str]]:
        """
        Extract and categorize facts from text.

        Args:
            text: Text to extract facts from

        Returns:
            List of dictionaries with fact text and category
        """
        fact_extraction_prompt = self.get_fact_extraction_prompt(text)

        extraction_chat = ChatHistory()
        extraction_chat.add_system_message(
            "You are a medical fact extraction assistant. Extract facts from medical text as JSON.")
        extraction_chat.add_user_message(fact_extraction_prompt)

        response = await self.evaluation_llm_service.get_chat_message_content(
            chat_history=extraction_chat,
            settings=AzureChatPromptExecutionSettings()
        )

        content = response.content

        try:
            # Look for JSON pattern in the response
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                facts = json.loads(json_str)
                return facts
            else:
                logging.error("No JSON found in fact extraction response")
                return []
        except Exception as e:
            logging.error(f"Error parsing facts: {e}")
            return []

    async def _evaluate_facts(self, facts: List[Dict[str, str]], reference_text: str) -> List[Dict[str, str]]:
        """
        Evaluate entailment of facts against reference text.

        Args:
            facts: List of facts to evaluate
            reference_text: Reference text to check entailment against

        Returns:
            List of dictionaries with entailment judgments
        """
        if not facts:
            return []

        facts_formatted = "\n".join([f"{i}: {fact['category']}: {fact['fact']}" for i, fact in enumerate(facts)])

        entailment_prompt = self.get_entailment_evaluation_prompt(facts_formatted, reference_text)

        entailment_chat = ChatHistory()
        entailment_chat.add_system_message("You are a medical entailment evaluation assistant.")
        entailment_chat.add_user_message(entailment_prompt)

        response = await self.evaluation_llm_service.get_chat_message_content(
            chat_history=entailment_chat,
            settings=AzureChatPromptExecutionSettings()
        )

        content = response.content

        try:
            # Look for JSON pattern in the response
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                results = json.loads(json_str)
                return results
            else:
                logging.error("No JSON found in entailment evaluation response")
                return []
        except Exception as e:
            logging.error(f"Error parsing entailment results: {e}")
            return []

    def _calculate_metrics(
        self,
        pred_to_gold_results: List[Dict[str, str]],
        gold_to_pred_results: List[Dict[str, str]]
    ) -> Dict[str, float]:
        """
        Calculate precision, recall, and F1 from entailment results.

        Args:
            pred_to_gold_results: Results of evaluating predicted facts against gold
            gold_to_pred_results: Results of evaluating gold facts against predicted

        Returns:
            Dictionary with precision, recall, and F1 scores
        """
        # Convert entailment values to numerical scores
        entailment_values = {"Yes": 1.0, "Partial": 0.5, "No": 0.0}

        # Calculate precision (how many predicted facts are in gold)
        precision_values = [entailment_values.get(r.get("entailment", "No"), 0.0) for r in pred_to_gold_results]
        precision = sum(precision_values) / len(precision_values) if precision_values else 0.0

        # Calculate recall (how many gold facts are in predicted)
        recall_values = [entailment_values.get(r.get("entailment", "No"), 0.0) for r in gold_to_pred_results]
        recall = sum(recall_values) / len(recall_values) if recall_values else 0.0

        # Calculate F1
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "precision_support": len(precision_values),
            "recall_support": len(recall_values)
        }

    def _calculate_category_metrics(self, fact_evaluations: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Calculate metrics broken down by fact category.

        Args:
            fact_evaluations: List of all fact evaluations

        Returns:
            Dictionary mapping categories to their metrics
        """
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(fact_evaluations)

        # Add numerical entailment values
        df["entailment_value"] = df["entailment"].map(
            {"Yes": 1.0, "Partial": 0.5, "No": 0.0}
        )

        # Initialize results dictionary
        category_metrics = {}

        # Calculate metrics for each category
        for category in self.fact_categories:
            category_df = df[df["category"] == category]
            if len(category_df) == 0:
                continue

            p2g = category_df[category_df["direction"] == "pred_to_gold"]
            g2p = category_df[category_df["direction"] == "gold_to_pred"]

            precision = p2g["entailment_value"].mean() if len(p2g) > 0 else 0.0
            recall = g2p["entailment_value"].mean() if len(g2p) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            category_metrics[category] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "precision_support": len(p2g),
                "recall_support": len(g2p)
            }

        return category_metrics
