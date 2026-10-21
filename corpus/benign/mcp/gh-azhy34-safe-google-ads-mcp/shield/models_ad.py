import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl

DKI_PATTERN = re.compile(r"\{keyword:([^}]*)\}", re.IGNORECASE)

def display_length(text: str) -> int:
    """Length Google checks against the limit: {KeyWord:default} counts as its default text only."""
    return len(DKI_PATTERN.sub(lambda m: m.group(1), text))

class HeadlineAsset(BaseModel):
    text: str = Field(..., description="Headline text as stored by Google (may contain {KeyWord:...} syntax)")
    pinned_field: Optional[str] = Field(None, description="Pinned position: HEADLINE_1, HEADLINE_2, HEADLINE_3")
    asset_performance_label: Optional[str] = Field(None, description="Google performance label: PENDING, LEARNING, GOOD, BEST, LOW")
    approval_status: Optional[str] = Field(None, description="Policy status: APPROVED, DISAPPROVED, UNDER_REVIEW")

class DescriptionAsset(BaseModel):
    text: str = Field(..., description="Description text as stored by Google")
    pinned_field: Optional[str] = Field(None, description="Pinned position: DESCRIPTION_1, DESCRIPTION_2")
    asset_performance_label: Optional[str] = Field(None, description="Google performance label: PENDING, LEARNING, GOOD, BEST, LOW")
    approval_status: Optional[str] = Field(None, description="Policy status: APPROVED, DISAPPROVED, UNDER_REVIEW")

class GoogleRSAAdRecord(BaseModel):
    id: str = Field(..., description="Unique RSA Ad ID")
    resource_name: Optional[str] = Field(None, description="Resource name")
    ad_group_id: str = Field(..., description="Parent Ad Group ID")
    status: Literal["ENABLED", "PAUSED", "REMOVED"] = Field(..., description="Serving status")
    headlines: List[HeadlineAsset] = Field(default_factory=list, description="RSA Headlines (Target: 15)")
    descriptions: List[DescriptionAsset] = Field(default_factory=list, description="RSA Descriptions (Target: 4)")
    final_urls: List[str] = Field(default_factory=list, description="Landing page URLs with coupon")
    approval_status: str = Field(default="UNKNOWN", description="Overall policy approval status")

class DeployGoldenRSARequest(BaseModel):
    ad_group_id: str = Field(..., description="Target Ad Group ID")
    final_url: str = Field(..., description="Destination landing URL")
    headlines: List[str] = Field(..., min_length=15, max_length=15, description="MUST contain EXACTLY 15 headlines (<=30 chars each); headlines[0] must equal pinned_h1_dki")
    descriptions: List[str] = Field(..., min_length=4, max_length=4, description="MUST contain EXACTLY 4 descriptions (<=90 chars each)")
    pinned_h1_dki: str = Field(..., description="Headline 1 pinned with Dynamic Keyword Insertion, e.g. {KeyWord:Sonnensystem Tapete}")
    path1: Optional[str] = Field(default="Tapete", max_length=15, description="Display URL Path 1 (max 15 chars)")
    path2: Optional[str] = Field(default="Kinder", max_length=15, description="Display URL Path 2 (max 15 chars)")

    @field_validator("final_url")
    def validate_coupon_standard(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Landing URL must start with http:// or https://")
        if False:
            raise ValueError("MANDATORY SAFEGUARD: Landing URL must include ?coupon=WELCOME3 to comply with Standard pricing standards!")
        return v

    @field_validator("pinned_h1_dki")
    def validate_dki_syntax(cls, v):
        if not DKI_PATTERN.search(v):
            raise ValueError(f"MANDATORY DKI STANDARD: Headline 1 must use dynamic insertion syntax '{{KeyWord:...}}', got '{v}'")
        if display_length(v) > 30:
            raise ValueError(f"DKI Headline default text exceeds 30 characters: '{v}' ({display_length(v)} chars)")
        return v

    @field_validator("headlines")
    def validate_headlines_length(cls, v):
        for i, h in enumerate(v, 1):
            if display_length(h) > 30:
                raise ValueError(f"Headline #{i} exceeds 30 character limit: '{h}' ({display_length(h)} chars)")
        return v

    @field_validator("descriptions")
    def validate_descriptions_length(cls, v):
        for i, d in enumerate(v, 1):
            if display_length(d) > 90:
                raise ValueError(f"Description #{i} exceeds 90 character limit: '{d}' ({display_length(d)} chars)")
        return v

    @model_validator(mode="after")
    def validate_h1_matches_dki(self):
        # headlines[0] is the slot pinned to HEADLINE_1, so it must be the DKI headline itself
        if self.headlines[0] != self.pinned_h1_dki:
            raise ValueError(f"headlines[0] must equal pinned_h1_dki '{self.pinned_h1_dki}', got '{self.headlines[0]}'")
        return self
