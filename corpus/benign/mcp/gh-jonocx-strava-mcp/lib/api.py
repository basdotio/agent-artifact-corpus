"""Functions to interact with external APIs."""

import httpx
import logging

from datetime import datetime

from dotenv import dotenv_values

from meteostat import Point, Hourly

ENVS = dotenv_values(".env")
logger = logging.getLogger(__name__)

STRAVA_ACCESS_TOKEN_ENDPOINT = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_ENDPOINT = (
    "https://www.strava.com/api/v3/athlete/activities?per_page={n}"
)
STRAVA_ACTIVITY_DETAILS_ENDPOINT = "https://www.strava.com/api/v3/activities/{activity_id}?include_all_efforts=true"

ACCESS_TOKEN_PAYLOAD = {
    "client_id": ENVS["STRAVA_CLIENT_ID"],
    "client_secret": ENVS["STRAVA_CLIENT_SECRET"],
    "refresh_token": ENVS["STRAVA_REFRESH_TOKEN"],
    "grant_type": "refresh_token",
    "f": "json",
}


async def make_request(url: str, access_token: str = None) -> dict:
    """Make a request the Strava API.

    Args:
        url: the specific endpoint to query.
        access_token: the access token. Defaults to None.

    Returns:
        the response as a dictionary.
    """
    async with httpx.AsyncClient() as client:
        try:
            if access_token is None:
                response = await client.post(
                    url=url, data=ACCESS_TOKEN_PAYLOAD
                )
            else:
                response = await client.get(
                    url=url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

            response.raise_for_status()
            return response.json()
        except Exception as err:
            logger.error(err)
            return None


async def get_access_token() -> str:
    """Fetch an access token from Strava.

    Returns:
        the access token.
    """
    response = await make_request(url=STRAVA_ACCESS_TOKEN_ENDPOINT)
    return response.get("access_token", None)


async def get_activities(access_token: str, n: int = 200) -> list[dict]:
    """Get a list of activities.

    Args:
        access_token: the access token required to access the Strava API.
        n: the number of activities to fetch. Defaults to 200.

    Returns:
        the list of activities.
    """
    response = await make_request(
        url=STRAVA_ACTIVITIES_ENDPOINT.format(n=n), access_token=access_token
    )
    logger.info(f"Fetched: {len(response)}")
    return response


async def get_activity(access_token: str, activity_id: int) -> dict:
    """Get a specific activity from Strava.

    Args:
        access_token: the access token required to access the Strava API.
        activity_id: the specific activity to get.

    Returns:
        the activity data.
    """
    response = await make_request(
        url=STRAVA_ACTIVITY_DETAILS_ENDPOINT.format(activity_id=activity_id),
        access_token=access_token,
    )
    return response


def get_weather_data(
    start: datetime, end: datetime, lat: float, lon: float
) -> dict[str, float]:
    """Get weather data from the meteostat API.

    Args:
        start: the start datetime.
        end: the end datetime.
        lat: the latitude.
        lon: the longitude.

    Returns:
        weather statistics for the specific dates.
    """
    location = Point(lat=lat, lon=lon)
    data = Hourly(loc=location, start=start, end=end)
    data = data.fetch()

    return data.to_dict(orient="records")
