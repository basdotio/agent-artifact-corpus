from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

class GoogleAdGroupRecord(BaseModel):
    id: str = Field(..., description="Ad Group ID")
    resource_name: Optional[str] = Field(None, description="Resource name")
    campaign_id: str = Field(..., description="Parent Campaign ID")
    name: str = Field(..., description="Ad Group Name (e.g. Space - Sonnensystem, Berge, Jungle)")
    status: Literal["ENABLED", "PAUSED", "REMOVED"] = Field(..., description="Serving status")
    type: str = Field(default="SEARCH_STANDARD", description="Ad Group Type")
    cpc_bid_micros: int = Field(default=0, description="Base CPC bid in micros (e.g. 600000 = 0.60 EUR)")
    cpc_bid_eur: float = Field(default=0.0, description="Base CPC bid in EUR")

class AdGroupBidUpdateRequest(BaseModel):
    ad_group_id: str = Field(..., description="Ad Group ID to update")
    new_bid_eur: float = Field(..., ge=0.05, le=3.00, description="New CPC bid in EUR (Safeguard ceiling: 3.00 EUR). MANUAL_CPC campaigns only.")
    
    @field_validator("new_bid_eur")
    def validate_bid_step(cls, v):
        # Round to 2 decimal places to prevent float rounding noise
        rounded = round(v, 2)
        if rounded <= 0.01:
            raise ValueError("CRITICAL SAFEGUARD: CPC bid <= 0.01 EUR is blocked to prevent accidental fallback bug!")
        return rounded

class KeywordStatusUpdateRequest(BaseModel):
    ad_group_id: str = Field(..., pattern=r"^\d+$", description="Ad Group ID of the keyword")
    criterion_id: str = Field(..., pattern=r"^\d+$", description="Keyword criterion ID (from get_ad_group_keywords)")
    enabled: bool = Field(..., description="True to ENABLE, False to PAUSE")

class AdGroupKeywordRecord(BaseModel):
    criterion_id: str = Field(..., description="Criterion ID")
    ad_group_id: str = Field(..., description="Parent Ad Group ID")
    keyword_text: str = Field(..., description="Keyword query text")
    match_type: str = Field(..., description="EXACT, PHRASE, BROAD")
    status: str = Field(..., description="ENABLED, PAUSED, REMOVED")
    cpc_bid_eur: Optional[float] = Field(None, description="Keyword-level override bid in EUR (None if inherited from AdGroup)")
    quality_score: Optional[int] = Field(None, description="Google Quality Score (1-10)")
    search_predicted_ctr: Optional[str] = Field(None, description="BELOW_AVERAGE, AVERAGE, ABOVE_AVERAGE")
    creative_quality_score: Optional[str] = Field(None, description="Ad Relevance evaluation")
    post_click_quality_score: Optional[str] = Field(None, description="Landing Page Experience evaluation")
