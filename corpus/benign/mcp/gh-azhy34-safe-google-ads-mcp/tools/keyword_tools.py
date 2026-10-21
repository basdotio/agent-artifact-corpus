"""
Keyword Planner volumes by month and country (KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics).
Market data only: no stats or settings of the ad account are read and nothing is changed,
so it is open without preflight_log_check (shield/preflight.py) and is the only tool of keyword_server.py.
"""
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.client import get_ads_client
from core.config import CUSTOMER_ID
from shield.error_shield import handle_google_ads_errors
from shield.models_keyword import (
    COUNTRIES, KeywordVolumesRequest, KeywordVolumesReport, CountryVolumes, KeywordVolume, MonthVolume,
)

# Same way out as search_keyword_ideas: without an approved developer token Keyword Planner answers only through
# the test manager, and the test account has no search volumes
FALLBACK_LOGIN_ID = "3508202294"
FALLBACK_CUSTOMER_ID = "3971857500"
FALLBACK_ERRORS = ("DEVELOPER_TOKEN_NOT_APPROVED", "USER_PERMISSION_DENIED")

MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
          "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

# Keyword Planner limits requests per method (429 "Too many requests. Retry in 4 seconds"): one request per country
# trips it after a few countries, so wait as long as Google says and try again
RETRY_AFTER = re.compile(r"Retry in (\d+) seconds")
RATE_LIMITED = ("429", "RESOURCE_EXHAUSTED", "Resource has been exhausted")
MAX_RETRIES = 3
MAX_WAIT_SEC = 15

def _historical_metrics(client, customer_id: str, keywords: List[str], geo: str, language: str):
    googleads = client.get_service("GoogleAdsService")
    request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
    request.customer_id = customer_id
    request.keywords.extend(keywords)
    request.geo_target_constants.append(googleads.geo_target_constant_path(geo))
    request.language = googleads.language_constant_path(language)
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    return list(client.get_service("KeywordPlanIdeaService").generate_keyword_historical_metrics(request=request).results)

def _with_retry(state: Dict[str, Any], keywords: List[str], geo: str, language: str):
    for attempt in range(MAX_RETRIES + 1):
        try:
            return _historical_metrics(state["client"], state["customer_id"], keywords, geo, language)
        except Exception as e:
            text = str(e)
            if attempt == MAX_RETRIES or not any(mark in text for mark in RATE_LIMITED):
                raise
            wait = RETRY_AFTER.search(text)
            time.sleep(min(int(wait.group(1)) if wait else 5, MAX_WAIT_SEC) + 1)

def _eur(micros: int) -> Optional[float]:
    return round(micros / 1_000_000, 2) if micros else None

def _keyword_volume(result) -> KeywordVolume:
    m = result.keyword_metrics
    months = []
    for v in m.monthly_search_volumes:
        name = getattr(v.month, "name", str(v.month))
        if name in MONTHS:
            months.append(MonthVolume(month=f"{v.year}-{MONTHS.index(name) + 1:02d}", searches=v.monthly_searches or 0))
    months.sort(key=lambda x: x.month)
    peak = max(months, key=lambda x: x.searches) if months else None
    competition = getattr(m.competition, "name", None)
    return KeywordVolume(
        keyword=result.text,
        avg_monthly=m.avg_monthly_searches if "avg_monthly_searches" in m else None,
        competition=competition if competition not in (None, "UNSPECIFIED", "UNKNOWN") else None,
        competition_index=m.competition_index if "competition_index" in m else None,
        cpc_low_eur=_eur(m.low_top_of_page_bid_micros),
        cpc_high_eur=_eur(m.high_top_of_page_bid_micros),
        close_variants=list(result.close_variants),
        peak_month=peak.month if peak and peak.searches else None,
        months=months,
    )

@handle_google_ads_errors
def keyword_volumes(req: KeywordVolumesRequest) -> KeywordVolumesReport:
    """Searches per month (last 12 months), average, competition and top-of-page bids — one request per country."""
    report = KeywordVolumesReport()
    state: Dict[str, Any] = {"client": get_ads_client(), "customer_id": CUSTOMER_ID, "fallback": False}

    for country in req.countries:
        geo, language = COUNTRIES[country]
        try:
            results = _with_retry(state, req.keywords, geo, language)
        except Exception as e:
            if state["fallback"] or not any(code in str(e) for code in FALLBACK_ERRORS):
                raise
            state.update(client=get_ads_client(FALLBACK_LOGIN_ID), customer_id=FALLBACK_CUSTOMER_ID, fallback=True)
            results = _with_retry(state, req.keywords, geo, language)

        volumes = [_keyword_volume(r) for r in results]
        report.countries.append(CountryVolumes(country=country, geo_target=geo, language=language,
                                               test_account_fallback=state["fallback"], keywords=volumes))

        if state["fallback"]:
            report.verdicts.append(f"⚠️ {country}: Keyword Planner ответил через тестовый аккаунт — объёмов там нет, нули не настоящие.")
            continue
        answered = {v.keyword.lower() for v in volumes} | {c.lower() for v in volumes for c in v.close_variants}
        no_data = [k for k in req.keywords if k.lower() not in answered] + [v.keyword for v in volumes if not v.avg_monthly]
        if no_data:
            report.verdicts.append(f"{country}: нет данных или 0 запросов — {', '.join(dict.fromkeys(no_data))}.")
        top = max(volumes, key=lambda v: v.avg_monthly or 0, default=None)
        if top and top.avg_monthly:
            report.verdicts.append(f"{country}: больше всего ищут «{top.keyword}» — {top.avg_monthly}/мес, пик {top.peak_month}.")

    return report
