# Phase 5: Email Validation Testing Checklist

## Pre-Flight Verification ✅

- [x] Script syntax valid (`ruby -c gmail_manager.rb`)
- [x] All gems installed and loadable (google-apis-gmail_v1, mail, json)
- [x] Auth mechanism working (generates valid authorization URL)
- [x] JSON output format correct
- [x] Usage documentation complete
- [x] Exit codes properly defined

## Authentication Status 🔐

- [ ] **PENDING: User must complete OAuth flow**
  - Authorization URL: https://accounts.google.com/o/oauth2/auth?access_type=offline&approval_prompt=force&client_id=948226087631-h46gg48bb541gheb82l8601titn13tpj.apps.googleusercontent.com&include_granted_scopes=true&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/calendar%20https://www.googleapis.com/auth/contacts%20https://www.googleapis.com/auth/gmail.modify
  - User must visit URL, grant permissions, copy code
  - Run: `ruby gmail_manager.rb auth <CODE>`
  - Verify: Token created at `~/.claude/.google/token.json`
  - Verify: Token contains all three scopes (calendar, contacts, gmail.modify)

## Test Cases (Run After Authentication) 🧪

### Test 1: Basic Send ✉️
```bash
echo '{"to":["arlenagreer@gmail.com"],"subject":"Gmail Manager Test - Send","body_html":"<html><body><h1>Test Email</h1><p>Sent at: '"$(date)"'</p></body></html>"}' | ruby gmail_manager.rb send
```
**Expected Results:**
- [ ] JSON response with `status: "success"`
- [ ] `message_id` and `thread_id` present
- [ ] BCC includes `arlenagreer@gmail.com` (automatic injection)
- [ ] Email received in Gmail
- [ ] Exit code: 0

### Test 2: Draft Creation 📝
```bash
echo '{"to":["test@example.com"],"subject":"Gmail Manager Test - Draft","body_html":"<html><body><h1>Draft</h1></body></html>","cc":["arlenagreer@gmail.com"]}' | ruby gmail_manager.rb draft
```
**Expected Results:**
- [ ] JSON response with `status: "success"`
- [ ] `draft_id`, `message_id`, `thread_id` present
- [ ] BCC includes `arlenagreer@gmail.com` (automatic injection)
- [ ] Draft visible in Gmail Drafts folder
- [ ] Exit code: 0

### Test 3: Message List 📋
```bash
echo '{"query":"from:arlenagreer@gmail.com","max_results":5}' | ruby gmail_manager.rb list
```
**Expected Results:**
- [ ] JSON response with `status: "success"`
- [ ] Array of messages with id, thread_id, snippet, from, to, subject, date
- [ ] Count matches number of messages returned
- [ ] Exit code: 0

### Test 4: Automatic BCC Verification 🔍
```bash
echo '{"to":["arlenagreer@gmail.com"],"subject":"Auto-BCC Test","body_html":"<p>No BCC specified</p>"}' | ruby gmail_manager.rb send
```
**Expected Results:**
- [ ] JSON response includes `bcc: ["arlenagreer@gmail.com"]`
- [ ] BCC was automatically added (not explicitly provided)
- [ ] Email received with proper BCC

### Test 5: Multi-Recipient 👥
```bash
echo '{"to":["arlenagreer@gmail.com"],"cc":["test@example.com"],"bcc":["another@example.com"],"subject":"Multi-Recipient","body_html":"<p>Multiple recipients</p>"}' | ruby gmail_manager.rb send
```
**Expected Results:**
- [ ] JSON response includes both `another@example.com` AND `arlenagreer@gmail.com` in BCC
- [ ] Automatic BCC preserved existing BCC recipients
- [ ] Email sent successfully

### Test 6: Error Handling - Missing Required Fields ❌
```bash
echo '{"subject":"Missing To Field"}' | ruby gmail_manager.rb send
```
**Expected Results:**
- [ ] JSON response with `status: "error"`
- [ ] `error_code: "MISSING_REQUIRED_FIELDS"`
- [ ] Clear error message
- [ ] Exit code: 4

### Test 7: Error Handling - Invalid Command ❌
```bash
ruby gmail_manager.rb invalid_command
```
**Expected Results:**
- [ ] Usage information displayed
- [ ] Exit code: 4

## Performance Validation ⚡

- [ ] Send operation completes in < 5 seconds
- [ ] Draft operation completes in < 5 seconds
- [ ] List operation completes in < 10 seconds
- [ ] No memory leaks or hanging processes
- [ ] JSON output properly formatted (parseable)

## Integration Readiness 🔗

After all tests pass:
- [ ] Script location verified: `~/.claude/skills/email/scripts/gmail_manager.rb`
- [ ] Token location verified: `~/.claude/.google/token.json`
- [ ] Script executable permissions set
- [ ] Documentation complete in `OAUTH_REAUTH_INSTRUCTIONS.md`
- [ ] Ready to update email skill wrapper
- [ ] Ready to remove Gmail MCP from `.mcp.json`

## Known Issues & Limitations ⚠️

- **Token Expiration**: OAuth tokens expire after a period. If errors occur, re-run auth flow.
- **Rate Limits**: Gmail API has rate limits. Avoid excessive testing.
- **Single-Use Codes**: Authorization codes can only be used once. Generate new URL if code fails.
- **BCC Visibility**: BCC recipients are not visible to To/CC recipients (by design).

## Troubleshooting Guide 🔧

### "Invalid credentials" error
- Solution: Delete token file and re-authenticate
- Command: `rm ~/.claude/.google/token.json && ruby gmail_manager.rb auth`

### "Scope not granted" error
- Solution: Ensure all three services (Gmail, Calendar, Contacts) were approved during OAuth
- Must grant ALL permissions, not just some

### Email not received
- Check Gmail spam folder
- Verify BCC is working (check sent folder)
- Try sending to a different email address

### JSON parsing error
- Verify input JSON is properly formatted
- Use `echo '{...}' | jq .` to validate JSON syntax before piping to script

## Success Criteria ✅

All tests passing means:
1. OAuth authentication working with all required scopes
2. Email sending functional with automatic BCC
3. Draft creation working correctly
4. Message listing operational
5. Error handling robust and informative
6. JSON output consistent and parseable
7. Ready for production use in email skill

## Next Phase: Integration

Once this checklist is complete, proceed to:
- Phase 6: Update email skill wrapper to use gmail_manager.rb
- Phase 7: Remove Gmail MCP dependency
- Phase 8: End-to-end skill testing
- Phase 9: Documentation and completion
