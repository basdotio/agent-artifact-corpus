from typing import Optional, Literal
from pydantic import BaseModel, Field

class CampaignBudgetRecord(BaseModel):
    resource_name: Optional[str] = Field(None, description="Resource name of the budget")
    amount_micros: int = Field(..., description="Daily budget in micros (e.g. 3000000 = 3.00 EUR)")
    amount_eur: float = Field(..., description="Daily budget in EUR (calculated from micros)")
    delivery_method: str = Field(default="STANDARD", description="Budget delivery method")

class GoogleCampaignRecord(BaseModel):
    id: str = Field(..., description="Unique Google Ads Campaign ID")
    resource_name: Optional[str] = Field(None, description="Campaign resource name")
    name: str = Field(..., description="Campaign name (e.g. Search - High Intent)")
    status: Literal["ENABLED", "PAUSED", "REMOVED"] = Field(..., description="Campaign serving status")
    advertising_channel_type: str = Field(default="SEARCH", description="Channel type: SEARCH, PERFORMANCE_MAX, DISPLAY")
    bidding_strategy_type: str = Field(default="TARGET_SPEND", description="Strategy: TARGET_SPEND, MANUAL_CPC, MAXIMIZE_CONVERSIONS")
    budget: Optional[CampaignBudgetRecord] = Field(None, description="Associated daily budget")
    cpc_ceiling_eur: Optional[float] = Field(None, description="Maximize Clicks (TARGET_SPEND) max CPC ceiling in EUR; None if not set or not TARGET_SPEND")

class CampaignStatusUpdateRequest(BaseModel):
    campaign_id: str = Field(..., description="ID of the campaign to modify")
    enabled: bool = Field(..., description="True to ENABLE, False to PAUSE")

class CampaignBudgetUpdateRequest(BaseModel):
    campaign_id: str = Field(..., description="ID of the campaign to modify")
    budget_eur: float = Field(..., ge=1.0, le=100.0, description="New daily budget in EUR (between 1.00 and 100.00)")

class CampaignCeilingStepRequest(BaseModel):
    campaign_id: str = Field(..., description="ID of the Maximize Clicks (TARGET_SPEND) campaign")
    direction: Literal["+0.05", "-0.05"] = Field("+0.05", description="Step the CPC ceiling up or down by 0.05 EUR")

class CampaignTargetingRecord(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID")
    campaign_name: str = Field(..., description="Campaign Name")
    target_google_search: bool = Field(default=True, description="Google Search Network")
    target_search_network: bool = Field(default=False, description="Search Partners")
    target_content_network: bool = Field(default=False, description="Display Network (Must be False for clean search)")
    targeted_locations: list[str] = Field(default_factory=list, description="Targeted geo constants (e.g. Germany 2276, Austria 2040)")
    excluded_locations: list[str] = Field(default_factory=list, description="Excluded geo constants")
    targeted_languages: list[str] = Field(default_factory=list, description="Targeted language constants (e.g. German 1001)")
    ad_schedules: list[str] = Field(default_factory=list, description="Dayparting ad schedules (e.g. 08:00 - 01:00)")
    device_modifiers: list[str] = Field(default_factory=list, description="Device bid adjustments")

class ChangeEventRecord(BaseModel):
    changed_at: str = Field(..., description="Change time in account time zone")
    client_type: str = Field(..., description="Who made it: GOOGLE_ADS_WEB_CLIENT (UI), GOOGLE_ADS_API, GOOGLE_ADS_AUTOMATED_RULE, ...")
    user_email: Optional[str] = Field(None, description="Google account that made the change")
    resource_type: str = Field(..., description="CAMPAIGN, AD_GROUP, CAMPAIGN_CRITERION, AD_GROUP_AD, CAMPAIGN_BUDGET, ...")
    operation: str = Field(..., description="CREATE, UPDATE or REMOVE")
    campaign_name: Optional[str] = Field(None, description="Campaign the change belongs to")
    resource_name: str = Field(..., description="Changed resource")
    keyword: Optional[str] = Field(None, description="Keyword text for keyword criteria, marked (negative) for negatives")
    changes: list[str] = Field(default_factory=list, description="Changed fields as 'path: old -> new'")

class IdArguments(BaseModel):
    """
    IDs a read tool puts into its GAQL query. Only digits: a name or text in place of an ID used to reach Google as a
    query (query_error.BAD_NUMBER, 05.10.2026) and could change the query itself.
    """
    campaign_id: Optional[str] = Field(None, pattern=r"^\d{1,20}$", description="Numeric campaign ID, e.g. 24103530881 (get_campaigns lists them)")
    ad_group_id: Optional[str] = Field(None, pattern=r"^\d{1,20}$", description="Numeric ad group ID, e.g. 201418406040 (get_ad_groups lists them)")
