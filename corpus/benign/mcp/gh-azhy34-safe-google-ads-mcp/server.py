import os
import sys
import io
import json
import functools
from pathlib import Path
from typing import List, Literal, Optional
from mcp.server.fastmcp import FastMCP

# Force UTF-8 encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add current folder to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from core.config import CUSTOMER_ID
from shield.error_shield import build_request
from shield.telemetry import current_tool
from shield import cloud_sink
from shield.models_campaign import CampaignStatusUpdateRequest, CampaignBudgetUpdateRequest, CampaignCeilingStepRequest, IdArguments
from shield.models_adgroup import AdGroupBidUpdateRequest, KeywordStatusUpdateRequest
from shield.models_ad import DeployGoldenRSARequest
from shield.models_asset import LinkAssetRequest, UnlinkAssetRequest, CreatePriceAssetRequest, SyncPriceExtensionRequest
from shield.models_criterion import ApplyNegativeShieldRequest, RemoveNegativeKeywordRequest

from tools.campaign_tools import (
    list_campaigns, get_campaign_detail, 
    update_campaign_status, update_campaign_budget, step_campaign_cpc_ceiling,
    get_campaign_targeting_overview as targeting_func
)
from tools.adgroup_tools import (
    list_ad_groups, update_ad_group_bid, update_keyword_status,
    get_ad_group_keywords as adgroup_keywords_func
)
from tools.rsa_tools import list_campaign_ads, deploy_golden_rsa as rsa_deploy_func
from tools.asset_tools import (
    list_account_assets, 
    get_assets_associations as assocs_func, 
    get_assets_performance as perf_func, 
    get_assets_diversity as diversity_func,
    link_asset_to_entity as link_func, 
    unlink_asset_from_entity as unlink_func,
    create_price_asset as create_price_func,
    sync_price_extension as sync_price_func,
    get_campaign_assets_overview as assets_overview_func
)
from tools.negative_tools import (
    apply_negative_shield as neg_shield_func,
    add_negative_keywords as add_neg_func,
    remove_negative_keyword as remove_neg_func,
    mine_search_terms,
    audit_campaign_4level_shield as audit_func,
    get_daily_performance as daily_perf_func,
    get_impression_share_loss as imp_share_func,
    auto_fix_collisions_and_dupes as fix_collisions_func,
    fetch_google_ai_recommendations as ai_recs_func,
    search_keyword_ideas as keyword_ideas_func
)
from tools.history_tools import get_change_history as change_history_func, verify_changes_logged as verify_logged_func
from tools.observability_tools import (
    get_cloud_logs as cloud_logs_func,
    get_cloud_trace as cloud_trace_func,
    analyze_tool_health as tool_health_func
)
from tools.eval_tools import evaluate_agent_process as process_eval_func
from tools.preflight_tools import preflight_log_check as preflight_func

# Initialize FastMCP Server
mcp = FastMCP("Google Ads")

def mcp_tool():
    """
    @mcp.tool() that also tells the journal which MCP tool the agent called (shield.telemetry.current_tool): the entry
    gets `tool` next to `function`, and the span is named 'tools/call <tool>' as on Google's MCP servers.
    functools.wraps keeps the signature and docstring FastMCP builds the tool schema from.
    """
    def decorate(fn):
        @functools.wraps(fn)
        def call(*args, **kwargs):
            token = current_tool.set(fn.__name__)
            try:
                return fn(*args, **kwargs)
            finally:
                current_tool.reset(token)
        return mcp.tool()(call)
    return decorate

def _bad_ids(function: str, action_type: str = "READ", **ids) -> Optional[str]:
    """Refuses a non-numeric campaign / ad group ID before it reaches a GAQL query; logged as REQUEST_REJECTED."""
    _, rejected = build_request(function, IdArguments, action_type=action_type, **{k: v for k, v in ids.items() if v is not None})
    return rejected

# --- STEP 0: MANDATORY LOG CHECK (every tool below refuses until it has passed) ---

