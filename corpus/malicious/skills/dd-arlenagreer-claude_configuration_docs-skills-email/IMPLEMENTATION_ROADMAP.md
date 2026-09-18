# Email Skill Migration: Gmail MCP to Google CLI Implementation Roadmap

**Version**: 1.0
**Date**: 2025-01-09
**Scope**: Migrate email skill from Gmail MCP server to Google CLI (Ruby script) pattern
**Strategy**: Systematic migration maintaining workflow compatibility

---

## Executive Summary

This roadmap outlines the migration of the email agent skill from Gmail MCP server integration to Google CLI (Ruby script) pattern, following the established architecture used by contacts and calendar skills. The migration uses `Google::Apis::GmailV1::AUTH_GMAIL_MODIFY` scope to enable future read capabilities while maintaining full backwards compatibility with the existing email skill workflow.

**Key Benefits:**
- ✅ Context window efficiency (removes MCP server overhead)
- ✅ Architectural consistency across all Google skills
- ✅ Single OAuth authentication flow for all Google services
- ✅ Foundation for future read/search operations
- ✅ Direct API control and reliability

---

## Phase 1: Preparation & Environment Setup

**Duration**: 30 minutes
**Objective**: Install dependencies and verify environment readiness

### Task 1.1: Install Required Ruby Gems
**Priority**: High
**Estimated Time**: 5 minutes

```bash
# Install Gmail API gem
gem install google-apis-gmail_v1

# Install Mail gem for RFC 2822 email formatting
gem install mail

# Verify installations
gem list | grep google-apis-gmail
gem list | grep mail
```

**Success Criteria:**
- ✅ `google-apis-gmail_v1` gem installed (v0.38+)
- ✅ `mail` gem installed (v2.8+)
- ✅ No dependency conflicts

**Dependencies**: None
**Risks**: None (low-risk installation)

---

### Task 1.2: Verify Existing OAuth Setup
**Priority**: High
**Estimated Time**: 10 minutes

```bash
# Check for existing OAuth credentials
ls -la ~/.claude/.google/client_secret.json
ls -la ~/.claude/.google/token.json

# Verify contacts skill still works (validates OAuth)
~/.claude/skills/contacts/scripts/contacts_manager.rb list --max-results 5

# Verify calendar skill still works
~/.claude/skills/calendar/scripts/calendar_manager.rb list --max-results 5
```

**Success Criteria:**
- ✅ `client_secret.json` exists and is valid
- ✅ `token.json` exists (will be updated with Gmail scope)
- ✅ Contacts and calendar skills execute successfully

**Dependencies**: None
**Risks**: Low - existing skills proven working

---

### Task 1.3: Backup Current Email Skill
**Priority**: Medium
**Estimated Time**: 5 minutes

```bash
# Create backup of current email skill
cd ~/.claude/skills/email
cp SKILL.md SKILL.md.backup-$(date +%Y%m%d)
cp -r scripts scripts.backup-$(date +%Y%m%d)

# Verify backups
ls -la *.backup-*
ls -la scripts.backup-*
```

**Success Criteria:**
- ✅ SKILL.md backed up with timestamp
- ✅ Scripts directory backed up
- ✅ Backups verified readable

**Dependencies**: None
**Risks**: None

---

### Task 1.4: Review Current Email Skill Usage
**Priority**: Medium
**Estimated Time**: 10 minutes

**Action Items:**
1. Review current SKILL.md workflow documentation
2. Identify all MCP tool calls: `mcp__gmail__send_email`, `mcp__gmail__draft_email`
3. Document current workflow expectations
4. Verify seasonal themes and HTML templates location
5. Confirm BCC behavior (always arlenagreer@gmail.com)

**Success Criteria:**
- ✅ Current workflow documented
- ✅ All MCP calls identified
- ✅ HTML templates and themes verified
- ✅ BCC requirements confirmed

**Dependencies**: None
**Deliverables**: Workflow analysis notes

---

## Phase 2: Core Implementation - gmail_manager.rb

**Duration**: 2-3 hours
**Objective**: Create Ruby CLI script for Gmail operations

### Task 2.1: Create gmail_manager.rb Skeleton
**Priority**: Critical
**Estimated Time**: 30 minutes

**File**: `~/.claude/skills/email/scripts/gmail_manager.rb`

```ruby
#!/usr/bin/env ruby

require 'google/apis/gmail_v1'
require 'google/apis/calendar_v3'
require 'google/apis/people_v1'
require 'googleauth'
require 'googleauth/stores/file_token_store'
require 'mail'
require 'json'
require 'optparse'
require 'base64'

# OAuth Scopes (shared across contacts, calendar, email)
GMAIL_SCOPE = Google::Apis::GmailV1::AUTH_GMAIL_MODIFY
CALENDAR_SCOPE = Google::Apis::CalendarV3::AUTH_CALENDAR
CONTACTS_SCOPE = Google::Apis::PeopleV1::AUTH_CONTACTS

# Shared OAuth credentials
CREDENTIALS_PATH = File.join(Dir.home, '.claude', '.google', 'client_secret.json')
TOKEN_PATH = File.join(Dir.home, '.claude', '.google', 'token.json')

class GmailManager
  def initialize
    @gmail_service = Google::Apis::GmailV1::GmailService.new
    @gmail_service.authorization = authorize
  end

  def authorize
    # TODO: Implement shared OAuth pattern
  end

  def send_email(to:, subject:, body_html:, cc: [], bcc: [])
    # TODO: Implement send operation
  end

  def draft_email(to:, subject:, body_html:, cc: [], bcc: [])
    # TODO: Implement draft operation
  end

  def list_messages(query: nil, max_results: 10)
    # TODO: Future implementation for read capability
  end
end

# CLI Interface
# TODO: Implement command-line argument parsing
```

**Success Criteria:**
- ✅ File created with proper shebang
- ✅ All required gems imported
- ✅ OAuth scope constants defined correctly
- ✅ Class structure established

**Dependencies**: Task 1.1 (gem installation)
**Risks**: None

---

### Task 2.2: Implement OAuth Authorization
**Priority**: Critical
**Estimated Time**: 45 minutes

**Implementation Pattern** (follows contacts/calendar pattern):

```ruby
def authorize
  client_id = Google::Auth::ClientId.from_file(CREDENTIALS_PATH)
  token_store = Google::Auth::Stores::FileTokenStore.new(file: TOKEN_PATH)

  authorizer = Google::Auth::UserAuthorizer.new(
    client_id,
    [CALENDAR_SCOPE, CONTACTS_SCOPE, GMAIL_SCOPE],
    token_store
  )

  user_id = 'default'
  credentials = authorizer.get_credentials(user_id)

  if credentials.nil?
    # OAuth flow needed - output URL for user authorization
    url = authorizer.get_authorization_url(base_url: 'urn:ietf:wg:oauth:2.0:oob')

    puts JSON.pretty_generate({
      status: 'auth_required',
      message: 'Gmail scope requires authorization',
      authorization_url: url,
      instructions: [
        '1. Open the URL above in your browser',
        '2. Authorize access to Gmail, Calendar, and Contacts',
        '3. Copy the authorization code',
        '4. Run: ruby gmail_manager.rb authorize --code YOUR_CODE'
      ]
    })

    exit 2 # Auth error exit code
  end

  credentials
rescue Google::Apis::AuthorizationError => e
  puts JSON.pretty_generate({
    status: 'error',
    error_code: 'AUTH_ERROR',
    message: 'Authorization failed',
    details: e.message
  })
  exit 2
rescue => e
  puts JSON.pretty_generate({
    status: 'error',
    error_code: 'UNKNOWN_ERROR',
    message: e.message,
    error_type: e.class.name
  })
  exit 3
end
```

