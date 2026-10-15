"""
Cal.com MCP Server

A FastMCP server for interacting with the Cal.com API. This enables LLMs to manage event types,
create bookings, and access Cal.com scheduling data programmatically.

Author: Arley Peter
License: MIT
Disclaimer: This project is not affiliated with or endorsed by Cal.com in any way.
"""

import os
import requests
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the FastMCP server
mcp = FastMCP(
    name="Cal.com MCP Server",
    description="A FastMCP server to interact with the Cal.com API, enabling LLMs to manage bookings, event types, and more."
)

# Get Cal.com API key from environment variable
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY")
print(f"Cal.com API Key: {CALCOM_API_KEY}")
CALCOM_API_BASE_URL = "https://api.cal.com/v2"

@mcp.tool()
def get_api_status() -> str:
    """Check if the Cal.com API key is configured in the environment.

    Returns:
        A string indicating whether the Cal.com API key is configured or not.
    """
    if CALCOM_API_KEY:
        return "Cal.com API key is configured."
    else:
        return "Cal.com API key is NOT configured. Please set the CALCOM_API_KEY environment variable."

@mcp.tool()
def list_event_types() -> list[dict] | dict:
    """Fetch a simplified list of active (non-hidden) event types from Cal.com.
    This is preferred for LLMs to easily present options or make booking decisions.

    Returns:
        A list of dictionaries, each with 'id', 'title', 'slug', 'length_minutes',
        'owner_profile_slug' (user or team slug), and 'location_summary'.
        Returns an error dictionary if the API call fails or no event types are found.
    """
    if not CALCOM_API_KEY:
        return {"error": "Cal.com API key not configured. Please set the CALCOM_API_KEY environment variable."}
    
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    raw_response_data = {}
    try:
        response = requests.get(f"{CALCOM_API_BASE_URL}/event-types", headers=headers)
        response.raise_for_status()
        raw_response_data = response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}", "status_code": response.status_code, "response_text": response.text}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request exception occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred during API call or data processing: {e}"}

    options = []
    event_type_groups = raw_response_data.get("data", {}).get("eventTypeGroups", [])

    if not event_type_groups and raw_response_data.get("data", {}).get("eventTypes"):
        event_types_direct = raw_response_data.get("data", {}).get("eventTypes", [])
        for et in event_types_direct:
            if not et.get("hidden"):
                owner_slug_info = f"user_id_{et.get('userId')}"
                if et.get("teamId"):
                    owner_slug_info = f"team_id_{et.get('teamId')}"

                location_types = [
                    loc.get("type", "unknown")
                    .replace("integrations:google:meet", "Google Meet")
                    .replace("integrations:zoom:zoom_video", "Zoom") # Common Zoom integration key
                    .replace("integrations:microsoft:teams", "Microsoft Teams") # Common Teams key
                    .replace("inPerson", "In-person")
                    for loc in et.get("locations", [])
                ]
                location_summary = ", ".join(location_types) or "Provider configured"
                # Check for Cal Video (often 'dailyCo', 'calvideo', or similar)
                if any("daily" in loc_type.lower() or "calvideo" in loc_type.lower() for loc_type in location_types):
                    location_summary = "Cal Video"

                options.append({
                    "id": et.get("id"),
                    "title": et.get("title"),
                    "slug": et.get("slug"),
                    "length_minutes": et.get("length"),
                    "owner_info": owner_slug_info,
                    "location_summary": location_summary,
                    "requires_confirmation": et.get("requiresConfirmation", False),
                    "description_preview": (et.get("description") or "")[:100] + "..." if et.get("description") else "No description."
                })

    else:
        for group in event_type_groups:
            owner_profile_slug = group.get("profile", {}).get("slug", f"group_owner_id_{group.get('id')}") # Fallback if slug missing
            for et in group.get("eventTypes", []):
                if not et.get("hidden"):  # Only include non-hidden event types
                    location_types = [
                        loc.get("type", "unknown")
                        .replace("integrations:google:meet", "Google Meet")
                        .replace("integrations:zoom:zoom_video", "Zoom")
                        .replace("integrations:microsoft:teams", "Microsoft Teams")
                        .replace("inPerson", "In-person")
                        for loc in et.get("locations", [])
                    ]
                    location_summary = ", ".join(location_types) or "Provider configured"
                    if any("daily" in loc_type.lower() or "calvideo" in loc_type.lower() for loc_type in location_types):
                        location_summary = "Cal Video"

                    options.append({
                        "id": et.get("id"),
                        "title": et.get("title"),
                        "slug": et.get("slug"),
                        "length_minutes": et.get("length"),
                        "owner_profile_slug": owner_profile_slug,
                        "location_summary": location_summary,
                        "requires_confirmation": et.get("requiresConfirmation", False),
                        # Add a snippet of the description if available
                        "description_preview": (et.get("description") or "")[:100] + "..." if et.get("description") else "No description."
                    })

    if not options:
        # Check if there was an issue with the raw response structure itself if it wasn't an HTTP/Request error
        if not raw_response_data or "data" not in raw_response_data:
             return {"error": "Failed to parse event types from Cal.com API response.", "raw_response_preview": str(raw_response_data)[:200]}
        return {"message": "No active (non-hidden) event types found for the configured API key."}
    
    return options

