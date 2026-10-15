"""FastMCP server exposing ClinicalTrials.gov as four MCP tools.

The tools are thin wrappers: they build API query parameters, call the
client, and parse the response into the models in
:mod:`clinical_trials_mcp.models`. Upstream failures are raised as
``ToolError`` with the plain-language messages from
:mod:`clinical_trials_mcp.errors`, so the calling model sees what failed and
what to try next, never a stack trace.
"""

from __future__ import annotations

import argparse
import re
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .client import TrialsClient
from .eligibility import evaluate_eligibility
from .errors import TrialsError
from .models import (
    EligibilityResult,
    RecruitingSitesResult,
    SearchResult,
    TrialDetail,
    effective_site_status,
    parse_detail,
    parse_locations,
    parse_site,
    parse_summary,
)

MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 10

mcp = FastMCP(
    "clinical-trials-mcp",
    instructions=(
        "Tools for searching ClinicalTrials.gov and reading study records. "
        "Data comes from the public registry and can lag behind the sponsor's "
        "own records. Eligibility checks cover age and sex only; the rest of a "
        "study's criteria are free text that a person must review."
    ),
)

_client: TrialsClient | None = None


def get_client() -> TrialsClient:
    """Return the shared client, creating it on first use."""
    global _client
    if _client is None:
        _client = TrialsClient()
    return _client


def set_client(client: TrialsClient | None) -> None:
    """Replace the shared client. Used by tests."""
    global _client
    _client = client


# ---------------------------------------------------------------------------
# Query parameter helpers
# ---------------------------------------------------------------------------

_PHASE_ALIASES = {
    "0": "EARLY_PHASE1",
    "EARLY": "EARLY_PHASE1",
    "EARLYPHASE1": "EARLY_PHASE1",
    "1": "PHASE1",
    "PHASE1": "PHASE1",
    "2": "PHASE2",
    "PHASE2": "PHASE2",
    "3": "PHASE3",
    "PHASE3": "PHASE3",
    "4": "PHASE4",
    "PHASE4": "PHASE4",
    "NA": "NA",
    "NOTAPPLICABLE": "NA",
}


def normalize_phase(raw: str) -> str | None:
    """Normalize 'Phase 2', 'phase2', or '2' to the API value 'PHASE2'.

    Returns None for anything that is not a recognized phase, so a stray
    filter value is dropped instead of sent to the API.
    """
    compact = raw.strip().upper()
    for char in (" ", "-", "_", "/"):
        compact = compact.replace(char, "")
    return _PHASE_ALIASES.get(compact)


def normalize_status(raw: str) -> str:
    """Normalize 'recruiting' or 'Not Yet Recruiting' to the API enum form."""
    return re.sub(r"[\s-]+", "_", raw.strip().upper())


def build_search_params(
    *,
    condition: str | None,
    intervention: str | None,
    location: str | None,
    phases: list[str] | None,
    statuses: list[str] | None,
    page_size: int,
    page_token: str | None,
) -> dict[str, str]:
    params: dict[str, str] = {"pageSize": str(page_size)}
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if location:
        params["query.locn"] = location
    if statuses:
        params["filter.overallStatus"] = ",".join(normalize_status(s) for s in statuses)
    if phases:
        normalized = [p for p in (normalize_phase(p) for p in phases) if p]
        if normalized:
            if len(normalized) == 1:
                params["filter.advanced"] = f"AREA[Phase]{normalized[0]}"
            else:
                joined = " OR ".join(normalized)
                params["filter.advanced"] = f"AREA[Phase]({joined})"
    if page_token:
        params["pageToken"] = page_token
    return params


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
async def search_trials(
    condition: Annotated[
        str | None, Field(description="Condition or disease, e.g. 'type 2 diabetes'.")
    ] = None,
    intervention: Annotated[
        str | None, Field(description="Drug, device, or procedure name, e.g. 'metformin'.")
    ] = None,
    location: Annotated[
        str | None,
        Field(description="City, state, or country text matched against study sites."),
    ] = None,
    phases: Annotated[
        list[str] | None,
        Field(description="Phase filter, e.g. ['Phase 2', 'Phase 3']. Omit for all phases."),
    ] = None,
    statuses: Annotated[
        list[str] | None,
        Field(
            description="Status filter, e.g. ['RECRUITING']. Other values include "
            "NOT_YET_RECRUITING, ACTIVE_NOT_RECRUITING, ENROLLING_BY_INVITATION, "
            "COMPLETED, SUSPENDED, TERMINATED, WITHDRAWN."
        ),
    ] = None,
    page_size: Annotated[
        int, Field(description=f"Results per page, 1 to {MAX_PAGE_SIZE}.")
    ] = DEFAULT_PAGE_SIZE,
    page_token: Annotated[
        str | None,
        Field(description="Token from a previous result's next_page_token, for paging."),
    ] = None,
) -> SearchResult:
    """Search ClinicalTrials.gov for studies matching the given filters.

    At least one filter should be supplied; an unfiltered search returns the
    whole registry one page at a time. Ordering is whatever the API returns
    for the query; this tool does not re-sort.
    """
    capped = max(1, min(page_size, MAX_PAGE_SIZE))
    params = build_search_params(
        condition=condition,
        intervention=intervention,
        location=location,
        phases=phases,
        statuses=statuses,
        page_size=capped,
        page_token=page_token,
    )
    try:
        payload = await get_client().search_studies(params)
    except TrialsError as exc:
        raise ToolError(str(exc)) from exc
    studies = payload.get("studies")
    if not isinstance(studies, list):
        studies = []
    total = payload.get("totalCount")
    return SearchResult(
        total_count=total if isinstance(total, int) else None,
        returned_count=len(studies),
        page_size=capped,
        next_page_token=payload.get("nextPageToken"),
        trials=[parse_summary(study) for study in studies if isinstance(study, dict)],
    )