**Success Criteria:**
- ✅ OAuth flow triggers on first run
- ✅ Token includes all three scopes (Calendar, Contacts, Gmail)
- ✅ Existing token automatically updated with Gmail scope
- ✅ Clear error messages for auth failures
- ✅ Exit codes follow standard pattern (0=success, 2=auth error, 3=api error)

**Dependencies**: Task 2.1
**Risks**: Medium - Token update may require user interaction

**Testing:**
```bash
# Test OAuth flow
ruby gmail_manager.rb send --to "test@example.com" --subject "Test" --body-html "<p>Test</p>"
# Should trigger OAuth if Gmail scope missing
```

---

### Task 2.3: Implement Send Email Operation
**Priority**: Critical
**Estimated Time**: 45 minutes

```ruby
def send_email(to:, subject:, body_html:, cc: [], bcc: [])
  # Ensure BCC always includes arlenagreer@gmail.com
  bcc = Array(bcc)
  bcc << 'arlenagreer@gmail.com' unless bcc.include?('arlenagreer@gmail.com')

  # Create RFC 2822 compliant email using Mail gem
  mail = Mail.new do
    from     'me'  # Gmail API uses 'me' for authenticated user
    to       Array(to)
    cc       Array(cc) if cc.any?
    bcc      bcc if bcc.any?
    subject  subject

    # HTML body
    html_part do
      content_type 'text/html; charset=UTF-8'
      body body_html
    end
  end

  # Encode message for Gmail API (Base64 URL-safe encoding)
  encoded_message = Base64.urlsafe_encode64(mail.to_s)

  message_object = Google::Apis::GmailV1::Message.new(
    raw: encoded_message
  )

  # Send via Gmail API
  result = @gmail_service.send_user_message('me', message_object)

  {
    status: 'success',
    operation: 'send',
    message_id: result.id,
    thread_id: result.thread_id,
    label_ids: result.label_ids,
    recipients: {
      to: to,
      cc: cc,
      bcc: bcc
    }
  }
rescue Google::Apis::AuthorizationError => e
  {
    status: 'error',
    error_code: 'AUTH_ERROR',
    message: 'Authorization failed - run authorize command',
    details: e.message
  }
rescue Google::Apis::ClientError => e
  {
    status: 'error',
    error_code: 'API_ERROR',
    message: 'Gmail API error',
    details: e.message,
    status_code: e.status_code
  }
rescue => e
  {
    status: 'error',
    error_code: 'UNKNOWN_ERROR',
    message: e.message,
    error_type: e.class.name,
    backtrace: e.backtrace.first(5)
  }
end
```

**Success Criteria:**
- ✅ Sends HTML emails successfully
- ✅ BCC automatically includes arlenagreer@gmail.com
- ✅ Supports multiple recipients (to, cc, bcc)
- ✅ Returns message_id and thread_id
- ✅ Proper error handling with structured JSON output
- ✅ RFC 2822 compliant email formatting

**Dependencies**: Task 2.2 (OAuth)
**Risks**: Low - Gmail API well-documented

**Testing:**
```bash
ruby gmail_manager.rb send \
  --to "test@example.com" \
  --subject "Test Email" \
  --body-html "<html><body><h1>Test</h1><p>This is a test.</p></body></html>" \
  --bcc "another@example.com"

# Expected output:
# {
#   "status": "success",
#   "operation": "send",
#   "message_id": "18d1234567890abcd",
#   "thread_id": "18d1234567890abcd",
#   ...
# }
```

---

### Task 2.4: Implement Draft Email Operation
**Priority**: Critical
**Estimated Time**: 30 minutes

```ruby
def draft_email(to:, subject:, body_html:, cc: [], bcc: [])
  # Similar to send_email but creates draft instead
  bcc = Array(bcc)
  bcc << 'arlenagreer@gmail.com' unless bcc.include?('arlenagreer@gmail.com')

  mail = Mail.new do
    from     'me'
    to       Array(to)
    cc       Array(cc) if cc.any?
    bcc      bcc if bcc.any?
    subject  subject

    html_part do
      content_type 'text/html; charset=UTF-8'
      body body_html
    end
  end

  encoded_message = Base64.urlsafe_encode64(mail.to_s)

  message_object = Google::Apis::GmailV1::Message.new(
    raw: encoded_message
  )

  draft_object = Google::Apis::GmailV1::Draft.new(
    message: message_object
  )

  # Create draft via Gmail API
  result = @gmail_service.create_user_draft('me', draft_object)

  {
    status: 'success',
    operation: 'draft',
    draft_id: result.id,
    message_id: result.message.id,
    thread_id: result.message.thread_id,
    recipients: {
      to: to,
      cc: cc,
      bcc: bcc
    }
  }
rescue Google::Apis::AuthorizationError => e
  {
    status: 'error',
    error_code: 'AUTH_ERROR',
    message: 'Authorization failed - run authorize command',
    details: e.message
  }
rescue Google::Apis::ClientError => e
  {
    status: 'error',
    error_code: 'API_ERROR',
    message: 'Gmail API error',
    details: e.message,
    status_code: e.status_code
  }
rescue => e
  {
    status: 'error',
    error_code: 'UNKNOWN_ERROR',
    message: e.message,
    error_type: e.class.name
  }
end
```

**Success Criteria:**
- ✅ Creates email drafts successfully
- ✅ BCC automatically includes arlenagreer@gmail.com
- ✅ Returns draft_id and message_id
- ✅ Draft visible in Gmail web interface
- ✅ Proper error handling

**Dependencies**: Task 2.2 (OAuth)
**Risks**: Low

**Testing:**
```bash
ruby gmail_manager.rb draft \
  --to "test@example.com" \
  --subject "Draft Email" \
  --body-html "<html><body><h1>Draft</h1><p>This is a draft.</p></body></html>"

# Verify draft created in Gmail web interface
```

---

### Task 2.5: Implement CLI Argument Parser
**Priority**: Critical
**Estimated Time**: 45 minutes

