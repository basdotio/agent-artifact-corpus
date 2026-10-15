"""
Implements the Strategy pattern for different search methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from loguru import logger
from qdrant_client import models

if TYPE_CHECKING:
    from fegis.storage import QdrantStorage

__all__ = [
    "SearchType",
    "FilterValidator",
    "ConditionBuilder",
    "SearchStrategy",
    "BasicSearchStrategy",
    "FilteredSearchStrategy",
    "ByIdSearchStrategy",
]

# Mapping of API field names to payload keys in Qdrant
FIELD_MAPPING = {
    "agent_id": "meta.agent_id",
    "archetype_title": "meta.archetype_title",
    "archetype_version": "meta.archetype_version",
    "schema_version": "meta.schema_version",
}

# Valid operators and fields for filter validation
VALID_OPERATORS = {
    "is",
    "is_not",
    "contains",
    "after",
    "before",
    "between",
    "any_of",
}

VALID_FIELDS = {
    "session_id",
    "tool",
    "agent_id",
    "title",
    "context",
    "sequence_order",
    "memory_id",
    "timestamp",
    "preceding_memory_id",
    "archetype_title",
    "archetype_version",
    "schema_version",
}

# Performance optimization - cache sorted lists for error messages
_SORTED_VALID_FIELDS = sorted(VALID_FIELDS)
_SORTED_VALID_OPERATORS = sorted(VALID_OPERATORS)

# Constants for magic numbers
EXACT_MATCH_SCORE = 1.0


class SearchType(str, Enum):
    """Available search strategies."""

    BASIC = "basic"
    FILTERED = "filtered"
    BY_MEMORY_ID = "by_memory_id"


class FilterValidator:
    """Handles validation of search filter parameters."""

    def validate_filters(self, filters: list[dict[str, Any]]) -> None:
        """Check filter field names, operators, and required parameters."""
        for i, filter_spec in enumerate(filters):
            self._validate_required_fields(filter_spec, i)
            self._validate_field_name(filter_spec["field"], i)
            self._validate_operator(filter_spec["operator"], i)
            self._validate_timestamp_format(
                filter_spec["field"], filter_spec["operator"], filter_spec["value"], i
            )

    def _validate_required_fields(
        self, filter_spec: dict[str, Any], index: int
    ) -> None:
        """Check that all required fields are present in the filter."""
        if "field" not in filter_spec:
            raise ValueError(
                f"Filter at index {index}: missing required 'field' parameter"
            )
        if "operator" not in filter_spec:
            raise ValueError(
                f"Filter at index {index}: missing required 'operator' parameter"
            )
        if "value" not in filter_spec:
            raise ValueError(
                f"Filter at index {index}: missing required 'value' parameter"
            )

    def _validate_field_name(self, field: str, index: int) -> None:
        """Validate that the field name is allowed."""
        if field not in VALID_FIELDS:
            raise ValueError(
                f"Filter at index {index}: invalid field '{field}'. Valid fields: {_SORTED_VALID_FIELDS}"
            )

    def _validate_operator(self, operator: str, index: int) -> None:
        """Validate that the operator is allowed."""
        if operator not in VALID_OPERATORS:
            raise ValueError(
                f"Filter at index {index}: invalid operator '{operator}'. Valid operators: {_SORTED_VALID_OPERATORS}"
            )

    def _validate_timestamp_format(
        self, field: str, operator: str, value: Any, index: int
    ) -> None:
        """Validate timestamp format for timestamp fields."""
        if field == "timestamp" and operator in ["after", "before"]:
            if not isinstance(value, str):
                raise ValueError(
                    f"Filter at index {index}: timestamp value must be string in ISO format"
                )
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(
                    f"Filter at index {index}: invalid timestamp format '{value}'. Use ISO format (e.g., '2024-01-01T00:00:00Z')"
                ) from e


class ConditionBuilder:
    """Handles building Qdrant filter conditions from validated filter specifications."""

    def build_filter(self, filters: list[dict[str, Any]]) -> models.Filter | None:
        """Convert filter parameters into Qdrant filter conditions."""
        if not filters:
            return None

        must_conditions = []

        for filter_spec in filters:
            field = filter_spec["field"]
            operator = filter_spec["operator"]
            value = filter_spec["value"]

            # Map field names to Qdrant payload paths
            field_key = self._map_field_to_key(field)

            # Build condition based on operator
            condition = self._build_condition(field_key, operator, value)
            if condition is None:
                raise ValueError(
                    f"Failed to build condition for field '{field}' with operator '{operator}' and value '{value}'"
                )
            must_conditions.append(condition)

        return models.Filter(must=must_conditions) if must_conditions else None

    def _map_field_to_key(self, field: str) -> str:
        """Map schema field names to Qdrant payload keys."""
        return FIELD_MAPPING.get(field, field)

    def _build_condition(
        self, field_key: str, operator: str, value
    ) -> models.Condition | None:
        """Build a Qdrant condition from instructional operator and value."""
        logger.info(
            f"Building condition: field_key={field_key}, operator={operator}, value={value}"
        )
        try:
            match operator:
                case "is":
                    return models.FieldCondition(
                        key=field_key, match=models.MatchValue(value=value)
                    )
                case "is_not":
                    return models.FieldCondition(
                        key=field_key, match=models.MatchExcept(**{"except": [value]})
                    )
                case "before" | "after":
                    return self._build_range_condition_for_operator(
                        field_key, operator, value
                    )
                case "between":
                    return self._build_range_condition(field_key, value)
                case "contains":
                    return self._build_contains_condition(field_key, value)
                case "any_of":
                    return self._build_array_condition(field_key, value)
                case _:
                    logger.warning(f"Unknown operator: {operator}")
                    return None
        except Exception as e:
            logger.error(f"Error building {operator} condition: {e}")
            raise e  # Re-raise to see the actual error

    def _build_range_condition_for_operator(
        self, field_key: str, operator: str, value
    ) -> models.Condition:
        """Builds a range condition for 'before' or 'after' operators."""
        range_operator = "lt" if operator == "before" else "gt"

        if field_key == "timestamp":
            if not isinstance(value, str):
                raise ValueError(
                    f"Expected string for timestamp, got {type(value)}: {value}"
                )
            dt_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return models.FieldCondition(
                key=field_key, range=models.DatetimeRange(**{range_operator: dt_value})
            )
        else:
            return models.FieldCondition(
                key=field_key, range=models.Range(**{range_operator: value})
            )

    def _build_range_condition(self, field_key: str, value) -> models.Condition:
        """Build range condition with validation."""
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("'between' operator requires array [min, max]")

        if field_key == "timestamp":
            dt_start = datetime.fromisoformat(value[0].replace("Z", "+00:00"))
            dt_end = datetime.fromisoformat(value[1].replace("Z", "+00:00"))
            return models.FieldCondition(
                key=field_key, range=models.DatetimeRange(gte=dt_start, lte=dt_end)
            )

        return models.FieldCondition(
            key=field_key, range=models.Range(gte=value[0], lte=value[1])
        )

    def _build_array_condition(self, field_key: str, value) -> models.Condition:
        """Build array condition with validation."""
        if not isinstance(value, list):
            raise ValueError("'any_of' operator requires array")
        return models.FieldCondition(key=field_key, match=models.MatchAny(any=value))

    def _build_contains_condition(self, field_key: str, value) -> models.Condition:
        """Build contains condition with case-insensitive and fuzzy matching."""
        if not isinstance(value, str):
            # For non-string values, use exact text matching
            return models.FieldCondition(
                key=field_key, match=models.MatchText(text=str(value))
            )

        # Build search variants and remove duplicates
        variants = {value, value.lower(), value.capitalize()}
        conditions = [
            models.FieldCondition(key=field_key, match=models.MatchText(text=v))
            for v in variants
        ]

        # Return single condition directly for efficiency
        if len(variants) == 1:
            return conditions[0]

        return models.Filter(should=conditions)


class SearchStrategy(ABC):
    """Abstract base class for a search strategy."""

    def __init__(self, storage: QdrantStorage):
        self.storage = storage
        self.validator = FilterValidator()
        self.condition_builder = ConditionBuilder()

    @abstractmethod
    async def search(self, params: dict[str, Any]) -> list[models.ScoredPoint]:
        """Executes a search query and returns a list of ScoredPoint objects."""
        pass

    def _build_structured_filter(self, params: dict[str, Any]) -> models.Filter | None:
        """Convert filter parameters into Qdrant filter conditions."""
        filters = params.get("filters", [])
        if not filters:
            return None
        self.validator.validate_filters(filters)
        return self.condition_builder.build_filter(filters)


class BasicSearchStrategy(SearchStrategy):
    """Basic semantic search using hybrid vector similarity."""

    async def search(self, params: dict[str, Any]) -> list[models.ScoredPoint]:
        logger.info(f"Performing basic search for: '{params['query']}'")
        return await self.storage.client.query(
            collection_name=self.storage.collection_name,
            query_text=params["query"],
            query_filter=self._build_structured_filter(params),
            limit=params["limit"],
        )


class FilteredSearchStrategy(SearchStrategy):
    """Filtered search using structured query filters."""

    async def search(self, params: dict[str, Any]) -> list[models.ScoredPoint]:
        query = params["query"]
        filters = params["filters"]
        limit = params["limit"]

        logger.info(f"Performing filtered search with {len(filters)} filters")

        # Always use semantic query (even with empty string for consistent scoring)
        return await self.storage.client.query(
            collection_name=self.storage.collection_name,
            query_text=query,  # Use empty string if no query provided
            query_filter=self._build_structured_filter(params),
            limit=limit,
        )


class ByIdSearchStrategy(SearchStrategy):
    """Retrieves specific memory by UUID."""

    async def search(self, params: dict[str, Any]) -> list[models.ScoredPoint]:
        memory_id = params["query"]
        logger.info(f"Retrieving memory by ID: {memory_id}")

        points = await self.storage.client.retrieve(
            collection_name=self.storage.collection_name,
            ids=[memory_id],
            with_payload=True,
            with_vectors=False,
        )

        # Convert to ScoredPoint format for consistency
        scored_points = []
        for point in points:
            scored_point = models.ScoredPoint(
                id=point.id,
                version=0,
                score=EXACT_MATCH_SCORE,
                payload=point.payload,
                vector=None,
            )
            scored_points.append(scored_point)

        return scored_points
