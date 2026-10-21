import sys
from pathlib import Path
from typing import List, Optional
from google.api_core import protobuf_helpers

# Add root of google-ads to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.client import get_ads_client, eur_to_micros
from core.config import CUSTOMER_ID
from shield.error_shield import ServiceResult, handle_google_ads_errors
from shield.models_campaign import (
    GoogleCampaignRecord, CampaignBudgetRecord, 
    CampaignStatusUpdateRequest, CampaignBudgetUpdateRequest,
    CampaignTargetingRecord, CampaignCeilingStepRequest
)

CEILING_MIN_MICROS = 100_000    # 0.10 EUR
CEILING_MAX_MICROS = 3_000_000  # 3.00 EUR

def _ceiling_eur(c) -> Optional[float]:
    """Maximize Clicks CPC ceiling in EUR, None when uncapped or not TARGET_SPEND."""
    micros = c.target_spend.cpc_bid_ceiling_micros
    return round(micros / 1_000_000.0, 2) if micros else None

@handle_google_ads_errors
def list_campaigns(customer_id: str = CUSTOMER_ID) -> List[GoogleCampaignRecord]:
    """
    Queries all non-removed campaigns and returns typed GoogleCampaignRecord models.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.target_spend.cpc_bid_ceiling_micros,
            campaign_budget.resource_name,
            campaign_budget.amount_micros,
            campaign_budget.delivery_method
        FROM campaign
        WHERE campaign.status != 'REMOVED'
        ORDER BY campaign.name ASC
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    
    results = []
    for row in response:
        c = row.campaign
        b = row.campaign_budget
        budget_rec = None
        if b and b.amount_micros:
            budget_rec = CampaignBudgetRecord(
                resource_name=b.resource_name,
                amount_micros=b.amount_micros,
                amount_eur=round(b.amount_micros / 1_000_000.0, 2),
                delivery_method=b.delivery_method.name if hasattr(b.delivery_method, "name") else str(b.delivery_method)
            )
        
        status_name = c.status.name if hasattr(c.status, "name") else str(c.status)
        channel_name = c.advertising_channel_type.name if hasattr(c.advertising_channel_type, "name") else str(c.advertising_channel_type)
        bidding_name = c.bidding_strategy_type.name if hasattr(c.bidding_strategy_type, "name") else str(c.bidding_strategy_type)
        
        results.append(GoogleCampaignRecord(
            id=str(c.id),
            resource_name=c.resource_name,
            name=c.name,
            status=status_name,
            advertising_channel_type=channel_name,
            bidding_strategy_type=bidding_name,
            budget=budget_rec,
            cpc_ceiling_eur=_ceiling_eur(c)
        ))
    return results

@handle_google_ads_errors
def get_campaign_detail(campaign_id: str, customer_id: str = CUSTOMER_ID) -> Optional[GoogleCampaignRecord]:
    """
    Fetches detailed settings for a single campaign.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.target_spend.cpc_bid_ceiling_micros,
            campaign_budget.resource_name,
            campaign_budget.amount_micros,
            campaign_budget.delivery_method
        FROM campaign
        WHERE campaign.id = {campaign_id}
        LIMIT 1
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    for row in response:
        c = row.campaign
        b = row.campaign_budget
        budget_rec = None
        if b and b.amount_micros:
            budget_rec = CampaignBudgetRecord(
                resource_name=b.resource_name,
                amount_micros=b.amount_micros,
                amount_eur=round(b.amount_micros / 1_000_000.0, 2),
                delivery_method=b.delivery_method.name if hasattr(b.delivery_method, "name") else str(b.delivery_method)
            )
        return GoogleCampaignRecord(
            id=str(c.id),
            resource_name=c.resource_name,
            name=c.name,
            status=c.status.name if hasattr(c.status, "name") else str(c.status),
            advertising_channel_type=c.advertising_channel_type.name if hasattr(c.advertising_channel_type, "name") else str(c.advertising_channel_type),
            bidding_strategy_type=c.bidding_strategy_type.name if hasattr(c.bidding_strategy_type, "name") else str(c.bidding_strategy_type),
            budget=budget_rec,
            cpc_ceiling_eur=_ceiling_eur(c)
        )
    return None

