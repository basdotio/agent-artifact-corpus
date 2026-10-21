import sys
from pathlib import Path
from typing import List, Optional
from datetime import date, timedelta
from google.api_core import protobuf_helpers

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.client import get_ads_client
from core.config import CUSTOMER_ID
from shield.error_shield import ServiceResult, handle_google_ads_errors
from shield.models_asset import (
    GoogleAssetRecord, ImageAssetData, SitelinkAssetData, 
    StructuredSnippetAssetData, CalloutAssetData, PromotionAssetData, PriceAssetData,
    AssetAssociationRecord, AssetPerformanceRecord, CampaignAssetDiversity,
    LinkAssetRequest, UnlinkAssetRequest, CreatePriceAssetRequest,
    SyncPriceExtensionRequest
)

@handle_google_ads_errors
def list_account_assets(asset_type: str = None, customer_id: str = CUSTOMER_ID) -> List[GoogleAssetRecord]:
    """
    Fetches all base assets in the account (Images, Sitelinks, Structured Snippets, Promotions, Prices).
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    where_clause = ""
    if asset_type:
        where_clause = f"WHERE asset.type = '{asset_type.upper()}'"
        
    query = f"""
        SELECT
            asset.id,
            asset.name,
            asset.type,
            asset.image_asset.full_size.url,
            asset.image_asset.file_size,
            asset.sitelink_asset.link_text,
            asset.sitelink_asset.description1,
            asset.sitelink_asset.description2,
            asset.structured_snippet_asset.header,
            asset.structured_snippet_asset.values,
            asset.callout_asset.callout_text,
            asset.promotion_asset.promotion_target,
            asset.promotion_asset.discount_modifier,
            asset.promotion_asset.percent_off
        FROM asset
        {where_clause}
        LIMIT 100
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    
    results = []
    for row in response:
        a = row.asset
        type_str = a.type_.name if hasattr(a.type_, "name") else str(a.type_)
        
        img_data = None
        if a.image_asset and a.image_asset.full_size and a.image_asset.full_size.url:
            img_data = ImageAssetData(
                url=a.image_asset.full_size.url,
                file_size=a.image_asset.file_size or None
            )
            
        sitelink_data = None
        if a.sitelink_asset and a.sitelink_asset.link_text:
            sitelink_data = SitelinkAssetData(
                link_text=a.sitelink_asset.link_text,
                description1=a.sitelink_asset.description1 or None,
                description2=a.sitelink_asset.description2 or None
            )
            
        snippet_data = None
        if a.structured_snippet_asset and a.structured_snippet_asset.header:
            snippet_data = StructuredSnippetAssetData(
                header=a.structured_snippet_asset.header,
                values=list(a.structured_snippet_asset.values)
            )
            
        callout_data = None
        if a.callout_asset and a.callout_asset.callout_text:
            callout_data = CalloutAssetData(callout_text=a.callout_asset.callout_text)
            
        promo_data = None
        if a.promotion_asset and a.promotion_asset.promotion_target:
            promo_data = PromotionAssetData(
                promotion_target=a.promotion_asset.promotion_target,
                discount_modifier=a.promotion_asset.discount_modifier.name if hasattr(a.promotion_asset.discount_modifier, "name") else None,
                percent_off=a.promotion_asset.percent_off or None
            )
            
        results.append(GoogleAssetRecord(
            id=str(a.id),
            resource_name=a.resource_name,
            name=a.name or None,
            type=type_str,
            image_data=img_data,
            sitelink_data=sitelink_data,
            snippet_data=snippet_data,
            callout_data=callout_data,
            promotion_data=promo_data
        ))
    return results

# --- TAB 1: СВЯЗИ (ASSOCIATIONS) ---

