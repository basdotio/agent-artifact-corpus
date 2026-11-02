---
name: analytics
description: Generate GA4 analytics reports for KStoryBridge dashboard. Use for daily summaries, weekly deep-dives, funnel analysis, traffic source breakdowns, and realtime monitoring. Priority focus on user acquisition and growth metrics.
---

# GA4 Analytics Report Generator

Generate on-demand analytics reports for KStoryBridge dashboard using GA4 MCP tools.

## Commands

```
/analytics daily      # Yesterday's summary (5-min read)
/analytics weekly     # Weekly deep-dive with trends
/analytics funnel     # Trial to signup conversion analysis
/analytics sources    # Traffic sources breakdown (30 days)
/analytics realtime   # Current active users
```

## GA4 Property

- **Property ID**: 496541587
- **Measurement ID**: G-DWL6MV0MC2
- **Timezone**: America/Los_Angeles

---

## Report Specifications

### `/analytics daily`

Generate a quick daily summary comparing yesterday to the day before.

**Queries to Run** (in parallel):

1. **Traffic Overview**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges:
    - {start_date: "yesterday", end_date: "yesterday", name: "Yesterday"}
    - {start_date: "2daysAgo", end_date: "2daysAgo", name: "DayBefore"}
  dimensions: ["date"]
  metrics: ["activeUsers", "newUsers", "sessions", "engagementRate", "averageSessionDuration", "bounceRate"]
```

2. **Traffic Sources** (top 5):
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "yesterday", end_date: "yesterday"}]
  dimensions: ["sessionSourceMedium"]
  metrics: ["sessions", "newUsers", "engagementRate"]
  limit: 5
  order_bys: [{metric: {metric_name: "sessions"}, desc: true}]
```

3. **Key Events**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "yesterday", end_date: "yesterday"}]
  dimensions: ["eventName"]
  metrics: ["eventCount"]
  order_bys: [{metric: {metric_name: "eventCount"}, desc: true}]
  limit: 20
```

**Output Format**:
```markdown
# KStoryBridge Daily Analytics - [DATE]

## Traffic Overview
| Metric | Yesterday | Day Before | Change |
|--------|-----------|------------|--------|
| Active Users | X | X | ±X% |
| New Users | X | X | ±X% |
| Sessions | X | X | ±X% |
| Engagement Rate | X% | X% | ±Xpp |

## Top Traffic Sources
| Source | Sessions | New Users |
|--------|----------|-----------|
| ... | ... | ... |

## Key Events
| Event | Count | Insight |
|-------|-------|---------|
| signup_completed | X | New signups |
| trial_page_view | X | Trial visitors |
| ... | ... | ... |

## Alerts
- [Flag if: traffic drop >20%, engagement <40%, zero signups]

## Insights
[Brief analysis and recommended actions]
```

---

### `/analytics weekly`

Generate comprehensive weekly analysis with trends.

**Queries to Run**:

1. **7-Day User Growth**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges:
    - {start_date: "7daysAgo", end_date: "yesterday", name: "ThisWeek"}
    - {start_date: "14daysAgo", end_date: "8daysAgo", name: "LastWeek"}
  dimensions: ["date"]
  metrics: ["activeUsers", "newUsers", "sessions", "engagementRate"]
  order_bys: [{dimension: {dimension_name: "date"}, desc: false}]
```

2. **Traffic Sources**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "7daysAgo", end_date: "yesterday"}]
  dimensions: ["sessionSourceMedium"]
  metrics: ["sessions", "newUsers", "engagementRate"]
  limit: 10
  order_bys: [{metric: {metric_name: "sessions"}, desc: true}]
```

3. **Landing Pages**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "7daysAgo", end_date: "yesterday"}]
  dimensions: ["landingPage"]
  metrics: ["sessions", "bounceRate", "engagementRate"]
  limit: 10
  order_bys: [{metric: {metric_name: "sessions"}, desc: true}]
```

4. **Key Events**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "7daysAgo", end_date: "yesterday"}]
  dimensions: ["eventName"]
  metrics: ["eventCount", "totalUsers"]
  dimension_filter:
    filter:
      field_name: "eventName"
      in_list_filter:
        values: ["signup_completed", "signin", "trial_page_view", "trial_tool_selected",
                 "trial_limit_reached", "trial_signup_cta_clicked", "chat_message_sent",
                 "comps_search", "mandate_search_submitted", "checkout_started",
                 "checkout_completed", "favorite_added"]
        case_sensitive: true
```

5. **Device Breakdown**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "7daysAgo", end_date: "yesterday"}]
  dimensions: ["deviceCategory"]
  metrics: ["activeUsers", "engagementRate"]
```

**Output Format**: Full weekly report with:
- Executive summary (2-3 sentences)
- Daily breakdown table with week-over-week comparison
- Traffic sources with engagement rates
- Landing page performance
- Tool usage (chat/comps/mandates events)
- Conversion funnel analysis
- Key insights and action items

---

### `/analytics funnel`

Analyze the trial-to-signup conversion funnel (last 30 days).

**Query**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "30daysAgo", end_date: "yesterday"}]
  dimensions: ["eventName"]
  metrics: ["eventCount", "totalUsers"]
  dimension_filter:
    filter:
      field_name: "eventName"
      in_list_filter:
        values: ["trial_page_view", "trial_tool_selected", "trial_comps_search",
                 "trial_mandate_search", "trial_chat_message_sent", "trial_search_completed",
                 "trial_limit_reached", "trial_signup_cta_clicked", "signup_completed",
                 "signin", "chat_message_sent", "comps_search", "mandate_search_submitted",
                 "checkout_started", "checkout_completed"]
        case_sensitive: true
