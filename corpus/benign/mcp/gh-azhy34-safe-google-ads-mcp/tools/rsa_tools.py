import sys
from pathlib import Path
from typing import List
from google.api_core import protobuf_helpers

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.client import get_ads_client
from core.config import CUSTOMER_ID
from shield.error_shield import ServiceResult, handle_google_ads_errors
from shield.models_ad import (
    GoogleRSAAdRecord, DeployGoldenRSARequest, 
    HeadlineAsset, DescriptionAsset
)

@handle_google_ads_errors
def list_campaign_ads(campaign_id: str, customer_id: str = CUSTOMER_ID) -> List[GoogleRSAAdRecord]:
    """
    Fetches all Responsive Search Ads in a campaign with headline/description arrays and approval status.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    query = f"""
        SELECT
            ad_group_ad.ad.id,
            ad_group_ad.ad_group,
            ad_group_ad.status,
            ad_group_ad.ad.final_urls,
            ad_group_ad.ad.responsive_search_ad.headlines,
            ad_group_ad.ad.responsive_search_ad.descriptions,
            ad_group_ad.policy_summary.approval_status
        FROM ad_group_ad
        WHERE campaign.id = {campaign_id}
          AND ad_group_ad.status != 'REMOVED'
          AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    
    results = []
    for row in response:
        aga = row.ad_group_ad
        ad = aga.ad
        rsa = ad.responsive_search_ad
        
        headlines = []
        for h in rsa.headlines:
            pinned = h.pinned_field.name if hasattr(h.pinned_field, "name") and h.pinned_field else None
            perf = h.asset_performance_label.name if hasattr(h.asset_performance_label, "name") and h.asset_performance_label else None
            headlines.append(HeadlineAsset(
                text=h.text,
                pinned_field=pinned,
                asset_performance_label=perf
            ))
            
        descriptions = []
        for d in rsa.descriptions:
            pinned = d.pinned_field.name if hasattr(d.pinned_field, "name") and d.pinned_field else None
            perf = d.asset_performance_label.name if hasattr(d.asset_performance_label, "name") and d.asset_performance_label else None
            descriptions.append(DescriptionAsset(
                text=d.text,
                pinned_field=pinned,
                asset_performance_label=perf
            ))
            
        approval = aga.policy_summary.approval_status.name if hasattr(aga.policy_summary.approval_status, "name") else str(aga.policy_summary.approval_status)
        ag_id = aga.ad_group.split("/")[-1] if hasattr(aga, "ad_group") else ""
        
        results.append(GoogleRSAAdRecord(
            id=str(ad.id),
            resource_name=aga.resource_name,
            ad_group_id=ag_id,
            status=aga.status.name if hasattr(aga.status, "name") else str(aga.status),
            headlines=headlines,
            descriptions=descriptions,
            final_urls=list(ad.final_urls),
            approval_status=approval
        ))
    return results

MAX_ENABLED_RSA_PER_AD_GROUP = 3

@handle_google_ads_errors
def deploy_golden_rsa(req: DeployGoldenRSARequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Deploys a Golden 15/4 RSA with Headline 1 DKI pinning and WELCOME3 compliance.
    If the ad group already has 3 enabled RSAs, pauses only the oldest ones needed to stay at 3.
    Pauses and the create go in one atomic request: if the new ad is rejected, nothing is paused.
    """
    client = get_ads_client()
    aga_service = client.get_service("AdGroupAdService")
    ga_service = client.get_service("GoogleAdsService")

    # 1. Existing enabled RSAs, oldest first
    query_existing = f"""
        SELECT ad_group_ad.resource_name, ad_group_ad.ad.id
        FROM ad_group_ad
        WHERE ad_group.id = {req.ad_group_id}
          AND ad_group_ad.status = 'ENABLED'
          AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
        ORDER BY ad_group_ad.ad.id ASC
    """
    existing_res = list(ga_service.search(customer_id=customer_id, query=query_existing))
    excess = len(existing_res) - (MAX_ENABLED_RSA_PER_AD_GROUP - 1)

    operations = []
    paused = []
    for row in existing_res[:max(0, excess)]:
        op = client.get_type("AdGroupAdOperation")
        ad_to_pause = op.update
        ad_to_pause.resource_name = row.ad_group_ad.resource_name
        ad_to_pause.status = client.enums.AdGroupAdStatusEnum.PAUSED
        op.update_mask.CopyFrom(protobuf_helpers.field_mask(None, ad_to_pause._pb))
        operations.append(op)
        paused.append(str(row.ad_group_ad.ad.id))

    # 2. The new Golden RSA
    create_operation = client.get_type("AdGroupAdOperation")
    ad_group_ad = create_operation.create
    ad_group_ad.ad_group = client.get_service("AdGroupService").ad_group_path(customer_id, req.ad_group_id)
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

    rsa_ad = ad_group_ad.ad
    rsa_ad.final_urls.append(req.final_url)

    # headlines[0] == pinned_h1_dki (enforced by the request model) goes to HEADLINE_1
    for i, text in enumerate(req.headlines):
        h = client.get_type("AdTextAsset")
        h.text = text
        if i == 0:
            h.pinned_field = client.enums.ServedAssetFieldTypeEnum.HEADLINE_1
        rsa_ad.responsive_search_ad.headlines.append(h)

    for text in req.descriptions:
        d = client.get_type("AdTextAsset")
        d.text = text
        rsa_ad.responsive_search_ad.descriptions.append(d)

    if req.path1:
        rsa_ad.responsive_search_ad.path1 = req.path1
    if req.path2:
        rsa_ad.responsive_search_ad.path2 = req.path2

    operations.append(create_operation)
    response = aga_service.mutate_ad_group_ads(customer_id=customer_id, operations=operations)
    new_ad_resource = response.results[-1].resource_name
    paused_note = f" Paused oldest ad(s): {', '.join(paused)}." if paused else ""
    return f"Successfully deployed Golden RSA {new_ad_resource} to AdGroup {req.ad_group_id} (15/4 Matrix + DKI + WELCOME3).{paused_note}"
