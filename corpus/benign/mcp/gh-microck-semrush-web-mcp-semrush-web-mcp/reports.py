"""Shared MCP and CLI operation schemas and observed browser request shapes."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class EmptyQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KeywordQuery(EmptyQuery):
    keyword: str = Field(min_length=1, max_length=200)
    database: str = Field(default="us", pattern="^[a-z]{2}$")


class KeywordListQuery(KeywordQuery):
    limit: int = Field(default=10, ge=1, le=100)


class IdeasSummaryQuery(KeywordQuery):
    questions_only: bool = False


class IdeasQuery(IdeasSummaryQuery):
    limit: int = Field(default=10, ge=1, le=100)


class DomainIdentityQuery(EmptyQuery):
    domain: str = Field(min_length=1, max_length=253, description="Bare domain, e.g. openai.com")


class DomainQuery(DomainIdentityQuery):
    database: str = Field(default="us", pattern="^(mobile-)?[a-z]{2}$")


class DomainListQuery(DomainQuery):
    limit: int = Field(default=5, ge=1, le=10)


class DatabaseQuery(EmptyQuery):
    database: str = Field(default="us", pattern="^(mobile-)?[a-z]{2}$")


class HistoryQuery(DatabaseQuery):
    global_data: bool = False


class DomainTrendQuery(DomainQuery):
    date_type: str = Field(default="monthly", pattern="^(daily|monthly)$")
    global_data: bool = False


class AiSourcesQuery(DomainQuery):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MagicSummaryQuery(IdeasSummaryQuery):
    mode: int = Field(default=4, ge=0, le=4, description="Web Keyword Magic matching mode")
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    sort_field: str = Field(default="similarity_score", pattern="^[a-z_]+$")
    descending: bool = True
    filters: dict = Field(default_factory=dict, description="Keyword Magic web filter object")
    groups: list[str] = Field(default_factory=list)


class MagicQuery(MagicSummaryQuery):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=100)


class DomainResearchQuery(DomainQuery):
    date: int | None = Field(
        default=None,
        ge=0,
        description="Unix snapshot timestamp from snapshot_dates; omit for latest",
    )
    search_type: str = Field(default="domain", pattern="^(domain|subdomain|subfolder|url)$")
    date_type: str = Field(default="daily", pattern="^(daily|monthly)$")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=100)
    sort_field: str = Field(default="trafficPercent", pattern="^[a-zA-Z]+$")
    descending: bool = True


class DomainReportQuery(DomainResearchQuery):
    filters: dict = Field(default_factory=dict, description="Organic report web filter object")


class DomainPagesQuery(DomainReportQuery):
    sort_field: str = Field(default="traffic", pattern="^[a-zA-Z]+$")


class DomainChangesQuery(DomainReportQuery):
    sort_field: str = Field(default="changeOfTraffic", pattern="^[a-zA-Z]+$")


class DomainCompetitorsQuery(DomainResearchQuery):
    sort_field: str = Field(default="competitionLvl", pattern="^[a-zA-Z]+$")


class BacklinkQuery(EmptyQuery):
    domain: str = Field(min_length=1, max_length=253)
    target_type: str = Field(default="root_domain", pattern="^(root_domain|domain|url)$")


class BacklinkListQuery(BacklinkQuery):
    filters: str = Field(default="", description="Web backlink filter, e.g. +|type||nofollow")
    page: int = Field(default=0, ge=0, description="Zero-based provider page")
    sort_field: str = Field(default="", pattern="^[a-z_]*$")
    descending: bool = True


class GapSummaryQuery(DatabaseQuery):
    domains: list[str] = Field(
        min_length=2, max_length=5, description="Two to five root domains, first is your site"
    )
    filters: str = Field(default="", description="Semrush spectrum filter expression")


class GapQuery(GapSummaryQuery):
    gap_type: int = Field(default=2, ge=1, le=7, description="Semrush web gap type, default 2")
    limit: int = Field(default=100, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class BacklinkComparisonQuery(EmptyQuery):
    domains: list[str] = Field(
        min_length=2, max_length=5, description="Two to five root domains, first is your site"
    )


class BacklinkGapQuery(BacklinkComparisonQuery):
    page: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=100)
    filters: str = Field(
        default="+|backlinksnum_0|Eq|0",
        description="Web filter; default finds referring domains missing from your site",
    )
    sort_field: str = Field(default="matchesnum", pattern="^[a-z_]+$")
    descending: bool = True
    sort_target: int = Field(default=0, ge=0, le=4)


class ProjectListQuery(EmptyQuery):
    limit: int = Field(default=15, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filters: dict = Field(default_factory=dict, description="Project list web filter object")


@dataclass(frozen=True)
class Report:
    method: str
    query: type[BaseModel]
    description: str
    transport: str = "keyword"
    total_method: str = ""
    web_report: str = "domain.overview"


REPORTS = {
    "account_status": Report("user.GetInfo", EmptyQuery, "Signed-in account and report limits."),
    "keyword_overview": Report(
        "keywords.GetInfo", KeywordQuery, "Volume, difficulty, CPC, intent and trends."
    ),
    "keyword_ideas": Report(
        "ideas.GetKeywords", IdeasQuery, "Overview sample of related keywords or questions."
    ),
    "keyword_ideas_summary": Report(
        "ideas.GetKeywordsSummary", IdeasSummaryQuery, "Total related keyword count and volume."
    ),
    "keyword_serp": Report("serp.GetURLs", KeywordListQuery, "Ranked URLs and SERP features."),
    "keyword_ads": Report("adwords.GetCopies", KeywordListQuery, "Search ad copies for a keyword."),
    "keyword_clusters": Report("clusters.Get", KeywordQuery, "Keyword topics and search intents."),
    "keyword_magic": Report(
        "ideas.GetKeywords",
        MagicQuery,
        "Paginated Keyword Magic research with filters and sorting.",
        "magic",
    ),
    "keyword_magic_summary": Report(
        "ideas.GetKeywordsSummary",
        MagicSummaryQuery,
        "Keyword Magic totals for matching filters.",
        "magic",
    ),
    "keyword_magic_groups": Report(
        "ideas.GetGroups", MagicQuery, "Keyword Magic topic groups.", "magic"
    ),
    "domain_overview": Report(
        "organic.Summary", DomainQuery, "Search metrics and backlink summary.", "domain"
    ),
    "domain_keywords": Report(
        "organic.Positions",
        DomainReportQuery,
        "Paginated organic rankings with filters, sorting and totals.",
        "domain",
        "organic.PositionsTotal",
        "organic.positions",
    ),
    "domain_pages": Report(
        "organic.PagesV3",
        DomainPagesQuery,
        "Paginated top organic pages with totals.",
        "domain",
        "organic.PagesTotalV3",
        "organic.pages",
    ),
    "domain_subdomains": Report(
        "organic.Subdomains",
        DomainPagesQuery,
        "Paginated organic subdomain traffic and keyword totals.",
        "domain",
        "organic.SubdomainsTotal",
        "organic.subdomains",
    ),
    "domain_position_changes": Report(
        "organic.PositionChangesV2",
        DomainChangesQuery,
        "Paginated ranking changes with totals.",
        "domain",
        "organic.PositionChangesTotalV2",
        "organic.changes",
    ),
    "domain_competitors": Report(
        "organic.Competitors",
        DomainCompetitorsQuery,
        "Paginated organic search competitors and totals.",
        "domain",
        "organic.CompetitorsTotal",
        "organic.competitors",
    ),
    "domain_backlinks": Report(
        "backlinks.Overview",
        DomainIdentityQuery,
        "Backlink summary, sample links and anchors.",
        "domain",
    ),
    "domain_ai_visibility": Report(
        "organic.AiSeoSummary",
        DomainIdentityQuery,
        "AI visibility, mentions and citations.",
        "domain",
    ),
    "domain_ai_countries": Report(
        "organic.AiDistributionByCountry",
        DomainIdentityQuery,
        "AI visibility and mentions by country.",
        "domain",
    ),
    "domain_ai_sources": Report(
        "organic.AiTopSources",
        AiSourcesQuery,
        "Top AI citation sources with offset and limit.",
        "domain",
    ),
    "domain_trends": Report(
        "organic.OverviewTrend",
        DomainTrendQuery,
        "Daily or monthly organic and paid search trends.",
        "domain",
    ),
    "domain_paid_keywords": Report(
        "adwords.PositionsOverview",
        DomainListQuery,
        "Paid keyword overview sample; account permissions apply.",
        "domain",
    ),
    "domain_paid_competitors": Report(
        "adwords.CompetitorsOverview",
        DomainListQuery,
        "Paid search competitors; account permissions apply.",
        "domain",
    ),
    "domain_topics": Report(
        "organic.TopicsResult",
        DomainQuery,
        "Organic search topics already available for a domain.",
        "domain",
    ),
    "domain_topics_status": Report(
        "organic.TopicsStatus", DomainQuery, "Availability of domain organic topics.", "domain"
    ),
    "databases": Report(
        "user.Databases", EmptyQuery, "Search databases and account access.", "direct"
    ),
    "snapshot_dates": Report(
        "organic.SnapshotDates", HistoryQuery, "Available historical domain snapshots.", "direct"
    ),
    "report_permissions": Report(
        "dpa.UserPermissions",
        DatabaseQuery,
        "Account history, export and research permissions.",
        "domain",
    ),
    "backlink_links": Report(
        "backlinks",
        BacklinkListQuery,
        "Paginated backlinks with provider caps and totals.",
        "backlink",
    ),
    "backlink_referring_domains": Report(
        "backlinks_refdomains", BacklinkListQuery, "Paginated referring domains.", "backlink"
    ),
    "backlink_history": Report(
        "historical",
        BacklinkQuery,
        "Historical backlink and referring-domain trends.",
        "backlink_overview",
    ),
    "backlink_competitors": Report(
        "competitors", BacklinkQuery, "Competitors sharing a backlink profile.", "backlink_overview"
    ),
    "backlink_top_pages": Report(
        "backlinks_pages",
        BacklinkListQuery,
        "Paginated indexed pages ranked by referring domains.",
        "backlink",
    ),
    "backlink_anchors": Report(
        "backlinks_anchors",
        BacklinkListQuery,
        "Paginated anchor texts and backlink counts.",
        "backlink",
    ),
    "backlink_outgoing_domains": Report(
        "backlinks_outgoing_domains",
        BacklinkListQuery,
        "Paginated outbound domains and outgoing link counts.",
        "backlink",
    ),
    "backlink_countries": Report(
        "geodomains", BacklinkQuery, "Referring-domain country distribution.", "backlink_overview"
    ),
    "backlink_authority": Report(
        "ascore", BacklinkQuery, "Authority score and supporting metrics.", "backlink_overview"
    ),
    "backlink_categories": Report(
        "category-profile", BacklinkQuery, "Referring-domain category profile.", "backlink_overview"
    ),
    "keyword_gap": Report(
        "/spectrum/v1/Gap/KeywordsList",
        GapQuery,
        "Paginated organic keyword gap between two to five sites.",
        "gap",
    ),
    "keyword_gap_totals": Report(
        "/spectrum/v1/Gap/KeywordsTotals",
        GapSummaryQuery,
        "Counts for keyword overlap and opportunity types.",
        "gap",
    ),
    "keyword_gap_overlap": Report(
        "/spectrum/v1/Gap/Overlaps", GapSummaryQuery, "Organic keyword profile overlaps.", "gap"
    ),
    "backlink_gap": Report(
        "backlinks_matrix",
        BacklinkGapQuery,
        "Paginated link-building prospects shared by competitors but missing from your site.",
        "backlink_gap",
    ),
    "backlink_comparison": Report(
        "backlinks_comparison",
        BacklinkComparisonQuery,
        "Compare backlink history, country distribution and domain zones.",
        "backlink_gap",
    ),
    "projects": Report(
        "/apis/v4-raw/crossroad/api/v0/crossroad/list",
        ProjectListQuery,
        "Existing projects and folder access, with pagination.",
        "projects",
    ),
    "ai_capabilities": Report(
        "/ai-seo/api/v2/user/user_capabilities",
        EmptyQuery,
        "Account AI Visibility Toolkit access and limits.",
        "post",
    ),
    "audit_campaigns": Report(
        "/siteaudit/api/campaigns/seolist",
        EmptyQuery,
        "Existing Site Audit campaigns; does not start a crawl.",
        "get",
    ),
    "folders": Report(
        "/apis/v4-raw/folders/api/v0/folders/selector-list",
        EmptyQuery,
        "Accessible project folders.",
        "get",
    ),
    "saved_keyword_lists": Report(
        "/apis/v4-raw/saved-keywords/api/v0/list/all",
        EmptyQuery,
        "Existing saved keyword lists.",
        "post",
    ),
}


def report_parameters(definition, query):
    """Build the fixed request shape observed for each browser report family."""
    family = definition.transport
    if family == "magic":
        filters = {
            key: []
            for key in (
                "phrase",
                "competition_level",
                "cpc",
                "difficulty",
                "results",
                "volume",
                "words_count",
            )
        }
        filters.update(serp_features=[{"inverted": False, "value": []}], phrase_include_logic=0)
        filters.update(query["filters"])
        params = {
            "phrase": query["keyword"],
            "database": query["database"],
            "currency": query["currency"],
            "mode": query["mode"],
            "questions_only": query["questions_only"],
            "topics_enabled": True,
            "filter": filters,
            "groups": query["groups"],
            "order": {"direction": 1 if query["descending"] else 0, "field": query["sort_field"]},
            "groups_order": {"direction": 1, "field": "relevance"},
        }
        if definition.method == "ideas.GetKeywords":
            params["page"] = {"number": query["page"], "size": query["page_size"]}
        elif definition.method == "ideas.GetGroups":
            params["groups_page"] = {"number": query["page"], "size": query["page_size"]}
        return params
    if family == "keyword":
        if "keyword" not in query:
            return {}
        params = {
            "phrase": query["keyword"],
            "database": query["database"],
            "device": 0,
            "currency": "USD",
            "location": 0,
            "date": "",
        }
        if definition.method.startswith("ideas."):
            params.update(mode=0, questions_only=query["questions_only"])
        return params
    if family == "direct":
        if "database" not in query:
            return {}
        return {"database": query["database"], "global": query["global_data"], "dateFormat": "date"}
    if family == "domain":
        if "domain" not in query:
            return {"database": query["database"]}
        params = {
            "searchItem": query["domain"],
            "searchType": "domain",
            "dateFormat": "date",
            "dateType": query.get("date_type", "daily"),
        }
        if "database" in query:
            params["database"] = query["database"]
        if issubclass(definition.query, DomainResearchQuery):
            params.pop("dateFormat")
            if query["date"] is not None:
                params["date"] = query["date"]
            params.update(
                searchType=query["search_type"],
                display={
                    "page": query["page"],
                    "pageSize": query["page_size"],
                    "order": {
                        "field": query["sort_field"],
                        "direction": "desc" if query["descending"] else "asc",
                    },
                },
            )
            if definition.method in ("organic.Positions", "organic.PositionChangesV2"):
                params["positionsType"] = "all"
            if "filters" in query:
                params["filter"] = query["filters"]
            if definition.method == "organic.PositionChangesV2":
                params.update(changesTypes=None, dateRange=None)

        if definition.method.endswith("CompetitorsOverview"):
            params.update(display={"page": 1, "pageSize": query["limit"]}, youDomain=True)
        if definition.method == "organic.OverviewTrend":
            params.pop("dateFormat")
            params.update(dateRange=None, **{"global": query["global_data"]})
        if definition.method in ("organic.TopicsStatus", "organic.TopicsResult"):
            params.pop("dateFormat")
            params.pop("dateType")
        if definition.method == "organic.AiTopSources":
            params["range"] = {"limit": query["limit"], "offset": query["offset"]}
        return params
    if family == "backlink_gap":
        params = {
            "action": "report",
            "type": definition.method,
            "targets[]": query["domains"],
            "target_types[]": ["root_domain"] * len(query["domains"]),
        }
        if definition.method == "backlinks_matrix":
            params.update(
                display_limit=query["limit"],
                export_columns="domain,domain_ascore,matches_num,backlinks_num,traffic",
                display_filter=query["filters"],
                sort_field=query["sort_field"],
                sort_type="desc" if query["descending"] else "asc",
                sort_target=query["sort_target"],
                display_page=query["page"],
            )
        else:
            params["export_columns"] = "zones,backlinks_historical,geodomains"
        return params
    if family.startswith("backlink"):
        params = {"target": query["domain"], "target_type": query["target_type"]}
        if family == "backlink":
            default_sort = {
                "backlinks": "page_ascore",
                "backlinks_refdomains": "backlinksnum",
                "backlinks_anchors": "backlinksnum",
                "backlinks_pages": "domainsnum",
                "backlinks_outgoing_domains": "links_num",
            }[definition.method]
            params.update(
                action="report",
                type=definition.method,
                display_page=query["page"],
                sort_field=query["sort_field"] or default_sort,
                sort_type="desc" if query["descending"] else "asc",
            )
            if query["filters"]:
                params["display_filter"] = query["filters"]
        return params
    if family == "gap":
        params = {
            "targets": [
                {"product_type": 2, "type": 1, "value": domain, "filters": ""}
                for domain in query["domains"]
            ],
            "date": None,
            "database": query["database"],
            "filters": query["filters"],
        }
        if definition.method.endswith("KeywordsList"):
            params.update(
                type=query["gap_type"],
                range={"limit": query["limit"], "offset": query["offset"]},
                columns=[
                    "KEYWORD",
                    "INTENTS",
                    "VOLUME",
                    "KEYWORD_DIFFICULTY",
                    "CPC",
                    "COMPETITION_DENSITY",
                    "TARGETS_POSITION",
                    "TARGETS_URL",
                    "RESULTS",
                ],
                order={"column": 6, "direction": 2},
            )
        return params
    if family == "projects":
        return {
            "filter": query["filters"],
            "range": {"limit": query["limit"], "offset": query["offset"]},
        }
    if family == "post" and definition.method.endswith("/list/all"):
        return {
            "ownership": 1,
            "order": {"field": 3, "direction": 2},
            "range": {"limit": 1000, "offset": 0},
        }
    if definition.method.endswith("selector-list"):
        return {"limit": 10000, "offset": 0}
    return {}