@mcp.tool()
def get_bookings(event_type_id: int = None, user_id: int = None, status: str = None, date_from: str = None, date_to: str = None, limit: int = 20) -> dict:
    """Fetch a list of bookings from Cal.com, with optional filters.

    Args:
        event_type_id: Optional. Filter bookings by a specific event type ID.
        user_id: Optional. Filter bookings by a specific user ID (typically the user associated with the API key or a managed user).
        status: Optional. Filter bookings by status (e.g., 'ACCEPTED', 'PENDING', 'CANCELLED', 'REJECTED').
        date_from: Optional. Filter bookings from this date (ISO 8601 format, e.g., '2023-10-26T10:00:00.000Z').
        date_to: Optional. Filter bookings up to this date (ISO 8601 format, e.g., '2023-10-27T10:00:00.000Z').
        limit: Optional. Maximum number of bookings to return (default is 20).

    Returns:
        A dictionary containing the API response (list of bookings) or an error message.
    """
    if not CALCOM_API_KEY:
        return {"error": "Cal.com API key not configured. Please set the CALCOM_API_KEY environment variable."}
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json"
    }
    params = {}
    if event_type_id is not None:
        params['eventTypeId'] = event_type_id
    if user_id is not None:
        params['userId'] = user_id
    if status is not None:
        params['status'] = status
    if date_from is not None:
        params['dateFrom'] = date_from
    if date_to is not None:
        params['dateTo'] = date_to
    if limit is not None:
        params['take'] = limit
    try:
        response = requests.get(f"{CALCOM_API_BASE_URL}/bookings", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}", "status_code": response.status_code, "response_text": response.text}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request exception occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@mcp.tool()
