from datetime import datetime, timedelta
from typing import List, TypedDict

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import (
    CalendarViewRequestBuilder,
)

from utils.auth import get_graph_client


class CalendarEvent(TypedDict):
    subject: str
    start_time: str
    end_time: str
    location: str
    organizer: str


class CalendarCategory(TypedDict):
    name: str
    color: str


def setup_calendar_resources(mcp: FastMCP):
    """Register all calendar-related resources"""

    @mcp.resource("outlook://calendar/week", name="Get Week's Events")
    async def get_week_events() -> List[CalendarEvent]:
        """get events for the current week from your calendar."""
        token = get_access_token()
        client = get_graph_client(token.token)

        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        start_time = start_of_week.isoformat()
        end_time = end_of_week.isoformat()

        query_params = (
            CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
                start_date_time=start_time,
                end_date_time=end_time,
                select=["subject", "start", "end", "location", "organizer"],
            )
        )
        request_configuration = RequestConfiguration(query_parameters=query_params)

        events_resp = await client.me.calendar.calendar_view.get(
            request_configuration=request_configuration
        )

        events = []
        if events_resp and events_resp.value:
            for event in events_resp.value:
                events.append(
                    {
                        "subject": event.subject,
                        "start_time": event.start.date_time,
                        "end_time": event.end.date_time,
                        "location": event.location.display_name,
                        "organizer": event.organizer.email_address.name,
                    }
                )
        return events

    @mcp.resource("outlook://calendar/today", name="Get Today's Events")
    async def get_today_events() -> List[CalendarEvent]:
        """get events for today from your calendar."""
        token = get_access_token()
        client = get_graph_client(token.token)

        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        start_time = start_of_day.isoformat()
        end_time = end_of_day.isoformat()

        query_params = (
            CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
                start_date_time=start_time,
                end_date_time=end_time,
                select=["subject", "start", "end", "location", "organizer"],
            )
        )
        request_configuration = RequestConfiguration(query_parameters=query_params)

        events_resp = await client.me.calendar.calendar_view.get(
            request_configuration=request_configuration
        )

        events = []
        if events_resp and events_resp.value:
            for event in events_resp.value:
                events.append(
                    {
                        "subject": event.subject,
                        "start_time": event.start.date_time,
                        "end_time": event.end.date_time,
                        "location": event.location.display_name,
                        "organizer": event.organizer.email_address.name,
                    }
                )
        return events

    @mcp.resource("outlook://calendar/categories", name="Get Calendar Categories")
    async def get_calendar_categories() -> List[CalendarCategory]:
        """gets the user's calendar categories"""
        token = get_access_token()
        client = get_graph_client(token.token)

        categories_resp = await client.me.outlook.master_categories.get()

        categories = []
        if categories_resp and categories_resp.value:
            for category in categories_resp.value:
                categories.append(
                    {"name": category.display_name, "color": str(category.color)}
                )

        return categories