@handle_google_ads_errors
def get_assets_associations(
    level: Optional[str] = None, 
    field_type: Optional[str] = None, 
    customer_id: str = CUSTOMER_ID
) -> List[AssetAssociationRecord]:
    """
    Reproduces Google Ads UI Tab 'Связи' (Associations).
    Retrieves asset links across Customer (Account), Campaign, and Ad Group levels
    with full text preview and image CDN URLs.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    results = []
    
    # 1. Customer Level (Account-wide, e.g. Business Logo, Price)
    if not level or level.upper() == "CUSTOMER":
        q_cust = """
            SELECT
                asset.id,
                asset.name,
                asset.type,
                asset.text_asset.text,
                asset.image_asset.full_size.url,
                customer_asset.field_type,
                customer_asset.status
            FROM customer_asset
            WHERE customer_asset.status != 'REMOVED'
        """
        if field_type:
            q_cust += f" AND customer_asset.field_type = '{field_type.upper()}'"
        for r in ga_service.search(customer_id=customer_id, query=q_cust):
            f_type = r.customer_asset.field_type.name if hasattr(r.customer_asset.field_type, "name") else str(r.customer_asset.field_type)
            a = r.asset
            txt = a.text_asset.text if a.text_asset else (a.name or None)
            img_url = a.image_asset.full_size.url if a.image_asset and a.image_asset.full_size else None
            results.append(AssetAssociationRecord(
                level="CUSTOMER",
                entity_id=customer_id,
                entity_name="Account Level",
                asset_id=str(a.id),
                asset_name=a.name or None,
                asset_text=txt,
                asset_image_url=img_url,
                field_type=f_type,
                status=r.customer_asset.status.name if hasattr(r.customer_asset.status, "name") else str(r.customer_asset.status)
            ))

    # 2. Campaign Level (Sitelinks, Callouts, Snippets, Promotions)
    if not level or level.upper() == "CAMPAIGN":
        q_camp = """
            SELECT
                campaign.id,
                campaign.name,
                asset.id,
                asset.name,
                asset.type,
                asset.text_asset.text,
                asset.sitelink_asset.link_text,
                asset.callout_asset.callout_text,
                asset.structured_snippet_asset.header,
                asset.image_asset.full_size.url,
                campaign_asset.field_type,
                campaign_asset.status
            FROM campaign_asset
            WHERE campaign_asset.status != 'REMOVED'
        """
        if field_type:
            q_camp += f" AND campaign_asset.field_type = '{field_type.upper()}'"
        for r in ga_service.search(customer_id=customer_id, query=q_camp):
            f_type = r.campaign_asset.field_type.name if hasattr(r.campaign_asset.field_type, "name") else str(r.campaign_asset.field_type)
            a = r.asset
            txt = (a.text_asset.text if a.text_asset else None) or \
                  (a.sitelink_asset.link_text if a.sitelink_asset else None) or \
                  (a.callout_asset.callout_text if a.callout_asset else None) or \
                  (a.structured_snippet_asset.header if a.structured_snippet_asset else None) or \
                  a.name
            img_url = a.image_asset.full_size.url if a.image_asset and a.image_asset.full_size else None
            results.append(AssetAssociationRecord(
                level="CAMPAIGN",
                entity_id=str(r.campaign.id),
                entity_name=r.campaign.name,
                asset_id=str(a.id),
                asset_name=a.name or None,
                asset_text=txt,
                asset_image_url=img_url,
                field_type=f_type,
                status=r.campaign_asset.status.name if hasattr(r.campaign_asset.status, "name") else str(r.campaign_asset.status)
            ))

    # 3. Ad Group Level (Image assets, group sitelinks)
    if not level or level.upper() == "AD_GROUP":
        q_ag = """
            SELECT
                ad_group.id,
                ad_group.name,
                asset.id,
                asset.name,
                asset.type,
                asset.text_asset.text,
                asset.sitelink_asset.link_text,
                asset.image_asset.full_size.url,
                ad_group_asset.field_type,
                ad_group_asset.status
            FROM ad_group_asset
            WHERE ad_group_asset.status != 'REMOVED'
        """
        if field_type:
            q_ag += f" AND ad_group_asset.field_type = '{field_type.upper()}'"
        for r in ga_service.search(customer_id=customer_id, query=q_ag):
            f_type = r.ad_group_asset.field_type.name if hasattr(r.ad_group_asset.field_type, "name") else str(r.ad_group_asset.field_type)
            a = r.asset
            txt = (a.text_asset.text if a.text_asset else None) or \
                  (a.sitelink_asset.link_text if a.sitelink_asset else None) or \
                  a.name
            img_url = a.image_asset.full_size.url if a.image_asset and a.image_asset.full_size else None
            results.append(AssetAssociationRecord(
                level="AD_GROUP",
                entity_id=str(r.ad_group.id),
                entity_name=r.ad_group.name,
                asset_id=str(a.id),
                asset_name=a.name or None,
                asset_text=txt,
                asset_image_url=img_url,
                field_type=f_type,
                status=r.ad_group_asset.status.name if hasattr(r.ad_group_asset.status, "name") else str(r.ad_group_asset.status)
            ))

    return results

# --- TAB 2: ЭФФЕКТИВНОСТЬ (PERFORMANCE) ---

@handle_google_ads_errors
def get_assets_performance(
    days: int = 30,
    field_type: Optional[str] = None,
    customer_id: str = CUSTOMER_ID
) -> List[AssetPerformanceRecord]:
    """
    Reproduces Google Ads UI Tab 'Эффективность' (Asset Performance).
    Retrieves Impressions, Clicks, CTR %, Cost (EUR), and Google AI Performance Label
    across both In-Ad Assets (ad_group_ad_asset_view) and Extensions (campaign_asset, customer_asset).
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    end_date = date.today().isoformat()
    results: List[AssetPerformanceRecord] = []
    
    # 1. In-Ad Assets (Headlines, Descriptions, Images, Logos, Videos)
    where_ad_extra = ""
    if field_type:
        where_ad_extra = f" AND ad_group_ad_asset_view.field_type = '{field_type.upper()}'"
        
    q_ad = f"""
        SELECT
            campaign.name,
            ad_group.name,
            asset.id,
            asset.name,
            asset.type,
            asset.text_asset.text,
            asset.image_asset.full_size.url,
            ad_group_ad_asset_view.field_type,
            ad_group_ad_asset_view.performance_label,
            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.cost_micros
        FROM ad_group_ad_asset_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND metrics.impressions > 0
          {where_ad_extra}
        ORDER BY metrics.impressions DESC
        LIMIT 60
    """
    for r in ga_service.search(customer_id=customer_id, query=q_ad):
        v = r.ad_group_ad_asset_view
        m = r.metrics
        a = r.asset
        f_type = v.field_type.name if hasattr(v.field_type, "name") else str(v.field_type)
        perf_label = v.performance_label.name if hasattr(v.performance_label, "name") else str(v.performance_label)
        txt = a.text_asset.text if a.text_asset else (a.name or None)
        img_url = a.image_asset.full_size.url if a.image_asset and a.image_asset.full_size else None
        
        results.append(AssetPerformanceRecord(
            asset_id=str(a.id),
            asset_name=a.name or None,
            asset_text=txt,
            asset_image_url=img_url,
            field_type=f_type,
            level="AD_ASSET",
            campaign_name=r.campaign.name,
            ad_group_name=r.ad_group.name,
            impressions=m.impressions or 0,
            clicks=m.clicks or 0,
            ctr_percent=round((m.ctr or 0.0) * 100, 2),
            cost_eur=round((m.cost_micros or 0) / 1_000_000.0, 2),
            performance_label=perf_label
        ))

    # 2. Campaign Level Assets (Sitelinks, Callouts, Snippets, Promotions)
    where_camp_extra = ""
    if field_type:
        where_camp_extra = f" AND campaign_asset.field_type = '{field_type.upper()}'"
        
    q_camp = f"""
        SELECT
            campaign.name,
            asset.id,
            asset.name,
            asset.type,
            asset.text_asset.text,
            asset.sitelink_asset.link_text,
            asset.callout_asset.callout_text,
            asset.structured_snippet_asset.header,
            asset.image_asset.full_size.url,
            campaign_asset.field_type,
            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.cost_micros
        FROM campaign_asset
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND metrics.impressions > 0
          {where_camp_extra}
        ORDER BY metrics.impressions DESC
        LIMIT 40
    """
    for r in ga_service.search(customer_id=customer_id, query=q_camp):
        ca = r.campaign_asset
        m = r.metrics
        a = r.asset
        f_type = ca.field_type.name if hasattr(ca.field_type, "name") else str(ca.field_type)
        txt = (a.text_asset.text if a.text_asset else None) or \
              (a.sitelink_asset.link_text if a.sitelink_asset else None) or \
              (a.callout_asset.callout_text if a.callout_asset else None) or \
              (a.structured_snippet_asset.header if a.structured_snippet_asset else None) or \
              a.name
        img_url = a.image_asset.full_size.url if a.image_asset and a.image_asset.full_size else None
        ctr = round((m.ctr or 0.0) * 100, 2)
        clicks = m.clicks or 0
        # Google exposes no performance_label for extensions; this is our own CTR heuristic
        perf = "HEURISTIC_BEST" if ctr > 5.0 and clicks > 10 else ("HEURISTIC_GOOD" if ctr > 2.0 else "HEURISTIC_LEARNING")
        
        results.append(AssetPerformanceRecord(
            asset_id=str(a.id),
            asset_name=a.name or None,
            asset_text=txt,
            asset_image_url=img_url,
            field_type=f_type,
            level="CAMPAIGN_ASSET",
            campaign_name=r.campaign.name,
            ad_group_name=None,
            impressions=m.impressions or 0,
            clicks=clicks,
            ctr_percent=ctr,
            cost_eur=round((m.cost_micros or 0) / 1_000_000.0, 2),
            performance_label=perf
        ))

    # 3. Customer Level Assets (Price, Business Logo, Business Name)
    where_cust_extra = ""
    if field_type:
        where_cust_extra = f" AND customer_asset.field_type = '{field_type.upper()}'"
        
    q_cust = f"""
        SELECT
            asset.id,
            asset.name,
            asset.type,
            customer_asset.field_type,
            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.cost_micros
        FROM customer_asset
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
          AND metrics.impressions > 0
          {where_cust_extra}
        LIMIT 10
    """
    for r in ga_service.search(customer_id=customer_id, query=q_cust):
        ca = r.customer_asset
        m = r.metrics
        a = r.asset
        f_type = ca.field_type.name if hasattr(ca.field_type, "name") else str(ca.field_type)
        ctr = round((m.ctr or 0.0) * 100, 2)
        clicks = m.clicks or 0
        perf = "HEURISTIC_BEST" if ctr > 5.0 and clicks > 10 else ("HEURISTIC_GOOD" if ctr > 1.0 else "HEURISTIC_LEARNING")
        
        results.append(AssetPerformanceRecord(
            asset_id=str(a.id),
            asset_name=a.name or None,
            asset_text=a.name or "Account Asset",
            asset_image_url=None,
            field_type=f_type,
            level="CUSTOMER_ASSET",
            campaign_name="All Campaigns (Account Level)",
            ad_group_name=None,
            impressions=m.impressions or 0,
            clicks=clicks,
            ctr_percent=ctr,
            cost_eur=round((m.cost_micros or 0) / 1_000_000.0, 2),
            performance_label=perf
        ))

    results.sort(key=lambda x: x.impressions, reverse=True)
    return results