```

**Output Format**:
```
Trial Funnel (Last 30 Days)
===========================

Step 1: Trial Page View          [XXX] 100%
           ↓ (XX% continue)
Step 2: Tool Selected            [XXX]  XX%
           ↓ (XX% continue)
Step 3: Search Completed         [XXX]  XX%
           ↓ (XX% continue)
Step 4: Limit Reached            [XXX]  XX%
           ↓ (XX% continue)
Step 5: Signup CTA Clicked       [XXX]  XX%
           ↓ (XX% continue)
Step 6: Signup Completed         [XXX]  XX%

Benchmarks:
- Trial → Signup target: >15% (Actual: XX%)
- Tool Selection target: >70% (Actual: XX%)

Recommendations:
- [Based on drop-off analysis]
```

---

### `/analytics sources`

Deep dive into traffic sources (last 30 days).

**Query**:
```
mcp__analytics-mcp__run_report:
  property_id: 496541587
  date_ranges: [{start_date: "30daysAgo", end_date: "yesterday"}]
  dimensions: ["sessionSourceMedium"]
  metrics: ["sessions", "newUsers", "engagementRate", "bounceRate"]
  limit: 20
  order_bys: [{metric: {metric_name: "sessions"}, desc: true}]
```

**Output Format**:
```
Traffic Sources (Last 30 Days)
==============================

| Source/Medium | Sessions | New Users | Engagement | Bounce |
|---------------|----------|-----------|------------|--------|
| direct/(none) | XXX | XXX | XX% | XX% |
| google/organic| XXX | XXX | XX% | XX% |
| ... | ... | ... | ... | ... |

Quality Analysis:
- Best engagement: [source] at XX%
- Most new users: [source] with XXX
- Highest bounce: [source] at XX% (investigate)

Recommendations:
- [Based on source quality]
```

---

### `/analytics realtime`

Show current active users.

**Query**:
```
mcp__analytics-mcp__run_realtime_report:
  property_id: 496541587
  dimensions: ["unifiedScreenName"]
  metrics: ["activeUsers"]
```

**Output Format**:
```
Realtime Activity
=================

Active Users: X

Current Pages:
- /trial: X users
- /buyers/chat: X users
- /buyers/home: X users
```

---

## Key Metrics Reference

### Targets & Alerts

| Metric | Target | Alert If |
|--------|--------|----------|
| New Users (daily) | Trending up | -20% vs yesterday |
| Trial → Signup | >15% | <10% |
| Engagement Rate | >50% | <40% |
| Bounce Rate | <50% | >60% |

### Funnel Benchmarks

```
Trial Visit → Tool Selection: >70%
Tool Selection → Search: >80%
Search → Limit Reached: >60%
Limit → Signup CTA: >30%
CTA → Signup Complete: >50%
Overall Trial → Signup: >15%
```

### Key Events

| Event | Meaning |
|-------|---------|
| `trial_page_view` | User visited trial page |
| `trial_tool_selected` | User clicked on a tool (chat/comps/mandates) |
| `trial_signup_cta_clicked` | User clicked signup from trial |
| `signup_completed` | User completed registration |
| `chat_message_sent` | User sent a chat message |
| `comps_search` | User searched in Comps Navigator |
| `mandate_search_submitted` | User searched with a mandate |
| `checkout_started` | User started checkout |
| `checkout_completed` | User completed purchase ($250) |

---

## Email Delivery (Required)

**IMPORTANT**: After generating ANY report, you MUST send it via email to all admins.

### How to Send

After the report is generated and displayed to the user, call the `send-analytics-report` edge function:

```bash
curl -X POST "https://dlrnrgcoguxlkkcitlpd.supabase.co/functions/v1/send-analytics-report" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRscm5yZ2NvZ3V4bGtrY2l0bHBkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjA4NTM3NzMsImV4cCI6MjAzNjQyOTc3M30.y0KTfJlcWRLLKsJMqSjDLMsohDX7KLByQK2xwzwMHaE" \
  -H "Content-Type: application/json" \
  -d '{
    "reportType": "daily",
    "reportDate": "January 7, 2026",
    "reportMarkdown": "[FULL REPORT MARKDOWN HERE]",
    "alerts": ["Traffic drop >20%: -55%", "Zero signups detected"],
    "sendSlack": true
  }'
```

### Payload Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reportType` | string | Yes | One of: `daily`, `weekly`, `funnel`, `sources`, `realtime` |
| `reportDate` | string | Yes | Human-readable date, e.g., "January 7, 2026" |
| `reportMarkdown` | string | Yes | The full markdown report (will be converted to HTML) |
| `alerts` | string[] | No | Array of triggered alert messages |
| `sendSlack` | boolean | No | Send Slack notification (default: true) |

### What Happens

1. Edge function queries `admin` table for all active admins
2. Converts markdown to styled HTML email (KStoryBridge brand)
3. Sends email to each admin (500ms delay between sends for rate limiting)
4. Sends Slack notification with summary and alerts
5. Returns success/failure status

### Response

```json
{
  "success": true,
  "results": {
    "emailsSent": 2,
    "emailsFailed": 0,
    "slackSent": true
  }
}
```

### After Sending

Confirm to user: "Report sent to X admin(s) via email and Slack."

---

## Related Skills

- `/health-check` - Verify system health before running analytics
- `/cost-report` - Track API costs alongside traffic
- `/deploy-staging` - Deploy changes based on analytics insights
