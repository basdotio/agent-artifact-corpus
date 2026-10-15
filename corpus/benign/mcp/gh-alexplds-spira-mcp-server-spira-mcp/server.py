"""
Spira Test Case MCP Server
===========================

Exposes create / read / update / delete operations for Spira
(SpiraTest / SpiraTeam / SpiraPlan) test cases as MCP tools, so an LLM
agent can manage test cases directly from a chat.

Connection settings are read from environment variables (see
.env.example) at call time. Set them in your MCP client's server config,
not in this file.

Spira REST API reference (v6.0):
  https://{instance}/Services/v6_0/RestService.svc/projects/{project_id}/test-cases
"""

import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

REQUIRED_ENV = ("SPIRA_BASE_URL", "SPIRA_USERNAME", "SPIRA_API_KEY")

mcp = FastMCP("spira-test-cases")


# ---------------------------------------------------------------------------
# Configuration (read lazily so it can be changed after import, e.g. in tests)
# ---------------------------------------------------------------------------


def _base_url() -> str:
    return os.environ.get("SPIRA_BASE_URL", "").rstrip("/")


def _username() -> str:
    return os.environ.get("SPIRA_USERNAME", "")


def _api_key() -> str:
    return os.environ.get("SPIRA_API_KEY", "")


def _api_version() -> str:
    return os.environ.get("SPIRA_API_VERSION", "v6_0")


def _default_project_id() -> str:
    return os.environ.get("SPIRA_DEFAULT_PROJECT_ID", "")


def _timeout() -> float:
    raw = os.environ.get("SPIRA_TIMEOUT", "")
    try:
        value = float(raw) if raw else 30.0
    except ValueError:
        return 30.0
    return value if value > 0 else 30.0


def _missing_env() -> list[str]:
    return [name for name in REQUIRED_ENV if not os.environ.get(name)]


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def _service_url(path: str) -> str:
    return f"{_base_url()}/Services/{_api_version()}/RestService.svc/{path}"


async def _request(
    method: str,
    path: str,
    json_body: dict | None = None,
    query_params: dict | None = None,
) -> Any:
    """Call the Spira REST API and return the parsed JSON response.

    query_params is merged into the auth params dict rather than baked into
    `path` -- httpx replaces a URL's existing query string with `params=`
    instead of merging it, so any query string embedded in `path` would
    otherwise be silently dropped.
    """
    if not _base_url() or not _username() or not _api_key():
        raise RuntimeError(
            "Spira connection is not configured. Set SPIRA_BASE_URL, "
            "SPIRA_USERNAME, and SPIRA_API_KEY as environment variables."
        )

    url = _service_url(path)
    params = {"username": _username(), "api-key": _api_key()}
    if query_params:
        params.update(query_params)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=_timeout()) as client:
        response = await client.request(method, url, params=params, headers=headers, json=json_body)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Spira API error {response.status_code} on {method} {path}: {response.text[:500]}"
        )

    if not response.content:
        return None
    return response.json()


def _resolve_project_id(project_id: int | None) -> int:
    if project_id is not None:
        return project_id
    default = _default_project_id()
    if default:
        return int(default)
    raise RuntimeError("No project_id was provided and SPIRA_DEFAULT_PROJECT_ID is not set.")


async def _resolve_project_template_id(project_id: int) -> int:
    """Look up the ProjectTemplateId a project uses.

    Test case types/statuses/priorities are defined per-template, not
    per-project, so this is required before calling any of the
    project-templates/{id}/test-cases/... lookup endpoints.
    """
    project = await _request("GET", f"projects/{project_id}")
    return project["ProjectTemplateId"]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def spira_list_test_cases(
    project_id: int | None = None,
    starting_row: int = 1,
    number_of_rows: int = 50,
) -> Any:
    """List test cases in a Spira project.

    Args:
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
        starting_row: 1-based row to start from (for pagination).
        number_of_rows: Max rows to return (Spira caps this at 500).
    """
    pid = _resolve_project_id(project_id)
    return await _request(
        "GET",
        f"projects/{pid}/test-cases",
        query_params={"starting_row": starting_row, "number_of_rows": number_of_rows},
    )


@mcp.tool()
async def spira_get_test_case(test_case_id: int, project_id: int | None = None) -> Any:
    """Get the full details of a single Spira test case by id.

    Args:
        test_case_id: The TestCaseId to retrieve.
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
    """
    pid = _resolve_project_id(project_id)
    return await _request("GET", f"projects/{pid}/test-cases/{test_case_id}")


@mcp.tool()
async def spira_create_test_case(
    name: str,
    description: str | None = None,
    test_case_status_id: int = 0,
    test_case_type_id: int = 0,
    test_case_priority_id: int | None = None,
    test_case_folder_id: int | None = None,
    project_id: int | None = None,
) -> Any:
    """Create a new test case in Spira.

    Args:
        name: Test case name (required).
        description: Test case description / steps, HTML or plain text allowed.
        test_case_status_id: Status id. Pass 0 to use the project's default status.
        test_case_type_id: Type id (e.g. functional, regression). Pass 0 for default.
        test_case_priority_id: Optional priority id.
        test_case_folder_id: Optional folder id to file the test case under.
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
    """
    pid = _resolve_project_id(project_id)
    body = {
        "Name": name,
        "Description": description,
        "TestCaseStatusId": test_case_status_id,
        "TestCaseTypeId": test_case_type_id,
        "TestCasePriorityId": test_case_priority_id,
        "TestCaseFolderId": test_case_folder_id,
    }
    return await _request("POST", f"projects/{pid}/test-cases", json_body=body)