@mcp.tool
async def get_trial(
    nct_id: Annotated[str, Field(description="NCT number, e.g. 'NCT04354155'.")],
) -> TrialDetail:
    """Get one study by NCT number, normalized into a readable structure.

    Returns titles, status, phases, conditions, interventions, an
    eligibility summary (including the full criteria text), location
    counts, sponsor, enrollment, and key dates.
    """
    try:
        study = await get_client().get_study(nct_id.strip().upper())
    except TrialsError as exc:
        raise ToolError(str(exc)) from exc
    return parse_detail(study)


@mcp.tool
async def eligibility_check(
    nct_id: Annotated[str, Field(description="NCT number, e.g. 'NCT04354155'.")],
    age: Annotated[
        float | None,
        Field(description="Patient age in years. Fractional values are fine (0.5 = 6 months)."),
    ] = None,
    sex: Annotated[str | None, Field(description="Patient sex: 'female' or 'male'.")] = None,
) -> EligibilityResult:
    """Check the deterministic eligibility criteria of a study for a patient.

    Only age range and sex are checked, because those are the fields the
    registry reports in structured form. The verdict is 'meets',
    'does_not_meet', or 'cannot_determine', with a reason per check. The
    full free-text criteria are included in the result for human review;
    they are never interpreted by this tool, and the verdict is not a final
    eligibility decision.
    """
    try:
        study = await get_client().get_study(nct_id.strip().upper())
    except TrialsError as exc:
        raise ToolError(str(exc)) from exc
    return evaluate_eligibility(study, patient_age=age, patient_sex=sex)


@mcp.tool
async def recruiting_sites(
    nct_id: Annotated[str, Field(description="NCT number, e.g. 'NCT04354155'.")],
    city: Annotated[str | None, Field(description="Only sites in this city.")] = None,
    state: Annotated[str | None, Field(description="Only sites in this state or region.")] = None,
    country: Annotated[str | None, Field(description="Only sites in this country.")] = None,
) -> RecruitingSitesResult:
    """List the sites of a study that are currently recruiting.

    A site counts as recruiting when the registry gives it a RECRUITING
    status, or when it has no status of its own and the study overall is
    RECRUITING. Contact details are included where the registry lists them
    for a site.
    """
    try:
        study = await get_client().get_study(nct_id.strip().upper())
    except TrialsError as exc:
        raise ToolError(str(exc)) from exc
    detail = parse_detail(study)
    locations = parse_locations(study)
    wanted = {"city": city, "state": state, "country": country}
    sites = []
    for location in locations:
        if effective_site_status(location, detail.status) != "RECRUITING":
            continue
        matches = True
        for key, wanted_value in wanted.items():
            if wanted_value is None:
                continue
            actual = location.get(key)
            if not isinstance(actual, str) or wanted_value.lower() not in actual.lower():
                matches = False
                break
        if matches:
            sites.append(parse_site(location, detail.status))
    return RecruitingSitesResult(
        nct_id=detail.nct_id,
        study_status=detail.status,
        total_sites_listed=len(locations),
        sites_returned=len(sites),
        sites=sites,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="clinical-trials-mcp",
        description="MCP server for the ClinicalTrials.gov API v2.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport to serve on (default: stdio).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port.")
    args = parser.parse_args()
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