# [чтение] ОБЯЗАТЕЛЬНЫЙ первый шаг сессии: проверка логов (ошибки и аномалии инструмента, правки мимо MCP, нарушения порядка работы). Пока она не пройдена, все рекламные тулы отвечают PREFLIGHT_REQUIRED; при находках агент показывает их владельцу и после его «продолжай» вызывает с acknowledge=True.
@mcp_tool()
def preflight_log_check(acknowledge: bool = False, days: Optional[int] = None) -> str:
    """
    MANDATORY before any analysis or change of the ad account, once per session: until it has passed, every other
    Google Ads tool answers PREFLIGHT_REQUIRED (only the journal tools stay open). It runs three checks over the time
    since the last accepted check (default: the last 7 days; `days` 1-30 sets the span by hand):
    TOOL_HEALTH (errors and anomalies of this MCP), OUTSIDE_CHANGES (account changes no MCP call made: scripts, other
    agents, the interface), AGENT_PROCESS (sessions that broke the working order). Verdict OK opens the ad tools.
    Verdict ATTENTION keeps them shut: show the findings to the owner, do not start the analysis, wait for their word
    to continue, and only then call preflight_log_check(acknowledge=True), which opens the tools and moves the
    checkpoint so accepted findings are not reported again. Read-only: it changes nothing in the ad account.
    """
    res = preflight_func(acknowledge, days)
    return res.model_dump_json(indent=2)

# --- LEVEL 1: CAMPAIGN TOOLS ---

# [чтение] Список кампаний (активные и на паузе): дневной бюджет, стратегия ставок, потолок CPC. В журнале: list_campaigns.
@mcp_tool()
def get_campaigns() -> str:
    """
    List all active and paused Google Ads campaigns with daily budgets, bidding strategies
    and the Maximize Clicks CPC ceiling (cpc_ceiling_eur).
    Returns typed JSON payload protected by Two-Layer Pydantic Error Shield.
    """
    res = list_campaigns()
    return res.model_dump_json(indent=2)

