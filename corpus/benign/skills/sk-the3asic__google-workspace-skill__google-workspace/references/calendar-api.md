# Google Calendar API Reference

Quick reference for Calendar API v3. Full documentation: https://developers.google.com/calendar/api/v3/reference

## Service Creation

```python
from googleapiclient.discovery import build
calendar = build('calendar', 'v3', credentials=creds)
```

## Common Operations

### List Calendars
```python
calendar.calendarList().list(maxResults=250).execute()
```

### List Events
```python
calendar.events().list(
    calendarId='primary',
    timeMin='2025-11-13T00:00:00Z',
    timeMax='2025-11-20T00:00:00Z',
    maxResults=100,
    singleEvents=True,
    orderBy='startTime'
).execute()
```

### Create Event
```python
event = {
    'summary': 'Meeting Title',
    'start': {'dateTime': '2025-11-14T10:00:00+08:00', 'timeZone': 'Asia/Shanghai'},
    'end': {'dateTime': '2025-11-14T11:00:00+08:00', 'timeZone': 'Asia/Shanghai'},
    'attendees': [{'email': 'user@example.com'}],
    'reminders': {
        'useDefault': False,
        'overrides': [
            {'method': 'email', 'minutes': 24 * 60},
            {'method': 'popup', 'minutes': 10}
        ]
    }
}
calendar.events().insert(calendarId='primary', body=event).execute()
```

### Update Event
```python
calendar.events().patch(
    calendarId='primary',
    eventId='event-id',
    body={'summary': 'New Title'}
).execute()
```

### Delete Event
```python
calendar.events().delete(calendarId='primary', eventId='event-id').execute()
```

### Free/Busy Query
```python
calendar.freebusy().query(
    body={
        'timeMin': '2025-11-14T09:00:00Z',
        'timeMax': '2025-11-14T18:00:00Z',
        'items': [{'id': 'primary'}]
    }
).execute()
```

## Event Properties

- `summary`: Event title
- `description`: Event description
- `start`: Start time (`dateTime` or `date` for all-day)
- `end`: End time
- `attendees`: List of `{'email': '...', 'displayName': '...'}`
- `recurrence`: List of RRULE strings for recurring events
- `reminders`: Custom reminders
- `colorId`: Event color (get available colors with `calendar.colors().get()`)
- `location`: Location string
- `status`: 'confirmed', 'tentative', 'cancelled'

## Time Formats

All times in ISO 8601 format:
- DateTime: `2025-11-14T10:00:00+08:00` or `2025-11-14T02:00:00Z`
- Date only (all-day): `2025-11-14`

## Scopes Required

- `https://www.googleapis.com/auth/calendar` - Full access
- `https://www.googleapis.com/auth/calendar.events` - Events only
- `https://www.googleapis.com/auth/calendar.readonly` - Read-only
