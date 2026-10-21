import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from google.api_core import protobuf_helpers

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.client import get_ads_client
from core.config import CUSTOMER_ID
from shield.error_shield import ServiceResult, handle_google_ads_errors
from shield.models_criterion import SearchTermWasteRecord, ApplyNegativeShieldRequest, RemoveNegativeKeywordRequest

# Target Account Verified Negative Shields
NEGATIVE_SHIELDS = {
    "de": [
        "obi", "bauhaus", "hornbach", "toom", "hagebau", "tedox", "ikea", "roller",
        "poco", "amazon", "ebay", "aliexpress", "temu", "shein",
        "kostenlos", "gratis", "umsonst", "free", "selber machen", "diy",
        "anleitung", "test", "stiftung warentest", "erfahrung", "bewertung",
        "forum", "youtube", "video", "pdf", "drucken", "ausdrucken",
        "malvorlage", "ausmalbild", "schablone", "vektorgrafik", "clipart",
        "wandtattoo", "wandsticker", "aufkleber", "wandleuchte", "lampe",
        "poster", "leinwand", "bild", "bilder", "teppich", "bettwäsche",
        "vorhang", "gardine", "möbel", "bett", "wickelkommode",
        "erwachsene", "wohnzimmer", "schlafzimmer", "küche", "bad", "flur"
    ],
    "fr": [
        "leroy merlin", "castorama", "brico depot", "bricorama", "ikea", "amazon",
        "cdiscount", "aliexpress", "temu", "shein", "action",
        "gratuit", "pas cher", "discount", "promo", "solde", "occasion",
        "diy", "tuto", "comment poser", "avis", "forum", "youtube", "video",
        "sticker", "stickers", "autocollant", "affiche", "poster", "tableau",
        "lampe", "veilleuse", "rideau", "tapis", "lit",
        "adulte", "salon", "chambre adulte", "cuisine", "salle de bain"
    ],
    "es": [
        "leroy merlin", "bricomart", "obramat", "bauhaus", "ikea", "amazon",
        "aliexpress", "temu", "shein", "wallapop", "milanuncios",
        "gratis", "barato", "economico", "descuento", "oferta", "segunda mano",
        "diy", "tutorial", "como poner", "opiniones", "foro", "youtube", "video",
        "vinilo", "pegatina", "sticker", "poster", "lamina", "cuadro",
        "lampara", "cortina", "alfombra", "cama",
        "adulto", "salon", "dormitorio matrimonio", "cocina", "baño"
    ]
}