def create_booking(
    start_time: str,
    attendee_name: str,
    attendee_email: str,
    attendee_timezone: str,
    event_type_id: int = None,
    event_type_slug: str = None,
    username: str = None,
    team_slug: str = None,
    organization_slug: str = None,
    attendee_phone_number: str = None,
    attendee_language: str = None,
    guests: list[str] = None,
    location_input: str = None,
    metadata: dict = None,
    length_in_minutes: int = None,
    booking_fields_responses: dict = None
) -> dict:
    """Create a new booking in Cal.com for a specific event type and attendee.

    Args:
        start_time: Required. The start time of the booking in ISO 8601 format in UTC (e.g., '2024-08-13T09:00:00Z').
        attendee_name: Required. The name of the primary attendee.
        attendee_email: Required. The email of the primary attendee.
        attendee_timezone: Required. The IANA time zone of the primary attendee (e.g., 'America/New_York').
        event_type_id: Optional. The ID of the event type to book. Either this or (eventTypeSlug + username/teamSlug) is required.
        event_type_slug: Optional. The slug of the event type. Used with username or team_slug if event_type_id is not provided.
        username: Optional. The username of the event owner. Used with event_type_slug.
        team_slug: Optional. The slug of the team owning the event type. Used with event_type_slug.
        organization_slug: Optional. The organization slug, used with event_type_slug and username/team_slug if applicable.
        attendee_phone_number: Optional. Phone number for the attendee (e.g., for SMS reminders).
        attendee_language: Optional. Preferred language for the attendee (e.g., 'en', 'it').
        guests: Optional. A list of additional guest email addresses.
        location_input: Optional. Specifies the meeting location. Can be a simple string for Cal Video, or a URL for custom locations.
        metadata: Optional. A dictionary of custom key-value pairs (max 50 keys, 40 char key, 500 char value).
        length_in_minutes: Optional. If the event type allows variable lengths, specify the desired duration.
        booking_fields_responses: Optional. A dictionary for responses to custom booking fields (slug: value).

    Returns:
        A dictionary containing the API response (booking details) or an error message.
    """
    if not CALCOM_API_KEY:
        return {"error": "Cal.com API key not configured. Please set the CALCOM_API_KEY environment variable."}
    if not event_type_id and not (event_type_slug and (username or team_slug)):
        return {"error": "Either 'event_type_id' or ('event_type_slug' and 'username'/'team_slug') must be provided."}
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json",
        "cal-api-version": "2024-08-13"
    }
    payload = {
        "start": start_time,
        "attendee": {
            "name": attendee_name,
            "email": attendee_email,
            "timeZone": attendee_timezone
        }
    }
    if event_type_id:
        payload['eventTypeId'] = event_type_id
    else:
        payload['eventTypeSlug'] = event_type_slug
        if username:
            payload['username'] = username
        elif team_slug:
            payload['teamSlug'] = team_slug
        if organization_slug:
            payload['organizationSlug'] = organization_slug
    if attendee_phone_number:
        payload['attendee']['phoneNumber'] = attendee_phone_number
    if attendee_language:
        payload['attendee']['language'] = attendee_language
    if guests:
        payload['guests'] = guests
    if location_input:
        payload['location'] = location_input
    if metadata:
        payload['metadata'] = metadata
    if length_in_minutes:
        payload['lengthInMinutes'] = length_in_minutes
    if booking_fields_responses:
        payload['bookingFieldsResponses'] = booking_fields_responses
    try:
        response = requests.post(f"{CALCOM_API_BASE_URL}/bookings", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_details = {"error": f"HTTP error occurred: {http_err}", "status_code": response.status_code}
        try:
            error_details["response_text"] = response.json()
        except ValueError:
            error_details["response_text"] = response.text
        return error_details
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request exception occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@mcp.tool()
def list_schedules(user_id: int = None, team_id: int = None, limit: int = 20) -> dict:
    """List all schedules available to the authenticated user or for a specific user/team.

    Args:
        user_id: Optional. Filter schedules by user ID.
        team_id: Optional. Filter schedules by team ID.
        limit: Optional. Maximum number of schedules to return (default 20).

    Returns:
        A dictionary containing the API response (list of schedules) or an error message.
    """
    if not CALCOM_API_KEY:
        return {"error": "Cal.com API key not configured. Please set the CALCOM_API_KEY environment variable."}
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json"
    }
    params = {}
    if user_id is not None:
        params["userId"] = user_id
    if team_id is not None:
        params["teamId"] = team_id
    if limit is not None:
        params["take"] = limit
    try:
        response = requests.get(f"{CALCOM_API_BASE_URL}/schedules", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}", "status_code": response.status_code, "response_text": response.text}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request exception occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@mcp.tool()
def list_teams(limit: int = 20) -> dict:
    """List all teams available to the authenticated user.

    Args:
        limit: Optional. Maximum number of teams to return (default 20).

    Returns:
        A dictionary containing the API response (list of teams) or an error message.
    """
    if not CALCOM_API_KEY:
        return {"error": "Cal.com API key not configured. Please set the CALCOM_API_KEY environment variable."}
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json"
    }
    params = {"take": limit} if limit is not None else {}
    try:
        response = requests.get(f"{CALCOM_API_BASE_URL}/teams", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}", "status_code": response.status_code, "response_text": response.text}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request exception occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@mcp.tool()
def list_users(limit: int = 20) -> dict:
    """List all users available to the authenticated account.

    Args:
        limit: Optional. Maximum number of users to return (default 20).

    Returns:
        A dictionary containing the API response (list of users) or an error message.
    """
    if not CALCOM_API_KEY:
        return {"error": "Cal.com API key not configured. Please set the CALCOM_API_KEY environment variable."}
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json"
    }
    params = {"take": limit} if limit is not None else {}
    try:
        response = requests.get(f"{CALCOM_API_BASE_URL}/users", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}", "status_code": response.status_code, "response_text": response.text}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request exception occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

@mcp.tool()
def list_webhooks(limit: int = 20) -> dict:
    """List all webhooks configured for the authenticated account.

    Args:
        limit: Optional. Maximum number of webhooks to return (default 20).

    Returns:
        A dictionary containing the API response (list of webhooks) or an error message.
    """
    if not CALCOM_API_KEY:
        return {"error": "Cal.com API key not configured. Please set the CALCOM_API_KEY environment variable."}
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "Content-Type": "application/json"
    }
    params = {"take": limit} if limit is not None else {}
    try:
        response = requests.get(f"{CALCOM_API_BASE_URL}/webhooks", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}", "status_code": response.status_code, "response_text": response.text}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request exception occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

if __name__ == "__main__":
    print("Starting Cal.com MCP Server...")
    if not CALCOM_API_KEY:
        print("WARNING: CALCOM_API_KEY environment variable is not set. Some tools may not function.")
    mcp.run()
