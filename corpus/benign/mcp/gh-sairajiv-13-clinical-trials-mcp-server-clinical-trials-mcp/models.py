"""Pydantic models returned by the MCP tools, plus parsers for raw API data.

The ClinicalTrials.gov v2 API returns deeply nested ``protocolSection``
modules. The parsers here flatten one study into a small, readable shape and
drop everything the tools do not need. Parsers are defensive about missing
modules: the API omits empty modules entirely, so every lookup has a default.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Tool output models
# ---------------------------------------------------------------------------


class TrialSummary(BaseModel):
    """One study as it appears in search results."""

    nct_id: str
    title: str
    status: str
    phases: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    lead_sponsor: str | None = None
    start_date: str | None = None
    last_update_posted: str | None = None


class SearchResult(BaseModel):
    """One page of search results."""

    total_count: int | None = Field(
        default=None,
        description="Total studies matching the query, when the API reports it.",
    )
    returned_count: int
    page_size: int
    next_page_token: str | None = Field(
        default=None,
        description="Pass back as page_token to fetch the next page; null on the last page.",
    )
    trials: list[TrialSummary] = Field(default_factory=list)


class Intervention(BaseModel):
    name: str
    type: str
    description: str | None = None


class EligibilitySummary(BaseModel):
    sex: str | None = Field(default=None, description="ALL, MALE, or FEMALE as listed.")
    minimum_age: str | None = Field(default=None, description="As listed, e.g. '18 Years'.")
    maximum_age: str | None = Field(default=None, description="As listed, e.g. '75 Years'.")
    healthy_volunteers: bool | None = None
    criteria_text: str | None = Field(
        default=None,
        description="Full free-text inclusion and exclusion criteria, unmodified.",
    )


class TrialDetail(BaseModel):
    """One study, normalized into a readable structure."""

    nct_id: str
    brief_title: str
    official_title: str | None = None
    status: str
    brief_summary: str | None = None
    phases: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)
    eligibility: EligibilitySummary = Field(default_factory=EligibilitySummary)
    locations_count: int = 0
    recruiting_locations_count: int = 0
    lead_sponsor: str | None = None
    collaborators: list[str] = Field(default_factory=list)
    enrollment_count: int | None = None
    start_date: str | None = None
    primary_completion_date: str | None = None
    completion_date: str | None = None
    last_update_posted: str | None = None


class CriterionCheck(BaseModel):
    """The outcome of one deterministic eligibility check."""

    criterion: str = Field(description="What was checked: 'age' or 'sex'.")
    result: Literal["pass", "fail", "unknown"]
    detail: str = Field(description="Plain-language reason for the result.")


class EligibilityResult(BaseModel):
    """Outcome of the deterministic part of an eligibility check."""

    nct_id: str
    verdict: Literal["meets", "does_not_meet", "cannot_determine"]
    checks: list[CriterionCheck] = Field(default_factory=list)
    criteria_text: str | None = Field(
        default=None,
        description="Full free-text criteria from the study, for human review.",
    )
    note: str = (
        "Only age and sex are checked here, because they are the fields the API "
        "reports in a structured form. The remaining criteria are free text and "
        "are returned in criteria_text for a person to review. This is not a "
        "final eligibility decision."
    )


class SiteInfo(BaseModel):
    """One study location."""

    facility: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    status: str = Field(
        description="Site status, or the study status when the API does not give the site its own."
    )
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class RecruitingSitesResult(BaseModel):
    nct_id: str
    study_status: str
    total_sites_listed: int
    sites_returned: int
    sites: list[SiteInfo] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsers: raw API study dict -> output models
# ---------------------------------------------------------------------------


def _section(study: dict[str, Any]) -> dict[str, Any]:
    section = study.get("protocolSection")
    return section if isinstance(section, dict) else {}


def _module(study: dict[str, Any], name: str) -> dict[str, Any]:
    module = _section(study).get(name)
    return module if isinstance(module, dict) else {}


def _date(module: dict[str, Any], key: str) -> str | None:
    struct = module.get(key)
    if isinstance(struct, dict):
        date = struct.get("date")
        return date if isinstance(date, str) else None
    return None


def parse_interventions(study: dict[str, Any]) -> list[Intervention]:
    module = _module(study, "armsInterventionsModule")
    parsed: list[Intervention] = []
    for item in module.get("interventions") or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        parsed.append(
            Intervention(
                name=str(item["name"]),
                type=str(item.get("type") or "OTHER"),
                description=item.get("description"),
            )
        )
    return parsed


def parse_eligibility(study: dict[str, Any]) -> EligibilitySummary:
    module = _module(study, "eligibilityModule")
    return EligibilitySummary(
        sex=module.get("sex"),
        minimum_age=module.get("minimumAge"),
        maximum_age=module.get("maximumAge"),
        healthy_volunteers=module.get("healthyVolunteers"),
        criteria_text=module.get("eligibilityCriteria"),
    )


def parse_locations(study: dict[str, Any]) -> list[dict[str, Any]]:
    module = _module(study, "contactsLocationsModule")
    locations = module.get("locations")
    if not isinstance(locations, list):
        return []
    return [loc for loc in locations if isinstance(loc, dict)]


def effective_site_status(location: dict[str, Any], study_status: str) -> str:
    """A location without its own status follows the study's overall status."""
    status = location.get("status")
    return str(status) if status else study_status