# --- TAB 3: РАЗНООБРАЗИЕ ОБЪЕКТОВ (ASSET DIVERSITY & HEALTH) ---

@handle_google_ads_errors
def get_assets_diversity(customer_id: str = CUSTOMER_ID) -> List[CampaignAssetDiversity]:
    """
    Reproduces Google Ads UI Tab 'Разнообразие объектов'.
    Audits active campaigns to ensure complete asset extension variety:
    Images (min 4), Sitelinks (min 4), Snippets, Callouts, Promotions, Price, Logo.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    # 1. Fetch active search campaigns
    q_camps = """
        SELECT campaign.id, campaign.name 
        FROM campaign 
        WHERE campaign.status = 'ENABLED' 
          AND campaign.advertising_channel_type = 'SEARCH'
    """
    campaigns = {str(r.campaign.id): r.campaign.name for r in ga_service.search(customer_id=customer_id, query=q_camps)}
    
    # 2. Fetch customer-level assets
    q_cust = "SELECT customer_asset.field_type FROM customer_asset WHERE customer_asset.status != 'REMOVED'"
    cust_assets = set()
    for r in ga_service.search(customer_id=customer_id, query=q_cust):
        cust_assets.add(r.customer_asset.field_type.name if hasattr(r.customer_asset.field_type, "name") else str(r.customer_asset.field_type))
        
    has_cust_price = "PRICE" in cust_assets
    has_cust_logo = "BUSINESS_LOGO" in cust_assets
    has_cust_name = "BUSINESS_NAME" in cust_assets

    # 3. Fetch campaign-level asset links
    q_camp_assets = """
        SELECT campaign.id, campaign_asset.field_type
        FROM campaign_asset
        WHERE campaign_asset.status != 'REMOVED'
    """
    camp_asset_map = {}
    for r in ga_service.search(customer_id=customer_id, query=q_camp_assets):
        cid = str(r.campaign.id)
        if cid not in camp_asset_map:
            camp_asset_map[cid] = []
        camp_asset_map[cid].append(r.campaign_asset.field_type.name if hasattr(r.campaign_asset.field_type, "name") else str(r.campaign_asset.field_type))

    # 4. Fetch ad-group-level image and sitelink counts
    q_ag_assets = """
        SELECT campaign.id, ad_group_asset.field_type
        FROM ad_group_asset
        WHERE ad_group_asset.status != 'REMOVED'
    """
    ag_asset_map = {}
    for r in ga_service.search(customer_id=customer_id, query=q_ag_assets):
        cid = str(r.campaign.id)
        if cid not in ag_asset_map:
            ag_asset_map[cid] = []
        ag_asset_map[cid].append(r.ad_group_asset.field_type.name if hasattr(r.ad_group_asset.field_type, "name") else str(r.ad_group_asset.field_type))

    summaries = []
    for cid, cname in campaigns.items():
        c_types = camp_asset_map.get(cid, [])
        ag_types = ag_asset_map.get(cid, [])
        
        sitelinks_count = c_types.count("SITELINK") + ag_types.count("SITELINK")
        images_count = ag_types.count("IMAGE") + c_types.count("IMAGE")
        has_snippets = "STRUCTURED_SNIPPET" in c_types
        has_callouts = "CALLOUT" in c_types
        has_promo = "PROMOTION" in c_types
        
        missing = []
        score = 0
        if sitelinks_count >= 4:
            score += 25
        elif sitelinks_count > 0:
            score += 15
            missing.append(f"Needs more sitelinks ({sitelinks_count}/4)")
        else:
            missing.append("Missing Sitelinks (min 4)")
            
        if images_count >= 4:
            score += 25
        elif images_count > 0:
            score += 15
            missing.append(f"Needs more images ({images_count}/4)")
        else:
            missing.append("Missing Visual Images (min 4)")
            
        if has_snippets:
            score += 15
        else:
            missing.append("Missing Structured Snippets")
            
        if has_callouts:
            score += 15
        else:
            missing.append("Missing Callouts")
            
        if has_promo:
            score += 10
        else:
            missing.append("Missing Promotion (WELCOME3)")
            
        if has_cust_price:
            score += 5
        if has_cust_logo:
            score += 5
            
        summaries.append(CampaignAssetDiversity(
            campaign_id=cid,
            campaign_name=cname,
            has_images=(images_count > 0),
            image_count=images_count,
            has_sitelinks=(sitelinks_count > 0),
            sitelink_count=sitelinks_count,
            has_snippets=has_snippets,
            has_callouts=has_callouts,
            has_promotions=has_promo,
            has_price=has_cust_price,
            has_business_name=has_cust_name,
            has_business_logo=has_cust_logo,
            missing_asset_types=missing,
            diversity_score=min(100, score)
        ))
        
    return summaries

# --- MUTATIONS: LINK & UNLINK ASSETS ---

@handle_google_ads_errors
def link_asset_to_entity(req: LinkAssetRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Binds an asset to Customer (Account), Campaign, or Ad Group.
    """
    client = get_ads_client()
    f_type_enum = getattr(client.enums.AssetFieldTypeEnum, req.field_type.upper())
    
    if req.level == "CUSTOMER":
        service = client.get_service("CustomerAssetService")
        op = client.get_type("CustomerAssetOperation")
        ca = op.create
        ca.asset = client.get_service("AssetService").asset_path(customer_id, req.asset_id)
        ca.field_type = f_type_enum
        service.mutate_customer_assets(customer_id=customer_id, operations=[op])
        return f"Successfully linked Asset {req.asset_id} to Account as {req.field_type}."
        
    elif req.level == "CAMPAIGN":
        service = client.get_service("CampaignAssetService")
        op = client.get_type("CampaignAssetOperation")
        ca = op.create
        ca.campaign = client.get_service("CampaignService").campaign_path(customer_id, req.entity_id)
        ca.asset = client.get_service("AssetService").asset_path(customer_id, req.asset_id)
        ca.field_type = f_type_enum
        service.mutate_campaign_assets(customer_id=customer_id, operations=[op])
        return f"Successfully linked Asset {req.asset_id} to Campaign {req.entity_id} as {req.field_type}."
        
    else: # AD_GROUP
        service = client.get_service("AdGroupAssetService")
        op = client.get_type("AdGroupAssetOperation")
        aga = op.create
        aga.ad_group = client.get_service("AdGroupService").ad_group_path(customer_id, req.entity_id)
        aga.asset = client.get_service("AssetService").asset_path(customer_id, req.asset_id)
        aga.field_type = f_type_enum
        service.mutate_ad_group_assets(customer_id=customer_id, operations=[op])
        return f"Successfully linked Asset {req.asset_id} to AdGroup {req.entity_id} as {req.field_type}."

