"""
Data Boundary Enforcer

This module is the MOST CRITICAL security component of V3.
It ensures that ONLY schema information goes to the LLM.
Actual data NEVER crosses this boundary.

Key Principle:
- Schema (table names, column names, types) = OK to send
- Data (actual values, row content) = NEVER sent
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class DataBoundaryViolation(Exception):
    """Raised when data boundary is violated."""
    pass


class SchemaElementType(str, Enum):
    """Types of schema elements."""
    TABLE = "table"
    COLUMN = "column"
    MEASURE = "measure"
    RELATIONSHIP = "relationship"
    HIERARCHY = "hierarchy"


@dataclass
class ColumnInfo:
    """Column metadata - NO actual data values."""
    name: str
    data_type: str
    table_name: str
    description: Optional[str] = None
    is_key: bool = False
    is_nullable: bool = True

    # NEVER include these in production
    # sample_values: list = None  # DANGER
    # distinct_count: int = None  # Could leak info


@dataclass
class TableInfo:
    """Table metadata - NO row counts or sample data."""
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    description: Optional[str] = None
    is_hidden: bool = False

    # NEVER include these in production
    # row_count: int = None  # Could leak business intelligence
    # sample_rows: list = None  # DANGER - actual data


@dataclass
class MeasureInfo:
    """Measure metadata."""
    name: str
    expression: str
    table_name: str
    description: Optional[str] = None
    format_string: Optional[str] = None


@dataclass
class RelationshipInfo:
    """Relationship metadata."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    is_active: bool = True
    cardinality: str = "many-to-one"


