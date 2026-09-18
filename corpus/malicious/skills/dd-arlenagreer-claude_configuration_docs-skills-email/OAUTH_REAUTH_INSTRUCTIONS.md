# Gmail OAuth Re-Authentication Instructions

## Status: Authentication Required
- **Current Token**: Expired 70 hours ago
- **Missing Scope**: `gmail.modify`
- **Required Services**: Gmail, Calendar, Contacts
- **Token Location**: `~/.claude/.google/token.json`

## Phase 4: OAuth Re-Authentication

### Step 1: Generate Authorization URL

The authorization URL has been generated and is ready for use:

```
https://accounts.google.com/o/oauth2/auth?access_type=offline&approval_prompt=force&client_id=948226087631-h46gg48bb541gheb82l8601titn13tpj.apps.googleusercontent.com&include_granted_scopes=true&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/calendar%20https://www.googleapis.com/auth/contacts%20https://www.googleapis.com/auth/gmail.modify
```

### Step 2: Complete Authorization (Manual Action Required)

**YOU MUST DO THIS MANUALLY** - Claude cannot complete this step as it requires browser interaction:

1. **Visit the authorization URL above** - Copy and paste it into your browser
2. **Sign in** to your Google account (arlenagreer@gmail.com)
3. **Review permissions** - You will be asked to grant access to:
   - Gmail (MODIFY) - Send, read, and manage emails
   - Google Calendar - Manage events
   - Google Contacts - Access contact information
4. **Click "Allow"** to grant permissions
5. **Copy the authorization code** - Google will display a code like `4/0AfJoh...XYZ`

### Step 3: Complete Authentication

Once you have the authorization code from Step 2, run:

```bash
cd ~/.claude/skills/email/scripts
ruby gmail_manager.rb auth YOUR_AUTH_CODE_HERE
```

Replace `YOUR_AUTH_CODE_HERE` with the actual code from Google.

**Expected Success Output:**
```json
{
  "status": "success",
  "operation": "auth",
  "message": "Authorization completed successfully",
  "token_path": "/Users/arlenagreer/.claude/.google/token.json",
  "scopes": [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/gmail.modify"
  ]
}
```

### Step 4: Verify Token

After successful authentication, verify the token was created:

```bash
ls -la ~/.claude/.google/token.json
cat ~/.claude/.google/token.json | jq .
```

You should see:
- A valid JSON file with `access_token`, `refresh_token`, and `expires_at`
- All three required scopes listed
- An expiration date in the future

## Phase 5: Email Validation Testing

Once authentication is complete, proceed with these validation tests:

### Test 1: Send Basic Email

```bash
cd ~/.claude/skills/email/scripts
echo '{
  "to": ["arlenagreer@gmail.com"],
  "subject": "Gmail Manager Test - Send",
  "body_html": "<html><body><h1>Test Email</h1><p>This is a test email from gmail_manager.rb script.</p><p>Sent at: '"$(date)"'</p></body></html>"
}' | ruby gmail_manager.rb send
```

**Expected Output:**
```json
{
  "status": "success",
  "operation": "send",
  "message_id": "18d1234567890abcd",
  "thread_id": "18d1234567890abcd",
  "recipients": {
    "to": ["arlenagreer@gmail.com"],
    "cc": [],
    "bcc": ["arlenagreer@gmail.com"]
  },
  "subject": "Gmail Manager Test - Send"
}
```

**Verify**: Check Gmail for the email (should have 2 copies - one To, one BCC)

### Test 2: Create Draft Email

```bash
echo '{
  "to": ["test@example.com"],
  "subject": "Gmail Manager Test - Draft",
  "body_html": "<html><body><h1>Draft Email</h1><p>This is a draft email for testing.</p></body></html>",
  "cc": ["arlenagreer@gmail.com"]
}' | ruby gmail_manager.rb draft
```

**Expected Output:**
```json
{
  "status": "success",
  "operation": "draft",
  "draft_id": "r-1234567890123456789",
  "message_id": "18d1234567890abcd",
  "thread_id": "18d1234567890abcd",
  "recipients": {
    "to": ["test@example.com"],
    "cc": ["arlenagreer@gmail.com"],
    "bcc": ["arlenagreer@gmail.com"]
  },
  "subject": "Gmail Manager Test - Draft"
}
```

**Verify**: Check Gmail Drafts folder for the draft

### Test 3: List Recent Messages

```bash
echo '{
  "query": "from:arlenagreer@gmail.com",
  "max_results": 5
}' | ruby gmail_manager.rb list
```

**Expected Output:**
```json
{
  "status": "success",
  "operation": "list",
  "query": "from:arlenagreer@gmail.com",
  "count": 5,
  "messages": [
    {
      "id": "18d...",
      "thread_id": "18d...",
      "snippet": "...",
      "from": "Arlen Agreer <arlenagreer@gmail.com>",
      "to": "...",
      "subject": "...",
      "date": "..."
    }
  ]
}
```

### Test 4: Automatic BCC Verification

Send an email without BCC specified and verify automatic BCC injection:

```bash
echo '{
  "to": ["arlenagreer@gmail.com"],
  "subject": "Auto-BCC Test",
  "body_html": "<html><body><p>Testing automatic BCC injection</p></body></html>"
}' | ruby gmail_manager.rb send
```

**Verify**: Check that arlenagreer@gmail.com appears in the BCC field in the JSON response

### Test 5: Multi-Recipient Email

```bash
echo '{
  "to": ["arlenagreer@gmail.com"],
  "cc": ["test@example.com"],
  "bcc": ["another@example.com"],
  "subject": "Multi-Recipient Test",
  "body_html": "<html><body><p>Testing multiple recipients with CC and BCC</p></body></html>"
}' | ruby gmail_manager.rb send
```

**Verify**: BCC field should include both `another@example.com` AND `arlenagreer@gmail.com`

## Troubleshooting

### Authentication Fails
- **Error**: "Invalid authorization code"
  - **Solution**: The code may have expired (they're single-use). Generate a new URL with `ruby gmail_manager.rb auth` and try again

### Missing Scopes
- **Error**: Token missing required scope
  - **Solution**: Delete `~/.claude/.google/token.json` and re-authenticate to ensure all scopes are granted

### API Errors
- **Error**: "Gmail API error: ..."
  - **Solution**: Check that Gmail API is enabled in Google Cloud Console
  - Verify the OAuth client credentials are correct

### Exit Codes
- **0**: Success
- **1**: Operation failed
- **2**: Authentication error
- **3**: API error
- **4**: Invalid arguments

## Next Steps After Validation

Once all tests pass:
1. Update email skill wrapper to use gmail_manager.rb
2. Remove Gmail MCP dependency from .mcp.json
3. Test email skill end-to-end
4. Document migration completion

## Script Information

- **Location**: `~/.claude/skills/email/scripts/gmail_manager.rb`
- **Version**: 3.0.0
- **Ruby Version**: 3.3.7
- **Dependencies**: google-apis-gmail_v1, mail (both installed)
- **Token Storage**: `~/.claude/.google/token.json` (shared with calendar and contacts)
- **Automatic BCC**: All emails automatically BCC to arlenagreer@gmail.com