@handle_google_ads_errors
def update_campaign_status(req: CampaignStatusUpdateRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Safely mutates campaign status using official sparse update_mask.
    """
    client = get_ads_client()
    campaign_service = client.get_service("CampaignService")
    
    operation = client.get_type("CampaignOperation")
    campaign = operation.update
    campaign.resource_name = campaign_service.campaign_path(customer_id, req.campaign_id)
    
    status_enum = client.enums.CampaignStatusEnum
    campaign.status = status_enum.ENABLED if req.enabled else status_enum.PAUSED
    operation.update_mask.CopyFrom(protobuf_helpers.field_mask(None, campaign._pb))
    
    campaign_service.mutate_campaigns(customer_id=customer_id, operations=[operation])
    state = "ENABLED" if req.enabled else "PAUSED"
    return f"Campaign {req.campaign_id} successfully set to {state}."

@handle_google_ads_errors
def update_campaign_budget(req: CampaignBudgetUpdateRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Safely updates daily campaign budget in EUR using official sparse update_mask.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    budget_service = client.get_service("CampaignBudgetService")
    
    # 1. Fetch budget resource name
    query = f"SELECT campaign.campaign_budget FROM campaign WHERE campaign.id = {req.campaign_id} LIMIT 1"
    res = list(ga_service.search(customer_id=customer_id, query=query))
    if not res:
        raise ValueError(f"Campaign {req.campaign_id} not found.")
    
    budget_resource_name = res[0].campaign.campaign_budget
    
    # 2. Mutate budget
    operation = client.get_type("CampaignBudgetOperation")
    budget = operation.update
    budget.resource_name = budget_resource_name
    budget.amount_micros = eur_to_micros(req.budget_eur)
    operation.update_mask.CopyFrom(protobuf_helpers.field_mask(None, budget._pb))
    
    budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[operation])
    return f"Campaign {req.campaign_id} budget updated to {req.budget_eur:.2f} EUR/day."

@handle_google_ads_errors
def step_campaign_cpc_ceiling(req: CampaignCeilingStepRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Steps the Maximize Clicks CPC ceiling (campaign.target_spend.cpc_bid_ceiling_micros) by +/-0.05 EUR.
    Under TARGET_SPEND the ceiling is the only effective bid lever; ad group cpc_bid_micros is ignored.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    campaign_service = client.get_service("CampaignService")

    query = f"""
        SELECT campaign.id, campaign.name, campaign.bidding_strategy_type,
               campaign.target_spend.cpc_bid_ceiling_micros
        FROM campaign
        WHERE campaign.id = {req.campaign_id}
        LIMIT 1
    """
    res = list(ga_service.search(customer_id=customer_id, query=query))
    if not res:
        raise ValueError(f"Campaign {req.campaign_id} not found.")

    c = res[0].campaign
    if c.bidding_strategy_type.name != "TARGET_SPEND":
        raise ValueError(f"Campaign '{c.name}' uses {c.bidding_strategy_type.name}, not TARGET_SPEND (Maximize Clicks); it has no CPC ceiling to step.")

    curr_micros = c.target_spend.cpc_bid_ceiling_micros
    if not curr_micros:
        raise ValueError(f"Campaign '{c.name}' has no CPC ceiling set (uncapped); refusing to guess a starting value.")

    step_micros = 50_000 if req.direction == "+0.05" else -50_000
    new_micros = curr_micros + step_micros
    if not CEILING_MIN_MICROS <= new_micros <= CEILING_MAX_MICROS:
        raise ValueError(f"New ceiling {new_micros / 1e6:.2f} EUR is outside the 0.10-3.00 EUR safeguard.")

    operation = client.get_type("CampaignOperation")
    campaign = operation.update
    campaign.resource_name = campaign_service.campaign_path(customer_id, req.campaign_id)
    campaign.target_spend.cpc_bid_ceiling_micros = new_micros
    operation.update_mask.CopyFrom(protobuf_helpers.field_mask(None, campaign._pb))

    campaign_service.mutate_campaigns(customer_id=customer_id, operations=[operation])
    return f"Campaign '{c.name}' ({req.campaign_id}) CPC ceiling updated from {curr_micros / 1e6:.2f} EUR to {new_micros / 1e6:.2f} EUR."

@handle_google_ads_errors
def get_campaign_targeting_overview(campaign_id: str = "24015242821", customer_id: str = CUSTOMER_ID) -> CampaignTargetingRecord:
    """
    Audits campaign targeting criteria (Geo Locations, Languages, Dayparting Ad Schedules, Device Modifiers)
    and network settings (Google Search vs Display Network).
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    # 1. Fetch network settings
    q_net = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.network_settings.target_google_search,
            campaign.network_settings.target_search_network,
            campaign.network_settings.target_content_network
        FROM campaign
        WHERE campaign.id = {campaign_id}
        LIMIT 1
    """
    res_net = list(ga_service.search(customer_id=customer_id, query=q_net))
    if not res_net:
        raise ValueError(f"Campaign {campaign_id} not found.")
        
    c = res_net[0].campaign
    cname = c.name
    net = c.network_settings
    
    # 2. Fetch targeting criteria
    q_crit = f"""
        SELECT
            campaign.id,
            campaign_criterion.criterion_id,
            campaign_criterion.type,
            campaign_criterion.negative,
            campaign_criterion.location.geo_target_constant,
            campaign_criterion.language.language_constant,
            campaign_criterion.ad_schedule.day_of_week,
            campaign_criterion.ad_schedule.start_hour,
            campaign_criterion.ad_schedule.start_minute,
            campaign_criterion.ad_schedule.end_hour,
            campaign_criterion.ad_schedule.end_minute,
            campaign_criterion.device.type,
            campaign_criterion.bid_modifier
        FROM campaign_criterion
        WHERE campaign.id = {campaign_id}
    """
    res_crit = ga_service.search(customer_id=customer_id, query=q_crit)
    
    locations = []
    ex_locations = []
    languages = []
    schedules = []
    devices = []
    
    for r in res_crit:
        cc = r.campaign_criterion
        ctype = cc.type_.name
        if ctype == "LOCATION":
            loc_id = cc.location.geo_target_constant.split("/")[-1] if cc.location and cc.location.geo_target_constant else str(cc.criterion_id)
            loc_name = "Germany (2276)" if loc_id == "2276" else ("Austria (2040)" if loc_id == "2040" else f"Geo {loc_id}")
            if cc.negative:
                ex_locations.append(loc_name)
            else:
                locations.append(loc_name)
        elif ctype == "LANGUAGE":
            lang_id = cc.language.language_constant.split("/")[-1] if cc.language and cc.language.language_constant else str(cc.criterion_id)
            lang_name = "German (1001)" if lang_id == "1001" else ("French (1002)" if lang_id == "1002" else ("Spanish (1003)" if lang_id == "1003" else f"Lang {lang_id}"))
            languages.append(lang_name)
        elif ctype == "AD_SCHEDULE":
            sch = cc.ad_schedule
            schedules.append(f"{sch.day_of_week.name}: {sch.start_hour:02d}:{sch.start_minute.name} - {sch.end_hour:02d}:{sch.end_minute.name}")
        elif ctype == "DEVICE":
            dev_name = cc.device.type_.name if cc.device else "DEVICE"
            devices.append(f"{dev_name} (bid mod: {cc.bid_modifier})")
            
    return CampaignTargetingRecord(
        campaign_id=str(c.id),
        campaign_name=cname,
        target_google_search=net.target_google_search,
        target_search_network=net.target_search_network,
        target_content_network=net.target_content_network,
        targeted_locations=locations,
        excluded_locations=ex_locations,
        targeted_languages=languages,
        ad_schedules=schedules,
        device_modifiers=devices
    )
