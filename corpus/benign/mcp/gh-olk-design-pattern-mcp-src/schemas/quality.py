"""Quality metrics model: the catalog's eight scoring axes aggregated to one design (0–10).

Attribute scale matches the catalog records (``pattern/*.json`` ``quality_attributes`` are
0–10 integers in the source document), so an aggregate is directly comparable to a record.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QualityMetrics(BaseModel):
    """Aggregated design quality across the eight scoring axes (§2.1), each 0–10.

    Built by averaging the applied patterns' catalog ``quality_attributes`` — traceable
    to catalog data, never invented (§11 item 1).
    """

    testability: float = Field(default=0.0, ge=0.0, le=10.0, description="Testability")
    extensibility: float = Field(default=0.0, ge=0.0, le=10.0, description="Extensibility")
    maintainability: float = Field(default=0.0, ge=0.0, le=10.0, description="Maintainability")
    simplicity: float = Field(default=0.0, ge=0.0, le=10.0, description="Simplicity")
    performance: float = Field(default=0.0, ge=0.0, le=10.0, description="Performance")
    reliability: float = Field(default=0.0, ge=0.0, le=10.0, description="Reliability")
    security: float = Field(default=0.0, ge=0.0, le=10.0, description="Security")
    scalability: float = Field(default=0.0, ge=0.0, le=10.0, description="Scalability")