@handle_google_ads_errors
def apply_negative_shield(req: ApplyNegativeShieldRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Deploys language-specific Negative Keyword Shields (DE, FR, ES) to block competitors, DIY, and freebie seekers.
    """
    client = get_ads_client()
    cs_service = client.get_service("CampaignCriterionService")
    ga_service = client.get_service("GoogleAdsService")
    
    # 1. Fetch existing campaign negatives
    query = f"""
        SELECT campaign_criterion.keyword.text
        FROM campaign_criterion
        WHERE campaign.id = {req.campaign_id}
          AND campaign_criterion.negative = TRUE
          AND campaign_criterion.status != 'REMOVED'
    """
    existing_words = set()
    for row in ga_service.search(customer_id=customer_id, query=query):
        if row.campaign_criterion.keyword and row.campaign_criterion.keyword.text:
            existing_words.add(row.campaign_criterion.keyword.text.lower())
            
    # 2. Gather target words
    shield_words = NEGATIVE_SHIELDS.get(req.language.lower(), [])
    custom_words = req.negative_words or []
    all_target_words = shield_words + custom_words
    
    new_words = [w.lower().strip() for w in all_target_words if w.lower().strip() not in existing_words]
    
    if not new_words:
        return f"Campaign {req.campaign_id} already has all {len(shield_words)} negative shield keywords deployed."
        
    operations = []
    campaign_resource = client.get_service("CampaignService").campaign_path(customer_id, req.campaign_id)
    
    for word in new_words:
        op = client.get_type("CampaignCriterionOperation")
        crit = op.create
        crit.campaign = campaign_resource
        crit.negative = True
        crit.keyword.text = word
        crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        operations.append(op)
        
    # Batch mutate in chunks of 500
    added_count = 0
    chunk_size = 500
    for i in range(0, len(operations), chunk_size):
        chunk = operations[i:i + chunk_size]
        cs_service.mutate_campaign_criteria(customer_id=customer_id, operations=chunk)
        added_count += len(chunk)
        
    return f"Successfully applied {req.language.upper()} negative shield to Campaign {req.campaign_id}: added {added_count} negative keywords."

@handle_google_ads_errors
def add_negative_keywords(campaign_id: str, keywords: List[str], customer_id: str = CUSTOMER_ID) -> str:
    """
    Directly adds negative keywords to a campaign. Automatically sets match type:
    PHRASE if keyword contains whitespace, BROAD if single word.
    """
    client = get_ads_client()
    cs_service = client.get_service("CampaignCriterionService")
    campaign_service = client.get_service("CampaignService")
    
    operations = []
    for kw in keywords:
        text = kw.strip()
        if not text:
            continue
        op = client.get_type("CampaignCriterionOperation")
        criterion = op.create
        criterion.campaign = campaign_service.campaign_path(customer_id, campaign_id)
        criterion.negative = True
        criterion.keyword.text = text
        
        if " " in text:
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
        else:
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            
        operations.append(op)
        
    if not operations:
        return f"No valid keywords provided for campaign {campaign_id}."
        
    response = cs_service.mutate_campaign_criteria(customer_id=customer_id, operations=operations)
    return f"Success: Added {len(response.results)} negative keywords to campaign {campaign_id}."

@handle_google_ads_errors
def remove_negative_keyword(req: RemoveNegativeKeywordRequest, customer_id: str = CUSTOMER_ID) -> str:
    """
    Removes one campaign-level negative keyword found by its exact text (and match type when ambiguous).
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    cs_service = client.get_service("CampaignCriterionService")

    text = req.keyword_text.replace("'", "\\'")
    query = f"""
        SELECT campaign_criterion.resource_name, campaign_criterion.keyword.text, campaign_criterion.keyword.match_type
        FROM campaign_criterion
        WHERE campaign.id = {req.campaign_id}
          AND campaign_criterion.negative = TRUE
          AND campaign_criterion.type = 'KEYWORD'
          AND campaign_criterion.keyword.text = '{text}'
    """
    found = list(ga_service.search(customer_id=customer_id, query=query))
    if req.match_type:
        found = [r for r in found if r.campaign_criterion.keyword.match_type.name == req.match_type]
    if not found:
        raise ValueError(f"Negative keyword '{req.keyword_text}' not found in campaign {req.campaign_id}.")
    if len(found) > 1:
        types = ", ".join(r.campaign_criterion.keyword.match_type.name for r in found)
        raise ValueError(f"'{req.keyword_text}' exists with several match types ({types}); pass match_type.")

    crit = found[0].campaign_criterion
    operation = client.get_type("CampaignCriterionOperation")
    operation.remove = crit.resource_name
    cs_service.mutate_campaign_criteria(customer_id=customer_id, operations=[operation])
    return f"Removed negative keyword '{crit.keyword.text}' [{crit.keyword.match_type.name}] from campaign {req.campaign_id}."

@handle_google_ads_errors
def mine_search_terms(campaign_id: str, days: int = 14, customer_id: str = CUSTOMER_ID) -> List[SearchTermWasteRecord]:
    """
    Mines search terms from search_term_view to identify irrelevant traffic and budget waste.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    end_date = date.today().isoformat()
    
    query = f"""
        SELECT
            search_term_view.search_term,
            metrics.clicks,
            metrics.impressions,
            metrics.cost_micros,
            metrics.ctr
        FROM search_term_view
        WHERE campaign.id = {campaign_id}
          AND segments.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY metrics.cost_micros DESC
        LIMIT 50
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    
    results = []
    waste_patterns = ["tattoo", "sticker", "leuchte", "lampe", "poster", "wohnzimmer", "erwachsen", "gratis", "free"]
    
    for row in response:
        st = row.search_term_view.search_term
        clicks = row.metrics.clicks or 0
        impressions = row.metrics.impressions or 0
        cost_micros = row.metrics.cost_micros or 0
        ctr = (row.metrics.ctr or 0.0) * 100
        
        # Check if candidate for negative
        is_candidate = any(p in st.lower() for p in waste_patterns)
        action = "EXACT_NEGATIVE" if is_candidate else None
        
        results.append(SearchTermWasteRecord(
            search_term=st,
            clicks=clicks,
            impressions=impressions,
            cost_micros=cost_micros,
            cost_eur=round(cost_micros / 1_000_000.0, 2),
            ctr_percent=round(ctr, 2),
            suggested_negative_action=action
        ))
    return results

@handle_google_ads_errors
def audit_campaign_4level_shield(campaign_id: str, customer_id: str = CUSTOMER_ID) -> Dict[str, Any]:
    """
    Comprehensive 4-Level Quality Audit:
    Level 1: Campaign settings & Budget
    Level 1 also checks primary_status and the Maximize Clicks CPC ceiling.
    Level 2: Ad Groups (bids are checked only for MANUAL_CPC campaigns)
    Level 3: RSA copy (15/4 matrix, WELCOME3 promo, Ad Strength notes)
    Level 4: Negative Keyword Shield strength
    Returns an objective 0-100% Quality Score.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")
    
    score = 100
    deductions = []
    notes = []
    
    # Level 1: Campaign Check
    q_c = f"""
        SELECT campaign.name, campaign.status, campaign.bidding_strategy_type,
               campaign.target_spend.cpc_bid_ceiling_micros,
               campaign.primary_status, campaign.primary_status_reasons,
               campaign_budget.amount_micros
        FROM campaign WHERE campaign.id = {campaign_id}
    """
    c_res = list(ga_service.search(customer_id=customer_id, query=q_c))
    if not c_res:
        raise ValueError(f"Campaign {campaign_id} not found.")
    
    c = c_res[0].campaign
    c_name = c.name
    strategy = c.bidding_strategy_type.name
    ceiling_micros = c.target_spend.cpc_bid_ceiling_micros
    ceiling_eur = round(ceiling_micros / 1_000_000.0, 2) if ceiling_micros else None
    c_budget_eur = (c_res[0].campaign_budget.amount_micros or 0) / 1_000_000.0
    if c.primary_status.name == "MISCONFIGURED":
        score -= 30
        reasons = ", ".join(r.name for r in c.primary_status_reasons)
        deductions.append(f"Level 1: Campaign is MISCONFIGURED ({reasons})")
    if c_budget_eur < 2.0:
        score -= 10
        deductions.append(f"Level 1: Daily budget is low ({c_budget_eur:.2f} EUR < 2.00 EUR)")
    if strategy == "TARGET_SPEND" and not ceiling_micros:
        score -= 15
        deductions.append("Level 1: Maximize Clicks CPC ceiling is not set (uncapped)")
        
    # Level 2: Ad Groups Check
    q_ag = f"SELECT ad_group.id, ad_group.name, ad_group.cpc_bid_micros FROM ad_group WHERE campaign.id = {campaign_id} AND ad_group.status != 'REMOVED'"
    ag_res = list(ga_service.search(customer_id=customer_id, query=q_ag))
    if not ag_res:
        score -= 30
        deductions.append("Level 2: No active ad groups found in campaign!")
    elif strategy == "MANUAL_CPC":
        # Ad group bids only drive auctions under manual bidding; TARGET_SPEND ignores them
        for row in ag_res:
            bid_eur = (row.ad_group.cpc_bid_micros or 0) / 1_000_000.0
            if bid_eur <= 0.01:
                score -= 25
                deductions.append(f"Level 2: Ad group '{row.ad_group.name}' has a {bid_eur:.2f} EUR manual CPC bid")
                
    # Level 3: RSA Copy Check
    q_ads = f"""
        SELECT ad_group.name,
               ad_group_ad.ad_strength,
               ad_group_ad.ad.responsive_search_ad.headlines, 
               ad_group_ad.ad.responsive_search_ad.descriptions,
               ad_group_ad.ad.final_urls
        FROM ad_group_ad
        WHERE campaign.id = {campaign_id}
          AND ad_group_ad.status = 'ENABLED'
          AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
    """
    ads_res = list(ga_service.search(customer_id=customer_id, query=q_ads))
    if not ads_res:
        score -= 30
        deductions.append("Level 3: No active RSA ads found in campaign!")
    else:
        for i, row in enumerate(ads_res, 1):
            h_count = len(row.ad_group_ad.ad.responsive_search_ad.headlines)
            d_count = len(row.ad_group_ad.ad.responsive_search_ad.descriptions)
            urls = list(row.ad_group_ad.ad.final_urls)
            
            if h_count < 15:
                score -= (15 - h_count) * 2
                deductions.append(f"Level 3: RSA #{i} headlines count {h_count}/15 (Missing {15 - h_count} headlines)")
            if d_count < 4:
                score -= (4 - d_count) * 5
                deductions.append(f"Level 3: RSA #{i} descriptions count {d_count}/4 (Missing {4 - d_count} descriptions)")
            if not any("coupon=WELCOME3" in u for u in urls):
                score -= 15
                deductions.append(f"Level 3: RSA #{i} final URL is missing mandatory ?coupon=WELCOME3")
            strength = row.ad_group_ad.ad_strength.name
            if strength in ("POOR", "AVERAGE"):
                notes.append(f"Level 3: RSA #{i} in '{row.ad_group.name}' has Ad Strength {strength}")
                
    # Level 4: Negative Keyword Shield
    q_neg = f"""
        SELECT campaign_criterion.criterion_id 
        FROM campaign_criterion 
        WHERE campaign.id = {campaign_id} 
          AND campaign_criterion.negative = TRUE
    """
    neg_res = list(ga_service.search(customer_id=customer_id, query=q_neg))
    neg_count = len(neg_res)
    if neg_count < 20:
        score -= 20
        deductions.append(f"Level 4: Negative keyword shield is weak ({neg_count} keywords < 20 target)")
        
    final_score = max(0, score)
    return {
        "campaign_id": campaign_id,
        "campaign_name": c_name,
        "bidding_strategy": strategy,
        "cpc_ceiling_eur": ceiling_eur,
        "quality_score_percent": final_score,
        "status": "PASS (100/100)" if final_score == 100 else ("NEEDS_OPTIMIZATION" if final_score >= 70 else "CRITICAL"),
        "deductions": deductions,
        "notes": notes
    }

@handle_google_ads_errors
def get_daily_performance(days: int = 14, customer_id: str = CUSTOMER_ID) -> List[Dict[str, Any]]:
    """
    Fetches daily impressions, clicks, cost (EUR), and day-of-week breakdown per campaign.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")

    start_date = (date.today() - timedelta(days=days)).isoformat()
    end_date = date.today().isoformat()
    query = f"""
        SELECT
            segments.date,
            segments.day_of_week,
            campaign.name,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks
        FROM campaign
        WHERE segments.date >= '{start_date}' AND segments.date <= '{end_date}'
          AND campaign.status != 'REMOVED'
        ORDER BY segments.date ASC
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    output = []
    for row in response:
        output.append({
            "date": row.segments.date,
            "day_of_week": row.segments.day_of_week.name if hasattr(row.segments.day_of_week, "name") else str(row.segments.day_of_week),
            "campaign": row.campaign.name,
            "cost_eur": round((row.metrics.cost_micros or 0) / 1_000_000.0, 2),
            "clicks": row.metrics.clicks or 0,
            "impressions": row.metrics.impressions or 0
        })
    return output

@handle_google_ads_errors
def get_impression_share_loss(days: int = 7, customer_id: str = CUSTOMER_ID) -> List[Dict[str, Any]]:
    """
    Fetches Impression Share and Lost Impression Share due to Budget and Ad Rank for active campaigns.
    """
    client = get_ads_client()
    ga_service = client.get_service("GoogleAdsService")

    start_date = (date.today() - timedelta(days=days)).isoformat()
    end_date = date.today().isoformat()
    query = f"""
        SELECT
            campaign.name,
            metrics.search_impression_share,
            metrics.search_budget_lost_impression_share,
            metrics.search_rank_lost_impression_share
        FROM campaign
        WHERE segments.date >= '{start_date}' AND segments.date <= '{end_date}'
          AND campaign.status != 'REMOVED'
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    output = []
    for row in response:
        is_val = f"{row.metrics.search_impression_share * 100:.1f}%" if row.metrics.search_impression_share else "<10%"
        budget_lost = f"{row.metrics.search_budget_lost_impression_share * 100:.1f}%" if row.metrics.search_budget_lost_impression_share else "0%"
        rank_lost = f"{row.metrics.search_rank_lost_impression_share * 100:.1f}%" if row.metrics.search_rank_lost_impression_share else "0%"
        output.append({
            "campaign": row.campaign.name,
            "search_impression_share": is_val,
            "lost_to_budget": budget_lost,
            "lost_to_rank": rank_lost
        })
    return output

@handle_google_ads_errors
def auto_fix_collisions_and_dupes(customer_id: str = CUSTOMER_ID) -> Dict[str, Any]:
    """
    Scans active campaigns for duplicate keywords between High Intent and Core/Jungle campaigns,
    and automatically pauses dupes in Core/Jungle.
    """
    client = get_ads_client()
    ga = client.get_service("GoogleAdsService")
    agc_service = client.get_service("AdGroupCriterionService")
    
    q_keys = """
        SELECT
          ad_group_criterion.resource_name,
          ad_group_criterion.keyword.text,
          ad_group.name,
          campaign.id,
          campaign.name
        FROM ad_group_criterion
        WHERE ad_group_criterion.type = 'KEYWORD'
          AND ad_group_criterion.status = 'ENABLED'
          AND campaign.status = 'ENABLED'
    """
    hi_keys = set()
    core_kw_map = []
    
    for r in ga.search(customer_id=customer_id, query=q_keys):
        text = r.ad_group_criterion.keyword.text.lower()
        camp_name = r.campaign.name
        rn = r.ad_group_criterion.resource_name
        
        if "High Intent" in camp_name:
            hi_keys.add(text)
        else:
            core_kw_map.append((text, rn, camp_name, r.ad_group.name))
            
    dupes_paused = []
    for text, rn, camp_name, ag_name in core_kw_map:
        if text in hi_keys:
            op = client.get_type("AdGroupCriterionOperation")
            item = op.update
            item.resource_name = rn
            item.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
            op.update_mask.CopyFrom(protobuf_helpers.field_mask(None, item._pb))
            agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=[op])
            dupes_paused.append(f"Paused '{text}' in {camp_name} -> {ag_name}")
            
    return {
        "status": "COLLISIONS_RESOLVED" if dupes_paused else "ZERO_COLLISIONS",
        "paused_count": len(dupes_paused),
        "details": dupes_paused
    }

