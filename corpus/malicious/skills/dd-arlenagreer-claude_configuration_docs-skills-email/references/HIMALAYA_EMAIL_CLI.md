# Himalaya CLI Email Client - Complete Setup

## Installation & Configuration
- **Version**: Himalaya v1.1.0
- **Installation**: `brew install himalaya`
- **Config Location**: `~/Library/Application Support/himalaya/config.toml`

## Gmail Configuration (Working)
```toml
[accounts.gmail]
email = "arlenagreer@gmail.com"
display-name = "Arlen A. Greer"
default = true

backend.type = "imap"
backend.host = "imap.gmail.com"
backend.port = 993
backend.login = "arlenagreer@gmail.com"
backend.auth.type = "password"
backend.auth.cmd = "echo 'upgwlxdnxqhymnst'"
backend.encryption.type = "tls"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.gmail.com"
message.send.backend.port = 587
message.send.backend.login = "arlenagreer@gmail.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "echo 'upgwlxdnxqhymnst'"
message.send.backend.encryption.type = "start-tls"
```

## Credentials
- **Email**: arlenagreer@gmail.com
- **App Password**: upgwlxdnxqhymnst (no spaces)

## Common Commands

### Reading Emails
```bash
himalaya envelope list                    # List emails
himalaya envelope list --page-size 5     # List 5 emails
himalaya message read <ID>               # Read specific email
```

### Sending Plain Text Email
```bash
himalaya message send << 'EOF'
From: arlenagreer@gmail.com
To: recipient@example.com
Subject: Subject Here

Message body here
EOF
```

### Sending HTML Email (Single Command)
```bash
himalaya message send << 'EOF'
From: arlenagreer@gmail.com
To: recipient@example.com
Subject: HTML Email
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<body>
  <h1>HTML Content</h1>
  <p>Your HTML content here</p>
</body>
</html>
EOF
```

## Key Features
- ✅ Send plain text emails
- ✅ Send HTML-formatted emails with CSS styling
- ✅ Send from command line without creating separate files
- ✅ Works as Gmail MCP fallback option
- ✅ Supports attachments
- ✅ Full IMAP/SMTP functionality

## Tested & Verified
- Installation completed: October 9, 2025
- IMAP connection: ✅ Working
- SMTP sending: ✅ Working
- HTML emails: ✅ Working (tested with Halloween-themed email)

## Use Case
**IMPORTANT**: When Gmail MCP is unavailable, offer to use Himalaya CLI to send emails directly via command line.

## Example HTML Email Sent
Successfully sent Halloween-themed HTML email with:
- CSS styling (gradients, shadows, borders)
- HTML structure
- Emoji decorations
- All in a single command using here-document syntax
