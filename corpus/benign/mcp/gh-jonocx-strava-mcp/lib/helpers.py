"""Helper functions."""

from datetime import datetime as dt
from datetime import timedelta

from lib.api import get_weather_data


def format_split(split: dict) -> str:
    """Format each split into a consistent string.

    Args:
        split: the split to format.

    Returns:
        the split as a string.
    """
    return f"""
            Split: {split["split"]}
            Time: {split["moving_time"] / 60}
            Distance: {split["distance"] / 1000} kilometers
            Elevation Difference: {split["elevation_difference"]} meters
            Average Pace: {(1000 / split["average_speed"]) / 60} min/km
            Grade-adjusted Pace: {(1000 / split["average_grade_adjusted_speed"]) / 60} min/km
            Average Heart Rate: {round(split["average_heartrate"], 2)} BPM
    """


def get_additional_info(activity: dict) -> str:
    """Get additional information available when working with a specific activity.

    Args:
        activity: the activity data.

    Returns:
        the activity data as a formatted string.
    """
    start_date = dt.strptime(activity["start_date"], "%Y-%m-%dT%H:%M:%SZ")
    end_date = start_date + timedelta(seconds=activity["elapsed_time"])

    weather = get_weather_data(
        start=start_date,
        end=end_date,
        lat=activity["start_latlng"][0],
        lon=activity["start_latlng"][1],
    )[0]

    splits = "\n---\n".join(
        format_split(split=split) for split in activity["splits_metric"]
    )

    return f"""
        Weather:
            Temperature: {weather["temp"]}
            Precipitation: {weather["prcp"]}
            Wind speed: {weather["wspd"]} km/h
        Number of Kudos: {activity["kudos_count"]}
        Number of PRs: {activity["pr_count"]}
        Splits:
            {splits}
    """


def format_activity(activity: dict, is_full_activity: bool = False) -> str:
    """Format an activity ready for ingestion by Claude.

    Args:
        activity: the activity for format.
        is_full_activity: whether it's an activity with additional data.
            Defaults to False.

    Returns:
        the formatted activity.
    """
    rest_time = (activity["elapsed_time"] - activity["moving_time"]) / 60
    average_pace = (
        (1000 / activity["average_speed"]) / 60
        if activity["average_speed"]
        else 0
    )
    base_info = f"""
        Activity name: {activity["name"]}
        Activity type: {activity["sport_type"]}
        Time (moving): {activity["moving_time"] / 60} minutes
        Time (elapsed): {activity["elapsed_time"] / 60} minutes
        Time (resting): {rest_time}
        Distance: {activity["distance"] / 1000} kilometers
        Elevation gain: {activity["total_elevation_gain"]} meters
        Average Heart Rate: {round(activity["average_heartrate"], 2)} BPM
        Average Pace: {average_pace} min/km
    """

    if is_full_activity:
        base_info += get_additional_info(activity=activity)

    return base_info


def parse_activities(activities: list[dict]) -> list[dict]:
    """Parse variables in the activities.

    Args:
        activities: the list of activities to parse.

    Returns:
        updated activities with variables parsed.
    """
    activities_parsed = []
    for activity in activities:
        activity["start_date"] = dt.strptime(
            activity["start_date"], "%Y-%m-%dT%H:%M:%SZ"
        )
        activities_parsed.append(activity)

    return activities_parsed


def filter_activities_by_date(
    activities: list[dict], since: str, until: str = None
) -> list[dict]:
    """Filter activities by dates.

    Args:
        activities: the list of activities to filter.
        since: the date from which to filter.
        until: the end date to filter. Defaults to None.

    Returns:
        a list of activities filtered to between dates.
    """
    since = dt.strptime(since, "%Y-%m-%d").date()

    if until:
        until = dt.strptime(until, "%Y-%m-%d").date()

    def date_filter(act):
        if until:
            return since <= act["start_date"].date() <= until
        return since <= act["start_date"].date()

    return list(filter(date_filter, activities))
