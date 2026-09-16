# Gmail API Reference

Quick reference for Gmail API v1. Full documentation: https://developers.google.com/gmail/api/reference/rest

## Service Creation

```python
from googleapiclient.discovery import build
gmail = build('gmail', 'v1', credentials=creds)
```

## Common Operations

### Send Email
```python
from email.mime.text import MIMEText
import base64

message = MIMEText('<h1>Hello</h1>', 'html')
message['to'] = 'recipient@example.com'
message['subject'] = 'Subject Line'

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
gmail.users().messages().send(userId='me', body={'raw': raw}).execute()
```

### Search Messages
```python
gmail.users().messages().list(
    userId='me',
    q='from:sender@example.com is:unread',
    maxResults=50
).execute()
```

### Get Message
```python
gmail.users().messages().get(
    userId='me',
    id='message-id',
    format='metadata',  # or 'full', 'minimal'
    metadataHeaders=['From', 'To', 'Subject', 'Date']
).execute()
```

### Batch Modify
```python
gmail.users().messages().batchModify(
    userId='me',
    body={
        'ids': ['id1', 'id2', ...],
        'addLabelIds': ['label-id'],
        'removeLabelIds': ['UNREAD']
    }
).execute()
```

### Batch Delete
```python
gmail.users().messages().batchDelete(
    userId='me',
    body={'ids': ['id1', 'id2', ...]}
).execute()
```

## Label Operations

### List Labels
```python
gmail.users().labels().list(userId='me').execute()
```

### Create Label
```python
gmail.users().labels().create(
    userId='me',
    body={
        'name': 'Label Name',
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
).execute()
```

### Modify Message Labels
```python
gmail.users().messages().modify(
    userId='me',
    id='message-id',
    body={
        'addLabelIds': ['label-id'],
        'removeLabelIds': ['UNREAD']
    }
).execute()
```

## Gmail Query Syntax

Use in `q` parameter of `messages.list()`:

| Query | Description |
|-------|-------------|
| `from:sender@example.com` | From specific sender |
| `to:recipient@example.com` | To specific recipient |
| `subject:keyword` | Subject contains keyword |
| `has:attachment` | Has attachment |
| `is:unread` | Unread messages |
| `is:important` | Important messages |
| `is:starred` | Starred messages |
| `after:2025/11/01` | After date |
| `before:2025/12/01` | Before date |
| `newer_than:7d` | Last 7 days |
| `older_than:1m` | Older than 1 month |

Combine with AND (space) or OR: `from:boss@example.com subject:urgent has:attachment`

## Message Format Options

- `minimal`: ID and thread ID only
- `metadata`: ID, thread ID, labels, and specified headers
- `full`: Complete message including body
- `raw`: Raw MIME message

For efficiency, use `metadata` with `metadataHeaders` to get only needed fields.

## Standard Label IDs

- `INBOX`, `SPAM`, `TRASH`, `UNREAD`, `STARRED`, `IMPORTANT`
- `SENT`, `DRAFT`, `CHAT`
- `CATEGORY_PERSONAL`, `CATEGORY_SOCIAL`, `CATEGORY_PROMOTIONS`, `CATEGORY_UPDATES`, `CATEGORY_FORUMS`

## Batch Limits

- `batchModify`: Up to 1000 messages per request
- `batchDelete`: Up to 1000 messages per request

For larger batches, split into chunks of 50-100 for reliability.

## Scopes Required

- `https://www.googleapis.com/auth/gmail.send` - Send only
- `https://www.googleapis.com/auth/gmail.readonly` - Read-only
- `https://www.googleapis.com/auth/gmail.modify` - Modify (labels, read status)
- `https://www.googleapis.com/auth/gmail.compose` - Create drafts and send
- `https://www.googleapis.com/auth/gmail.labels` - Label management