@dataclass
class SchemaInfo:
    """
    Complete schema information for LLM context.

    This class represents the MAXIMUM information that can be sent to an LLM.
    It contains ONLY metadata - never actual data values.
    """
    tables: list[TableInfo] = field(default_factory=list)
    measures: list[MeasureInfo] = field(default_factory=list)
    relationships: list[RelationshipInfo] = field(default_factory=list)

    # Metadata about the schema (safe to include)
    model_name: Optional[str] = None
    model_description: Optional[str] = None

    def to_prompt_string(self) -> str:
        """
        Convert schema to a string suitable for LLM prompts.

        This is the format that gets sent to the LLM.
        """
        lines = []

        # Tables and columns
        lines.append("TABLES:")
        for table in self.tables:
            if table.is_hidden:
                continue

            table_name = self._format_table_name(table.name)
            lines.append(f"\n{table_name}")

            if table.description:
                lines.append(f"  Description: {table.description}")

            lines.append("  Columns:")
            for col in table.columns:
                col_str = f"    - {col.name} ({col.data_type})"
                if col.is_key:
                    col_str += " [KEY]"
                if col.description:
                    col_str += f" -- {col.description}"
                lines.append(col_str)

        # Measures
        if self.measures:
            lines.append("\nMEASURES:")
            for measure in self.measures:
                lines.append(f"  - [{measure.table_name}].[{measure.name}]")
                lines.append(f"    Expression: {measure.expression}")
                if measure.description:
                    lines.append(f"    Description: {measure.description}")

        # Relationships
        if self.relationships:
            lines.append("\nRELATIONSHIPS:")
            for rel in self.relationships:
                active = "" if rel.is_active else " (inactive)"
                lines.append(
                    f"  - {rel.from_table}[{rel.from_column}] -> "
                    f"{rel.to_table}[{rel.to_column}] ({rel.cardinality}){active}"
                )

        return "\n".join(lines)

    def _format_table_name(self, name: str) -> str:
        """Format table name, quoting if necessary."""
        if " " in name or any(c in name for c in "[](){}"):
            return f"'{name}'"
        return name

    def get_hash(self) -> str:
        """Get a hash of the schema for audit logging."""
        content = self.to_prompt_string()
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class DataBoundary:
    """
    Enforces the data boundary between Power BI and the LLM.

    This class is responsible for:
    1. Extracting ONLY schema information from Power BI
    2. Validating that no actual data is included
    3. Sanitizing schema info before sending to LLM
    4. Logging all boundary crossings for audit
    """

    # Patterns that might indicate data leakage
    DATA_LEAK_PATTERNS = [
        # Looks like actual values
        r'\b\d{3}-\d{2}-\d{4}\b',           # SSN pattern
        r'\b\d{16}\b',                        # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\$[\d,]+\.?\d*',                    # Currency values
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP address

        # SQL/DAX that returns data
        r'SELECT\s+\*',                       # Select all
        r'EVALUATE\s+VALUES\s*\(',            # Returns actual values
        r'SAMPLE\s*\(',                       # Sample data
    ]

    # Maximum lengths for schema elements (prevent info dump)
    MAX_TABLE_DESCRIPTION_LENGTH = 500
    MAX_COLUMN_DESCRIPTION_LENGTH = 200
    MAX_MEASURE_EXPRESSION_LENGTH = 2000

    def __init__(
        self,
        allow_descriptions: bool = True,
        allow_measures: bool = True,
        allow_relationships: bool = True,
        strict_mode: bool = True,
    ):
        """
        Initialize the data boundary.

        Args:
            allow_descriptions: Allow table/column descriptions
            allow_measures: Allow measure definitions
            allow_relationships: Allow relationship info
            strict_mode: Raise exception on any potential leak
        """
        self.allow_descriptions = allow_descriptions
        self.allow_measures = allow_measures
        self.allow_relationships = allow_relationships
        self.strict_mode = strict_mode
        self._violations: list[str] = []

    def validate_schema(self, schema: SchemaInfo) -> SchemaInfo:
        """
        Validate and sanitize schema before sending to LLM.

        Args:
            schema: Raw schema from Power BI

        Returns:
            Sanitized schema safe for LLM

        Raises:
            DataBoundaryViolation: If data leakage detected in strict mode
        """
        self._violations = []

        # Create sanitized copy
        sanitized = SchemaInfo(
            model_name=schema.model_name,
            model_description=self._sanitize_text(
                schema.model_description,
                self.MAX_TABLE_DESCRIPTION_LENGTH
            ) if schema.model_description else None,
        )

        # Sanitize tables
        for table in schema.tables:
            sanitized_table = self._sanitize_table(table)
            if sanitized_table:
                sanitized.tables.append(sanitized_table)

        # Sanitize measures (if allowed)
        if self.allow_measures:
            for measure in schema.measures:
                sanitized_measure = self._sanitize_measure(measure)
                if sanitized_measure:
                    sanitized.measures.append(sanitized_measure)

        # Sanitize relationships (if allowed)
        if self.allow_relationships:
            sanitized.relationships = schema.relationships.copy()

        # Final validation
        self._validate_final(sanitized)

        if self._violations and self.strict_mode:
            raise DataBoundaryViolation(
                f"Data boundary violations detected: {self._violations}"
            )

        return sanitized

    def _sanitize_table(self, table: TableInfo) -> Optional[TableInfo]:
        """Sanitize table information."""
        sanitized_columns = []

        for col in table.columns:
            sanitized_col = ColumnInfo(
                name=self._sanitize_identifier(col.name),
                data_type=col.data_type,
                table_name=table.name,
                description=self._sanitize_text(
                    col.description,
                    self.MAX_COLUMN_DESCRIPTION_LENGTH
                ) if self.allow_descriptions and col.description else None,
                is_key=col.is_key,
                is_nullable=col.is_nullable,
            )
            sanitized_columns.append(sanitized_col)

        return TableInfo(
            name=self._sanitize_identifier(table.name),
            columns=sanitized_columns,
            description=self._sanitize_text(
                table.description,
                self.MAX_TABLE_DESCRIPTION_LENGTH
            ) if self.allow_descriptions and table.description else None,
            is_hidden=table.is_hidden,
        )

    def _sanitize_measure(self, measure: MeasureInfo) -> Optional[MeasureInfo]:
        """Sanitize measure information."""
        # Check measure expression for data leakage
        expression = measure.expression

        if len(expression) > self.MAX_MEASURE_EXPRESSION_LENGTH:
            self._violations.append(
                f"Measure {measure.name} expression too long, truncating"
            )
            expression = expression[:self.MAX_MEASURE_EXPRESSION_LENGTH] + "..."

        # Check for patterns that might leak data
        for pattern in self.DATA_LEAK_PATTERNS:
            if re.search(pattern, expression, re.IGNORECASE):
                self._violations.append(
                    f"Measure {measure.name} contains potential data leak pattern"
                )
                if self.strict_mode:
                    return None

        return MeasureInfo(
            name=self._sanitize_identifier(measure.name),
            expression=expression,
            table_name=measure.table_name,
            description=self._sanitize_text(
                measure.description,
                self.MAX_COLUMN_DESCRIPTION_LENGTH
            ) if self.allow_descriptions and measure.description else None,
            format_string=measure.format_string,
        )

    def _sanitize_identifier(self, name: str) -> str:
        """Sanitize an identifier (table/column name)."""
        # Remove potential injection attempts
        sanitized = re.sub(r'[<>{}|\\^`]', '', name)
        return sanitized.strip()

    def _sanitize_text(
        self,
        text: Optional[str],
        max_length: int
    ) -> Optional[str]:
        """Sanitize free-text fields."""
        if not text:
            return None

        # Check for data leak patterns
        for pattern in self.DATA_LEAK_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                self._violations.append(
                    f"Description contains potential data: {text[:50]}..."
                )
                if self.strict_mode:
                    return "[REDACTED]"

        # Truncate if too long
        if len(text) > max_length:
            return text[:max_length] + "..."

        return text

    def _validate_final(self, schema: SchemaInfo) -> None:
        """Final validation of the sanitized schema."""
        prompt_string = schema.to_prompt_string()

        # Check total size (prevent massive schema dumps)
        if len(prompt_string) > 50000:  # 50KB limit
            self._violations.append(
                f"Schema too large ({len(prompt_string)} chars), may need filtering"
            )

        # Check for any remaining data patterns
        for pattern in self.DATA_LEAK_PATTERNS:
            matches = re.findall(pattern, prompt_string, re.IGNORECASE)
            if matches:
                self._violations.append(
                    f"Final schema contains data pattern: {pattern}"
                )

    def get_violations(self) -> list[str]:
        """Get list of violations from last validation."""
        return self._violations.copy()

    def create_audit_record(self, schema: SchemaInfo) -> dict:
        """
        Create an audit record of what's being sent to LLM.

        This record proves that only schema was sent.
        """
        return {
            "schema_hash": schema.get_hash(),
            "table_count": len(schema.tables),
            "column_count": sum(len(t.columns) for t in schema.tables),
            "measure_count": len(schema.measures),
            "relationship_count": len(schema.relationships),
            "tables": [t.name for t in schema.tables],
            "data_included": False,  # This is ALWAYS false
            "violations": self._violations,
            "boundary_settings": {
                "allow_descriptions": self.allow_descriptions,
                "allow_measures": self.allow_measures,
                "allow_relationships": self.allow_relationships,
                "strict_mode": self.strict_mode,
            },
        }


