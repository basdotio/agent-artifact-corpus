---
name: gmail
description: Skill for reading, searching, and sending emails using the user's Gmail account over the Google Gmail API. Use this when the user asks to summarize emails, read specific emails, search for emails by query, or send a new email to someone.
---

# Gmail Skill

This skill allows Tracks to act as a fully-featured email client using the user's Gmail account through the official Gmail API. It supports listing, searching, reading, and sending emails.

## Prerequisites

The authentication is handled automatically by Tracks's built-in OAuth support. Environment variables `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_TOKEN` and `GOOGLE_OAUTH_REFRESH_TOKEN` are securely passed to these scripts via the Agent's runtime environment.

If a script fails with missing credentials or authentication errors, instruct the user to go to the "Connections" page in the App Settings and reconnect the Google integration.

## Available Tools

The following scripts are available in the `scripts/` directory:

### 1. Listing Emails
Lists the most recent emails in the inbox. Supports pagination.
```bash
python scripts/list_messages.py [--max-results 10] [--label INBOX] [--page-token TOKEN]
```

### 2. Searching Emails
Searches emails using standard Gmail search queries (e.g., "from:alice is:unread", "subject:meeting"). Supports pagination.
```bash
python scripts/search_messages.py "query string" [--max-results 10] [--page-token TOKEN]
```

### 3. Reading an Email
Reads the full text body of a specific email. You will need the ID from the list or search commands.
```bash
python scripts/read_message.py <MESSAGE_ID>
```

### 4. Sending an Email
Sends an email from the user's Gmail account.
```bash
python scripts/send_message.py --to "recipient@example.com" --subject "Hello" --body "Message body text" [--cc "cc@example.com"] [--bcc "bcc@example.com"]
```

## Usage Guidelines

- **Search first**: If a user asks to find an email about something specific, prefer using `search_messages.py` rather than listing the inbox to preserve context tokens.
- **Reading**: Use `read_message.py` to get the full body. `list_messages.py` only provides a snippet.
- **Privacy Notice**: Only read emails when explicitly requested by the user or when necessary to fulfill an objective.
- **Attachments**: Currently, sending and downloading attachments is unsupported by these standard scripts.