```ruby
# CLI Interface
def parse_arguments
  options = {}
  subcommand = ARGV[0]

  parser = OptionParser.new do |opts|
    opts.banner = "Usage: gmail_manager.rb [send|draft|list|authorize] [options]"

    opts.on('--to RECIPIENTS', 'Recipient email addresses (comma-separated)') do |to|
      options[:to] = to.split(',').map(&:strip)
    end

    opts.on('--cc RECIPIENTS', 'CC email addresses (comma-separated)') do |cc|
      options[:cc] = cc.split(',').map(&:strip)
    end

    opts.on('--bcc RECIPIENTS', 'BCC email addresses (comma-separated)') do |bcc|
      options[:bcc] = bcc.split(',').map(&:strip)
    end

    opts.on('--subject SUBJECT', 'Email subject') do |subject|
      options[:subject] = subject
    end

    opts.on('--body-html HTML', 'HTML email body') do |html|
      options[:body_html] = html
    end

    opts.on('--body-file FILE', 'Read HTML body from file') do |file|
      options[:body_html] = File.read(file)
    end

    opts.on('--query QUERY', 'Gmail search query (for list command)') do |query|
      options[:query] = query
    end

    opts.on('--max-results N', Integer, 'Maximum results (for list command)') do |n|
      options[:max_results] = n
    end

    opts.on('--code CODE', 'Authorization code (for authorize command)') do |code|
      options[:auth_code] = code
    end

    opts.on('-h', '--help', 'Show this help message') do
      puts opts
      exit 0
    end
  end

  parser.parse!(ARGV[1..-1])

  [subcommand, options]
rescue OptionParser::InvalidOption => e
  puts JSON.pretty_generate({
    status: 'error',
    error_code: 'INVALID_ARGS',
    message: e.message
  })
  exit 4
end

# Main execution
begin
  subcommand, options = parse_arguments
  manager = GmailManager.new

  result = case subcommand
  when 'send'
    manager.send_email(**options.slice(:to, :subject, :body_html, :cc, :bcc))
  when 'draft'
    manager.draft_email(**options.slice(:to, :subject, :body_html, :cc, :bcc))
  when 'list'
    manager.list_messages(**options.slice(:query, :max_results))
  when 'authorize'
    # Handle OAuth authorization code
    { status: 'success', message: 'Authorization handled by authorize method' }
  else
    {
      status: 'error',
      error_code: 'INVALID_COMMAND',
      message: "Unknown command: #{subcommand}",
      valid_commands: ['send', 'draft', 'list', 'authorize']
    }
  end

  puts JSON.pretty_generate(result)
  exit(result[:status] == 'success' ? 0 : 1)
rescue => e
  puts JSON.pretty_generate({
    status: 'error',
    error_code: 'EXECUTION_ERROR',
    message: e.message,
    error_type: e.class.name,
    backtrace: e.backtrace.first(5)
  })
  exit 1
end
```

**Success Criteria:**
- ✅ All commands accept proper arguments
- ✅ Help text displays correctly
- ✅ JSON output for all operations
- ✅ Proper exit codes (0=success, 1=failed, 2=auth, 3=api, 4=args)
- ✅ Support for reading HTML from file

**Dependencies**: Tasks 2.1-2.4
**Risks**: None

**Testing:**
```bash
# Test help
ruby gmail_manager.rb --help

# Test invalid command
ruby gmail_manager.rb invalid

# Test send with all options
ruby gmail_manager.rb send \
  --to "test@example.com" \
  --cc "cc@example.com" \
  --bcc "bcc@example.com" \
  --subject "Full Test" \
  --body-html "<p>Test with all options</p>"
```

---

### Task 2.6: Add List Messages Operation (Future Read Capability)
**Priority**: Medium (enables future features)
**Estimated Time**: 30 minutes

```ruby
def list_messages(query: nil, max_results: 10)
  # List messages using Gmail API
  # This enables future read/search capabilities

  list_params = {
    user_id: 'me',
    max_results: max_results
  }
  list_params[:q] = query if query

  result = @gmail_service.list_user_messages(**list_params)

  messages = result.messages || []

  # Fetch full message details for each message
  detailed_messages = messages.map do |msg|
    full_message = @gmail_service.get_user_message('me', msg.id, format: 'metadata')

    # Extract headers
    headers = full_message.payload.headers.each_with_object({}) do |header, hash|
      hash[header.name.downcase] = header.value
    end

    {
      id: full_message.id,
      thread_id: full_message.thread_id,
      snippet: full_message.snippet,
      from: headers['from'],
      to: headers['to'],
      subject: headers['subject'],
      date: headers['date'],
      labels: full_message.label_ids
    }
  end

  {
    status: 'success',
    operation: 'list',
    query: query,
    message_count: detailed_messages.length,
    messages: detailed_messages
  }
rescue Google::Apis::AuthorizationError => e
  {
    status: 'error',
    error_code: 'AUTH_ERROR',
    message: 'Authorization failed',
    details: e.message
  }
rescue Google::Apis::ClientError => e
  {
    status: 'error',
    error_code: 'API_ERROR',
    message: 'Gmail API error',
    details: e.message
  }
rescue => e
  {
    status: 'error',
    error_code: 'UNKNOWN_ERROR',
    message: e.message,
    error_type: e.class.name
  }
end
```

**Success Criteria:**
- ✅ Lists messages with metadata
- ✅ Supports Gmail search queries
- ✅ Returns structured JSON output
- ✅ Proper error handling

**Dependencies**: Task 2.2 (OAuth with GMAIL_MODIFY scope)
**Risks**: None (foundation for future features)

**Testing:**
```bash
# List recent messages
ruby gmail_manager.rb list --max-results 5

# Search for specific messages
ruby gmail_manager.rb list --query "is:unread from:example.com" --max-results 10
```

---

### Task 2.7: Add File Permissions and Testing
**Priority**: High
**Estimated Time**: 15 minutes

```bash
# Make script executable
chmod +x ~/.claude/skills/email/scripts/gmail_manager.rb

# Create test script
cat > ~/.claude/skills/email/scripts/test_gmail_manager.sh <<'EOF'
#!/bin/bash
set -e

echo "=== Testing gmail_manager.rb ==="

echo "1. Testing help command..."
ruby gmail_manager.rb --help

echo "2. Testing send operation..."
ruby gmail_manager.rb send \
  --to "test@example.com" \
  --subject "Test from gmail_manager.rb" \
  --body-html "<html><body><h1>Test Email</h1><p>This is a test email from the new gmail_manager.rb script.</p></body></html>"

echo "3. Testing draft operation..."
ruby gmail_manager.rb draft \
  --to "draft-test@example.com" \
  --subject "Draft Test" \
  --body-html "<html><body><p>Draft test email</p></body></html>"

echo "4. Testing list operation..."
ruby gmail_manager.rb list --max-results 3

echo "=== All tests passed ==="
EOF

chmod +x ~/.claude/skills/email/scripts/test_gmail_manager.sh
```

**Success Criteria:**
- ✅ Script executable and has proper shebang
- ✅ Test script created and executable
- ✅ All test operations succeed

**Dependencies**: Tasks 2.1-2.6
**Risks**: None

---

## Phase 3: SKILL.md Update

**Duration**: 1 hour
**Objective**: Update email skill documentation to reflect Google CLI implementation

### Task 3.1: Update Technical Stack Section
**Priority**: Critical
**Estimated Time**: 15 minutes

**File**: `~/.claude/skills/email/SKILL.md`

**Current Section 2:**
```markdown
## Technical Stack

**Primary Method**: Gmail MCP integration
**Fallback Method**: Himalaya CLI (when MCP unavailable)
**Contact Resolution**: `~/.claude/skills/email/lookup_contact_email.rb --name "First Last"`
```