# [чтение] Детали одной кампании по ID: бюджет, способ показа, стратегия, потолок CPC. В журнале: get_campaign_detail.
@mcp_tool()
def get_campaign_details(campaign_id: str = "24015242821") -> str:
    """
    Get detailed budget, delivery method, bidding strategy and Maximize Clicks CPC ceiling for a single campaign by ID.
    """
    rejected = _bad_ids("get_campaign_detail", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = get_campaign_detail(campaign_id)
    return res.model_dump_json(indent=2)

# [запись] Включить или поставить на паузу кампанию по ID. В журнале: update_campaign_status.
@mcp_tool()
def toggle_campaign_status(campaign_id: str, enabled: bool) -> str:
    """
    Enable or pause a campaign by ID. Uses official sparse update_mask.
    """
    req, rejected = build_request("update_campaign_status", CampaignStatusUpdateRequest, campaign_id=campaign_id, enabled=enabled)
    if rejected:
        return rejected
    res = update_campaign_status(req)
    return res.model_dump_json(indent=2)

# [запись] Изменить дневной бюджет кампании в EUR (допустимо 1–100). В журнале: update_campaign_budget.
@mcp_tool()
def set_campaign_daily_budget(campaign_id: str, budget_eur: float) -> str:
    """
    Updates campaign daily budget in EUR with bounds validation (1.00 - 100.00 EUR).
    """
    req, rejected = build_request("update_campaign_budget", CampaignBudgetUpdateRequest, campaign_id=campaign_id, budget_eur=budget_eur)
    if rejected:
        return rejected
    res = update_campaign_budget(req)
    return res.model_dump_json(indent=2)

# [чтение] Аудит таргетинга: гео, языки, расписание показов, корректировки устройств, сети (Поиск/КМС).
@mcp_tool()
def get_campaign_targeting_overview(campaign_id: str = "24015242821") -> str:
    """
    Audits campaign targeting criteria (Geo Locations, Languages, Dayparting Ad Schedules, Device Modifiers)
    and network settings (Google Search vs Display Network).
    """
    rejected = _bad_ids("get_campaign_targeting_overview", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = targeting_func(campaign_id)
    return res.model_dump_json(indent=2)

# --- LEVEL 2: ADGROUP & BIDDING TOOLS ---

# [чтение] Группы объявлений с базовыми CPC-ставками и статусом показа. В журнале: list_ad_groups.
@mcp_tool()
def get_ad_groups(campaign_id: Optional[str] = None) -> str:
    """
    Lists ad groups with their base CPC bids in EUR and serving status.
    """
    rejected = _bad_ids("list_ad_groups", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = list_ad_groups(campaign_id)
    return res.model_dump_json(indent=2)

# [запись] Сдвинуть потолок CPC кампании на ±0.05 € (границы 0.10–3.00). Главный рычаг ставок: у всех кампаний Maximize Clicks. В журнале: step_campaign_cpc_ceiling.
@mcp_tool()
def step_bid_threshold(campaign_id: str, direction: Literal["+0.05", "-0.05"] = "+0.05") -> str:
    """
    Steps the campaign's Maximize Clicks CPC ceiling (target_spend.cpc_bid_ceiling_micros)
    by +0.05 or -0.05 EUR (bounds 0.10-3.00 EUR). This is the bid lever for all Target Account
    campaigns, which use TARGET_SPEND; ad group bids are ignored under that strategy.
    """
    req, rejected = build_request("step_campaign_cpc_ceiling", CampaignCeilingStepRequest, campaign_id=campaign_id, direction=direction)
    if rejected:
        return rejected
    res = step_campaign_cpc_ceiling(req)
    return res.model_dump_json(indent=2)

# [запись] Ставка CPC группы; работает только в MANUAL_CPC, иначе отказ. В журнале: update_ad_group_bid.
@mcp_tool()
def set_ad_group_cpc_bid(ad_group_id: str, new_bid_eur: float) -> str:
    """
    Sets the base CPC bid of an Ad Group. Works only in MANUAL_CPC campaigns and refuses otherwise,
    because Maximize Clicks (TARGET_SPEND) ignores ad group bids without error.
    """
    req, rejected = build_request("update_ad_group_bid", AdGroupBidUpdateRequest, ad_group_id=ad_group_id, new_bid_eur=new_bid_eur)
    if rejected:
        return rejected
    res = update_ad_group_bid(req)
    return res.model_dump_json(indent=2)

# [чтение] Ключи группы: Quality Score, тип соответствия, прогноз CTR, релевантность, индивидуальные ставки.
@mcp_tool()
def get_ad_group_keywords(ad_group_id: str) -> str:
    """
    Lists all biddable keywords in an Ad Group with their Google Quality Scores (1-10),
    match types (EXACT, PHRASE, BROAD), predicted CTR, ad relevance, and override bids.
    """
    rejected = _bad_ids("get_ad_group_keywords", ad_group_id=ad_group_id)
    if rejected:
        return rejected
    res = adgroup_keywords_func(ad_group_id)
    return res.model_dump_json(indent=2)

# [запись] Пауза/включение одного позитивного ключа по criterion_id (минус-слова не трогает). В журнале: update_keyword_status.
@mcp_tool()
def set_keyword_status(ad_group_id: str, criterion_id: str, enabled: bool) -> str:
    """
    Pauses (enabled=False) or enables one positive keyword in an ad group.
    criterion_id comes from get_ad_group_keywords. Refuses negative keywords and non-keyword criteria.
    """
    req, rejected = build_request("update_keyword_status", KeywordStatusUpdateRequest, ad_group_id=ad_group_id, criterion_id=criterion_id, enabled=enabled)
    if rejected:
        return rejected
    res = update_keyword_status(req)
    return res.model_dump_json(indent=2)

# --- LEVEL 3: RSA ADS TOOLS ---

# [чтение] RSA-объявления кампании со всеми 15 заголовками и 4 описаниями. В журнале: list_campaign_ads.
@mcp_tool()
def get_campaign_ads(campaign_id: str = "24015242821") -> str:
    """
    Lists all active/paused Responsive Search Ads with all 15 headlines and 4 descriptions.
    """
    rejected = _bad_ids("list_campaign_ads", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = list_campaign_ads(campaign_id)
    return res.model_dump_json(indent=2)

# [запись] Создать «золотое» RSA: 15 заголовков (≤30) + 4 описания (≤90), H1 закреплён с DKI, в URL ?coupon=WELCOME3; при 3 активных RSA ставит на паузу самое старое.
@mcp_tool()
def deploy_golden_rsa(
    ad_group_id: str,
    final_url: str,
    headlines: List[str],
    descriptions: List[str],
    pinned_h1_dki: str,
    path1: str = "Tapete",
    path2: str = "Kinder"
) -> str:
    """
    Deploys a Golden RSA with strict 15/4 validation:
    - Exactly 15 headlines (<=30 chars); headlines[0] must equal pinned_h1_dki
    - Exactly 4 descriptions (<=90 chars)
    - headlines[0] is pinned to Headline 1 and must use Dynamic Keyword Insertion ({KeyWord:...})
    - Mandatory ?coupon=WELCOME3 in URL
    - If 3 RSAs are already enabled, pauses only the oldest one, atomically with the create.
    """
    req, rejected = build_request(
        "deploy_golden_rsa", DeployGoldenRSARequest,
        ad_group_id=ad_group_id,
        final_url=final_url,
        headlines=headlines,
        descriptions=descriptions,
        pinned_h1_dki=pinned_h1_dki,
        path1=path1,
        path2=path2
    )
    if rejected:
        return rejected
    res = rsa_deploy_func(req)
    return res.model_dump_json(indent=2)

# --- LEVEL 4: ASSETS (OBJECTS) TOOLS (Matching Google Ads UI Tabs) ---

# [чтение] Вкладка «Связи»: какие объекты привязаны к аккаунту/кампании/группе (фильтр по уровню и типу).
@mcp_tool()
def get_assets_associations(level: Optional[str] = None, field_type: Optional[str] = None) -> str:
    """
    Google Ads UI Tab 1: 'Связи' (Associations).
    Retrieves linked assets across Account (CUSTOMER), CAMPAIGN, and AD_GROUP levels.
    Supports filtering by level ('CUSTOMER', 'CAMPAIGN', 'AD_GROUP') and field_type ('IMAGE', 'SITELINK', 'CALLOUT', 'PRICE', 'STRUCTURED_SNIPPET', 'PROMOTION', 'BUSINESS_LOGO', 'BUSINESS_NAME', etc.).
    Returns text previews, image CDN URLs, and binding status.
    """
    res = assocs_func(level=level, field_type=field_type)
    return res.model_dump_json(indent=2)

# [чтение] Вкладка «Эффективность»: показы, клики, CTR, расход и оценка Google по объектам за N дней.
@mcp_tool()
def get_assets_performance(days: int = 30, field_type: Optional[str] = None) -> str:
    """
    Google Ads UI Tab 2: 'Эффективность' (Asset Performance).
    Retrieves Impressions, Clicks, CTR %, Cost (EUR), and Google AI Performance Label (BEST, GOOD, LOW, LEARNING, NOT_APPLICABLE)
    for in-ad assets (Headlines, Descriptions, Landscape/Square Images) and extensions (Sitelinks, Snippets, Callouts, Price).
    Extensions have no Google label; their HEURISTIC_* label is a CTR-based estimate.
    """
    res = perf_func(days=days, field_type=field_type)
    return res.model_dump_json(indent=2)

# [чтение] Вкладка «Разнообразие»: полнота набора объектов (картинки, сайтлинки, сниппеты и т.д.), оценка 0–100%.
@mcp_tool()
def get_assets_diversity() -> str:
    """
    Google Ads UI Tab 3: 'Разнообразие объектов' (Asset Variety & Health).
    Audits active campaigns to ensure complete asset extension variety:
    Images (min 4), Sitelinks (min 4), Snippets, Callouts, Promotions, Price, Logo, and returns a 0-100% Quality Score.
    """
    res = diversity_func()
    return res.model_dump_json(indent=2)

# [запись] Привязать существующий объект к аккаунту, кампании или группе.
@mcp_tool()
def link_asset_to_entity(level: str, entity_id: str, asset_id: str, field_type: str) -> str:
    """
    Binds an existing asset to Account ('CUSTOMER'), Campaign ('CAMPAIGN'), or Ad Group ('AD_GROUP').
    field_type: IMAGE, SITELINK, CALLOUT, PROMOTION, STRUCTURED_SNIPPET, BUSINESS_NAME, BUSINESS_LOGO, PRICE.
    """
    req, rejected = build_request("link_asset_to_entity", LinkAssetRequest, level=level.upper(), entity_id=entity_id, asset_id=asset_id, field_type=field_type.upper())
    if rejected:
        return rejected
    res = link_func(req)
    return res.model_dump_json(indent=2)

# [запись] Отвязать объект от аккаунта, кампании или группы.
@mcp_tool()
def unlink_asset_from_entity(level: str, entity_id: str, asset_id: str, field_type: str) -> str:
    """
    Unlinks/removes an asset association from Account ('CUSTOMER'), Campaign ('CAMPAIGN'), or Ad Group ('AD_GROUP').
    """
    req, rejected = build_request("unlink_asset_from_entity", UnlinkAssetRequest, level=level.upper(), entity_id=entity_id, asset_id=asset_id, field_type=field_type.upper())
    if rejected:
        return rejected
    res = unlink_func(req)
    return res.model_dump_json(indent=2)

# [запись] Создать новый объект цен (Price Asset) с валидацией предложений.
@mcp_tool()
def create_price_asset(
    name: str,
    offerings: List[dict],
    price_type: str = "PRODUCT_TIERS",
    price_qualifier: str = "FROM",
    language_code: str = "de"
) -> str:
    """
    Creates a new Price Asset in Google Ads.
    price_type: PRODUCT_TIERS, PRODUCT_CATEGORIES, SERVICES.
    price_qualifier: FROM, UP_TO, AVERAGE, UNSPECIFIED.
    offerings: list of dicts with header, description, price_eur, final_url.
    """
    req, rejected = build_request(
        "create_price_asset",
        CreatePriceAssetRequest,
        name=name,
        price_type=price_type,
        price_qualifier=price_qualifier,
        language_code=language_code,
        offerings=offerings
    )
    if rejected:
        return rejected
    res = create_price_func(req)
    return res.model_dump_json(indent=2)

# [запись] Smart Facade: атомарная синхронизация цен (создание + поиск старых + отвязка + привязка)
@mcp_tool()
def sync_price_extension(
    entity_id: str,
    name: str,
    offerings: List[dict],
    level: str = "CAMPAIGN",
    price_type: str = "PRODUCT_TIERS",
    price_qualifier: str = "FROM",
    language_code: str = "de"
) -> str:
    """
    Smart Facade Macro Tool for Price Extensions:
    Atomically creates a new Price Asset with validated offerings (EUR prices, valid URLs, headers),
    discovers existing active Price Assets linked to the target entity, unlinks them, and links the new
    Price Asset in a single atomic flow.
    level: 'CAMPAIGN' (default), 'AD_GROUP', or 'CUSTOMER'.
    price_type: 'PRODUCT_TIERS' (default), 'PRODUCT_CATEGORIES', 'SERVICES'.
    price_qualifier: 'FROM' (default), 'UP_TO', 'AVERAGE', 'UNSPECIFIED'.
    language_code: 'de' (default).
    offerings: list of 3 to 8 dicts with 'header', 'description', 'price_eur', 'final_url'.
    """
    req, rejected = build_request(
        "sync_price_extension",
        SyncPriceExtensionRequest,
        entity_id=entity_id,
        level=level.upper(),
        name=name,
        offerings=offerings,
        price_type=price_type,
        price_qualifier=price_qualifier,
        language_code=language_code
    )
    if rejected:
        return rejected
    res = sync_price_func(req)
    return res.model_dump_json(indent=2)



# [чтение] Все картинки аккаунта с полноразмерными превью. В журнале: list_account_assets.
@mcp_tool()
def get_campaign_images() -> str:
    """
    Lists all image assets in the account with full-size CDN preview URLs.
    """
    res = list_account_assets("IMAGE")
    return res.model_dump_json(indent=2)

# [чтение] Матрица объектов кампании и её групп: какие типы подключены, каких не хватает.
@mcp_tool()
def get_campaign_assets_overview(campaign_id: str) -> str:
    """
    Inspects all Level 4 Assets (Objects) linked to a Campaign and its Ad Groups
    (Images, Sitelinks, Callouts, Structured Snippets, Promotions, Prices).
    Returns a comprehensive status matrix showing active and missing asset types.
    """
    rejected = _bad_ids("get_campaign_assets_overview", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = assets_overview_func(campaign_id)
    return res.model_dump_json(indent=2)

# --- LEVEL 5: NEGATIVE SHIELDS & AUDITS ---

# [запись] Залить языковой набор минус-слов (DE/FR/ES): DIY-магазины, «бесплатно», мебель.
@mcp_tool()
def apply_negative_shield(campaign_id: str, language: str = "de") -> str:
    """
    Deploys language-specific Negative Keyword Shield (DE, FR, ES) blocking DIY stores, gratis seekers, and furniture clutter.
    """
    req, rejected = build_request("apply_negative_shield", ApplyNegativeShieldRequest, campaign_id=campaign_id, language=language)
    if rejected:
        return rejected
    res = neg_shield_func(req)
    return res.model_dump_json(indent=2)

# [запись] Добавить минус-слова в кампанию (PHRASE если несколько слов, BROAD если одно).
@mcp_tool()
def add_negative_keywords(campaign_id: str, keywords: List[str]) -> str:
    """
    Directly adds negative keywords to a campaign. Automatically sets match type:
    PHRASE if keyword contains whitespace, BROAD if single word.
    """
    rejected = _bad_ids("add_negative_keywords", action_type="MUTATION", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = add_neg_func(campaign_id, keywords)
    return res.model_dump_json(indent=2)

# [запись] Удалить минус-слово кампании по тексту (match_type нужен при дублях).
@mcp_tool()
def remove_negative_keyword(campaign_id: str, keyword_text: str, match_type: Optional[str] = None) -> str:
    """
    Removes one campaign-level negative keyword by its exact text.
    match_type (EXACT, PHRASE, BROAD) is required only when the same text exists with several match types.
    """
    req, rejected = build_request("remove_negative_keyword", RemoveNegativeKeywordRequest, campaign_id=campaign_id, keyword_text=keyword_text, match_type=match_type)
    if rejected:
        return rejected
    res = remove_neg_func(req)
    return res.model_dump_json(indent=2)

# [чтение] Разбор поисковых запросов за N дней: нерелевантные без конверсий — кандидаты в минусы. В журнале: mine_search_terms.
@mcp_tool()
def mine_search_terms_and_harvest_negatives(campaign_id: str = "24015242821", days: int = 14) -> str:
    """
    Scans search_term_view to identify non-converting, irrelevant search queries leaking ad budget.
    """
    rejected = _bad_ids("mine_search_terms", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = mine_search_terms(campaign_id, days)
    return res.model_dump_json(indent=2)

# [чтение] Аудит кампании по 4 уровням (бюджет/потолок, группы, RSA, минус-щит), оценка 0–100%.
@mcp_tool()
def audit_campaign_4level_shield(campaign_id: str = "24015242821") -> str:
    """
    Comprehensive 4-Level Quality Audit:
    - Level 1: Campaign budget, primary status, Maximize Clicks CPC ceiling
    - Level 2: Ad Groups (bids checked only for MANUAL_CPC)
    - Level 3: RSA Copy (15/4 Matrix, WELCOME3 promo, Ad Strength notes)
    - Level 4: Negative Keyword Shield strength
    Returns an objective 0-100% Quality Score.
    """
    rejected = _bad_ids("audit_campaign_4level_shield", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = audit_func(campaign_id)
    return res.model_dump_json(indent=2)

# [чтение] Показы, клики, расход по дням и дням недели в разрезе кампаний.
@mcp_tool()
def get_daily_performance(days: int = 14) -> str:
    """
    Fetches daily impressions, clicks, cost (EUR), and day-of-week breakdown per campaign.
    """
    res = daily_perf_func(days)
    return res.model_dump_json(indent=2)

# [чтение] Доля показов и потери из-за бюджета и рейтинга объявления.
@mcp_tool()
def get_impression_share_loss(days: int = 7) -> str:
    """
    Fetches Impression Share and Lost Impression Share due to Budget and Ad Rank for active campaigns.
    """
    res = imp_share_func(days)
    return res.model_dump_json(indent=2)

# [чтение] История изменений аккаунта (1–30 дней): кто и что менял — UI, API, скрипты, авто-правила.
@mcp_tool()
def get_change_history(days: int = 7, campaign_id: Optional[str] = None, limit: int = 200) -> str:
    """
    Account change history (Google change_event, last 1-30 days): every change made via the Google Ads UI,
    the API (this MCP, scripts, other agents) or automated rules, with who made it and old -> new values.
    Use it to answer "what changed in the account"; the local audit log only sees calls made through this MCP.
    Newest first, at most `limit` events (1-500, default 200); `truncated` = true means older changes of the period
    were cut off: narrow days or campaign_id. changed_at is account time (Europe/Berlin), the journal is UTC.
    """
    rejected = _bad_ids("get_change_history", campaign_id=campaign_id)
    if rejected:
        return rejected
    res = change_history_func(days, campaign_id, limit)
    return res.model_dump_json(indent=2)

# [чтение] Сверка истории Google с журналом MCP: какие изменения сделаны через MCP, а какие мимо (скрипты, другие агенты). Изменения старше журнала не сверяются: вердикт NOT_VERIFIABLE_BEFORE_JOURNAL.
@mcp_tool()
def verify_changes_logged(days: int = 2, source: str = "local") -> str:
    """
    Reconciles Google's change history with the MCP audit log: which API changes in the account
    were made through this MCP (logged) and which were not (scripts, other agents). Also flags logged
    calls chained in one process (script_suspected) and logged mutations that left no change in the account.
    source="local": this machine's google-ads/logs/audit.jsonl; source="cloud": the online journal of every
    operator (needs the reader key), so other operators' MCP changes count as logged; source="auto": the online
    journal if it reaches back over the whole period, else the local file. Changes older than the journal cannot be
    checked (before_log_started); if that is all there is, the verdict is NOT_VERIFIABLE_BEFORE_JOURNAL. Read-only.
    """
    res = verify_logged_func(days, source)
    return res.model_dump_json(indent=2)

# --- OBSERVABILITY: ONLINE JOURNAL (Cloud Logging) AND TRACES (Cloud Trace) ---

# [чтение] Онлайн-журнал MCP из Cloud Logging со всех машин (фильтры: severity, operator, function, session_id); с него начинать разбор ошибок.
@mcp_tool()
def get_cloud_logs(hours: int = 24, severity: Optional[str] = None, operator: Optional[str] = None,
                   function: Optional[str] = None, request_id: Optional[str] = None, limit: int = 50,
                   session_id: Optional[str] = None, tool: Optional[str] = None) -> str:
    """
    Online journal of this MCP from every operator's machine (Cloud Logging, last 1-720 hours).
    Filters: severity = a minimum level (DEBUG observer reads, INFO read, NOTICE account change, WARNING rejected by the
    shield, ERROR failure, CRITICAL token dead; default INFO hides the observer's own DEBUG entries), operator,
    function (Python function, e.g. step_campaign_cpc_ceiling), tool (MCP tool name, e.g. step_bid_threshold; entries
    from 06.10.2026 on),
    request_id (Google Ads), session_id (one agent session = one MCP server process; every entry carries it).
    Returns counts by severity / operator / function / error code, the newest entries
    with args, error, latency and trace_id, and Logs Explorer links. Start any error or failure investigation here;
    the local audit.jsonl only has this machine's calls. Read-only.
    """
    res = cloud_logs_func(hours, severity, operator, function, request_id, limit, session_id, tool)
    return res.model_dump_json(indent=2)

# [чтение] Трейс одного вызова из Cloud Trace: тайминги и куда ушло время (Google Ads API или наш код).
@mcp_tool()
def get_cloud_trace(trace_id: str) -> str:
    """
    One tool call from Cloud Trace by trace_id (from get_cloud_logs or a ServiceResult telemetry):
    the call span and every Google Ads API call inside it with timings, and where the time went
    (Google Ads API vs our own code). Use it for slow or failed calls. Read-only.
    """
    res = cloud_trace_func(trace_id)
    return res.model_dump_json(indent=2)

# [чтение] Здоровье самого MCP по журналу: ошибки, p50/p95, находки (CODE_BUG, SLOW, AUTH…) и аномалии против предыдущего окна (новый код ошибки, всплеск, цикл отказов, правки одним процессом). Что чинить.
@mcp_tool()
def analyze_tool_health(days: int = 7, operator: Optional[str] = None, since: Optional[str] = None, source: str = "auto") -> str:
    """
    How well this MCP itself works, from the journal (online journal of every operator if the reader key is set,
    else this machine's audit.jsonl): per function calls, error rate, p50/p95 latency, error codes, and findings
    with what to fix and where — CODE_BUG (exception in tools/*.py), UNCLEAR_CONTRACT (agents rejected by the
    Pydantic shield and retrying), MISSING_PREVALIDATION (Google rejects what the shield could catch), SLOW,
    AUTH, GOOGLE_SIDE. Anomalies are measured against the window of equal length before it: NEW_ERROR_CODE,
    ERROR_SPIKE, REJECTION_BURST (agent looping on the shield), MUTATION_CHAIN (account changes made by one
    process, i.e. a script), UNKNOWN_OPERATOR (change from a clone without MCP_OPERATOR); baseline_calls /
    baseline_note say whether the baseline is long enough. since="2026-10-05" analyses only calls after a fix,
    to confirm it worked. source: auto (the online journal of every operator only if it reaches back to the window
    start, else this machine's audit.jsonl, which starts earlier), cloud, local. Read-only; code changes it suggests
    need the owner's approval.
    """
    res = tool_health_func(days, operator, since, source)
    return res.model_dump_json(indent=2)

# [чтение] Проверка, соблюдал ли агент порядок работы скилла (READ_FIRST, ONE_LEVER, AUTO_FIX_ALONE, VERIFY_AFTER); только советует. record=True пишет вердикты в облачный лог.
@mcp_tool()
def evaluate_agent_process(days: int = 7, since: Optional[str] = None, session_id: Optional[str] = None,
                           operator: Optional[str] = None, source: str = "auto", record: bool = False) -> str:
    """
    Did the agent follow the working order of the google-ads-mcp skill? Judges every session that changed the
    account, from the journal, with fixed rules (no model): READ_FIRST (get_change_history before the first change),
    ONE_LEVER (changes made together touch one lever group), AUTO_FIX_ALONE (auto_fix_collisions_and_dupes never
    together with other changes), VERIFY_AFTER (verify_changes_logged 15 min to 24 h after the changes).
    Returns PASS/FAIL/PENDING counts per rule and the FAIL/PENDING verdicts with session_id and trace_id.
    since="2026-10-05" or session_id narrow it; source: auto (online journal of every operator only if it reaches
    back to the window start, else this machine's audit.jsonl), cloud, local. record=True also writes the final verdicts to the cloud log
    google-ads-mcp-evals, each once. Advisory: it blocks nothing. Run it after any session that changed ads.
    """
    res = process_eval_func(days, since, session_id, operator, source, record)
    return res.model_dump_json(indent=2)

# [запись] Находит дубли ключей между High Intent и Core/Jungle и ставит дубли в Core/Jungle на паузу.
@mcp_tool()
def auto_fix_collisions_and_dupes() -> str:
    """
    Scans active campaigns for duplicate keywords between High Intent and Core/Jungle campaigns,
    and automatically pauses dupes in Core/Jungle.
    """
    res = fix_collisions_func()
    return res.model_dump_json(indent=2)

# [чтение] Рекомендации Google AI из Recommendations API (только просмотр).
@mcp_tool()
def fetch_google_ai_recommendations() -> str:
    """
    Queries Google Ads Recommendations API to audit Google AI suggestions.
    """
    res = ai_recs_func()
    return res.model_dump_json(indent=2)

# [чтение] Идеи ключей и объём поиска через KeywordPlanIdeaService (по умолчанию DE/Германия).
@mcp_tool()
def search_keyword_ideas(seeds: List[str], language_id: str = "1001", location_ids: List[str] = ["2276"]) -> str:
    """
    Fetches keyword ideas and search volumes using Google Ads KeywordPlanIdeaService.
    Default: German (1001), Germany (2276).
    """
    res = keyword_ideas_func(seeds, language_id, location_ids)
    return res.model_dump_json(indent=2)

if __name__ == "__main__":
    cloud_sink.start()
    mcp.run()