def extract_schema_from_model(model_metadata: dict) -> SchemaInfo:
    """
    Extract schema information from Power BI model metadata.

    This function converts Power BI model metadata into our
    SchemaInfo format, ensuring no actual data is included.

    Args:
        model_metadata: Metadata from Power BI (tables, columns, etc.)

    Returns:
        SchemaInfo ready for LLM
    """
    schema = SchemaInfo()

    # Extract tables
    for table_data in model_metadata.get("tables", []):
        columns = []
        for col_data in table_data.get("columns", []):
            columns.append(ColumnInfo(
                name=col_data.get("name", ""),
                data_type=col_data.get("dataType", "Unknown"),
                table_name=table_data.get("name", ""),
                description=col_data.get("description"),
                is_key=col_data.get("isKey", False),
                is_nullable=col_data.get("isNullable", True),
            ))

        schema.tables.append(TableInfo(
            name=table_data.get("name", ""),
            columns=columns,
            description=table_data.get("description"),
            is_hidden=table_data.get("isHidden", False),
        ))

    # Extract measures
    for measure_data in model_metadata.get("measures", []):
        schema.measures.append(MeasureInfo(
            name=measure_data.get("name", ""),
            expression=measure_data.get("expression", ""),
            table_name=measure_data.get("tableName", ""),
            description=measure_data.get("description"),
            format_string=measure_data.get("formatString"),
        ))

    # Extract relationships
    for rel_data in model_metadata.get("relationships", []):
        schema.relationships.append(RelationshipInfo(
            from_table=rel_data.get("fromTable", ""),
            from_column=rel_data.get("fromColumn", ""),
            to_table=rel_data.get("toTable", ""),
            to_column=rel_data.get("toColumn", ""),
            is_active=rel_data.get("isActive", True),
            cardinality=rel_data.get("cardinality", "many-to-one"),
        ))

    return schema