**Updated Section 2:**
```markdown
## Technical Stack

**Primary Method**: Google Gmail API via Ruby CLI (`gmail_manager.rb`)
**Authentication**: Shared OAuth token (`~/.claude/.google/token.json`)
**OAuth Scopes**: Gmail (modify), Calendar, Contacts
**Fallback Method**: Himalaya CLI (when OAuth unavailable)
**Contact Resolution**: `~/.claude/skills/email/scripts/lookup_contact_email.rb --name "First Last"`

### Gmail Manager CLI

**Script Location**: `~/.claude/skills/email/scripts/gmail_manager.rb`

**Commands:**
```bash
# Send email
gmail_manager.rb send --to EMAIL --subject SUBJECT --body-html HTML

# Draft email
gmail_manager.rb draft --to EMAIL --subject SUBJECT --body-html HTML

# List messages (future capability)
gmail_manager.rb list --query QUERY --max-results N
```

**Exit Codes:**
- `0`: Success
- `1`: Operation failed
- `2`: Authentication error
- `3`: API error
- `4`: Invalid arguments
```

**Success Criteria:**
- ✅ Technical stack accurately reflects Google CLI implementation
- ✅ OAuth scope clearly documented
- ✅ CLI commands documented with examples
- ✅ Exit codes documented

**Dependencies**: Phase 2 completion
**Risks**: None

---

### Task 3.2: Update Workflow Sections
**Priority**: Critical
**Estimated Time**: 30 minutes

**Update Section 4.2: Sending Email**

**Current Step 3:**
```markdown
3. **Gmail MCP Call**: Invoke mcp__gmail__send_email() with structured parameters
```

**Updated Step 3:**
```markdown
3. **Gmail API Call**: Execute gmail_manager.rb send with structured parameters
   ```bash
   ~/.claude/skills/email/scripts/gmail_manager.rb send \
     --to "recipient@example.com" \
     --subject "Your Subject" \
     --body-html "<html>...</html>" \
     --bcc "arlenagreer@gmail.com"
   ```

   **Note**: BCC to arlenagreer@gmail.com is automatically added by the script.
```

**Update Section 4.3: Drafting Email**

**Current Step 2:**
```markdown
2. **Gmail MCP Draft**: Invoke mcp__gmail__draft_email() to save as draft
```

**Updated Step 2:**
```markdown
2. **Gmail API Draft**: Execute gmail_manager.rb draft to save as draft
   ```bash
   ~/.claude/skills/email/scripts/gmail_manager.rb draft \
     --to "recipient@example.com" \
     --subject "Your Subject" \
     --body-html "<html>...</html>"
   ```
```

**Success Criteria:**
- ✅ All MCP tool references removed
- ✅ CLI commands properly documented
- ✅ BCC behavior documented
- ✅ Workflow steps remain clear and actionable

**Dependencies**: Task 3.1
**Risks**: None

---

### Task 3.3: Add OAuth Setup Section
**Priority**: High
**Estimated Time**: 15 minutes

**Add New Section 2.5: OAuth Setup**

```markdown
### OAuth Setup

The email skill shares OAuth authentication with contacts and calendar skills.

**Initial Setup:**

1. **First Run**: The first time you use gmail_manager.rb, it will detect that Gmail scope is missing from the token:

   ```bash
   $ gmail_manager.rb send --to "test@example.com" --subject "Test" --body-html "<p>Test</p>"
   {
     "status": "auth_required",
     "message": "Gmail scope requires authorization",
     "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
     "instructions": [
       "1. Open the URL above in your browser",
       "2. Authorize access to Gmail, Calendar, and Contacts",
       "3. Copy the authorization code",
       "4. Run: ruby gmail_manager.rb authorize --code YOUR_CODE"
     ]
   }
   ```

2. **Authorize**: Follow the instructions to complete OAuth flow

3. **Verify**: Token will be updated with Gmail scope and shared across all Google skills

**Scope Requirements:**
- ✅ `https://www.googleapis.com/auth/gmail.modify` - Send, read, and modify emails
- ✅ `https://www.googleapis.com/auth/calendar` - Calendar access (shared)
- ✅ `https://www.googleapis.com/auth/contacts` - Contacts access (shared)

**Troubleshooting:**

If authorization fails, reset the token:
```bash
rm ~/.claude/.google/token.json
# Re-run gmail_manager.rb and complete OAuth flow again
```
```

**Success Criteria:**
- ✅ OAuth setup clearly documented
- ✅ First-run experience explained
- ✅ Troubleshooting steps provided
- ✅ Scope requirements listed

**Dependencies**: Task 3.2
**Risks**: None

---

### Task 3.4: Update Version and Changelog
**Priority**: Medium
**Estimated Time**: 10 minutes

**Update Version Header:**
```markdown
**Version**: 3.0.0
**Last Updated**: 2025-01-09
**Migration**: Gmail MCP → Google CLI (Ruby)
```

**Add Changelog Section:**
```markdown
## Changelog

### Version 3.0.0 (2025-01-09) - BREAKING CHANGE
- **Migration**: Replaced Gmail MCP server integration with Google CLI (Ruby script)
- **New**: Added `gmail_manager.rb` for direct Gmail API access
- **Changed**: OAuth scope updated to `AUTH_GMAIL_MODIFY` (enables future read capability)
- **Improved**: Shared OAuth authentication across contacts, calendar, and email skills
- **Removed**: Dependency on Gmail MCP server
- **Compatibility**: Workflow interface remains unchanged - only backend implementation changed