@handle_google_ads_errors
def fetch_google_ai_recommendations(customer_id: str = CUSTOMER_ID) -> List[Dict[str, Any]]:
    """
    Queries Google Ads Recommendations API to pull Google AI suggestions with estimated impact.
    """
    client = get_ads_client()
    ga = client.get_service("GoogleAdsService")
    
    q = """
        SELECT
            recommendation.resource_name,
            recommendation.type,
            recommendation.campaign,
            campaign.name
        FROM recommendation
    """
    recs = list(ga.search(customer_id=customer_id, query=q))
    output = []
    for r in recs:
        rec_type = r.recommendation.type_.name if hasattr(r.recommendation.type_, "name") else str(r.recommendation.type_)
        c_name = r.campaign.name if r.campaign and r.campaign.name else "Account-level"
        output.append({
            "type": rec_type,
            "campaign": c_name,
            "resource_name": r.recommendation.resource_name
        })
    return output

@handle_google_ads_errors
def search_keyword_ideas(seeds: List[str], language_id: str = "1001", location_ids: List[str] = ["2276"]) -> List[Dict[str, Any]]:
    """
    Fetches keyword ideas and search volumes using Google Ads KeywordPlanIdeaService.
    Default: German (1001), Germany (2276).
    """
    client = get_ads_client()
    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = CUSTOMER_ID
    request.language = client.get_service("GoogleAdsService").language_constant_path(language_id)
    for loc in location_ids:
        request.geo_target_constants.append(
            client.get_service("GoogleAdsService").geo_target_constant_path(loc)
        )
    request.include_adult_keywords = False
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    request.keyword_seed.keywords.extend(seeds)
    
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    try:
        ideas = keyword_plan_idea_service.generate_keyword_ideas(request=request)
        ideas_list = list(ideas)
    except Exception as e:
        err_str = str(e)
        if "DEVELOPER_TOKEN_NOT_APPROVED" in err_str or "USER_PERMISSION_DENIED" in err_str:
            fallback_client = get_ads_client("3508202294")
            request.customer_id = "3971857500"
            request.language = fallback_client.get_service("GoogleAdsService").language_constant_path(language_id)
            del request.geo_target_constants[:]
            for loc in location_ids:
                request.geo_target_constants.append(
                    fallback_client.get_service("GoogleAdsService").geo_target_constant_path(loc)
                )
            keyword_plan_idea_service = fallback_client.get_service("KeywordPlanIdeaService")
            ideas = keyword_plan_idea_service.generate_keyword_ideas(request=request)
            ideas_list = list(ideas)
        else:
            raise e
            
    results = []
    for idea in ideas_list:
        metrics = idea.keyword_idea_metrics
        results.append({
            "keyword": idea.text,
            "monthly_volume": metrics.avg_monthly_searches or 0,
            "competition": metrics.competition.name if hasattr(metrics.competition, "name") else str(metrics.competition)
        })
    results.sort(key=lambda x: x["monthly_volume"], reverse=True)
    return results[:50]

