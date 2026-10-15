"""Strava MCP server for Claude to interact with the Strava API."""

import logging

from mcp.server.fastmcp import FastMCP

from lib.api import get_activities, get_activity, get_access_token
from lib.helpers import (
    parse_activities,
    format_activity,
    filter_activities_by_date,
)

logger = logging.getLogger(__name__)
mcp = FastMCP("strava")


@mcp.tool()
async def fetch_activity(
    activity_name: str = None, on_date: str = None, sport_type: str = "run"
) -> None:
    """Fetch a specific activity from Strava.

    The activity must be in the most recent 200.

    Args:
        activity_name: the name of the activity. Defaults to None.
        on_date: the date on which the activity occurred (e.g., 2025-01-01). Defaults to None.
        sport_type: the type of activity (e.g., run or workout). Defaults to "run".

    Returns:
        the specific activity request. By default, the most recent activity is returned.
    """
    access_token = await get_access_token()

    logger.info(
        f"fetch_activity called with activity_name={activity_name}, on_date={on_date}, sport_type={sport_type}"
    )

    activities = await get_activities(access_token=access_token, n=200)

    if activity_name is None and on_date is None and sport_type == "run":
        return format_activity(activity=activities[0])

    activities = list(
        filter(lambda act: act["type"].lower() == sport_type, activities)
    )

    if on_date is not None:
        activities = filter_activities_by_date(
            activities=activities, since=on_date, until=on_date
        )

        if not activities:
            return f"Unable to find activity on the specified date. Date={on_date}"

    if activity_name is not None:
        activities = list(
            filter(lambda act: act["name"] == activity_name, activities)
        )

        if not activities:
            return f"Unable to find activity with name '{activity_name}'"

    activity = await get_activity(
        access_token=access_token, activity_id=activities[0]["id"]
    )

    return format_activity(activity=activity, is_full_activity=True)


@mcp.tool()
async def fetch_activities(
    n: int, since: str = None, until: str = None
) -> str:
    """Get a list of activities from Strava.

    Args:
        n: the number of activities to fetch (e.g., 30). Max is 200.
        since: a date to get activities from (e.g., 2025-01-01). Defaults to None.
        until: an end date to get activities to, used with the `since` parameter (e.g., 2025-01-07)

    Returns:
        a list of Strava activities.
    """
    access_token = await get_access_token()
    logger.info(
        f"fetch_activities called with n={n}, since={since}, until={until}"
    )

    if n > 200:
        return "Number of activities should be less than 200."

    activities = await get_activities(access_token=access_token, n=n)

    activities = parse_activities(activities=activities)

    logger.info(f"fetched {len(activities)} activities")

    if since is not None:
        activities = filter_activities_by_date(
            activities=activities, since=since, until=until
        )

        if until:
            logger.info(f"activities filtered between {since} and {until}")
        else:
            logger.info(f"activities filtered up to date {since}")

        logger.info(
            f"number of activities after date filter: {len(activities)}"
        )

    return "\n---\n".join(
        [format_activity(activity=activity) for activity in activities]
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
