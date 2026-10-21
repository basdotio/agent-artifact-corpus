from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class KeywordCriterionRecord(BaseModel):
    criterion_id: str = Field(..., description="Unique criterion ID")
    resource_name: Optional[str] = Field(None, description="Resource name")
    ad_group_id: Optional[str] = Field(None, description="Parent Ad Group ID")
    text: str = Field(..., description="Keyword text")
    match_type: Literal["EXACT", "PHRASE", "BROAD"] = Field(..., description="Match type")
    negative: bool = Field(default=False, description="True if negative keyword")
    status: Literal["ENABLED", "PAUSED", "REMOVED"] = Field(default="ENABLED", description="Serving status")

class SearchTermWasteRecord(BaseModel):
    search_term: str = Field(..., description="Actual query searched by user")
    clicks: int = Field(default=0, description="Total clicks")
    impressions: int = Field(default=0, description="Total impressions")
    cost_micros: int = Field(default=0, description="Total spend in micros")
    cost_eur: float = Field(default=0.0, description="Total spend in EUR")
    ctr_percent: float = Field(default=0.0, description="Click-through rate %")
    suggested_negative_action: Optional[str] = Field(None, description="EXACT or PHRASE negative recommendation")

class RemoveNegativeKeywordRequest(BaseModel):
    campaign_id: str = Field(..., pattern=r"^\d+$", description="Campaign ID")
    keyword_text: str = Field(..., min_length=1, description="Exact text of the campaign negative keyword")
    match_type: Optional[Literal["EXACT", "PHRASE", "BROAD"]] = Field(None, description="Required when the same text exists with several match types")

class ApplyNegativeShieldRequest(BaseModel):
    campaign_id: str = Field(..., description="Target Campaign ID")
    language: Literal["de", "fr", "es"] = Field(..., description="Target language shield")
    negative_words: Optional[List[str]] = Field(default=None, description="Optional custom negative words to append")