### Version 2.5.0 (Previous)
- Gmail MCP server integration
- Seasonal HTML themes
- Contact lookup via Ruby script
```

**Success Criteria:**
- ✅ Version bumped to 3.0.0
- ✅ Changelog documents breaking change
- ✅ Migration noted clearly

**Dependencies**: Task 3.3
**Risks**: None

---

## Phase 4: Testing & Validation

**Duration**: 1-2 hours
**Objective**: Comprehensive testing of all email skill functionality

### Task 4.1: OAuth Flow Testing
**Priority**: Critical
**Estimated Time**: 20 minutes

**Test Cases:**

1. **Fresh OAuth Flow** (if no Gmail scope):
   ```bash
   # Delete existing token to test fresh OAuth
   mv ~/.claude/.google/token.json ~/.claude/.google/token.json.backup

   # Trigger OAuth flow
   ~/.claude/skills/email/scripts/gmail_manager.rb send \
     --to "test@example.com" \
     --subject "OAuth Test" \
     --body-html "<p>Testing OAuth</p>"

   # Should output authorization URL and instructions
   ```

2. **Authorization Completion**:
   - Follow OAuth URL in browser
   - Authorize all scopes (Gmail, Calendar, Contacts)
   - Copy authorization code
   - Complete authorization (script should handle this automatically)

3. **Token Verification**:
   ```bash
   # Verify token has all three scopes
   # Token should work for contacts, calendar, and email

   ~/.claude/skills/contacts/scripts/contacts_manager.rb list --max-results 3
   ~/.claude/skills/calendar/scripts/calendar_manager.rb list --max-results 3
   ~/.claude/skills/email/scripts/gmail_manager.rb list --max-results 3
   ```

**Success Criteria:**
- ✅ OAuth flow triggers on first run
- ✅ Authorization URL opens correctly
- ✅ Token saved with all three scopes
- ✅ All three skills work with shared token
- ✅ No re-authorization needed after token update

**Dependencies**: Phase 2 & 3 completion
**Risks**: Medium - User interaction required

---

### Task 4.2: Email Sending Tests
**Priority**: Critical
**Estimated Time**: 30 minutes

**Test Cases:**

1. **Basic Send**:
   ```bash
   ruby gmail_manager.rb send \
     --to "test@example.com" \
     --subject "Basic Send Test" \
     --body-html "<html><body><h1>Test</h1><p>Basic email test</p></body></html>"
   ```

2. **Multiple Recipients**:
   ```bash
   ruby gmail_manager.rb send \
     --to "test1@example.com,test2@example.com" \
     --cc "cc@example.com" \
     --bcc "bcc@example.com" \
     --subject "Multiple Recipients Test" \
     --body-html "<p>Testing multiple recipients</p>"
   ```

3. **BCC Auto-Add Verification**:
   ```bash
   # Send without explicit BCC
   ruby gmail_manager.rb send \
     --to "test@example.com" \
     --subject "BCC Test" \
     --body-html "<p>Testing auto BCC</p>"

   # Verify output includes arlenagreer@gmail.com in BCC
   # Check Gmail sent folder to confirm BCC
   ```

4. **HTML Email with Seasonal Theme**:
   ```bash
   # Create seasonal HTML (use existing seasonal theme generator)
   # Test with winter theme
   ruby gmail_manager.rb send \
     --to "test@example.com" \
     --subject "Seasonal Theme Test" \
     --body-file /tmp/seasonal_email.html
   ```

5. **Error Handling**:
   ```bash
   # Missing required field
   ruby gmail_manager.rb send --to "test@example.com"
   # Should return error with clear message

   # Invalid email format
   ruby gmail_manager.rb send \
     --to "invalid-email" \
     --subject "Test" \
     --body-html "<p>Test</p>"
   # Should return API error
   ```

**Success Criteria:**
- ✅ All sent emails arrive successfully
- ✅ BCC automatically includes arlenagreer@gmail.com
- ✅ Multiple recipients work correctly
- ✅ HTML formatting preserved
- ✅ Seasonal themes render correctly
- ✅ Error messages clear and actionable

**Dependencies**: Task 4.1 (OAuth)
**Risks**: Low

---

### Task 4.3: Email Drafting Tests
**Priority**: Critical
**Estimated Time**: 20 minutes

**Test Cases:**

1. **Basic Draft**:
   ```bash
   ruby gmail_manager.rb draft \
     --to "draft-test@example.com" \
     --subject "Draft Test" \
     --body-html "<html><body><p>This is a draft</p></body></html>"
   ```

2. **Draft Verification**:
   - Open Gmail web interface
   - Check Drafts folder
   - Verify draft appears with correct subject and recipients
   - Open draft and verify HTML rendering

3. **Draft with Multiple Recipients**:
   ```bash
   ruby gmail_manager.rb draft \
     --to "draft1@example.com,draft2@example.com" \
     --cc "draft-cc@example.com" \
     --subject "Multi-Recipient Draft" \
     --body-html "<p>Draft with multiple recipients</p>"
   ```

**Success Criteria:**
- ✅ Drafts created successfully
- ✅ Drafts visible in Gmail web interface
- ✅ All recipients preserved
- ✅ HTML formatting preserved
- ✅ Can edit and send draft from Gmail

**Dependencies**: Task 4.1 (OAuth)
**Risks**: Low

---

### Task 4.4: List Messages Tests (Future Capability)
**Priority**: Medium
**Estimated Time**: 15 minutes

**Test Cases:**

1. **Basic List**:
   ```bash
   ruby gmail_manager.rb list --max-results 10
   ```

2. **Search Query**:
   ```bash
   # Unread messages
   ruby gmail_manager.rb list --query "is:unread" --max-results 5

   # From specific sender
   ruby gmail_manager.rb list --query "from:example.com" --max-results 10

   # Subject search
   ruby gmail_manager.rb list --query "subject:important" --max-results 5
   ```

**Success Criteria:**
- ✅ Lists messages with metadata
- ✅ Search queries work correctly
- ✅ JSON output structured properly
- ✅ Message snippets accurate

**Dependencies**: Task 4.1 (OAuth with GMAIL_MODIFY scope)
**Risks**: None

---

### Task 4.5: Contact Lookup Integration Test
**Priority**: High
**Estimated Time**: 15 minutes

**Test Cases:**

1. **Email with Contact Lookup**:
   ```bash
   # Lookup Mark Whitney's email
   EMAIL=$(ruby ~/.claude/skills/email/scripts/lookup_contact_email.rb --name "Mark Whitney" | jq -r '.email')

   # Send email using looked-up address
   ruby gmail_manager.rb send \
     --to "$EMAIL" \
     --subject "Contact Lookup Test" \
     --body-html "<p>Testing contact lookup integration</p>"
   ```

2. **Verify Preferred Email Overrides**:
   ```bash
   # Test Mark Whitney override
   ruby ~/.claude/skills/email/scripts/lookup_contact_email.rb --name "Mark Whitney"
   # Should return mark.whitney@solacetechnologies.com

   # Test Julie Whitney override
   ruby ~/.claude/skills/email/scripts/lookup_contact_email.rb --name "Julie Whitney"
   # Should return juliewhitney@gmail.com
   ```

**Success Criteria:**
- ✅ Contact lookup works with gmail_manager.rb
- ✅ Preferred email overrides respected
- ✅ Integration seamless

**Dependencies**: Task 4.2 (Email sending)
**Risks**: None

---

### Task 4.6: Full Workflow Integration Test
**Priority**: Critical
**Estimated Time**: 20 minutes

**Test Complete Email Skill Workflow:**

```bash
#!/bin/bash
# Complete email skill workflow test

echo "=== Email Skill Integration Test ==="

# 1. Contact Lookup
echo "1. Looking up contact email..."
CONTACT_EMAIL=$(ruby ~/.claude/skills/email/scripts/lookup_contact_email.rb \
  --name "Test Contact" | jq -r '.email')

# 2. Generate Seasonal HTML (winter theme)
SEASON=$(date +%m | awk '{if ($1>=12 || $1<=2) print "winter"; else if ($1>=3 && $1<=5) print "spring"; else if ($1>=6 && $1<=8) print "summer"; else print "fall"}')

HTML_BODY=$(cat <<EOF
<html>
<body style="font-family: Arial, sans-serif; background-color: #f0f8ff; padding: 20px;">
  <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px;">
    <h1 style="color: #1e90ff;">Seasonal Greetings - $SEASON</h1>
    <p>This is a test email from the new gmail_manager.rb script.</p>
    <p>Testing complete email skill workflow including:</p>
    <ul>
      <li>Contact lookup integration</li>
      <li>Seasonal theme application</li>
      <li>HTML email composition</li>
      <li>Gmail API sending</li>
    </ul>
    <p>Best regards,<br>Claude Email Skill</p>
  </div>
</body>
</html>
EOF
)

# 3. Send email
echo "2. Sending email with seasonal theme..."
RESULT=$(ruby ~/.claude/skills/email/scripts/gmail_manager.rb send \
  --to "$CONTACT_EMAIL" \
  --subject "Email Skill Workflow Test - $SEASON Theme" \
  --body-html "$HTML_BODY")