@mcp.tool()
async def spira_update_test_case(
    test_case_id: int,
    name: str | None = None,
    description: str | None = None,
    test_case_status_id: int | None = None,
    test_case_type_id: int | None = None,
    test_case_priority_id: int | None = None,
    test_case_folder_id: int | None = None,
    project_id: int | None = None,
) -> Any:
    """Update an existing Spira test case. Only provided fields are changed.

    This fetches the current test case first (required by Spira to obtain a
    valid ConcurrencyDate for optimistic-concurrency checks), merges in the
    changed fields, then PUTs the result back.

    Args:
        test_case_id: The TestCaseId to update (required).
        name: New name, if changing.
        description: New description, if changing.
        test_case_status_id: New status id, if changing.
        test_case_type_id: New type id, if changing.
        test_case_priority_id: New priority id, if changing.
        test_case_folder_id: New folder id, if changing.
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
    """
    pid = _resolve_project_id(project_id)
    current = await _request("GET", f"projects/{pid}/test-cases/{test_case_id}")
    if current is None:
        raise RuntimeError(f"Test case {test_case_id} not found in project {pid}.")

    if name is not None:
        current["Name"] = name
    if description is not None:
        current["Description"] = description
    if test_case_status_id is not None:
        current["TestCaseStatusId"] = test_case_status_id
    if test_case_type_id is not None:
        current["TestCaseTypeId"] = test_case_type_id
    if test_case_priority_id is not None:
        current["TestCasePriorityId"] = test_case_priority_id
    if test_case_folder_id is not None:
        current["TestCaseFolderId"] = test_case_folder_id

    return await _request("PUT", f"projects/{pid}/test-cases", json_body=current)


@mcp.tool()
async def spira_delete_test_case(test_case_id: int, project_id: int | None = None) -> str:
    """DESTRUCTIVE: permanently delete a test case from Spira.

    Only call this when the user has explicitly asked for the test case to be
    deleted; the deletion is not undone by this server.

    Args:
        test_case_id: The TestCaseId to delete.
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
    """
    pid = _resolve_project_id(project_id)
    await _request("DELETE", f"projects/{pid}/test-cases/{test_case_id}")
    return f"Test case {test_case_id} deleted from project {pid}."


@mcp.tool()
async def spira_list_lookup_values(project_id: int | None = None) -> Any:
    """List the valid test case types, statuses, and priorities for a project.

    Call this before spira_create_test_case / spira_update_test_case whenever
    you need to pick a status, type, or priority by name -- those fields take
    numeric ids that are specific to this Spira instance's configured
    template, and this tool resolves names to ids.

    Args:
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
    """
    pid = _resolve_project_id(project_id)
    template_id = await _resolve_project_template_id(pid)

    types = await _request("GET", f"project-templates/{template_id}/test-cases/types")
    statuses = await _request("GET", f"project-templates/{template_id}/test-cases/statuses")
    priorities = await _request("GET", f"project-templates/{template_id}/test-cases/priorities")

    return {
        "types": [{"id": t["TestCaseTypeId"], "name": t["Name"]} for t in types],
        "statuses": [{"id": s["TestCaseStatusId"], "name": s["Name"]} for s in statuses],
        "priorities": [{"id": p["PriorityId"], "name": p["Name"]} for p in priorities],
    }


@mcp.tool()
async def spira_list_test_steps(test_case_id: int, project_id: int | None = None) -> Any:
    """List the steps of a Spira test case, in order.

    Args:
        test_case_id: The TestCaseId whose steps to list.
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
    """
    pid = _resolve_project_id(project_id)
    return await _request("GET", f"projects/{pid}/test-cases/{test_case_id}/test-steps")


@mcp.tool()
async def spira_add_test_step(
    test_case_id: int,
    description: str,
    expected_result: str | None = None,
    sample_data: str | None = None,
    position: int | None = None,
    project_id: int | None = None,
) -> Any:
    """Add a new step to a Spira test case.

    Steps are Spira's structured "Step / Expected Result" rows, separate from
    the test case's free-text Description -- use this instead of cramming
    steps into the description when the test case should show proper
    step-by-step actions.

    Args:
        test_case_id: The TestCaseId to add the step to.
        description: What the tester should do for this step (required).
        expected_result: The expected outcome of this step.
        sample_data: Optional test data to use for this step.
        position: 1-based position in the step list. Appends to the end if omitted.
        project_id: Spira project id. Uses SPIRA_DEFAULT_PROJECT_ID if omitted.
    """
    pid = _resolve_project_id(project_id)
    # Spira rejects explicit nulls for optional fields (e.g. "Position": null
    # -> 400 Bad Request) but is fine with the key omitted entirely.
    body: dict[str, Any] = {"Description": description}
    if expected_result is not None:
        body["ExpectedResult"] = expected_result
    if sample_data is not None:
        body["SampleData"] = sample_data
    if position is not None:
        body["Position"] = position
    return await _request(
        "POST", f"projects/{pid}/test-cases/{test_case_id}/test-steps", json_body=body
    )


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    missing = _missing_env()
    if missing:
        print(
            f"[spira-mcp] WARNING: missing required env vars: {', '.join(missing)}. "
            "Tool calls will fail until these are set.",
            file=sys.stderr,
        )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
