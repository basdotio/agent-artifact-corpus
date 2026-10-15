# TODO: Policy-Based Auto-Approval

**Problem:** Manual approval doesn't scale. At 10,000 actions/day, no human can review each.

**Solution:** Pre-set policy rules. Auto-approve if action matches, queue for human only if unmatched.

**Rule categories:**
- AUTO: emails < $500, read-only queries, report generation, file reads, cert issuance < $1
- HUMAN: new outreach, payments > $1, external paid APIs, contract signing, file deletion, PII access

**Estimated reduction:** ~95% auto-approved, ~5% human review (20x reduction in queue size).

**Priority:** LOW. Build when volume demands it (after 1,000 actions/day).

**Saved:** 2026-09-28