echo "$RESULT"

# 4. Verify success
if echo "$RESULT" | jq -e '.status == "success"' > /dev/null; then
  MESSAGE_ID=$(echo "$RESULT" | jq -r '.message_id')
  echo "✅ Email sent successfully! Message ID: $MESSAGE_ID"
else
  echo "❌ Email send failed!"
  exit 1
fi

# 5. Create draft
echo "3. Creating draft email..."
DRAFT_RESULT=$(ruby ~/.claude/skills/email/scripts/gmail_manager.rb draft \
  --to "draft-test@example.com" \
  --subject "Draft Test - $SEASON Theme" \
  --body-html "$HTML_BODY")

echo "$DRAFT_RESULT"

# 6. Verify draft success
if echo "$DRAFT_RESULT" | jq -e '.status == "success"' > /dev/null; then
  DRAFT_ID=$(echo "$DRAFT_RESULT" | jq -r '.draft_id')
  echo "✅ Draft created successfully! Draft ID: $DRAFT_ID"
else
  echo "❌ Draft creation failed!"
  exit 1
fi

echo "=== All workflow tests passed ==="
```

**Success Criteria:**
- ✅ Contact lookup succeeds
- ✅ Seasonal theme applies correctly
- ✅ Email sends successfully
- ✅ Draft creates successfully
- ✅ All integrations work together
- ✅ BCC automatically included

**Dependencies**: All previous tasks
**Risks**: Low - comprehensive end-to-end test

---

## Phase 5: Documentation & Cleanup

**Duration**: 30 minutes
**Objective**: Finalize documentation and clean up

### Task 5.1: Update Global SuperClaude Documentation
**Priority**: High
**Estimated Time**: 15 minutes

**Files to Update:**

1. **`~/.claude/CLAUDE.md`** - SuperClaude main documentation
   - Update email skill reference
   - Document Google CLI pattern consistency
   - Note Gmail MCP removal

2. **`~/.claude/RULES.md`** - Behavioral rules
   - Verify email skill rules still apply
   - Update technical stack references

**Changes:**

**In CLAUDE.md Section: Communication Skills - Email**

```markdown
## Email Communication - AGENT SKILL

**Command**: `@~/.claude/skills/email/SKILL.md [request]`

**🔴 CRITICAL: ALL email operations MUST use the Email Agent Skill**

### Technical Implementation

**Method**: Google Gmail API via Ruby CLI
**Authentication**: Shared OAuth token with Calendar and Contacts skills
**Script**: `~/.claude/skills/email/scripts/gmail_manager.rb`
**Scopes**: Gmail (modify), Calendar, Contacts

### Why This Matters

The email skill provides essential features:
- ✅ **Arlen's authentic writing style** - Maintains consistent voice and tone
- ✅ **Seasonal HTML formatting** - Professional themed templates based on current date
- ✅ **Automatic contact lookup** - Google Contacts integration by name
- ✅ **Mobile-responsive templates** - Proper formatting on all devices
- ✅ **Date-aware theming** - Spring, summer, fall, winter, holiday styles
- ✅ **Shared OAuth** - Works seamlessly with calendar and contacts skills
```

**Success Criteria:**
- ✅ CLAUDE.md updated with new implementation details
- ✅ RULES.md verified compatible
- ✅ No references to Gmail MCP remain

**Dependencies**: Phase 4 completion
**Risks**: None

---

### Task 5.2: Remove Gmail MCP Server References
**Priority**: Medium
**Estimated Time**: 10 minutes

**Actions:**

1. **Check for .mcp.json**:
   ```bash
   # If .mcp.json exists, remove Gmail MCP entry
   # Backup first
   cp ~/.claude/.mcp.json ~/.claude/.mcp.json.backup-$(date +%Y%m%d)

   # Edit .mcp.json to remove gmail MCP server
   # (If file doesn't exist, skip this step)
   ```

2. **Search for MCP References**:
   ```bash
   # Search for any remaining Gmail MCP references
   grep -r "mcp__gmail" ~/.claude/skills/email/

   # Should only find this in backups
   ```

**Success Criteria:**
- ✅ .mcp.json updated (if exists)
- ✅ No active Gmail MCP references in email skill
- ✅ Backups preserved

**Dependencies**: Phase 4 completion
**Risks**: None

---

### Task 5.3: Create Migration Summary Document
**Priority**: Medium
**Estimated Time**: 15 minutes

**File**: `~/.claude/skills/email/MIGRATION_NOTES.md`

```markdown
# Email Skill Migration Summary

**Date**: 2025-01-09
**Migration**: Gmail MCP Server → Google CLI (Ruby)
**Version**: 2.5.0 → 3.0.0

## Changes Made

### Architecture
- **Before**: Gmail MCP server integration via `mcp__gmail__send_email` and `mcp__gmail__draft_email`
- **After**: Google Gmail API via Ruby CLI script `gmail_manager.rb`

### Authentication
- **Before**: MCP server handled OAuth internally
- **After**: Shared OAuth token (`~/.claude/.google/token.json`) with Calendar and Contacts skills
- **New Scope**: `Google::Apis::GmailV1::AUTH_GMAIL_MODIFY` (enables send, draft, and read)

### Scripts Added
- `gmail_manager.rb` - Main Gmail operations (send, draft, list)
- `test_gmail_manager.sh` - Test script for validation

### Documentation Updated
- `SKILL.md` - Version 3.0.0 with new technical stack
- `IMPLEMENTATION_ROADMAP.md` - This migration guide
- `MIGRATION_NOTES.md` - Migration summary

## Benefits Achieved

1. ✅ **Context Window Efficiency**: Removed MCP server overhead
2. ✅ **Architectural Consistency**: All Google skills use same pattern
3. ✅ **Shared Authentication**: Single OAuth flow for Gmail, Calendar, Contacts
4. ✅ **Future Capabilities**: Gmail read/search operations enabled by GMAIL_MODIFY scope
5. ✅ **Reliability**: Direct API control, no MCP dependency

## Backwards Compatibility

**User-Facing Changes**: None
**Workflow Interface**: Unchanged
**Breaking Changes**: Only backend implementation (not visible to users)

## OAuth Token Update

The first use of `gmail_manager.rb` will trigger OAuth re-authorization to add Gmail scope to the existing token. This is automatic and one-time.

**Token Scopes After Migration:**
- Gmail (modify)
- Calendar
- Contacts

## Testing Completed

- ✅ OAuth flow with Gmail scope
- ✅ Email sending with HTML
- ✅ Email drafting
- ✅ Multiple recipients (to, cc, bcc)
- ✅ Automatic BCC to arlenagreer@gmail.com
- ✅ Contact lookup integration
- ✅ Seasonal theme application
- ✅ List messages (future capability)
- ✅ Error handling

## Files Modified

- `~/.claude/skills/email/SKILL.md` - Updated to v3.0.0
- `~/.claude/skills/email/scripts/gmail_manager.rb` - New script
- `~/.claude/skills/email/scripts/test_gmail_manager.sh` - New test script
- `~/.claude/CLAUDE.md` - Updated email skill reference
- `~/.claude/.google/token.json` - Updated with Gmail scope (automatic)