@handle_google_ads_errors
def unlink_asset_from_entity(req: UnlinkAssetRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Unlinks/removes an asset association from Customer (Account), Campaign, or Ad Group.
    """
    client = get_ads_client()
    
    if req.level == "CUSTOMER":
        service = client.get_service("CustomerAssetService")
        resource_name = service.customer_asset_path(customer_id, req.asset_id, req.field_type.upper())
        op = client.get_type("CustomerAssetOperation")
        op.remove = resource_name
        service.mutate_customer_assets(customer_id=customer_id, operations=[op])
        return f"Successfully unlinked Asset {req.asset_id} from Account ({req.field_type})."
        
    elif req.level == "CAMPAIGN":
        service = client.get_service("CampaignAssetService")
        resource_name = service.campaign_asset_path(customer_id, req.entity_id, req.asset_id, req.field_type.upper())
        op = client.get_type("CampaignAssetOperation")
        op.remove = resource_name
        service.mutate_campaign_assets(customer_id=customer_id, operations=[op])
        return f"Successfully unlinked Asset {req.asset_id} from Campaign {req.entity_id} ({req.field_type})."
        
    else: # AD_GROUP
        service = client.get_service("AdGroupAssetService")
        resource_name = service.ad_group_asset_path(customer_id, req.entity_id, req.asset_id, req.field_type.upper())
        op = client.get_type("AdGroupAssetOperation")
        op.remove = resource_name
        service.mutate_ad_group_assets(customer_id=customer_id, operations=[op])
        return f"Successfully unlinked Asset {req.asset_id} from AdGroup {req.entity_id} ({req.field_type})."

@handle_google_ads_errors
def create_price_asset(req: CreatePriceAssetRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Creates a new Price Asset in Google Ads with the specified offerings.
    """
    client = get_ads_client()
    asset_service = client.get_service("AssetService")
    op = client.get_type("AssetOperation")
    a = op.create
    a.name = req.name
    a.type_ = client.enums.AssetTypeEnum.PRICE
    a.price_asset.type_ = getattr(client.enums.PriceExtensionTypeEnum, req.price_type)
    a.price_asset.price_qualifier = getattr(client.enums.PriceExtensionPriceQualifierEnum, req.price_qualifier)
    a.price_asset.language_code = req.language_code

    for off in req.offerings:
        po = client.get_type("PriceOffering")
        po.header = off.header
        po.description = off.description
        po.price.currency_code = "EUR"
        po.price.amount_micros = int(round(off.price_eur * 1_000_000))
        po.unit = client.enums.PriceExtensionPriceUnitEnum.UNSPECIFIED
        po.final_url = off.final_url
        a.price_asset.price_offerings.append(po)

    res = asset_service.mutate_assets(customer_id=customer_id, operations=[op])
    created_id = res.results[0].resource_name.split("/")[-1]
    return f"Successfully created Price Asset {created_id} ('{req.name}') with {len(req.offerings)} offerings."


@handle_google_ads_errors
def sync_price_extension(req: SyncPriceExtensionRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Smart Facade Macro Tool:
    1. Creates a new Price Asset with validated offerings (EUR prices, valid URLs, headers).
    2. Discovers all existing active Price Assets linked to the specified entity (Customer, Campaign, or Ad Group).
    3. Unlinks all existing old Price Assets.
    4. Links the newly created Price Asset to the target entity.
    5. Returns an itemized report of unlinked old assets and the newly active asset.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    asset_service = client.get_service("AssetService")

    # 1. CREATE NEW PRICE ASSET
    op = client.get_type("AssetOperation")
    a = op.create
    a.name = req.name
    a.type_ = client.enums.AssetTypeEnum.PRICE
    a.price_asset.type_ = getattr(client.enums.PriceExtensionTypeEnum, req.price_type)
    a.price_asset.price_qualifier = getattr(client.enums.PriceExtensionPriceQualifierEnum, req.price_qualifier)
    a.price_asset.language_code = req.language_code

    for off in req.offerings:
        po = client.get_type("PriceOffering")
        po.header = off.header
        po.description = off.description
        po.price.currency_code = "EUR"
        po.price.amount_micros = int(round(off.price_eur * 1_000_000))
        po.unit = client.enums.PriceExtensionPriceUnitEnum.UNSPECIFIED
        po.final_url = off.final_url
        a.price_asset.price_offerings.append(po)

    res = asset_service.mutate_assets(customer_id=customer_id, operations=[op])
    new_asset_id = res.results[0].resource_name.split("/")[-1]

    # 2. DISCOVER EXISTING PRICE ASSETS & MUTATE AT TARGET LEVEL
    f_type_enum = client.enums.AssetFieldTypeEnum.PRICE
    unlinked_ids = []

    if req.level == "CUSTOMER":
        q = """
        SELECT customer_asset.asset, customer_asset.resource_name
        FROM customer_asset
        WHERE customer_asset.field_type = 'PRICE' AND customer_asset.status != 'REMOVED'
        """
        rows = list(ga_service.search(customer_id=customer_id, query=q))
        cust_service = client.get_service("CustomerAssetService")
        remove_ops = []
        for r in rows:
            old_id = r.customer_asset.asset.split("/")[-1]
            if old_id != new_asset_id:
                op_rm = client.get_type("CustomerAssetOperation")
                op_rm.remove = r.customer_asset.resource_name
                remove_ops.append(op_rm)
                unlinked_ids.append(old_id)
        if remove_ops:
            cust_service.mutate_customer_assets(customer_id=customer_id, operations=remove_ops)

        op_link = client.get_type("CustomerAssetOperation")
        ca = op_link.create
        ca.asset = asset_service.asset_path(customer_id, new_asset_id)
        ca.field_type = f_type_enum
        cust_service.mutate_customer_assets(customer_id=customer_id, operations=[op_link])

    elif req.level == "CAMPAIGN":
        q = f"""
        SELECT campaign_asset.asset, campaign_asset.resource_name
        FROM campaign_asset
        WHERE campaign.id = '{req.entity_id}' AND campaign_asset.field_type = 'PRICE' AND campaign_asset.status != 'REMOVED'
        """
        rows = list(ga_service.search(customer_id=customer_id, query=q))
        camp_service = client.get_service("CampaignAssetService")
        remove_ops = []
        for r in rows:
            old_id = r.campaign_asset.asset.split("/")[-1]
            if old_id != new_asset_id:
                op_rm = client.get_type("CampaignAssetOperation")
                op_rm.remove = r.campaign_asset.resource_name
                remove_ops.append(op_rm)
                unlinked_ids.append(old_id)
        if remove_ops:
            camp_service.mutate_campaign_assets(customer_id=customer_id, operations=remove_ops)

        op_link = client.get_type("CampaignAssetOperation")
        ca = op_link.create
        ca.campaign = client.get_service("CampaignService").campaign_path(customer_id, req.entity_id)
        ca.asset = asset_service.asset_path(customer_id, new_asset_id)
        ca.field_type = f_type_enum
        camp_service.mutate_campaign_assets(customer_id=customer_id, operations=[op_link])

    else:  # AD_GROUP
        q = f"""
        SELECT ad_group_asset.asset, ad_group_asset.resource_name
        FROM ad_group_asset
        WHERE ad_group.id = '{req.entity_id}' AND ad_group_asset.field_type = 'PRICE' AND ad_group_asset.status != 'REMOVED'
        """
        rows = list(ga_service.search(customer_id=customer_id, query=q))
        ag_service = client.get_service("AdGroupAssetService")
        remove_ops = []
        for r in rows:
            old_id = r.ad_group_asset.asset.split("/")[-1]
            if old_id != new_asset_id:
                op_rm = client.get_type("AdGroupAssetOperation")
                op_rm.remove = r.ad_group_asset.resource_name
                remove_ops.append(op_rm)
                unlinked_ids.append(old_id)
        if remove_ops:
            ag_service.mutate_ad_group_assets(customer_id=customer_id, operations=remove_ops)

        op_link = client.get_type("AdGroupAssetOperation")
        aga = op_link.create
        aga.ad_group = client.get_service("AdGroupService").ad_group_path(customer_id, req.entity_id)
        aga.asset = asset_service.asset_path(customer_id, new_asset_id)
        aga.field_type = f_type_enum
        ag_service.mutate_ad_group_assets(customer_id=customer_id, operations=[op_link])

    return (
        f"Smart Facade SUCCESS: Price Extension synchronized on {req.level} '{req.entity_id}'. "
        f"Created Asset {new_asset_id} ('{req.name}', {len(req.offerings)} offerings). "
        f"Unlinked {len(unlinked_ids)} old asset(s): {unlinked_ids if unlinked_ids else 'none'}. "
        f"New asset {new_asset_id} is now ACTIVE."
    )


@handle_google_ads_errors
def get_campaign_assets_overview(campaign_id: str, customer_id: str = CUSTOMER_ID) -> str:
    """
    Inspects all Level 4 Assets (Objects) linked to a Campaign and its Ad Groups
    (Images, Sitelinks, Callouts, Structured Snippets, Promotions, Prices).
    Returns a comprehensive status matrix showing active and missing asset types.
    """
    client = get_ads_client()
    ga = client.get_service("GoogleAdsService")
    
    # 1. Query Campaign Assets
    q_camp = f"""
    SELECT campaign.id, campaign_asset.asset, campaign_asset.field_type, campaign_asset.status, asset.name, asset.type
    FROM campaign_asset
    WHERE campaign.id = '{campaign_id}' AND campaign_asset.status = 'ENABLED'
    """
    camp_assets = list(ga.search(customer_id=customer_id, query=q_camp))
    
    # 2. Query Ad Group Assets
    q_ag = f"""
    SELECT campaign.id, ad_group.name, ad_group_asset.asset, ad_group_asset.field_type, ad_group_asset.status, asset.name, asset.type
    FROM ad_group_asset
    WHERE campaign.id = '{campaign_id}' AND ad_group_asset.status = 'ENABLED'
    """
    ag_assets = list(ga.search(customer_id=customer_id, query=q_ag))
    
    output = []
    output.append("=" * 65)
    output.append(f"📦 LEVEL 4 ASSETS AUDIT FOR CAMPAIGN {campaign_id}")
    output.append("=" * 65)
    
    # Campaign Level Assets Summary
    output.append(f"\n🏛️ CAMPAIGN-LEVEL ASSETS ({len(camp_assets)} active):")
    if camp_assets:
        for ca in camp_assets:
            output.append(f"  • [{ca.asset.type.name}] Field: {ca.campaign_asset.field_type.name} | Name: '{ca.asset.name}'")
    else:
        output.append("  ⚠️ Zero campaign-level assets attached!")
        
    # Ad Group Level Assets Summary
    output.append(f"\n📂 AD GROUP-LEVEL ASSETS ({len(ag_assets)} active):")
    if ag_assets:
        by_ag = {}
        for aa in ag_assets:
            by_ag.setdefault(aa.ad_group.name, []).append(f"[{aa.asset.type.name}] {aa.asset.name}")
        for ag_name, items in by_ag.items():
            output.append(f"  📁 {ag_name} ({len(items)} assets):")
            for it in items[:4]:
                output.append(f"     - {it}")
            if len(items) > 4:
                output.append(f"     ... (+{len(items)-4} more)")
    else:
        output.append("  ⚠️ Zero ad-group level assets attached!")
        
    # Missing Assets Health Check
    types_present = set(ca.asset.type.name for ca in camp_assets) | set(aa.asset.type.name for aa in ag_assets)
    checklist = {
        "IMAGE": "Изображения (Square 1:1 & Landscape 1.91:1)",
        "SITELINK": "Дополнительные ссылки (Sitelinks)",
        "CALLOUT": "Уточнения (Callouts - Greenguard, Free Shipping)",
        "PROMOTION": "Промоакция (Promotion WELCOME3)",
        "STRUCTURED_SNIPPET": "Структурированные описания (Snippets)"
    }
    output.append("\n" + "-" * 65)
    output.append("📋 ASSET COMPLETION HEALTH CHECK:")
    for t, desc in checklist.items():
        status = "✅ ACTIVE" if t in types_present else "❌ MISSING"
        output.append(f"  {status:<12} | {desc}")
    output.append("=" * 65)
    
    return "\n".join(output)
