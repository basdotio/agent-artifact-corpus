from typing import Optional, List
from datetime import datetime

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from msgraph.generated.users.item.calendar.events.events_request_builder import (
    EventsRequestBuilder,
)
from msgraph.generated.models.event import Event
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.location import Location
from msgraph.generated.models.attendee import Attendee
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.attendee_type import AttendeeType
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from kiota_abstractions.base_request_configuration import RequestConfiguration

from utils.auth import get_graph_client


def setup_calendar_tools(mcp: FastMCP):
    """Register all calendar-related tools"""

    @mcp.tool()
    async def search_calendar_events(
        title: Optional[str] = None,
        attendee: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 20,
    ) -> List[dict]:
        """
        Search for calendar events based on various criteria.

        Args:
            title: Text to search for in event titles/subjects
            attendee: Email address or name of an attendee to search for
            start_date: Search for events starting on or after this date (ISO format: YYYY-MM-DD)
            end_date: Search for events starting on or before this date (ISO format: YYYY-MM-DD)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            List of calendar events matching the search criteria, including subject, start/end times, location, attendees, and body
        """
        token = get_access_token()
        client = get_graph_client(token.token)

        # Build the filter query using OData syntax
        filter_terms = []

        if start_date:
            # Search for events starting on or after the start date
            filter_terms.append(f"start/dateTime ge '{start_date}T00:00:00'")

        if end_date:
            # Search for events starting on or before the end date
            filter_terms.append(f"start/dateTime le '{end_date}T23:59:59'")

        # Combine all filter terms with AND operator
        filter_query = " and ".join(filter_terms) if filter_terms else None

        # For title and attendee, use search for more flexible text matching
        search_terms = []
        if title:
            search_terms.append(title)
        if attendee:
            search_terms.append(attendee)

        search_query = " ".join(search_terms) if search_terms else None

        # If no search criteria provided, return an error
        if not filter_query and not search_query:
            return {
                "error": "Please provide at least one search criterion (title, attendee, start_date, or end_date)"
            }

        # Limit max_results to 100
        if max_results > 100:
            max_results = 100

        # Build the query parameters
        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            filter=filter_query,
            search=search_query,
            select=[
                "subject",
                "start",
                "end",
                "location",
                "attendees",
                "organizer",
                "body",
                "isAllDay",
                "webLink",
            ],
            top=max_results,
            orderby=["start/dateTime"],
        )

        request_configuration = RequestConfiguration(
            query_parameters=query_params,
        )

        # Execute the search
        events_resp = await client.me.calendar.events.get(
            request_configuration=request_configuration
        )

        # Process the results
        events = []
        if events_resp and events_resp.value:
            for event in events_resp.value:
                # Process attendees
                attendees_list = []
                if event.attendees:
                    for attendee_obj in event.attendees:
                        if attendee_obj.email_address:
                            attendees_list.append(
                                {
                                    "name": attendee_obj.email_address.name,
                                    "address": attendee_obj.email_address.address,
                                    "status": (
                                        attendee_obj.status.response.value
                                        if attendee_obj.status
                                        and attendee_obj.status.response
                                        else None
                                    ),
                                }
                            )

                # Process location
                location_str = None
                if event.location:
                    if event.location.display_name:
                        location_str = event.location.display_name
                    elif event.location.unique_id:
                        location_str = event.location.unique_id

                events.append(
                    {
                        "subject": event.subject,
                        "start": (
                            {
                                "dateTime": event.start.date_time,
                                "timeZone": event.start.time_zone,
                            }
                            if event.start
                            else None
                        ),
                        "end": (
                            {
                                "dateTime": event.end.date_time,
                                "timeZone": event.end.time_zone,
                            }
                            if event.end
                            else None
                        ),
                        "location": location_str,
                        "is_all_day": event.is_all_day,
                        "organizer": (
                            {
                                "name": event.organizer.email_address.name,
                                "address": event.organizer.email_address.address,
                            }
                            if event.organizer and event.organizer.email_address
                            else None
                        ),
                        "attendees": attendees_list,
                        "body_preview": (
                            event.body.content[:200]
                            if event.body and event.body.content
                            else None
                        ),
                        "web_link": event.web_link,
                    }
                )

        return events

    @mcp.tool()
    async def create_calendar_event(
        subject: str,
        start_datetime: str,
        end_datetime: str,
        timezone: str = "UTC",
        location: Optional[str] = None,
        body: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: bool = False,
    ) -> dict:
        """
        Create a new calendar event.

        Args:
            subject: The title/subject of the event
            start_datetime: Start date and time in ISO format (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD for all-day events)
            end_datetime: End date and time in ISO format (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD for all-day events)
            timezone: Timezone for the event (default: UTC). Examples: "UTC", "Pacific Standard Time", "Eastern Standard Time"
            location: Location of the event (optional)
            body: Description/body of the event (optional)
            attendees: List of attendee email addresses (optional)
            is_all_day: Whether this is an all-day event (default: False)

        Returns:
            Created event details including event ID, subject, start/end times, and web link
        """
        token = get_access_token()
        client = get_graph_client(token.token)

        # Create the event object
        event = Event()
        event.subject = subject
        event.is_all_day = is_all_day

        # Set start time
        start = DateTimeTimeZone()
        start.date_time = start_datetime
        start.time_zone = timezone
        event.start = start

        # Set end time
        end = DateTimeTimeZone()
        end.date_time = end_datetime
        end.time_zone = timezone
        event.end = end

        # Set location if provided
        if location:
            location_obj = Location()
            location_obj.display_name = location
            event.location = location_obj

        # Set body if provided
        if body:
            body_obj = ItemBody()
            body_obj.content_type = BodyType.Text
            body_obj.content = body
            event.body = body_obj

        # Set attendees if provided
        if attendees:
            attendee_list = []
            for attendee_email in attendees:
                attendee = Attendee()
                email_address = EmailAddress()
                email_address.address = attendee_email
                attendee.email_address = email_address
                attendee.type = AttendeeType.Required
                attendee_list.append(attendee)
            event.attendees = attendee_list

        # Create the event
        created_event = await client.me.calendar.events.post(event)

        # Return the created event details
        return {
            "id": created_event.id,
            "subject": created_event.subject,
            "start": (
                {
                    "dateTime": created_event.start.date_time,
                    "timeZone": created_event.start.time_zone,
                }
                if created_event.start
                else None
            ),
            "end": (
                {
                    "dateTime": created_event.end.date_time,
                    "timeZone": created_event.end.time_zone,
                }
                if created_event.end
                else None
            ),
            "location": (
                created_event.location.display_name if created_event.location else None
            ),
            "is_all_day": created_event.is_all_day,
            "web_link": created_event.web_link,
            "message": "Event created successfully",
        }