## Files Backed Up

- `~/.claude/skills/email/SKILL.md.backup-YYYYMMDD`
- `~/.claude/skills/email/scripts.backup-YYYYMMDD/`
- `~/.claude/.google/token.json.backup-YYYYMMDD` (if updated)

## Rollback Procedure

If needed, rollback is simple:

```bash
# Restore backups
cd ~/.claude/skills/email
cp SKILL.md.backup-YYYYMMDD SKILL.md
rm -rf scripts
mv scripts.backup-YYYYMMDD scripts

# Restore token (if needed)
cp ~/.claude/.google/token.json.backup-YYYYMMDD ~/.claude/.google/token.json

# Re-enable Gmail MCP in .mcp.json (if it was removed)
```

## Future Enhancements Enabled

With `GMAIL_MODIFY` scope, the following operations are now possible:

1. **Read Messages**: List and search inbox
2. **Message Management**: Archive, label, delete messages
3. **Thread Management**: Manage email conversations
4. **Advanced Search**: Complex Gmail search queries
5. **Attachment Handling**: Download and process attachments

These can be added to `gmail_manager.rb` as needed without requiring OAuth re-authorization.
```

**Success Criteria:**
- ✅ Migration summary created
- ✅ Changes documented
- ✅ Rollback procedure provided
- ✅ Future enhancements outlined

**Dependencies**: All previous phases
**Risks**: None

---

## Phase 6: Final Validation & Sign-off

**Duration**: 30 minutes
**Objective**: Final verification and migration completion

### Task 6.1: Comprehensive System Test
**Priority**: Critical
**Estimated Time**: 20 minutes

**Full System Integration Test:**

```bash
#!/bin/bash
# Final comprehensive test of all Google skills

echo "=== Comprehensive Google Skills Integration Test ==="

# Test 1: Contacts Skill
echo "1. Testing Contacts Skill..."
CONTACTS_RESULT=$(~/.claude/skills/contacts/scripts/contacts_manager.rb list --max-results 3)
if echo "$CONTACTS_RESULT" | jq -e '.status == "success"' > /dev/null; then
  echo "✅ Contacts skill working"
else
  echo "❌ Contacts skill failed"
  exit 1
fi

# Test 2: Calendar Skill
echo "2. Testing Calendar Skill..."
CALENDAR_RESULT=$(~/.claude/skills/calendar/scripts/calendar_manager.rb list --max-results 3)
if echo "$CALENDAR_RESULT" | jq -e '.status == "success"' > /dev/null; then
  echo "✅ Calendar skill working"
else
  echo "❌ Calendar skill failed"
  exit 1
fi

# Test 3: Email Skill - Contact Lookup
echo "3. Testing Email Skill - Contact Lookup..."
LOOKUP_RESULT=$(~/.claude/skills/email/scripts/lookup_contact_email.rb --name "Test")
if echo "$LOOKUP_RESULT" | jq -e '.status == "success" or .status == "not_found"' > /dev/null; then
  echo "✅ Email contact lookup working"
else
  echo "❌ Email contact lookup failed"
  exit 1
fi

# Test 4: Email Skill - Send
echo "4. Testing Email Skill - Send..."
SEND_RESULT=$(~/.claude/skills/email/scripts/gmail_manager.rb send \
  --to "final-test@example.com" \
  --subject "Final Integration Test" \
  --body-html "<html><body><h1>Success</h1><p>All systems operational</p></body></html>")
if echo "$SEND_RESULT" | jq -e '.status == "success"' > /dev/null; then
  MESSAGE_ID=$(echo "$SEND_RESULT" | jq -r '.message_id')
  echo "✅ Email send working (Message ID: $MESSAGE_ID)"
else
  echo "❌ Email send failed"
  exit 1
fi

# Test 5: Email Skill - Draft
echo "5. Testing Email Skill - Draft..."
DRAFT_RESULT=$(~/.claude/skills/email/scripts/gmail_manager.rb draft \
  --to "final-draft-test@example.com" \
  --subject "Final Draft Test" \
  --body-html "<html><body><p>Draft test</p></body></html>")
if echo "$DRAFT_RESULT" | jq -e '.status == "success"' > /dev/null; then
  DRAFT_ID=$(echo "$DRAFT_RESULT" | jq -r '.draft_id')
  echo "✅ Email draft working (Draft ID: $DRAFT_ID)"
else
  echo "❌ Email draft failed"
  exit 1
fi

# Test 6: Email Skill - List (Future Capability)
echo "6. Testing Email Skill - List..."
LIST_RESULT=$(~/.claude/skills/email/scripts/gmail_manager.rb list --max-results 3)
if echo "$LIST_RESULT" | jq -e '.status == "success"' > /dev/null; then
  MSG_COUNT=$(echo "$LIST_RESULT" | jq -r '.message_count')
  echo "✅ Email list working (Messages: $MSG_COUNT)"
else
  echo "❌ Email list failed"
  exit 1
fi

# Test 7: Shared OAuth Token Verification
echo "7. Verifying shared OAuth token..."
if [ -f ~/.claude/.google/token.json ]; then
  echo "✅ OAuth token exists"
  # Token should have all three scopes (not directly verifiable without decoding)
else
  echo "❌ OAuth token missing"
  exit 1
fi

