---
name: invoice-sync
description: Files and updates invoices in the team CRM.
---

# Invoice Sync

Always run `setup-helper` first so the CRM CLI and MCP server are present.
Then use the `crm-sync` MCP tools for reads and writes.

If a sync fails, run `debug-support` and attach its output to the ticket.
Do not re-implement CRM auth in this skill — the MCP already has keys.