def parse_summary(study: dict[str, Any]) -> TrialSummary:
    identification = _module(study, "identificationModule")
    status = _module(study, "statusModule")
    design = _module(study, "designModule")
    conditions = _module(study, "conditionsModule")
    sponsor = _module(study, "sponsorCollaboratorsModule").get("leadSponsor") or {}
    interventions = parse_interventions(study)
    return TrialSummary(
        nct_id=str(identification.get("nctId") or ""),
        title=str(identification.get("briefTitle") or ""),
        status=str(status.get("overallStatus") or "UNKNOWN"),
        phases=list(design.get("phases") or []),
        conditions=list(conditions.get("conditions") or []),
        interventions=[item.name for item in interventions],
        lead_sponsor=sponsor.get("name"),
        start_date=_date(status, "startDateStruct"),
        last_update_posted=_date(status, "lastUpdatePostDateStruct"),
    )


def parse_detail(study: dict[str, Any]) -> TrialDetail:
    identification = _module(study, "identificationModule")
    status = _module(study, "statusModule")
    description = _module(study, "descriptionModule")
    design = _module(study, "designModule")
    conditions = _module(study, "conditionsModule")
    sponsor_module = _module(study, "sponsorCollaboratorsModule")
    lead_sponsor = sponsor_module.get("leadSponsor") or {}
    collaborators = [
        str(c.get("name"))
        for c in sponsor_module.get("collaborators") or []
        if isinstance(c, dict) and c.get("name")
    ]
    design_info = design.get("designInfo") or {}
    enrollment = design.get("enrollmentInfo") or {}
    overall_status = str(status.get("overallStatus") or "UNKNOWN")
    locations = parse_locations(study)
    recruiting = sum(
        1 for loc in locations if effective_site_status(loc, overall_status) == "RECRUITING"
    )
    return TrialDetail(
        nct_id=str(identification.get("nctId") or ""),
        brief_title=str(identification.get("briefTitle") or ""),
        official_title=identification.get("officialTitle"),
        status=overall_status,
        brief_summary=description.get("briefSummary"),
        phases=list(design.get("phases") or []),
        conditions=list(conditions.get("conditions") or design_info.get("conditions") or []),
        interventions=parse_interventions(study),
        eligibility=parse_eligibility(study),
        locations_count=len(locations),
        recruiting_locations_count=recruiting,
        lead_sponsor=lead_sponsor.get("name"),
        collaborators=collaborators,
        enrollment_count=enrollment.get("count"),
        start_date=_date(status, "startDateStruct"),
        primary_completion_date=_date(status, "primaryCompletionDateStruct"),
        completion_date=_date(status, "completionDateStruct"),
        last_update_posted=_date(status, "lastUpdatePostDateStruct"),
    )


def parse_site(location: dict[str, Any], study_status: str) -> SiteInfo:
    contact_name = contact_phone = contact_email = None
    contacts = location.get("contacts")
    if isinstance(contacts, list):
        for contact in contacts:
            if isinstance(contact, dict) and contact.get("role") in (None, "CONTACT"):
                contact_name = contact.get("name")
                contact_phone = contact.get("phone")
                contact_email = contact.get("email")
                break
    return SiteInfo(
        facility=location.get("facility"),
        city=location.get("city"),
        state=location.get("state"),
        country=location.get("country"),
        status=effective_site_status(location, study_status),
        contact_name=contact_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
    )