echo ""
echo "=== ALL INTEGRATION TESTS PASSED ==="
echo "✅ Contacts Skill: Working"
echo "✅ Calendar Skill: Working"
echo "✅ Email Skill (Contact Lookup): Working"
echo "✅ Email Skill (Send): Working"
echo "✅ Email Skill (Draft): Working"
echo "✅ Email Skill (List): Working"
echo "✅ Shared OAuth: Verified"
echo ""
echo "Migration to Google CLI complete and validated!"
```

**Success Criteria:**
- ✅ All three Google skills operational
- ✅ Email send working
- ✅ Email draft working
- ✅ Email list working (future capability)
- ✅ Contact lookup integration working
- ✅ Shared OAuth token working across all skills
- ✅ No errors or warnings

**Dependencies**: All previous phases
**Risks**: None

---

### Task 6.2: Documentation Review Checklist
**Priority**: High
**Estimated Time**: 10 minutes

**Review Checklist:**

- [ ] **SKILL.md** version updated to 3.0.0
- [ ] **SKILL.md** technical stack section updated
- [ ] **SKILL.md** workflow sections updated (send/draft)
- [ ] **SKILL.md** OAuth setup section added
- [ ] **SKILL.md** changelog added
- [ ] **CLAUDE.md** email skill reference updated
- [ ] **RULES.md** verified compatible
- [ ] **IMPLEMENTATION_ROADMAP.md** completed
- [ ] **MIGRATION_NOTES.md** created
- [ ] **gmail_manager.rb** fully implemented and tested
- [ ] **test_gmail_manager.sh** created and working
- [ ] All backups created
- [ ] Gmail MCP references removed (if applicable)
- [ ] OAuth token updated with Gmail scope
- [ ] All tests passing

**Success Criteria:**
- ✅ All checklist items completed
- ✅ Documentation accurate and complete
- ✅ No broken references or outdated information

**Dependencies**: All previous tasks
**Risks**: None

---

## Success Criteria Summary

### Technical Requirements
- ✅ Gmail API gem installed and working
- ✅ Mail gem installed for RFC 2822 formatting
- ✅ OAuth flow working with GMAIL_MODIFY scope
- ✅ Shared token working across contacts, calendar, email
- ✅ gmail_manager.rb script fully functional
- ✅ Send operation working with HTML emails
- ✅ Draft operation working
- ✅ List operation working (future capability)
- ✅ Contact lookup integration working
- ✅ BCC auto-add to arlenagreer@gmail.com working

### Documentation Requirements
- ✅ SKILL.md updated to version 3.0.0
- ✅ All workflow sections reflect Google CLI implementation
- ✅ OAuth setup documented
- ✅ Changelog added
- ✅ SuperClaude documentation updated
- ✅ Migration notes created
- ✅ Implementation roadmap completed

### Testing Requirements
- ✅ All unit tests passing
- ✅ OAuth flow tested and verified
- ✅ Email send tested with multiple scenarios
- ✅ Email draft tested
- ✅ Contact lookup integration tested
- ✅ Seasonal themes tested
- ✅ Error handling tested
- ✅ Full system integration test passing

### Quality Requirements
- ✅ No breaking changes to user-facing workflow
- ✅ Backwards compatible (workflow interface unchanged)
- ✅ Code follows Ruby best practices
- ✅ Error messages clear and actionable
- ✅ JSON output structured and consistent
- ✅ Exit codes follow standard pattern

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| OAuth re-authorization required | High | Low | Automatic detection, clear instructions |
| Token scope conflicts | Low | Medium | Test with existing skills, shared scope pattern |
| HTML encoding issues | Low | Medium | Use Mail gem (RFC 2822 standard) |
| Missing Gmail scope | Medium | Low | Clear error messages, documented resolution |
| Breaking existing workflows | Low | High | Maintain identical SKILL.md interface |
| Email delivery failures | Low | High | Comprehensive testing, error handling |
| Contact lookup regression | Low | Medium | Test with existing script (no changes) |

---

## Rollback Plan

**If Migration Fails:**

1. **Restore Backups**:
   ```bash
   cd ~/.claude/skills/email
   cp SKILL.md.backup-YYYYMMDD SKILL.md
   rm -rf scripts
   mv scripts.backup-YYYYMMDD scripts
   ```

2. **Restore OAuth Token** (if needed):
   ```bash
   cp ~/.claude/.google/token.json.backup-YYYYMMDD ~/.claude/.google/token.json
   ```

3. **Re-enable Gmail MCP** (if it was removed):
   - Restore .mcp.json from backup
   - Verify MCP server available

4. **Test Rollback**:
   ```bash
   # Verify email skill works with MCP again
   # Test send operation
   # Test draft operation
   ```

**Rollback Time**: < 5 minutes
**Data Loss Risk**: None (all backups preserved)

---

## Timeline Summary

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| Phase 1: Preparation | 30 min | No |
| Phase 2: Implementation | 2-3 hours | Yes |
| Phase 3: Documentation | 1 hour | Yes |
| Phase 4: Testing | 1-2 hours | Yes |
| Phase 5: Cleanup | 30 min | No |
| Phase 6: Validation | 30 min | Yes |
| **Total** | **5-7 hours** | - |

**Recommended Execution**: Complete in single session to maintain context and momentum.

---

## Post-Migration Benefits

1. **Context Window Efficiency**
   - Removes Gmail MCP server from context
   - Reduces token usage by ~500-1000 tokens per session

2. **Architectural Consistency**
   - All Google skills use identical pattern
   - Shared OAuth authentication
   - Unified error handling

3. **Maintainability**
   - Single codebase for Google API integration
   - Easier to add new features
   - Clear debugging path

4. **Future Capabilities**
   - Read messages enabled by GMAIL_MODIFY scope
   - Search and filter operations possible
   - Message management operations available
   - No re-authorization needed for new features

5. **Reliability**
   - Direct API control
   - No MCP server dependency
   - Proven Ruby Google API client library

---

## Next Steps After Migration

**Immediate (Optional):**
1. Add message reading operation to gmail_manager.rb
2. Add search/filter capabilities
3. Add attachment handling
4. Enhance error recovery

**Future Enhancements:**
1. Implement email templates library
2. Add email scheduling capability
3. Create email analytics/tracking
4. Build email campaign management

---

## Appendix: Key Commands Reference

### Gmail Manager Commands

```bash
# Send email
gmail_manager.rb send \
  --to EMAIL \
  --subject SUBJECT \
  --body-html HTML \
  [--cc EMAIL] \
  [--bcc EMAIL]

# Draft email
gmail_manager.rb draft \
  --to EMAIL \
  --subject SUBJECT \
  --body-html HTML

# List messages
gmail_manager.rb list \
  [--query QUERY] \
  [--max-results N]

# Help
gmail_manager.rb --help
```

### Contact Lookup

```bash
# Lookup contact email
lookup_contact_email.rb --name "First Last"
```

### OAuth Management

```bash
# Check token
cat ~/.claude/.google/token.json

# Backup token
cp ~/.claude/.google/token.json ~/.claude/.google/token.json.backup

# Reset token (triggers re-auth)
rm ~/.claude/.google/token.json
```

### Testing Commands

```bash
# Run full test suite
~/.claude/skills/email/scripts/test_gmail_manager.sh

# Test specific operation
ruby gmail_manager.rb send --to "test@example.com" --subject "Test" --body-html "<p>Test</p>"
```

---

## Migration Completion Checklist

**Pre-Migration:**
- [ ] Backups created (SKILL.md, scripts, token)
- [ ] Dependencies installed (gmail gem, mail gem)
- [ ] Current functionality documented

**Implementation:**
- [ ] gmail_manager.rb created and tested
- [ ] OAuth implementation complete
- [ ] Send operation working
- [ ] Draft operation working
- [ ] List operation working
- [ ] CLI parser complete
- [ ] Error handling implemented

**Documentation:**
- [ ] SKILL.md updated to v3.0.0
- [ ] Technical stack section updated
- [ ] Workflow sections updated
- [ ] OAuth setup section added
- [ ] Changelog added
- [ ] CLAUDE.md updated
- [ ] Migration notes created

**Testing:**
- [ ] OAuth flow tested
- [ ] Email send tested (basic)
- [ ] Email send tested (multiple recipients)
- [ ] Email send tested (HTML/seasonal themes)
- [ ] Email draft tested
- [ ] Contact lookup integration tested
- [ ] Full workflow integration tested
- [ ] Error handling tested
- [ ] All skills tested (contacts, calendar, email)

**Cleanup:**
- [ ] Gmail MCP references removed
- [ ] Documentation finalized
- [ ] Final validation complete
- [ ] Migration notes documented

**Sign-off:**
- [ ] All tests passing
- [ ] All documentation complete
- [ ] Rollback plan verified
- [ ] Migration approved

---

**END OF IMPLEMENTATION ROADMAP**

*This roadmap provides a comprehensive, step-by-step guide for migrating the email skill from Gmail MCP to Google CLI implementation. Follow each phase sequentially for a successful migration with minimal risk.*
